#!/usr/bin/python

import sys

from uiautomator import Device

# get the target device
d = Device(sys.argv[1])

# check whether the text exists
if d(text=sys.argv[2]).exists:
	d(text=sys.argv[2]).long_click()







