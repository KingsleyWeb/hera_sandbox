#!/usr/bin/env python


## NAME: 
#         single_baseline.py
## PURPOSE: 
#         Visibility simulator for a single baseline for all frequencies for 1 Sidereal day

#------------------------------------------------------------------------------------------------

import aipy
import numpy
import pylab
import pyfits
import matplotlib.pyplot as plt

root = '/Users/carinacheng/capo/ctc/'

print 'setting up miriad UV file...'

#miriad uv file set-up

uv = aipy.miriad.UV(root + 'tables/single_baseline_test.uv', status='new')

uv.add_var('telescop' ,'a');   uv['telescop'] = 'AIPY'
uv.add_var('operator' ,'a');   uv['operator'] = 'AIPY'
uv.add_var('version'  ,'a');   uv['version'] = '0.0.1'
uv.add_var('epoch'    ,'r');   uv['epoch'] = 2000.
uv.add_var('sdf'      ,'d');   uv['sdf'] = 0.1/256
uv.add_var('sfreq'    ,'d');   uv['sfreq'] = 0.1
uv.add_var('freq'     ,'d');   uv['freq'] = 0.1
uv.add_var('restfreq' ,'d');   uv['restfreq'] = 0.1
uv.add_var('nchan'    ,'i');   uv['nchan'] = 256
uv.add_var('nschan'   ,'i');   uv['nschan'] = 256
uv.add_var('inttime'  ,'r');   uv['inttime'] = 10.0
uv.add_var('npol'     ,'i');   uv['npol'] = 1
uv.add_var('nspect'   ,'i');   uv['nspect'] = 1
uv.add_var('nants'    ,'i');   uv['nants'] = 32

#variables to be updated

uv.add_var('coord'    ,'d')
uv.add_var('time'     ,'d')
uv.add_var('lst'      ,'d')
uv.add_var('ra'       ,'d')
uv.add_var('obsra'    ,'d')
uv.add_var('baseline' ,'r')
uv.add_var('pol'      ,'i')

#get antenna array

print 'getting antenna array...'

freqs = numpy.asarray([0.1,0.12,0.16,0.2])

filename = 'psa898_v003'
aa = aipy.cal.get_aa(filename, freqs)
#aa = aipy.cal.get_aa(filename, uv['sdf'],uv['sfreq'],uv['nchan'])
#freqs = aa.get_afreqs()
i = 0
j = 16
baseline = aa.get_baseline(i,j) #for antennas 0 and 16; array of length 3 in ns



#more miriad variables

uv.add_var('latitud'  ,'d');   uv['latitud'] = aa.lat
uv.add_var('dec'      ,'d');   uv['dec'] = aa.lat
uv.add_var('obsdec'   ,'d');   uv['obsdec'] = aa.lat
uv.add_var('longitu'  ,'d');   uv['longitu'] = aa.long
uv.add_var('antpos'   ,'d');   uv['antpos'] = (numpy.array([ant.pos for ant in aa], dtype = numpy.double)).transpose().flatten() #transpose is miriad convention

"""

#get Haslam map

img3d = aipy.map.Map(fromfits = root + 'images/lambda_haslam408_dsds_eq.fits') #reads in 3D image; default is nside=512 (3145728 pixels)

#rescale frequency (Haslam map is 408GHz)

r = 150.0/408
f = r**-2.5 #synchrotron emission (spectral index -2.5)

img3d.map.map *= f #3D image data rescaled (array of size 3145728)

"""

#get eq coordinates for one image 

print 'calculating beam response...'

img3d1 = aipy.map.Map(fromfits = root + 'images/gsm/gsm256/gsm1001.fits')

px = numpy.arange(img3d1.npix()) #number of pixels in map
crd3d = numpy.array(img3d1.px2crd(px,ncrd=3)) #aipy.healpix.HealpixMap.px2crd?
x3d,y3d,z3d = crd3d[0], crd3d[1], crd3d[2] #1D arrays of eq coordinates of 3Dimg (can define to be whatever coordinate system, but eq is most useful here)

aa.set_jultime(2454500)

t3d = aipy.coord.eq2top_m(aa.sidereal_time(),aa.lat)
tx3d, ty3d, tz3d = numpy.dot(t3d,crd3d) #topocentric coordinates
tops3d = numpy.asarray([tx3d,ty3d,tz3d])
#tops3d = numpy.append([tx3d,ty3d],[tz3d],axis=0)
tops3d = tops3d.compress(tops3d[2]>=0,axis=1)
#tops3d = numpy.asarray([tx3d,ty3d,tz3d])
bm3d = aa[0].bm_response((tops3d[0],tops3d[1],tops3d[2])) #beam response (makes code slow)
print bm3d.shape
#bm3d = numpy.where(tz3d < 0, 0, bm3d) #gets rid of beam values below horizon
sum_bm3d = numpy.sum(bm3d,axis=1)


#loop through frequency to get GSM and calculate fringe

print 'getting GSMs and calculating fringes...'


flags = numpy.zeros(len(freqs), dtype=numpy.int32)

img3d = {}
fng = {}
for jj, f in enumerate(freqs):
    img3d[f] = aipy.map.Map(fromfits = root + 'images/gsm/gsm256/gsm1' + str(jj+1).zfill(3) + '.fits', interp=True) 
    #XXX east-west baseline only
    fng[f] = numpy.exp(-2j*numpy.pi*tops3d[0]*baseline[0]*f) #fringe pattern
    fng[f]*= bm3d[jj]/sum_bm3d[jj]
    print str(f) + ' GHz done'


#loop through time to pull out fluxes from changing equatorial coordinates
#loop through frequency to get GSM and fringe

print 'writing miriad uv file...'

times = numpy.arange(2454500., 2454501., 300*uv['inttime']/aipy.const.s_per_day)
#flags = numpy.zeros((uv['nchan'],),dtype=numpy.int32)

for ii, t in enumerate(times):

    print 'Timestep %d/%d' %(ii+1, len(times))
    aa.set_jultime(t)
    uv['time'] = t
    uv['lst'] = aa.sidereal_time()
    uv['ra'] = aa.sidereal_time()
    uv['obsra'] = aa.sidereal_time()

    eq3d = aipy.coord.top2eq_m(aa.sidereal_time(),aa.lat)
    eqx3d, eqy3d, eqz3d = numpy.dot(eq3d,tops3d) #equatorial coordinates

    data = []

    px, wgts = img3d[freqs[0]].crd2px(eqx3d,eqy3d,eqz3d, interpolate=1)

    for jj, f in enumerate(freqs):

        fringe3d = fng[f]
        
        #fluxes3d = img3d[f][eqx3d,eqy3d,eqz3d]
        fluxes3d = numpy.sum(img3d[f][px]*wgts, axis=1)

        p13d = fluxes3d*fringe3d#*bm3d
        sump13d = numpy.sum(p13d)#/sum_bm3d
        data.append(sump13d)

        print str(f) + ' GHz done'
    
    data = numpy.asarray(data)
   
    preamble = (baseline, t, (i,j))
    uv['pol'] = aipy.miriad.str2pol['xx']
    uv.write(preamble, data, flags)

del(uv)


