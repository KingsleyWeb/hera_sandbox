import numpy as np
import cPickle as pickle
import matplotlib.pyplot as plt
import capo.omni as omni, capo.zsa as zsa, capo.arp as arp
import scipy
import scipy.constants
import aipy as a
import optparse, sys, os
import capo
import capo.uCal as uc

uc = reload(capo.uCal)
from joblib import Parallel, delayed
import multiprocessing
from scipy.optimize import curve_fit




#TODO: look into the effects of the range of u values included
#TODO: look at phase ramp

#%%##########################################
#   Set-up functions specific to PAPER 128
#############################################

def getBaselines(freqs, intSeps, exampleDataFile, calFile='psa6622_v003'):
    aa = a.cal.get_aa(calFile, freqs)
    blstr, _, bl2sep = zsa.grid2ij(aa.ant_layout)
    m, _, mdl,_= omni.from_npz(exampleDataFile)
    bls = [(0,i) for i in intSeps]
    for ij in mdl['xx'].keys():
        bl = a.miriad.ij2bl(ij[0],ij[1]) 
        try:
            s = tuple(map(int,bl2sep[bl].split(',')))
        except(KeyError):
            continue
        if s in bls and s[0] == 0:
            bls[s[-1]-1] = ij
    return bls

def blRedundancyDictFromCalFile(calFile = 'psa6622_v003', verbose = False):
    """ Uses Omnical to figure out the number of redundant baselines for a given separation (as demarkated by a representative baseline tuple). 
    Returns redundancyDict and also saves it as an instance variable."""
    aa = a.cal.get_aa(calFile,np.array([.15]))
    if verbose: print 'Now generating baseline redundancy dictionary from calfile...'
    ex_ants = [5,7,8,15,16,17,24,26,27,28,29,37,38,46,48,50,51,53,55,63,68,69,72,74,76,77,82,83,84,85,92,107,110]
    info = capo.omni.aa_to_info(aa, pols=['x'], ex_ants=ex_ants)
    reds = info.get_reds()
    redundancyDict = {}
    #This is overkill...it maps all baselines to their redundancy, not just the ones we need. But that's fine.
    for red in reds:
        for bl in red: redundancyDict[bl] = len(red)
    return redundancyDict

def loadVisibilitiesAndSamples(dataFiles, pol, blList, redundancyDict):
    """Based on Zaki and Carina's omni_get_k.py"""
    print 'Now reading all data files...'
    data = {}
    samples = {}
    jds = []
    lsts = []
    files = []
    conjugate = [(0,101), (0,62), (0,100), (0,97), (12,43), (57,64)]
    for fl in dataFiles:
        print '   Reading %s'%fl
        meta,_,mdl,_ = omni.from_npz(fl)
        jd = meta['jds']
        lst = meta['lsts']
        jds.append(jd)
        lsts.append(lst)
        files.append(fl.split('/')[-1]) #ignore the folder
        for b in bls:
            if b in conjugate: _d = np.conj(mdl[pol][b])
            else: _d = mdl[pol][b]
            if b not in data.keys(): data[b] = _d
            else: data[b] = np.concatenate((data[b],_d), axis=0)
            samples[b] = redundancyDict[b] * np.ones(data[b].shape)
            samples[b][data[b]==0] = 0 #TODO: we need a more sophisticated way of handling flagging than this!!!
    return data, samples

def dataAndSamplesBootstraps(data, samples, bls, nBootstraps):
    """This function returns a list of """
    dataBootstraps, samplesBootstraps = [{} for i in range(nBootstraps)], [{} for i in range(nBootstraps)] 
    nIntegrations = len(data[bls[0]])
    for i in range(nBootstraps):
        indices = np.random.random_integers(0,nIntegrations-1,nIntegrations)        
        for bl in bls:
            dataBootstraps[i][bl] = data[bl][indices,:]
            samplesBootstraps[i][bl] = samples[bl][indices,:]
    return dataBootstraps, samplesBootstraps    

def harmonizeChannelFlags(chans, uCal, uCalBootstraps, verbose=False):
    """This function flags all channels that are flagged in any of the splits for both uCal and all splits."""
    unflagged = set(uCal.chans)
    for split in uCalBootstraps: unflagged &= set(split.chans)
    toFlag = list(set(chans) - unflagged)
    uCal.applyChannelFlagCut(toFlag)
    for split in uCalBootstraps: split.applyChannelFlagCut(toFlag)
    if verbose: print "After harmonizing channels flags, " + str(len(toFlag)) + " channels have been flagged for all bootstraps."

#############################################
#   uCal Parameters
#############################################

regenerateEverything = False
verbose = True
dataFiles = ["./Data/" + file for file in os.listdir("./Data") if file.endswith("uvcRRE.npz")]
nBootstraps = 40
uMin, uMax = 25, 100

