#!/usr/bin/python3

# Author: Luca Piccolboni (piccolboni@cs.columbia.edu)
# This script checks if some cryptographic rules are violated or not.

import os
import re
import sys
import time
import zxcvbn
import binascii
import argparse
import traceback
import subprocess
import shutil
import logging


###############################################################################
# Common functions
###############################################################################
def run_cmd(cmd):
    split = cmd.split(" ")

    try:
        # Return the full standard output
        return subprocess.check_output(split, stderr=subprocess.STDOUT).decode("utf-8")
    except subprocess.CalledProcessError as e:
        print(e.output.decode("utf-8"))
        # Just return an error string
        return str("Error")


def is_hex(s):
    try:
        int(s, 16)
        return True
    except ValueError:
        return False


###############################################################################
# Print Utilities
###############################################################################

def print_verbose(args, message):
    if args.verbose:
        args.out_file.write(message)


def print_start(args):
    print_verbose(args, args.current_rule + "\n")


def print_result(args, fail):
    if fail == 0:
        args.out_file.write(args.current_rule + ": RESPECTED\n")
    elif fail == 1:
        args.out_file.write(args.current_rule + ": VIOLATED\n")
    else:  # fail == -1
        args.out_file.write(args.current_rule + ": SKIPPED\n")

    return fail


def write_misuse(error_text, args):
    args.rvsec_file.write(args.current_rule + " ### "+ error_text+"\n")


###############################################################################
# Search Utilities
###############################################################################
def search_string_in_file(string, content, start=0):
    pos = content.lower().find(string.lower(), start)
    if pos == -1:
        return 0
    return pos


def search_regexp_in_file(reg, content, start=0):
    pattern = re.compile(reg.lower())
    return pattern.search(content.lower(), start)


def collect_all_values_with_position(string, content, hexa=False):
    start = 0
    res = set()

    pos1 = search_string_in_file(string, content, start)
    while pos1:
        pos2 = search_string_in_file("\n", content, pos1)        

        value = content[pos1 + len(string): pos2]
        #remove the stacktrace, to get only the value
        stacktrace_separator_position = value.find("::")
        value = value[0 : stacktrace_separator_position].strip()
                
        if value == "null":
            start = pos2 + 1
            pos1 = search_string_in_file(string, content, start)
            continue
        
        if hexa:
            try:
                conv = int(value.strip(), 16)
                res.add((pos1,value.strip()))
                #res.add((pos1,conv))
            except ValueError as e:
                # insert only hexadecimal string
                pass
        else:
            res.add((pos1,value.strip()))

        start = pos2 + 1
        pos1 = search_string_in_file(string, content, start)

    return res


def collect_all_values_regexp_with_position(exp, content):
    start = 0
    res = set()

    pos1 = search_regexp_in_file(exp, content, start)
    while pos1:
        string = pos1.group(0)

        pos2 = search_string_in_file("\n", content, pos1.start(0))

        value = content[pos1.start(0) + len(string): pos2]
        #remove the stacktrace, to get only the value
        stacktrace_separator_position = value.find("::")
        value = value[0 : stacktrace_separator_position].strip()
        res.add((pos1.start(0),value))
        start = pos2 + 1
        pos1 = search_regexp_in_file(exp, content, start)

    return res


def collect_all_duplicated_values_with_position(string, content):
    start = 0
    seen = set()
    dupl = set()

    pos1 = search_string_in_file(string, content, start)
    while pos1:
        pos2 = search_string_in_file("\n", content, pos1)
        if pos2 == 0:
            break

        value = content[pos1 + len(string): pos2].strip()
        #remove the stacktrace, to get only the value
        stacktrace_separator_position = value.find("::")
        value = value[0 : stacktrace_separator_position].strip()
        if value in seen:
            dupl.add((pos1,value))

        seen.add(value)
        
        start = pos2 + 1
        pos1 = search_string_in_file(string, content, start)

    return dupl


