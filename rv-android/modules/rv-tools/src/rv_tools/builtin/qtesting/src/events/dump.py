#!/usr/bin/python

import sys

from uiautomator import Device

# get the target device
d = Device(sys.argv[1])

# dump ui xml
d.dump(sys.argv[2])