#manualChannelFlags = [14, 17, 55, 74, 93, 101, 102, 152, 153, 166, 168, 176, 177, 178, 179, 180, 181, 182, 183, 184, 185, 186]
manualChannelFlags = [74, 178, 166, 168, 102]

#%%##########################################
#   uCal Setup
#############################################

#PAPER 128 Setup
pol='xx'
freqs = np.arange(.1,.2,.1/203) 
chans = range(len(freqs))
chan2FreqDict = {chan: freqs[chan] for chan in chans}
intSeps = np.arange(1,16) #* 15m  = baseline lengths
dx = 15.0 / scipy.constants.c * 1e9
separations = dx*intSeps
bls = getBaselines(freqs, intSeps, dataFiles[0], calFile='psa6622_v003')
bl2SepDict = {bl: np.asarray([sep,0.0]) for bl,sep in zip(bls,separations)}
redundancyDict = blRedundancyDictFromCalFile(calFile = 'psa6622_v003')

if regenerateEverything:
    uReds = uc.uCalReds(freqs, bls, chan2FreqDict, bl2SepDict, maxDeltau=.3, verbose=verbose) #just pass in freqs
    uCal = uc.uCalibrator(uReds.getBlChanPairs())
    data, samples = loadVisibilitiesAndSamples(dataFiles, pol, bls, redundancyDict)
    uCal.computeVisibilityCorrelations(data, samples, verbose=verbose)
    uCalBootstraps = [uc.uCalibrator(uReds.getBlChanPairs()) for i in range(nBootstraps)]
    dataBootstraps, samplesBootstraps = dataAndSamplesBootstraps(data, samples, bls, nBootstraps)
    for i in range(nBootstraps): uCalBootstraps[i].computeVisibilityCorrelations(dataBootstraps[i], samplesBootstraps[i], verbose=verbose)
    harmonizeChannelFlags(chans, uCal, uCalBootstraps, verbose=verbose)
    pickle.dump([uReds, uCal, uCalBootstraps, dataFiles], open('./Data/uCalDataWithBootstraps.p', 'wb'))
else: 
    uReds, uCal, uCalBootstraps, loadedDataFiles = pickle.load(open('./Data/uCalDataWithBootstraps.p','rb'))
    if not len(uCalBootstraps) == nBootstraps or not loadedDataFiles == dataFiles: raise RuntimeError('Loaded uCalDataWithBootstraps.p does not match current specifications.')

#%%##########################################
#   uCal Functionality
#############################################

def uCalSetup(uCal, channelFlags=[]):
    if len(channelFlags)> 0: uCal.applyChannelFlagCut(channelFlags)
    uCal.applyuCut(uMin=uMin, uMax=uMax)
    uCal.setupBinning(uBinSize = .5, duBinSize = 5.0/203)

def performuCal(uCal, noiseVariance=None, maxIterations = 40, verbose = False):
    if not uCal.binningIsSetup: uCal.setupBinning(uBinSize = .5, duBinSize = 5.0/203)
    if verbose: print 'Now performing logcal...'
    betas, Sigmas, Ds = uCal.performLogcal()
    noiseCovDiag = uCal.generateNoiseCovariance(betas)
    if noiseVariance is not None: noiseCovDiag = noiseVariance
    if verbose: print 'Now performing lincal...'
    prevBetas, prevSigmas, prevDs = 0, 0, 0
    for iteration in range(maxIterations): 
        betas, Sigmas, Ds, chiSqPerDoF = uCal.performLincalIteration(betas, Sigmas, Ds, noiseCovDiag, alpha = .5)
        if verbose: print '    ' + str(iteration) + ') chi^2/dof = ' + str(chiSqPerDoF)
        if np.average(np.abs(betas - prevBetas)/np.abs(betas)) < 1e-6: break
        prevBetas, prevSigmas, prevDs = betas, Sigmas, Ds 
        noiseCovDiag = uCal.generateNoiseCovariance(betas)
    noiseCovDiag = uCal.renormalizeNoise(betas, Sigmas, Ds, noiseCovDiag)
    return betas, Sigmas, Ds, noiseCovDiag

def renormalizeNoiseFromBootstraps(uCal, betas, Sigmas, Ds, noiseCovDiag, bootstrapBetas, bootstrapSigmas, bootstrapDs, verbose=False):
    noiseStart = noiseCovDiag[0]
    for i in range(3):
        modelAbsErrors = (np.diag(np.linalg.pinv(uCal.AtNinvA))[0::2] + np.diag(np.linalg.pinv(uCal.AtNinvA))[1::2])
        modelAbsErrors[0:uCal.nChans] *= np.abs(betas)**2
        bootstrapAbsErrors = np.asarray([sigma for bootstrap in (bootstrapBetas, bootstrapSigmas, bootstrapDs) for sigma in np.var(np.asarray(bootstrap).T,axis=1)])
        noiseCovDiag *= np.median(bootstrapAbsErrors[0:uCal.nChans]) / np.median(modelAbsErrors[0:uCal.nChans])
        uCal.performLincalIteration(betas, Sigmas, Ds, noiseCovDiag, alpha = .5)        
    if verbose: print 'Noise covariance rescaled by ' + str(noiseCovDiag[0]/noiseStart) + ' to match bootstraps.'
    return noiseCovDiag


