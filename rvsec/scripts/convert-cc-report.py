import csv
import re

# name = input('input file (a CC report in CSV): ')

p1 = "(.*) (<?\w+>?)\(.*\)"
p2 = "violating CrySL rule for ((\w+.)+)\.(\w+) "
p3 = "org.cryptoapi.bench"
p4 = "br.unb.cic.mop.bench02"

out = open("cc-report-converted.csv","w")

out.write("spec,error,class,className,method\n")

with open('cc-report.csv', newline='') as csvfile:
    rows = csv.reader(csvfile, delimiter = ';')

    rn = 0
    for row in rows:
        if rn > 0:
            err = row[0]
            clasz = row[1].replace(p3, p4)
            className = clasz[clasz.rfind(".")+1:]
            method = row[2]
            rule = row[3]

            res1 = re.match(p1, method)
            res2 = re.match(p2, rule)

            out.write("{},{},{},{},{}\n".format(res2.group(3) + "Spec", err, clasz, className, res1.group(2)))
            
        rn = rn + 1

out.close()