def collect_all_duplicate_pairs_with_position(string1, string2, content):
    start = 0
    seen = set()
    dupl = set()

    pos1 = search_string_in_file(string1, content, start)
    while pos1:
        pos2 = search_string_in_file("::", content, pos1)

        pos3 = search_string_in_file(string2, content, pos2)
        if pos3 == 0:
            break

        pos4 = search_string_in_file("::", content, pos3)
        pos_end = search_string_in_file("\n", content, pos3)

        val1 = content[pos1 + len(string1): pos2].strip()
        val2 = content[pos3 + len(string2): pos4].strip()

        if (val1, val2) in seen:
            dupl.add((pos1, val1, val2))

        seen.add((val1, val2))
        start = pos_end + 1
        pos1 = search_string_in_file(string1, content, start)

    return dupl


###############################################################################
# Random tests
###############################################################################
def random_tests(bitset):

    test_failed = 0
    test_passed = 0

    f = open("hexstream.bin", "wb")
    for b in bitset:
        string = str(b)
        print(string)
        print(type(string))
        if is_hex(string):
            #f.write(binascii.unhexlify(string))
            f.write(string)
    f.close()

    summary_found = False
    output = run_cmd("python random-tests/sp800_22_tests.py hexstream.bin")
    for line in output.split("\n"):

        if "SUMMARY" in line:
            summary_found = True

        if summary_found:
            if "PASS" in line:
                test_passed = test_passed + 1
            else:  # FAIL
                test_failed = test_failed + 1

    os.remove("hexstream.bin")
    return (test_passed, test_failed)


def getUtilRandom(content):

    start = 0
    random = set()
    str1 = "[Random] next bytes: "

    while True:

        pos1 = search_string_in_file(str1, content, start)

        if pos1 == 0:
            break

        pos2 = search_string_in_file("\n", content, pos1)

        if pos2 == 0:
            break

        random.add(content[pos1 + len(str1): pos2].strip())

        start = pos2 + 1

    return random


def getSecureRandom(content):

    start = 0
    random = set()
    str1 = "[SecureRandom] next bytes: "

    while True:

        pos1 = search_string_in_file(str1, content, start)

        if pos1 == 0:
            break

        pos2 = search_string_in_file("\n", content, pos1)

        if pos2 == 0:
            break

        random.add(content[pos1 + len(str1): pos2].strip())

        start = pos2 + 1

    return random


###############################################################################
# custom
###############################################################################
def get_content(text, pos):
    newline_position = text.find("\n",pos)
    return text[pos : newline_position]    


def insert_text_before_stacktrace(text_to_insert, text):
    stacktrace_separator_position = text.find("::")
    return text[:stacktrace_separator_position] + text_to_insert + text[stacktrace_separator_position:]


def search_string(text_to_search, args):
    fail = search_string_util(text_to_search, args.in1_content, args)    

    if args.in2_content is not None:
        result = search_string_util(text_to_search, args.in2_content, args)  
        if result == 1:
            fail = 1
    
    return fail


def search_string_util(text_to_search, content, args):
    fail = 0
    
    pos = search_string_in_file(text_to_search, content)
    while pos: # != 0:               
        write_misuse(get_content(content,pos), args)                         
        pos = search_string_in_file(text_to_search, content, pos+len(text_to_search))
        fail = 1
    
    return fail


def search_regex(text_to_search, args):
    fail = search_regex_util(text_to_search,args.in1_content,args)

    if args.in2_content is not None:
        fail = search_regex_util(text_to_search,args.in2_content,args)
    
    return fail


def search_regex_util(text_to_search, content, args):
    fail = 0
    
    match = search_regexp_in_file(text_to_search, content)
    while match:   
        pos = match.start()        
        write_misuse(get_content(content,pos), args)                         
        match = search_regexp_in_file(text_to_search, content, pos+len(text_to_search))
        fail = 1
    
    return fail