#%%##########################################
#   Run uCal
#############################################

try: channelsToFlag = manualChannelFlags
except: channelsToFlag = []

while True:
    uCalSetup(uCal, channelFlags=channelsToFlag)
    betas, Sigmas, Ds, noiseCovDiag = performuCal(uCal, verbose=verbose)
    newFlags = uCal.identifyBadChannels(betas, Sigmas, Ds, noiseCovDiag, maxAvgError=4, cutUpToThisFracOfMaxError=.5)    
    if len(newFlags)==0: break
    for chan in newFlags: channelsToFlag.append(chan)
if verbose: print str(len(channelsToFlag)) + ' channels flagged manually or due to high error: ' + str(sorted(channelsToFlag))
    
for bootstrap in uCalBootstraps: uCalSetup(bootstrap, channelFlags=channelsToFlag)
bootstrapBetas, bootstrapSigmas, bootstrapDs =  [[None for i in range(nBootstraps)] for j in range(3)]
parallelBootstrapResults = Parallel(n_jobs=multiprocessing.cpu_count())(delayed(performuCal)(uCalBootstraps[i], noiseVariance=noiseCovDiag) for i in range(nBootstraps))
for i in range(nBootstraps): bootstrapBetas[i], bootstrapSigmas[i], bootstrapDs[i], dummy = parallelBootstrapResults[i]

noiseCovDiag = renormalizeNoiseFromBootstraps(uCal, betas, Sigmas, Ds, noiseCovDiag, bootstrapBetas, bootstrapSigmas, bootstrapDs, verbose=verbose)
betas, Sigmas, Ds, chiSqPerDoF = uCal.performLincalIteration(betas, Sigmas, Ds, noiseCovDiag, alpha = .5)
if verbose: print 'Final chi^2/dof =', chiSqPerDoF 


#%%##########################################
#   Complex Fitting
#############################################

length = np.max(freqs)-np.min(freqs)
def fourier(x, *a):
    ret = a[0]
    for deg in range(1, len(a)):
        ret += a[deg] * np.cos((deg) * np.pi / length * x)
    return ret

def cosineFit(x, data, errors, degree):
    popt, pcov = curve_fit(fourier, x, data, sigma=errors, p0=[1.0] * (degree+1))
    return fourier(x, *popt)
    
def BIC(data, realModel, imagModel, realErrors, imagErrors, DoF):
    chiSq = np.sum(((np.real(data) - realModel)/realErrors)**2) + np.sum(((np.imag(data) - imagModel)/imagErrors)**2)
    return np.sum(np.log(2*np.pi*realErrors**2)) + np.sum(np.log(2*np.pi*imagErrors**2)) + chiSq + DoF*np.log(2*len(data))

def findBestModel(x, data, realErrors, imagErrors, degreeRange):
    BICs = []
    for degree in degreeRange:
        realModel = cosineFit(x, np.real(data), realErrors, degree)
        imagModel = cosineFit(x, np.imag(data), imagErrors, degree)
        BICs.append(BIC(data, realModel, imagModel, realErrors, imagErrors, DoF=2*degree+2))
    bestDegree = (degreeRange[BICs==np.min(BICs)][0])
    bestModel = cosineFit(x, np.real(data), realErrors, bestDegree) + 1.0j * cosineFit(x, np.imag(data), imagErrors, bestDegree)
    bestChiSqPerDoF = (np.sum(((np.real(data) - np.real(bestModel))/realErrors)**2) + np.sum(((np.imag(data) - np.imag(bestModel))/imagErrors)**2))/(len(data)*2)
    return bestModel, BICs, bestDegree, bestChiSqPerDoF

degreeRange = np.arange(60,120,2)
observedRealErrors = np.std(np.real(np.asarray(bootstrapBetas).T),axis=1)
observedImagErrors = np.std(np.imag(np.asarray(bootstrapBetas).T),axis=1)
modelRealErrors = np.abs(betas)*((np.diag(np.linalg.pinv(uCal.AtNinvA))[0:2*uCal.nChans:2]))**.5
modelImagErrors = np.abs(betas)*((np.diag(np.linalg.pinv(uCal.AtNinvA))[1:2*uCal.nChans:2]))**.5
model, BICs, bestDegree, bestChiSqPerDoF = findBestModel(freqs[uCal.chans] - .1, betas*freqs[uCal.chans]**2.55, modelRealErrors*freqs[uCal.chans]**2.55, modelImagErrors*freqs[uCal.chans]**2.55, degreeRange)
if verbose: print 'The fourier mode limit with the lowest BIC is ' + str(bestDegree) + ' with a fit chi^2 per DoF of ' + str(bestChiSqPerDoF)

