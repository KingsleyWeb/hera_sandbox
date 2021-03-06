#! /usr/bin/env python
import sys, os, math
"""
A specialized version of pull_args.  Assumes args are broken into "day long" chunks.
Eg
 zen.2454977.50748.uvcbt
 zen.2454977.54924.uvcbt
 -
 zen.2454978.50964.uvcbt
 zen.2454978.55140.uvcbt
This type of output is generated by lst_select with the '-d -' option
"""
args = sys.argv[1:]
try:
    n = int(os.environ['SGE_TASK_FIRST'])
    m = int(os.environ['SGE_TASK_LAST'])
    i = int(os.environ['SGE_TASK_ID']) - 1
    num = int(math.ceil(float(len(args)) / (m - n + 1)))
    print ' '.join(sys.stdin.readlines()[1:]).split('-')[i].strip()
except(KeyError,ValueError): print ' '.join(args)
