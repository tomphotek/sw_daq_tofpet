# -*- coding: utf-8 -*-
import atb
import tofpet
from loadLocalConfig import loadLocalConfig
from bitarray import bitarray
from sys import argv, stdout, exit
from time import time, sleep
import ROOT
from rootdata import DataFile
import numpy as np
import argparse

parser = argparse.ArgumentParser(description='Acquires a set of data for 4 relative phases of the test pulse, either injecting it directly in the tdcs or/and in the front end. Output reports the time rms and tot by asic')


parser.add_argument('OutputFile',
                   help='output file (ROOT file). Contains histograms of data.')

parser.add_argument('hvBias', type=float,
                   help='The voltage to be set for the HV DACs. Relevant only to fetp mode. In tdca mode, it is set to 5V.')


parser.add_argument('--asics', nargs='*', type=int, help='If set, only the selected asics will acquire data')

parser.add_argument('--channels', nargs='*', type=int, help='If set, only the selected channels will acquire data')

parser.add_argument('--mode', type=str, required=True,choices=['tdca', 'fetp', 'both'], help='Defines where the test pulse is injected. Three modes are allowed: tdca, fetp and both. ')

parser.add_argument('--tpDAC', type=int, default=32, help='The amplitude of the test pulse in DAC units (Default is 32 )')

args = parser.parse_args()


# Parameters
T = 6.25E-9
nominal_m = 128

#### PLL based generator
Generator = 1
M = 0x348	# 80 MHz PLL, 80 MHz AIC
M = 392		# 160 MHz PLL, 160 MHz ASIC
#M = 2*392	# 160 MHz PLL, 80 MHz ASIC 

minEventsA = 1200
minEventsB = 300

###


##### 560 MHz clean clock based generator
#Generator = 0
#M = 14	# 2x due to DDR
#K = 2 	# DO NOT USE DDR for TDCA calibration, as rising/falling is not symmetrical!
#minEvents = 1000 # Low jitter, not so many events
#####



Nmax = 8
tpLength = 128
tpFrameInterval = 16
tpCoarsePhase = 1
tpFinePhase = 196


#rootFileName = argv[1] ##########



uut = atb.ATB("/tmp/d.sock", False, F=1/T)
atbConfig = loadLocalConfig(useBaseline=False)
defaultConfig=atbConfig
uut.config=atbConfig
uut.initialize()

rootFileName=args.OutputFile
rootFile = ROOT.TFile(rootFileName, "RECREATE");
#rootData1 = DataFile( rootFile, "3")
#rootData2 = DataFile( rootFile, "3B")

if args.channels == None:
	activeChannels = [ x for x in range(0,64) ]
else:
	activeChannels= args.channels


if args.asics == None:
	activeAsics =  uut.getActiveTOFPETAsics()
else:
	activeAsics= args.asics


for tAsic in activeAsics:
    print "-------------------"
    print "Config for ASIC ", tAsic
    print "dc_start= ",atbConfig.asicConfig[tAsic].globalConfig.getValue("sipm_idac_dcstart")
    print "vbl= ",atbConfig.asicConfig[tAsic].channelConfig[0].getValue("vbl")
    print "ib1= ",atbConfig.asicConfig[tAsic].globalConfig.getValue("vib1")
    print "postamp= ", atbConfig.asicConfig[tAsic].globalConfig.getValue("postamp")

print "-------------------\n"
maxAsics=max(activeAsics) + 1
systemAsics = [ i for i in range(maxAsics) ]

minEventsA *= len(activeAsics)
minEventsB *= len(activeAsics)

s=(2,maxAsics,64,4)


deadChannels=np.zeros(s)
nlargeTFine=np.zeros((2,maxAsics))
largeTFineTAC=np.zeros((2,maxAsics,64,4))
largeTFineRMS=np.zeros((2,maxAsics,64,4))
nsmallToT=np.zeros((2,maxAsics))
smallToTTAC=np.zeros((2,maxAsics,64,4))
smallToT=np.zeros((2,maxAsics,64,4))

TFineRMS=np.zeros((2,maxAsics,64,4))
ToT=np.zeros((2,maxAsics,64,4))
EFineRMS=np.zeros((2,maxAsics,64,4))
TFineMean=np.zeros((2,maxAsics,64,4))
EFineMean=np.zeros((2,maxAsics,64,4))
#print activeAsics, minEventsA, minEventsB
#hTPoint = ROOT.TH1F("hTPoint", "hTPoint", 64, 0, 64)

