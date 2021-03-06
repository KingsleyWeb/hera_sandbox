#$ -S /bin/bash
source .bashrc
POL=xx
CAL=pgb322_v008_gc
ANTS="cross,-16,-31,-3_13,-3_14,-3_29,-4_14,-4_15,-4_30,-4_32,-5_15,-5_32,-6_32,-13_20,-14_21,-15_21,-15_22,-15_23,-20_29,-21_30,-21_32,-22_32,-23_32"
SZ=400
RES=.4
ALTMIN=30
NSIDE=512
C1=80
C2=180
dC=1
MINUV=20
DEC=2
SNAP=180
CHS=`python -c "for a in range($C1,$C2,$dC): print '%d_%d' % (a,a)"`
MYCHS=`pull_args.py $CHS`
for ch in $MYCHS ; do
    echo Working on channels: $ch
    FMT_FILE=pgb322_c${ch}_MCMC_
    FMT=${FMT_FILE}%04d
    mk_img.py -p $POL -a $ANTS -C $CAL -c $ch --fmt=${FMT} --size=$SZ --res=$RES -o dim,dbm -x $DEC --altmin=$ALTMIN --minuv=$MINUV $*
    cl_img.py -d cln --maxiter=10000 --div --tol=1e-6 -r radial -o bim ${FMT_FILE}*.d[ib]m.fits
    mk_map.py --nside=$NSIDE -m ${FMT_FILE}bmap.fits ${FMT_FILE}*.bim.fits
done