def search_values_intersection(text_to_search, args):
    fail = 0

    if args.in2_content is None:
        return -1
    
    tuples1 = collect_all_values_with_position(text_to_search, args.in1_content)
    tuples2 = collect_all_values_with_position(text_to_search, args.in2_content)
    
    intersect = [ (x,y) for x, y in tuples1 if any([(x2,y2) for x2, y2 in tuples2 if y == y2])]
    for tuple in intersect:
        write_misuse(get_content(args.in1_content,tuple[0]), args)
        fail = 1
        
    return fail


def contains_value(value, tuples):
    tmp = [ (x,y) for x, y in tuples if y == value ]
    
    if tmp:
        return True
    return False
    

###############################################################################
# Rule R-01
###############################################################################
insecure_hash_functions = ["MD2", "MD-2",
                           "MD4", "MD-4",
                           "MD5", "MD-5",
                           "SHA1", "SHA-1"]


def check_rule_R01(args):
    
    # Don't use insecure hash (e.g., MD2, MD4, SHA-1)

    fail = 0
    prefix = "[MessageDigest] algorithm: "

    for h in insecure_hash_functions:
        text_to_search = prefix + h
    
        result = search_string(text_to_search, args)
        if result == 1:
            fail = 1

    return print_result(args, fail)


###############################################################################
# Rule R-02
###############################################################################
insecure_symm_encryption_functions = ["RC2", "RC-2",
                                      "RC4", "RC-4",
                                      "RC5", "RC-5",
                                      "DES", "DESede",
                                      "Blowfish", "IDEA",
                                      "3-KeyTripleDES"]

def check_rule_R02(args):

    # Don't use insecure algorithms (e.g., RC2, RC4, IDEA, ..)

    prefix = "[Cipher] algorithm: "
    reg1 = "\[Cipher\] algorithm: PBEWith"

    fail = check_rule_R02_insecure_hash_functions(reg1, args)

    # AES without operation mode (insecure)
    result = check_rule_R02_operation_mode(args)
    if result == 1:
        fail = 1

    for func in insecure_symm_encryption_functions:
        text_to_search = prefix + func   
             
        pos = search_string_in_file(text_to_search, args.in1_content)
        while pos:
            print_verbose(args, "\t Encr " + func + "\n")
            write_misuse(get_content(args.in1_content,pos), args)
            pos = search_string_in_file(text_to_search, args.in1_content, pos+len(text_to_search))
            fail = 1

        if args.in2_content is not None:
            re_to_search = reg1 + ".*" + func
            match = search_regexp_in_file(re_to_search, args.in2_content)
            while match:
                print_verbose(args, "\t Hash " + func + "\n")
                write_misuse(get_content(args.in2_content,match.start()), args)
                match = search_regexp_in_file(re_to_search, args.in2_content, match.start()+len(re_to_search))
                fail = 1

    return print_result(args, fail)


def check_rule_R02_insecure_hash_functions(reg1, args):
    fail = 0
    for func in insecure_hash_functions:
        re_to_search = reg1 + func 
        fail = check_rule_R02_search_regex(re_to_search, args.in1_content, args)

        if args.in2_content is not None:
            result = check_rule_R02_search_regex(re_to_search, args.in2_content, args)
            if result == 1:
                fail = 1
    return fail
    

def check_rule_R02_search_regex(re_to_search, content, args):
    fail = 0
    match = search_regexp_in_file(re_to_search + ".*", content)        
    while match:
        write_misuse(get_content(content,match.start()), args)
        match = search_regexp_in_file(re_to_search + ".*", content, match.start()+len(re_to_search))
        fail = 1
    return fail


def check_rule_R02_operation_mode(args):
    fail = check_rule_R02_operation_mode_util(args.in1_content, args)
    if args.in2_content is not None:
        # AES without operation mode (insecure)
        result = check_rule_R02_operation_mode_util(args.in2_content, args)
        if result == 1:
            fail = 1
    return fail
        
    
