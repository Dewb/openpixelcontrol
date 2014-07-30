#!/usr/bin/env python
import time
import random
import opc

ADDRESS = '10.42.0.42:7890'

client = opc.Client(ADDRESS)

my_pixels = [(255, 0, 0), (0, 255, 0), (0, 255, 0), (0, 255, 0), (0, 255, 0)]
while True:
    my_pixels.append(my_pixels.pop(0))    
    client.put_pixels(my_pixels, channel=0)
    time.sleep(0.5)

