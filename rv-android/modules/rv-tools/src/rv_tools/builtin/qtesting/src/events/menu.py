#!/usr/bin/python

import sys

from uiautomator import Device

# get the target device
d = Device(sys.argv[1])

# press the menu
d.press.menu()