def check_rule_R02_operation_mode_util(content, args):
    fail = 0
    prefix = "[Cipher] algorithm: "
    tuples = collect_all_values_with_position(prefix + "AES", content)
    for t in tuples:
        position = t[0]
        alg = t[1]
        stacktrace_separator_position = alg.find("::")
        alg_value = alg[0 : stacktrace_separator_position].strip()
        if alg_value == "":
            text = get_content(content,position)
            stacktrace_separator_position = text.find("::")
            text = text[:stacktrace_separator_position] + "- Encr AES missing mode " + text[stacktrace_separator_position:]
            write_misuse(text, args)
            fail = 1
    return fail


###############################################################################
# Rule R-03
###############################################################################
def check_rule_R03(args):

    # Don't use the operation mode ECB with > 1 block

    fail = check_rule_R03_util(args.in1_content, args)

    if args.in2_content is not None:        
        result = check_rule_R03_util(args.in2_content, args)
        if result == 1:
            fail = 1

    return print_result(args, fail)


def check_rule_R03_util(content, args):
    fail = 0
    str1 = "[Cipher] out bytes: "
    str2 = " with "
    str3 = "ECB"
    start = 0
    
    pos1 = search_string_in_file(str1, content, start)
    while pos1:        
        pos2 = search_string_in_file(str2, content, pos1)
        pos3 = search_string_in_file("::", content, pos2)

        if search_string_in_file(str3, content[pos1: pos3]):
            fin_bytes = content[pos1 + len(str1): pos2].strip()
            if int(fin_bytes) > 16:
                print_verbose(args, "\t ECB bytes: " + fin_bytes + "\n")
                write_misuse(get_content(content,pos1), args)
                fail = 1

        start = pos3 + 1
        pos1 = search_string_in_file(str1, content, start)
        
    return fail

###############################################################################
# Rule R-04
###############################################################################
def check_rule_R04(args):

    # Don't use the operation mode CBC if AES is used

    text_to_search = "[Cipher] algorithm: AES/CBC/"
    
    fail = search_string(text_to_search, args)

    return print_result(args, fail)


###############################################################################
# Rule R-05
###############################################################################
def check_rule_R05(args):

    # Don't use a static (constant) key for encryption

    text_to_search = "[Cipher] key.encoded: "

    fail = search_values_intersection(text_to_search, args)

    return print_result(args, fail)


###############################################################################
# Rule R-06
###############################################################################
def check_rule_R06(args):
    
    #TODO review random tests ... commented for now ... same to rule 08

    # Don't use a 'badly-derived' key for encryption
    
    fail = check_rule_R06_util(args.in1_content, args)

    if args.in2_content is not None:
        result = check_rule_R06_util(args.in2_content, args)
        if result == 1:
            fail = 1

    return print_result(args, fail)


def check_rule_R06_util(content, args):
    str1 = "[Random] next: "
    str2 = "[SecureRandom] next: "
    str3 = "[Cipher] key.encoded: "

    return check_rule_R06_R08(str1, str2, str3, content, args)


def check_rule_R06_R08(str1, str2, str3, content, args):
    fail = 0
    
    badvaluestuples = collect_all_values_with_position(str1, content, True)
    #goodvaluestuples = collect_all_values_with_position(str2, content, True)
    keyvaluestuples = collect_all_values_with_position(str3, content, True)

    #potbadkeys = set()

    for t in keyvaluestuples:
        key = t[1]
        
        if contains_value(key,badvaluestuples):
            write_misuse(get_content(content,t[0]), args)
            fail = 1
        
        #if not contains_value(key,goodvaluestuples):
        #    potbadkeys.add(key)

    #if not fail and potbadkeys:
    #    passed, failed = random_tests(potbadkeys)
    #    print_verbose(args, "\t Tests failed: " + str(failed) + "\n")
    #    print_verbose(args, "\t Tests passed: " + str(passed) + "\n")
    #    if failed > 0:
    #        fail = 1
    
    return fail


###############################################################################
# Rule R-07
###############################################################################
def check_rule_R07(args):

    # Don't use a static (constant) initialization vector

    text_to_search = "[Cipher] key.iv: "
    
    fail = search_values_intersection(text_to_search, args)

    return print_result(args, fail)


