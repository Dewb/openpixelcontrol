#!/usr/bin/env python

from __future__ import division
import time
import sys
import optparse
import random
import math
try:
    import json
except ImportError:
    import simplejson as json

import opc 
import color_utils

# remember to 
# $ sudo easy_install colormath
from colormath.color_objects import *


#-------------------------------------------------------------------------------
# command line

parser = optparse.OptionParser()
parser.add_option('-l', '--layout', dest='layout',
                    action='store', type='string',
                    help='layout file')
parser.add_option('-s', '--server', dest='server', default='127.0.0.1:7890',
                    action='store', type='string',
                    help='ip and port of server')
parser.add_option('-f', '--fps', dest='fps', default=20,
                    action='store', type='int',
                    help='frames per second')

options, args = parser.parse_args()

if not options.layout:
    parser.print_help()
    print
    print 'ERROR: you must specify a layout file using --layout'
    print
    sys.exit(1)


#-------------------------------------------------------------------------------
# parse layout file

print
print '    parsing layout file'
print


def computeRegion(cube, channel, ledindex):
    regionmap = {
        (0,0): [ (30, "off"), (60, "off"), (90, "C"), (999, "C") ],
        (0,1): [ (30, "BC"), (60, "B"), (90, "off"), (999, "off") ],
        (0,2): "AB",
        (0,3): "off",
        (0,4): [ (86, "A"), (999, "off") ],
        (0,5): [ (86, "off"), (999, "off") ],
        (0,6): "B",
        (0,7): "off",
        (1,0): [ (30, "off"), (60, "off"), (90, "A"), (999, "A") ],
        (1,1): [ (30, "AC"), (60, "C"), (90, "off"), (999, "off") ],
        (1,2): "BC",
        (1,3): "off",
        (1,4): [ (86, "B"), (999, "off") ],
        (1,5): [ (86, "off"), (999, "off") ],
        (1,6): "C",
        (1,7): "off",
        (2,0): [ (30, "off"), (60, "off"), (90, "B"), (999, "B") ],
        (2,1): [ (30, "AB"), (60, "A"), (90, "off"), (999, "off") ],
        (2,2): "AC",
        (2,3): "off",
        (2,4): [ (86, "C"), (999, "off") ],
        (2,5): [ (86, "off"), (999, "off") ],
        (2,6): "A",
        (2,7): "off",

    }
    r = regionmap[(cube, channel)]
    if not isinstance(r, list):
        return r
    else:
        for item in r:
            if ledindex < item[0]:
                return item[1]
    
    print "error: unmapped region"
    return "?"

coordinates = []
channels = []
regions = []

for item in json.load(open(options.layout)):

    if 'point' in item:
        coordinates.append(tuple(item['point']))
    if 'channel' in item:
        channels.append(item['channel'])
        if 'cube' in item and 'ledindex' in item:
            regions.append(computeRegion(item['cube'], item['channel'], item['ledindex']))

#-------------------------------------------------------------------------------
# connect to server

client = opc.Client(options.server)
if client.can_connect():
    print '    connected to %s' % options.server
else:
    # can't connect, but keep running in case the server appears later
    print '    WARNING: could not connect to %s' % options.server
print



def test_pixel_color(t, coord, ii, n_pixels, random_values, accum):
    return ((ii % 30) / 30.0 * 125 + color_utils.cos(t) * 130, (1 - ii / n_pixels) * 180, color_utils.cos(t*0.1) * 255)

def quadrant(radians):
    radians = radians % math.pi * 2.0
    if 0 <= radians < math.pi / 2.0:
        return 1
    elif math.pi / 2.0 <= radians < math.pi:
        return 2
    elif math.pi <= radians < math.pi * 3.0/2.0:
        return 3
    elif math.pi * 3.0/2.0 <= radians:
        return 4
    else:
        return -1

def prism_color(t, coord, ii, n_pixels, random_values, accum):
    arcwidth = math.pi/12.0
    theta = (t * math.pi/16.0) % (2.0 * math.pi)
    x, y, z, = coord
    #a = math.atan2(x, z) * 0.5 + math.pi
    #if a < 0:
    #    a = 2.0 * math.pi + a
    a = math.atan2(x, z) + math.pi

    #colors = ((255, 0, 0), (0, 255, 0), (0, 0, 255), (128, 0, 128))

    #if quadrant(theta) == quadrant(a):
    #    return colors[quadrant(theta)-1]
    #else:
    #    return (240, 240, 240)

    delta = abs(theta - a)

    if delta > math.pi:
        delta = 2.0 * math.pi - delta

    if delta < arcwidth:
        p = delta / arcwidth
        c = HSLColor(360.0 * (1 - p), 1.0, 0.5)
        return c.convert_to('rgb').get_value_tuple()
    else:
        return (240, 240, 240)

