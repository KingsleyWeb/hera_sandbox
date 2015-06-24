#!/usr/bin/env python

import aipy
import numpy
import pylab
import pyfits
import matplotlib.pyplot as plt
import optparse
import os, sys

#fills healpix maps pixel by pixel with a Gaussian distributed value

o = optparse.OptionParser()
o.set_description(__doc__)
o.add_option('--nchan',dest='nchan',default=203,type='int',help='Number of channels/maps to be made. Default is 203.')
o.add_option('--name',dest='name',default='pspec_wn',type='string',help='Map names.')
opts, args = o.parse_args(sys.argv[1:])

dirname = opts.name+str(opts.nchan)
os.system('mkdir /Users/carinacheng/capo/ctc/images/pspecs/'+dirname)

for i in range(opts.nchan):

    map = aipy.map.Map(nside=512)
    px = numpy.arange(map.npix())
    fluxes = numpy.random.normal(size=len(px))
    wgts = numpy.ones_like(fluxes)

    crds = numpy.array(map.px2crd(px,ncrd=3))
    x,y,z = crds[0],crds[1],crds[2]

    map.add((x,y,z),wgts,fluxes)
        
    map.to_fits('/Users/carinacheng/capo/ctc/images/pspecs/'+dirname+'/pspec1'+("%03i" % (i+1))+'.fits',clobber=True)

    print 'Map #',i+1,' complete'