###############################################################################
# Rule R-08
###############################################################################
def check_rule_R08(args):

    # Don't use a 'badly-derived' iv for encryption
    
    fail = check_rule_R08_util(args.in1_content, args)

    if args.in2_content is not None:
        result = check_rule_R08_util(args.in2_content, args)
        if result == 1:
            fail = 1

    return print_result(args, fail)


def check_rule_R08_util(content, args):
    str1 = "[Random] next: "
    str2 = "[SecureRandom] next: "
    str3 = "[Cipher] key.iv: "

    return check_rule_R06_R08(str1, str2, str3, content, args)


###############################################################################
# Rule R-09
###############################################################################
def check_rule_R09(args):

    # Don't reuse the initialization vector and key pairs

    fail = check_rule_R09_util(args.in1_content, args)

    if args.in2_content is not None:
        result = check_rule_R09_util(args.in2_content, args)
        if result == 1:
            fail = 1

    return print_result(args, fail)


def check_rule_R09_util(content, args):
    fail = 0
    str1 = "[Cipher] key.iv: "
    str2 = "[Cipher] key.encoded: "

    dupl = collect_all_duplicate_pairs_with_position(str1, str2, content)

    for d in dupl:
        position = d[0]
        write_misuse(get_content(content,position), args)
        fail = 1
        
    return fail


###############################################################################
# Rule R-10
###############################################################################
def check_rule_R10(args):

    # Don't use a static (constant) salt for key derivation

    fail = 0
    str1 = "[PBEKeySpec] salt: "
    str2 = "[PBEParameterSpec] salt: "

    if args.in2_content is None:
        return print_result(args, -1)
    
    salt1a = collect_all_values_with_position(str1, args.in1_content)
    salt1b = collect_all_values_with_position(str2, args.in1_content)
    salt1a = salt1a.union(salt1b)
    
    salt2a = collect_all_values_with_position(str1, args.in2_content)
    salt2b = collect_all_values_with_position(str2, args.in2_content)
    salt2a = salt2a.union(salt2b)
    
    intersect = [ (x,y) for x, y in salt1a if any([(x2,y2) for x2, y2 in salt2a if y == y2])]
    for tuple in intersect:
        write_misuse(get_content(args.in1_content,tuple[0]), args)
        fail = 1

    return print_result(args, fail)


###############################################################################
# Rule R-11
###############################################################################
def check_rule_R11(args):

    # Don't use a short salt (< 64 bits) for key derivation

    fail = check_rule_R11_wrapper(args.in1_content, args)
    
    if args.in2_content is not None:
        result = check_rule_R11_wrapper(args.in2_content, args)
        if result == 1:
            fail = 1        

    return print_result(args, fail)

def check_rule_R11_wrapper(content, args):
    fail = 0
    
    str1 = "[PBEKeySpec] salt: "
    str2 = "[PBEParameterSpec] salt: "
    str3 = "[PBEKeySpec] PBEKeySpec(char[])"

    fail = check_rule_R11_util(str1, content, args)
    
    result = check_rule_R11_util(str2, content, args)
    if result == 1:
        fail = 1

    result = search_string_util(str3, content, args) 
    if result == 1:
        fail = 1
        
    return fail


def check_rule_R11_util(text_to_search, content, args):
    fail = 0

    tuples = collect_all_values_with_position(text_to_search, content)

    for t in tuples:
        position = t[0]
        salt = t[1]        
        logging.debug("salt="+salt)
        if len(salt.strip()) * 4 < 64:
            print_verbose(args, "\t Short salt: " + salt + "\n")
            write_misuse(get_content(content,position), args)
            fail = 1
        
    return fail


###############################################################################
# Rule R-12
###############################################################################
def check_rule_R12(args):

    # Don't use the salt for different purposes

    fail = check_rule_R12_util(args.in1_content, args)

    if args.in2_content is not None:
        result = check_rule_R12_util(args.in2_content, args)
        if result == 1:
            fail = 1

    return print_result(args, fail)


