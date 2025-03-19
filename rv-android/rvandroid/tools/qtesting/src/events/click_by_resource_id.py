#!/usr/bin/python

import sys

from uiautomator import Device

# get the target device
d = Device(sys.argv[1])

# check whether the resourceId exists
if d(resourceId=sys.argv[2]).exists:
	d(resourceId=sys.argv[2]).click()







