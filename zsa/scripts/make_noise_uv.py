#! /usr/bin/env python
import aipy as a
import numpy as n
import optparse, sys

args = sys.argv[1:]

curtime=None
noise_t_fr=None

def mfunc(uv, p, d, f):
    global curtime, noise_t_fr
    uvw, t, (i,j) = p
    if curtime != t:
        curtime = t
        #new noise for every time step/freq but same for all baselines.
        print len(d)
        noise_t_fr = n.random.normal(size=len(d)) * n.exp(2j*n.pi*n.random.uniform(size=len(d)))
    noise_t_fr_bl = n.random.normal(size=len(d)) * n.exp(2j*n.pi*n.random.uniform(size=len(d)))
    data = .5*noise_t_fr + .5*noise_t_fr_bl
    return p, data, f

for filename in args:
    outfile = filename + '_noise'
    print 'Writing %s'%(outfile)
    uvi = a.miriad.UV(filename)
#    a.scripting.uv_selector(uvi, ants=baselines)
    uvo = a.miriad.UV(outfile, status='new')
    uvo.init_from_uv(uvi)
    uvo.pipe(uvi, mfunc=mfunc, append2hist=' '.join(sys.argv)+'\n', raw=True)