def check_rule_R12_util(content, args):
    fail = 0
    str1 = "[PBEKeySpec] salt: "
    str2 = "[PBEParameterSpec] salt: "

    dupl1 = collect_all_duplicated_values_with_position(str1, content)
    dupl2 = collect_all_duplicated_values_with_position(str2, content)
    dupl = dupl1.union(dupl2)

    for d in dupl:
        position = d[0]
        write_misuse(get_content(content,position), args)
        fail = 1
        
    return fail


###############################################################################
# Rule R-13
###############################################################################
def check_rule_R13(args):

    # Don't use < 1000 iterations for key derivation

    fail = check_rule_R13_wrapper(args.in1_content, args)
    
    if args.in2_content is not None:
        result = check_rule_R13_wrapper(args.in2_content, args)
        if result == 1:
            fail = 1        

    return print_result(args, fail)


def check_rule_R13_wrapper(content, args):
    fail = 0
    
    str1 = "[PBEKeySpec] iteration: "
    str2 = "[PBEParameterSpec] iteration: "
    str3 = "[PBEKeySpec] PBEKeySpec(char[])"

    fail = check_rule_R13_util(str1, content, args)
    
    result = check_rule_R13_util(str2, content, args)
    if result == 1:
        fail = 1

    result = search_string_util(str3, content, args) 
    if result == 1:
        fail = 1
        
    return fail


def check_rule_R13_util(text_to_search, content, args):
    fail = 0

    tuples = collect_all_values_with_position(text_to_search, content)

    for t in tuples:
        position = t[0]
        value = t[1]        
        if int(value) < 1000:
            print_verbose(args, "\t Iterations: " + value + "\n")
            write_misuse(get_content(content,position), args)
            fail = 1
        
    return fail


###############################################################################
# Rule R-14
###############################################################################
def check_rule_R14(args):
    
    # Don't use a weak password (score < 3) for PBE

    subnames = args.in_file_name1.split(".")
    
    fail = check_rule_R14_wrapper(args.in1_content, subnames, args)

    if args.in2_content is not None:
        result = check_rule_R14_wrapper(args.in2_content, subnames, args)
        if result == 1:
            fail = 1

    return print_result(args, fail)


def check_rule_R14_wrapper(content, subnames, args):
    fail = 0
    str1 = "[PBEKeySpec] password: "
    str2 = "[KeyStore] password: "

    fail = check_rule_R14_util(str1, content, subnames, args)
    
    result = check_rule_R14_util(str2, content, subnames, args)
    if result == 1:
        fail = 1
        
    return fail


def check_rule_R14_util(text_to_search, content, subnames, args):
    fail = 0

    tuples = collect_all_values_with_position(text_to_search, content)

    for t in tuples:
        position = t[0]
        password = t[1]        

        analysis_result = zxcvbn.zxcvbn(password)
        if int(analysis_result["score"]) < 3:
            print_verbose(args, "\t Weak: " + password + "\n")
            write_misuse(get_content(content,position), args)
            fail = 1

        for subname in subnames:
            if subname in password:
                print_verbose(args, "\t Weak: " + password + "\n")
                write_misuse(get_content(content,position), args)
                fail = 1
        
    return fail

###############################################################################
# Rule R-15
###############################################################################
def check_rule_R15(args):

    # Don't use NIST-black-listed passwords for PBE
    
    fail = check_rule_R15_util(args.in1_content, args)

    if args.in2_content is not None:
        result = check_rule_R15_util(args.in2_content, args)
        if result == 1:
            fail = 1        

    return print_result(args, fail)


def check_rule_R15_util(content, args):
    fail = 0
    str1 = "[PBEKeySpec] password: "
    str2 = "[KeyStore] password: "
    passwords = set()
    
    passwords1a = collect_all_values_with_position(str1, content)
    passwords1b = collect_all_values_with_position(str2, content)
    passwords = passwords.union(passwords1a)
    passwords = passwords.union(passwords1b)
    
    with open("./passwords/xato-net-10-million-passwords.txt") as passfile:

        pwned_passwords = passfile.read()

        for t in passwords:
            position = t[0]
            password = t[1]

            if password in pwned_passwords:
                print_verbose(args, "\t Broken: " + password + "\n")
                write_misuse(get_content(content,position), args)
                fail = 1
                
    return fail
    