hTFine = [[[[ ROOT.TH1F("htFine_%03d_%02d_%1d_%1d" % (tAsic, tChannel, tac, finephase), "T Fine", 1024, 0, 1024) for finephase in range(4)]for tac in range(4) ] for tChannel in range(64)] for tAsic in systemAsics ]
hEFine = [[[[ ROOT.TH1F("heFine_%03d_%02d_%1d_%1d" % (tAsic, tChannel, tac, finephase), "E Fine", 1024, 0, 1014) for finephase in range(4)]for tac in range(4) ] for tChannel in range(64)] for tAsic in systemAsics ]
hToT = [[[[ ROOT.TH1F("heToT_%03d_%02d_%1d_%1d" % (tAsic, tChannel, tac, finephase), "Coarse ToT", 1024, 0, 1014) for finephase in range(4)]for tac in range(4) ] for tChannel in range(64)] for tAsic in systemAsics ]

nmodes=0
if args.mode == "tdca" or args.mode == "fetp":
    nmodes=1
if args.mode == "both":
    nmodes=2
  



for iteration in range(nmodes):
   

    if (args.mode == "tdca" and iteration==0) or (args.mode == "both" and iteration==0):
        mode=0
        tdcaMode = True
        vbias =  5
        frameInterval = 0
        pulseLow = False
	

    elif (args.mode == "fetp" and iteration ==0) or (args.mode == "both" and iteration ==1):
        mode=1
        tdcaMode = False
        tpDAC = args.tpDAC
        if args.hvBias == None:
            vbias =  5
        else:
            vbias = args.hvBias
        frameInterval = 16
        pulseLow = True

    for  asic in range(len(systemAsics)):
        for  channel in range(64):
            for  tac in range(4):
                for  finephase in range(4):
                    hTFine[asic][channel][tac][finephase].Reset()
                    hEFine[asic][channel][tac][finephase].Reset()
                    hToT[asic][channel][tac][finephase].Reset()


    for i in range(4):
        tpFinePhase=i*98+1
        
        nEvents=0
        nDead=0
        #nlargeTFine=0
        #nlargeEFine=0
        #nsmallToT=0
       # deadChannels=[]
       # largeTFineChannel=[]
       # largeTFineTAC=[]
       # largeTFineRMS=[]
       # largeEFineChannel=[]
       # largeEFineTAC=[]
       # largeEFineRMS=[]
        nManualtfine=np.zeros(maxAsics)
        nNUtfine=np.zeros(maxAsics)
        nManualTOT=np.zeros(maxAsics) 
        nNUTOT=np.zeros(maxAsics)

      #  smallToTChannel=[]
      #  smallToTTAC=[]
       # smallToT=[]

        if vbias > 50: minEventsA *= 10

        for tChannel in activeChannels:

            if(tdcaMode):
                print "Running for Channel %d; Test pulse fine phase %d; mode TDCA" %(tChannel, tpFinePhase)
            else:
                print "Running for Channel %d; Test pulse fine phase %d; mode FETP" %(tChannel, tpFinePhase)
            
            atbConfig = loadLocalConfig(useBaseline=False)
            for c in range(len(atbConfig.hvBias)):
                atbConfig.hvBias[c] = vbias

            for tAsic in activeAsics:
                atbConfig.asicConfig[tAsic].globalConfig.setValue("test_pulse_en", 1)

            for tAsic in activeAsics:

                atbConfig.asicConfig[tAsic].channelConfig[tChannel].setValue("fe_test_mode", 1)
                if tdcaMode:

                    # Both TDC branches
                    atbConfig.asicConfig[tAsic].channelConfig[tChannel][52-47:52-42+1] = bitarray("11" + "11" + "1" + "1") 


                else:				
                    atbConfig.asicConfig[tAsic].channelTConfig[tChannel] = bitarray('1')
                    atbConfig.asicConfig[tAsic].globalTConfig = bitarray(atb.intToBin(tpDAC, 6) + '1')


            #uut.stop()
            uut.config = atbConfig
            uut.uploadConfig()
            #uut.start()
            uut.setTestPulsePLL(tpLength, tpFrameInterval, tpFinePhase, pulseLow)
            uut.doSync()

        
            t0 = time()


            #print "check1", tChannel, nReceivedEvents
           
            nReceivedEvents = 0
            nAcceptedEvents = 0
            nReceivedFrames = 0
            #print "check2", tChannel, nReceivedEvents

            t0 = time()        
            while nAcceptedEvents < minEventsA and (time() - t0) < 10:

                decodedFrame = uut.getDataFrame(nonEmpty=True)
                if decodedFrame is None: continue

                nReceivedFrames += 1

                for asic, channel, tac, tCoarse, eCoarse, tFine, eFine, channelIdleTime, tacIdleTime in decodedFrame['events']:
                    if channel == tChannel:
                        nReceivedEvents += 1
                    #print channel
                    
                    #    if tdcaMode==False:
                    #       print asic, tac, tCoarse, eCoarse, eCoarse-tCoarse,  6.25*(eCoarse-tCoarse)
                        nAcceptedEvents += 1				
                        nEvents += 1	
                    #rootData1.addEvent(step1, step2, decodedFrame['id'], asic, channel, tac, tCoarse, eCoarse, tFine, eFine, channelIdleTime, tacIdleTime)

                        hTFine[asic][channel][tac][i].Fill(tFine)
                        hEFine[asic][channel][tac][i].Fill(eFine)
                        hToT[asic][channel][tac][i].Fill((eCoarse-tCoarse)*6.25)

         
            print "Channel %(tChannel)d: Got %(nReceivedEvents)d events in  %(nReceivedFrames)d frames, accepted %(nAcceptedEvents)d" % locals()
          


    avTRMS=0
    avERMS=0

   
    for tChannel in activeChannels:   
        for tAsic in activeAsics:
            tfineflag=True
            efineflag=True
            totflag=True
            for tac in range(4):
                if (hTFine[tAsic][tChannel][tac][0].GetEntries()==0 and hTFine[tAsic][tChannel][tac][1].GetEntries() == 0 and hTFine[tAsic][tChannel][tac][2].GetEntries()==0 and hTFine[tAsic][tChannel][tac][3].GetEntries() == 0):
                    deadChannels[mode][tAsic][tChannel][tac]=1
                    
                tRMS=min(hTFine[tAsic][tChannel][tac][0].GetRMS(), hTFine[tAsic][tChannel][tac][1].GetRMS(), hTFine[tAsic][tChannel][tac][2].GetRMS(), hTFine[tAsic][tChannel][tac][3].GetRMS() )
                    
                eRMS=min(hEFine[tAsic][tChannel][tac][0].GetRMS(), hEFine[tAsic][tChannel][tac][1].GetRMS(), hEFine[tAsic][tChannel][tac][2].GetRMS(), hEFine[tAsic][tChannel][tac][3].GetRMS() ) 
               
                coarseTOT=max(hToT[tAsic][tChannel][tac][0].GetMean(), hToT[tAsic][tChannel][tac][1].GetMean(), hToT[tAsic][tChannel][tac][2].GetMean(), hToT[tAsic][tChannel][tac][3].GetMean())
               
                tMean=hTFine[tAsic][tChannel][tac][0].GetMean()
                for phase in [1,2,3]:
                    if(abs(hTFine[tAsic][tChannel][tac][phase].GetMean()-320) < abs(tMean-320)):
                        tMean= hTFine[tAsic][tChannel][tac][phase].GetMean()
                       
                eMean=hEFine[tAsic][tChannel][tac][0].GetMean()
                for phase in [1,2,3]:
                    if(abs(hEFine[tAsic][tChannel][tac][phase].GetMean()-320) < abs(eMean-320)):
                        eMean= hEFine[tAsic][tChannel][tac][phase].GetMean()

        
                TFineRMS[mode][tAsic][tChannel][tac]=tRMS
                TFineMean[mode][tAsic][tChannel][tac]=tMean

                EFineRMS[mode][tAsic][tChannel][tac]=eRMS
                EFineMean[mode][tAsic][tChannel][tac]=eMean
       
                ToT[mode][tAsic][tChannel][tac]=coarseTOT
                #    totflag=False 
                    
   

