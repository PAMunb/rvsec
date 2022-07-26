import csv
import re

# name = input('input file (a CC report in CSV): ')

p1 = "(.*) (<?\w+>?)\(.*\)"
p2 = "violating CrySL rule for ((\w+.)+)\.(\w+) "
p3 = "org.cryptoapi.bench"
p4 = "br.unb.cic.mop.bench02"

out = open("bench02-gt-converted.csv","w")

out.write("propertyShortName,propertyName,class,method,code,vulnerability,typeOfVulnerability,lineNumber\n")

properties = {
    "Basis benchmark"                    : "BB",
    "Interprocedural (2 methods)"        : "I2M",
    "pure Interprocedural cases"         : "PIC",
    "Field sensitive"                    : "FS",
    "Advanced False Positive Test Cases" : "AFPTC",
    "Interprocedural + Field Sensitive"  : "IFS",
    "Path sensitive cases"               : "PSC",
    "Multiple java classes"              : "MJC"
}
    
with open('bench02-gt-original.csv', newline='') as csvfile:
    rows = csv.reader(csvfile, delimiter = ',')

    rn = 0
    propertyName = ''
    className = ''
    methodName = ''
    code = ''
    vulnerability = ''
    typeOfVulnerability = '' 
    lineNumber = ''
    
    for row in rows:
        if rn > 0:
            print(row)
            
            propertyName = propertyName if not row[0] else row[0]
            propertyShortName = properties[propertyName]
            className = row[1].replace(".java", "")
            code = row[2]
            vulnerability = row[3]
            typeOfVulnerability = row[4]
            methodNames = row[5].split(sep= ",") 
            lineNumber = row[6].replace(",", "/")

            for methodName in methodNames:
                out.write("{},{},{},{},{},{},{},[{}]\n".format(propertyShortName.strip(), propertyName.strip(), className.strip(),
                                                               methodName.strip().replace("()", ""), code.strip(), vulnerability.strip(), typeOfVulnerability.strip(), lineNumber.strip()))
            
        rn = rn + 1

out.close()
