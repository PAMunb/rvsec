#!/usr/bin/python

import random
import sys

from uiautomator import Device

# get the target device
d = Device(sys.argv[1])

inputs = ["l", "r", "n"]

# dump the orientation
# print d.orientation

d.orientation = inputs[random.randint(0, 2)]
# d.orientation = "r"
