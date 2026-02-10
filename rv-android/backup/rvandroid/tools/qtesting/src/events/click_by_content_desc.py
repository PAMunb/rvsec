#!/usr/bin/python

import sys

from uiautomator import Device

# get the target device
d = Device(sys.argv[1])

# check whether the description exists
if d(description=sys.argv[2]).exists:
    print(('click by content-desc is activated and the content-desc is ' + str(sys.argv[2])))
    d(description=sys.argv[2]).click()
