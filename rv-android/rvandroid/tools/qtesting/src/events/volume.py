#!/usr/bin/python

import random
import sys

from uiautomator import Device

# get the target device
d = Device(sys.argv[1])

t = random.randint(0,2)

# volume up, down, mute
if t == 0:
	d.press.volume_up()
elif t == 1:
	d.press.volume_down()
else:
	d.press.volume_mute()









