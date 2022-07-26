import json
import re

# name = input('input file (a CC report in CSV): ')

p1 = "(.*) (<?\w+>?)\(.*\)"
p2 = "violating CrySL rule for ((\w+.)+)\.(\w+) "
p3 = "org.cryptoapi.bench"
p4 = "br.unb.cic.mop.bench02"

out = open("cg-report-converted.csv","w")

out.write("spec,error,class,className,method\n")

with open("cg-report.json", "r") as read_file:
    data = json.load(read_file)

    issues = data["Issues"]

    for issue in issues:
        fullPath = issue["_FullPath"]
        className = fullPath[fullPath.rfind('/')+1:].replace(".class", "")
        out.write("{},{},{},{},{}\n".format(issue["RuleNumber"], issue["Message"], className, className, "-"))


out.close()