def distance_color(t, coord, ii, n_pixels, random_values, accum):
    x, y, z, = coord
    dist = math.sqrt(x * x + y * y + z * z)
    maxdist = 8.0
    c = HSLColor(360.0 * (t % 20)/20.0, 1.0, dist/maxdist)
    return c.convert_to('rgb').get_value_tuple()

def channel_color(t, coord, ii, n_pixels, random_value, accum):
    hue = {
        0: 0,   # red
        1: 40,  # orange
        2: 120, # green
        3: 260, # violet
        4: 70,  # yellow
        5: 180, # cyan
        6: 210, # blue
        7: 320, # magenta
    }[channels[ii]]
    c = HSLColor(hue, 0.8, 0.4)
    return c.convert_to('rgb').get_value_tuple()

def distance(x1, y1, x2, y2):
    v = (x2 - x1, y2 - y1)
    return math.sqrt(v[0] * v[0] + v[1] * v[1])
    #return v[0] * v[0] + v[1] * v[1]

def lerp(a, b, t):
    return a + t * (b - a)

def plasma(t, accum, x, y):
    phase = accum
    stretch = 0.008 + (math.sin(t/20 * TF) ** 3 + 1.0) * 3.6
    p1 = ((math.sin(phase * 1.000) + 0.0) * 2.0, (math.sin(phase * 1.310) + 0.0) * 2.0)
    p2 = ((math.sin(phase * 1.770) + 0.0) * 2.0, (math.sin(phase * 2.865) + 0.0) * 2.0)
    d1 = distance(p1[0], p1[1], x, y)
    d2 = distance(p2[0], p2[1], x, y)
    f = (math.sin(d1 * d2 * stretch) + 1.0) * 0.5
    return f * f

# time factor to speed up certain aspects of the animation during debugging
TF = 1 # /30

def region_color(t, coord, ii, n_pixels, random_value, accum):

    p = plasma(t, accum, coord[0], coord[1])
    d = abs(p - 0.5)

    s = lerp(0.6, 1.0, p)
    l = lerp(0.2, 0.5, p)
    
    smix = lerp(1.0, 0.7, d)
    lmix = lerp(0.5, 0.2, d)

    c = {
        'A': (0, s, l),
        'AB': (lerp(0, 40, p), smix, lmix),
        'B': (40, s, l),
        'BC': (lerp(40, 80, p), smix, lmix),
        'C': (80, s, l),
        'AC': (lerp(80, 100, p), smix, lmix),
        'off': (0, 0, 0),
    }.get(regions[ii], (0, 0.3, 0.6))

    return HSLColor((c[0] + t * 3 * TF) % 360, 
                    c[1],
                    c[2]
                    ).convert_to('rgb').get_value_tuple()


    # apply gamma curve
    # only do this on live leds, not in the simulator
    #r, g, b = color_utils.gamma((r, g, b), 2.2)

def mesmerize_color(t, coord, ii, n_pixels, random_value, accum):
    if regions[ii] == "off":
        return (0, 0, 0)
    s = color_utils.clamp(math.sin(1.8 * math.sqrt(coord[0] ** 2 + coord[1] ** 2 + 2 * (coord[2] ** 2)) - t * 6.0) * 0.75 + 0.5, 0, 1) 
    return HSLColor(0, 0, s).convert_to('rgb').get_value_tuple()

def checker_color(t, coord, ii, n_pixels, random_value, accum):
    if regions[ii] == "off":
        return (0, 0, 0)

    w = 1.8 + 1.2 * math.sin(t/2)
    dx = t
    dy = 0
    u = ((coord[0] - dx) % w) / w
    v = ((coord[1] - dy) % w) / w
    h = 0 
    if (u < 0.5) == (v < 0.5):
        h = 45
    tol = 0.021
    if abs(u - 0.5) < tol or abs(v - 0.5) < tol:
        h = 120

    return HSLColor((h + t*4) % 360, 
                    0.4 + 0.3 * u + 0.3 * math.sin(t/8), 
                    0.5 + 0.2 * v
                    ).convert_to('rgb').get_value_tuple()



#-------------------------------------------------------------------------------
# send pixels

print '    sending pixels forever (control-c to exit)...'
print

n_pixels = len(coordinates)
random_values = [random.random() for ii in range(n_pixels)]
start_time = time.time()
accum = 0
while True:
    t = time.time() - start_time
    pixels = [region_color(t*0.6, coord, ii, n_pixels, random_values, accum) for ii, coord in enumerate(coordinates)]
    accum = accum + 0.001 * ( 1.0 + 80.0 * math.pow(math.sin(t/10 * TF), 2))
    client.put_pixels(pixels, channel=0)
    time.sleep(1 / options.fps)

