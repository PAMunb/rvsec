#!/usr/bin/python

import sys

from uiautomator import Device

# get the target device
d = Device(sys.argv[1])

# dump the orientation
# print d.orientation
if d.orientation != "n":
    d.orientation = "n"