###############################################################################
# Rule R-16
###############################################################################
def check_rule_R16(args):

    # Don't use a static (constant) password for PBE

    text_to_search = "[PBEKeySpec] password: "
    
    fail = search_values_intersection(text_to_search, args)

    return print_result(args, fail)


###############################################################################
# Rule R-17
###############################################################################
def check_rule_R17(args):

    # Don't use a static (constant) seed for PRNG

    text_to_search = "[SecureRandom] next: "
    
    fail = search_values_intersection(text_to_search, args)

    return print_result(args, fail)


###############################################################################
# Rule R-18
###############################################################################
def check_rule_R18(args):

    # Don't use insecure PRNG (java.util.Random)

    text_to_search = "[Random] Random() called"
    
    fail = search_string(text_to_search, args)

    return print_result(args, fail)


###############################################################################
# Rule R-19
###############################################################################
def check_rule_R19(args):

    # A1: Don't use a short key (< 2048 bits) for RSA
    
    fail = check_rule_R19_util(args.in1_content, args)

    if args.in2_content is not None:
        result = check_rule_R19_util(args.in2_content, args)
        if result == 1:
            fail = 1

    return print_result(args, fail)


def check_rule_R19_util(content, args):
    fail = 0
    exp1 = "\[Cipher\] key.bits \(RSA.*\): "
    exp2 = "\[Signature\] key.bits \(.*withRSA.*\): "
    
    allbits1 = collect_all_values_regexp_with_position(exp1, content)
    allbits2 = collect_all_values_regexp_with_position(exp2, content)
    allbits = allbits1.union(allbits2)

    for t in allbits:
        bits = t[1]
        if int(bits) < 2048:
            write_misuse(get_content(content,t[0]), args)  
            fail = 1
            
    return fail
    

###############################################################################
# Rule R-20
###############################################################################
def check_rule_R20(args):

    # Don't use the textbook (raw) algorithm for RSA

    re_to_search = ".*RSA/.*/NoPadding"
    
    fail = search_regex(re_to_search, args)

    return print_result(args, fail)


###############################################################################
# Rule R-21
###############################################################################
def check_rule_R21(args):

    # Don't use the padding PKCS1Padding for RSA

    re_to_search = ".*RSA/.*/PKCS1Padding"
    
    fail = search_regex(re_to_search, args)

    return print_result(args, fail)


###############################################################################
# Rule R-22
###############################################################################
def check_rule_R22(args):

    text_to_search = "[URL] protocol: http:"
    
    fail = search_string(text_to_search, args)    

    return print_result(args, fail)


###############################################################################
# Rule R-23
###############################################################################
def check_rule_R23(args):

    # Don't use a static (constant) password for KeyStore

    text_to_search = "[KeyStore] password: "
    
    fail = search_values_intersection(text_to_search, args)

    return print_result(args, fail)


###############################################################################
# Rule R-24
###############################################################################
def check_rule_R24(args):

    # Don't verify the hostname for SSL connections

    text_to_search = "[HttpsURLConnection] dummyverifier: true"
    
    fail = search_string(text_to_search, args)

    return print_result(args, fail)


###############################################################################
# Rule R-25
###############################################################################
def check_rule_R25(args):

    # Don't verify certificates for SSL connections

    str1 = "[SSLContext] dummy checkClient: true"
    str2 = "[SSLContext] dummy checkServer: true"
    str3 = "[SSLContext] dummy acceptedIssuers: true"
    
    fail = search_string(str1, args)

    result = search_string(str2, args)
    if result == 1:
        fail = 1
        
    result = search_string(str3, args)
    if result == 1:
        fail = 1

    return print_result(args, fail)