for tAsic in activeAsics:
    nDeadTAC=0
    nDeadFETP=0
    nTTDCMean=0
    nETDCMean=0
    nTTDCRms=0
    nETDCRms=0
    nTFETPMean=0
    nEFETPMean=0
    nMIRms=0
    nMIToT=0
    nNURms=0
    nNUToT=0
    print "\n\n############ Report for ASIC %d ############\n\n" % tAsic
    for tChannel in activeChannels:
	continue_flag=0    
        if any(deadChannels[0][tAsic][tChannel][:])==1 and args.mode!="fetp":
            print "Channel %d: DEAD on TDCA" % tChannel
            nDeadTAC+=1
            continue
        
        if any(deadChannels[1][tAsic][tChannel][:])==1 and args.mode!="tdca":
            print "Channel %d:  DEAD on FETP" % tChannel
            nDeadFETP+=1
            continue

        if args.mode!="fetp":
            for i in range(4):
                if TFineMean[0][tAsic][tChannel][i]<128 or TFineMean[0][tAsic][tChannel][i]>512:
                    print "Channel %d:  Out of range Tfine on TDCA: %lf" % (tChannel,TFineMean[0][tAsic][tChannel][i])
                    nTTDCMean+=1
		    continue_flag=1
                    break
	    if(continue_flag):
                continue
        
            for i in range(4):
                if EFineMean[0][tAsic][tChannel][i]<128 or EFineMean[0][tAsic][tChannel][i]>512:
                    print "Channel %d:  Out of range Efine on TDCA: %lf" % (tChannel,EFineMean[0][tAsic][tChannel][i])
                    nETDCMean+=1
		    continue_flag=1
                    break
	    if(continue_flag):
                continue
	    
        ###################################################
	    for i in range(4):
                if TFineRMS[0][tAsic][tChannel][i]>1:
                    print "Channel %d:  High TFine RMS on TDCA: %lf (MANUAL INSPECTION)" % (tChannel,TFineRMS[0][tAsic][tChannel][i])
                    nTTDCRms+=1
		    continue_flag=1
                    break
	    if(continue_flag):
                continue

        ###################################################
	    for i in range(4):
                if EFineRMS[0][tAsic][tChannel][i]>2:
                    print "Channel %d:  High EFine RMS on TDCA: %lf (MANUAL INSPECTION)" % (tChannel,EFineRMS[0][tAsic][tChannel][i])
                    nETDCRms+=1
		    continue_flag=1
                    break
	    if(continue_flag):
                continue


        if args.mode=="tdca":
             continue
      
       ###################################################
	for i in range(4):
            if TFineMean[1][tAsic][tChannel][i]<128 or TFineMean[1][tAsic][tChannel][i]>512:
                print "Channel %d:  Out of range Tfine on FETP: %lf" % (tChannel,TFineMean[1][tAsic][tChannel][i])
                nTFETPMean+=1
		continue_flag=1
		break
	if(continue_flag):
            continue

	###################################################
	for i in range(4):
            if EFineMean[1][tAsic][tChannel][i]<128 or EFineMean[1][tAsic][tChannel][i]>512:
                print "Channel %d:  Out of range Efine on FETP: %lf" % (tChannel,EFineMean[1][tAsic][tChannel][i])
                nEFETPMean+=1
		continue_flag=1
		break
	if(continue_flag):
            continue

        ###################################################
        for i in range(4):
            if (TFineRMS[1][tAsic][tChannel][i]> 1 and TFineRMS[1][tAsic][tChannel][i]<2 and ToT[1][tAsic][tChannel][i]> 50 and ToT[1][tAsic][tChannel][i]<80):
                print "Channel %d:  High RMS: %lf (MANUAL INSPECTION)  and Low TOT: %lf (MANUAL INSPECTION)" % (tChannel,TFineRMS[1][tAsic][tChannel][i], ToT[1][tAsic][tChannel][i])
                nMIRms+=1
		nMIToT+=1
		continue_flag=1
		break
	if(continue_flag):
            continue      
       
        ###################################################
	for i in range(4):
            if TFineRMS[1][tAsic][tChannel][i]> 1 and TFineRMS[1][tAsic][tChannel][i]<2 and ToT[1][tAsic][tChannel][i]<50:
                print "Channel %d:  High RMS: %lf (MANUAL INSPECTION)  and Low TOT: %lf (NOT USABLE)" % (tChannel,TFineRMS[1][tAsic][tChannel][i], ToT[1][tAsic][tChannel][i])
	        nMIRms+=1
	        nNUToT+=1
		continue_flag=1
		break
	if(continue_flag):
            continue 
          
        ###################################################
	for i in range(4):
            if TFineRMS[1][tAsic][tChannel][i]>2 and ToT[1][tAsic][tChannel][i]> 50 and ToT[1][tAsic][tChannel][i]<80:
                print "Channel %d:  High RMS: %lf (NOT USABLE)  and Low TOT: %lf (MANUAL INSPECTION)" % (tChannel,TFineRMS[1][tAsic][tChannel][i], ToT[1][tAsic][tChannel][i])
                nNURms+=1
                nMIToT+=1
		continue_flag=1
		break
	if(continue_flag):
            continue 

        ###################################################
	for i in range(4):
            if TFineRMS[1][tAsic][tChannel][i]>2 and ToT[1][tAsic][tChannel][i]< 50:
                print "Channel %d:  High RMS: %lf (NOT USABLE)  and Low TOT: %lf (NOT USABLE)" % (tChannel,TFineRMS[1][tAsic][tChannel][i], ToT[1][tAsic][tChannel][i])
                nNURms+=1
                nNUToT+=1
		continue_flag=1
		break
	if(continue_flag):
            continue 

       ###################################################
	for i in range(4):
            if TFineRMS[1][tAsic][tChannel][i]>2 and ToT[1][tAsic][tChannel][i]>80:
                print "Channel %d:  High RMS: %lf (NOT USABLE)" % (tChannel,TFineRMS[1][tAsic][tChannel][i])
                nNURms+=1
		continue_flag=1
		break
	if(continue_flag):
            continue 
        
       ###################################################
        for i in range(4):
            if TFineRMS[1][tAsic][tChannel][i]>1 and TFineRMS[1][tAsic][tChannel][i]<2 and ToT[1][tAsic][tChannel][i]>80:
                print "Channel %d:  High RMS: %lf (MANUAL INSPECTION)" % (tChannel,TFineRMS[1][tAsic][tChannel][i])
                nMIRms+=1
		continue_flag=1
		break
	if(continue_flag):
            continue

      ###################################################
        for i in range(4):
            if TFineRMS[1][tAsic][tChannel][i]<1 and ToT[1][tAsic][tChannel][i]< 50 :
                print "Channel %d:  Low TOT: %lf (NOT USABLE)" % (tChannel, ToT[1][tAsic][tChannel][i])
                nNUToT+=1
		continue_flag=1
		break
	if(continue_flag):
            continue

      ###################################################
        for i in range(4):
            if TFineRMS[1][tAsic][tChannel][i]<1 and ToT[1][tAsic][tChannel][i]> 50 and ToT[1][tAsic][tChannel][i]< 80:
                print "Channel %d:  Low TOT: %lf (MANUAL INSPECTION)" % (tChannel, ToT[1][tAsic][tChannel][i])
                nMIToT+=1
		continue_flag=1
		break
        
     

    print "\nSummary:"
    if(args.mode!="fetp"):
        print "Dead on TDCA : %d" %  nDeadTAC
    if(args.mode!="tdca"):
        print "Dead on FETP : %d" %  nDeadFETP
    if(args.mode!="fetp"):
        print "Out of range tFine on TDCA: %d" %  nTTDCMean
        print "Out of range eFine on TDCA: %d" %  nETDCMean
        print "High tFine RMS TDCA: %d" %  nTTDCRms
        print "High eFine RMS TDCA: %d" %  nETDCRms
    if(args.mode!="tdca"):
        print "Out of range tFine on FETP: %d" % nTFETPMean
        print "Out of range eFine on FETP: %d" % nEFETPMean
        print "Manual inspection due to high tFine RMS: %d" %   nMIRms
        print "Not usable due to high tFine RMS: %d" %  nNURms 
        print "Manual inspection due to low ToT: %d" %  nMIToT 
        print "Not usable due to low ToT: %d" %   nNUToT


rootFile.Write()
rootFile.Close()

uut.setAllHVDAC(0)