###############################################################################
# Rule R-26
###############################################################################
def check_rule_R26(args):

    # Don't verify hostnames for SSL connections

    fail = check_rule_R26_util(args.in1_content, args)
   
    if args.in2_content is not None and not fail:
        result = check_rule_R26_util(args.in2_content, args)
        if result == 1:
            fail = 1

    return print_result(args, fail)

    
def check_rule_R26_util(content, args):
    fail = 0
    str1 = "[SSLSocketFactory] getDefault() called"
    str2 = "[HttpsURLConnection] getHostnameVerifier() called"
    str3 = "[HttpsURLConnection] getDefaultHostnameVerifier() called"
    
    positions = check_rule_R26_search_string(str1, content)
    if positions:
        fail = 1

    if check_rule_R26_search_string(str2, content):
        fail = 0

    if check_rule_R26_search_string(str3, content):
        fail = 0
        
    if fail == 1:
        for pos in positions:
            write_misuse(get_content(content,pos), args)  
            
    return fail   
                
                
def check_rule_R26_search_string(text_to_search, content):
    positions = []
    
    pos = search_string_in_file(text_to_search, content)
    while pos:             
        positions.append(pos)                       
        pos = search_string_in_file(text_to_search, content, pos+len(text_to_search))
    
    return positions


###############################################################################
# Argument parser
###############################################################################
def get_parser():

    parser = argparse.ArgumentParser(prog="check")

    parser.add_argument("--work_dir", required=True, metavar="<path>",
                        help="the directory containing the crypto logs")
    parser.add_argument("--rule_id", required=False, metavar="<id>",
                        help="check only the rule specified by its ID")
    parser.add_argument("--verbose", required=False, action="store_true",
                        help="print additional information about rules")

    return parser


###############################################################################
# Main
###############################################################################
def main():
    
    logging.basicConfig(level=logging.INFO)

    start = time.time()
    
    parser = get_parser()
    args = parser.parse_args()

    args.work_dir = os.path.abspath(args.work_dir)

    for log_name in os.listdir(args.work_dir):

        if log_name.endswith("cryptolog"):        
            logging.info('Checking file: '+log_name)
            args.in_file_name1 = os.path.join(args.work_dir, log_name + "")
            args.in_file_name2 = os.path.join(args.work_dir, log_name + "2")
            out_file_name = os.path.abspath(args.in_file_name1[:-9] + "rules")
            rvsec_out_file_name = os.path.abspath(args.in_file_name1[:-9] + "rvsec")

            # Input file 1
            in1_file = open(args.in_file_name1, "r")
            args.in1_content = in1_file.read()
            in1_file.close()

            # Input file 2
            args.in2_content = None
            if os.path.exists(args.in_file_name2):
                in2_file = open(args.in_file_name2, "r")
                args.in2_content = in2_file.read()
                in2_file.close()

            # Output files
            args.out_file = open(out_file_name, "w")
            args.rvsec_file = open(rvsec_out_file_name, "w")
            
            args.current_rule = ""

            if args.rule_id:
                rule = "rule_R" + args.rule_id
                method_name = "check_" + rule
                args.current_rule = rule
                logging.info("Checking rule: "+args.rule_id)
                print_start(args)
                globals()[method_name](args)  # calls check
            else:
                for i in range(1,27):                    
                    value = "{:02d}".format(i)
                    rule = "rule_R" + value
                    method_name = "check_" + rule
                    args.current_rule = rule
                    #logging.info("Checking rule: "+value)
                    print_start(args)
                    method_start = time.time()
                    globals()[method_name](args)
                    method_end = time.time()
                    logging.info(f"Checked rule: {value}\t {(method_end-method_start):.03f}s")                  

            print("Violations reported in " + out_file_name)
            print("Violations (with positions) reported in " + rvsec_out_file_name)
            args.out_file.close()
            args.rvsec_file.close()
    
    end = time.time()
    logging.info(f"Total time: {(end-start):.03f}s")


if __name__ == "__main__":
    main()
