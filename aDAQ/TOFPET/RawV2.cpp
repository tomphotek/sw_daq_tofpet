#include "RawV2.hpp"

#include <algorithm>
#include <functional>
#include <math.h>
#include <set>
#include <limits.h>
#include <iostream>

using namespace std;
using namespace DAQ::Core;
using namespace DAQ::TOFPET;

static const unsigned outBlockSize = 128*1024;
static const unsigned maxEventsPerFrame = 16*1024;

RawReaderV2::RawReaderV2(FILE *dataFile, float T, unsigned long long eventsBegin, unsigned long long eventsEnd, EventSink<RawPulse> *sink)
	: EventSource<RawPulse>(sink), dataFile(dataFile), T(T)
{
	this->eventsBegin = eventsBegin;
	this->eventsEnd = eventsEnd;
	start();
}

RawReaderV2::~RawReaderV2()
{
}


struct SortEntry {
	short tCoarse;
	RawPulse *event;	
};
static bool operator< (SortEntry lhs, SortEntry rhs) { return lhs.tCoarse < rhs.tCoarse; }

static const long long wrapPeriod = 1LL<<31 - 1;


static bool isAfter(long long  frameID2, long long frameID1)
{
	if (frameID2 >= frameID1)
		return true;
	
	if(frameID1 > 0.99 * wrapPeriod && frameID2 < 0.01 * wrapPeriod)
		return true;
	
	return false;
}
bool RawReaderV2::isOutlier(long long currentFrameID, FILE *dataFile, int entry, int N)
{	
	RawEventV2 rawEvent;
	fseek(dataFile, entry * sizeof(RawEventV2), SEEK_SET);
	fread(&rawEvent, sizeof(RawEventV2), 1, dataFile);
	
	if(rawEvent.frameID == currentFrameID) {
/*		printf("C1: good!\n");*/
		return false;
	}
	
	if(rawEvent.frameID == currentFrameID + 1) {
		return false;
	}
	
	if(!isAfter(rawEvent.frameID, currentFrameID)) {
//		printf("C2: outlier\n");
		return true;
	}
	
	
	long long thisFrameID = rawEvent.frameID;
	
	set<long long> frameList;
	int j = entry;
	while(j < eventsEnd && frameList.size() < N) {
		
		fseek(dataFile, j * sizeof(RawEventV2), SEEK_SET);		
		fread(&rawEvent, sizeof(RawEventV2), 1, dataFile);
		
		frameList.insert(rawEvent.frameID);
		j += 1;
	}
	
	bool frameOK = true;
/*	for (set<long long>::iterator it = frameList.begin(); it != frameList.end(); it++) {
		bool c = isAfter(*it, thisFrameID) && (*it - thisFrameID) < 100*N;
		if(!c) { 
			printf("Fail check for %lld vs %lld\n", thisFrameID, *it); 
			
		}
		frameOK &= c;
	}*/
	
	set<long long>::iterator it1 = frameList.begin();
	set<long long>::iterator it2 = it1;
	it1++;
	for(; it1 != frameList.end(); it1++, it2++) {
		bool c = isAfter(*it1, *it2);
/*		if(!c) { 
			printf("Fail check for %lld vs %lld\n", *it2, *it1);
		}*/
		frameOK &= c;
		
	}
	
	fseek(dataFile, entry * sizeof(RawEventV2), SEEK_SET);
	return !frameOK;
	
}

void RawReaderV2::run()
{

	unsigned nWraps = 0;
	
	EventBuffer<RawPulse> *outBuffer = NULL;
	
	RawPulse framePulses[maxEventsPerFrame];
	SortEntry sortArray[maxEventsPerFrame];
	int nEventsInFrame = 0;
	
	long long tMax = 0, lastTMax = 0;

	sink->pushT0(0);
	
	long long minFrameID = LLONG_MAX;
	long long maxFrameID = LLONG_MIN;
	
	fprintf(stderr, "Reading %llu to %llu\n", eventsBegin, eventsEnd);
	fseek(dataFile, eventsBegin * sizeof(RawEventV2), SEEK_SET);
	
	int maxReadBlock = 1024*1024;
	RawEventV2 *rawEvents = new RawEventV2[maxReadBlock];

	unsigned long long readPointer = eventsBegin;
	while (readPointer < eventsEnd) {
		unsigned long long count = eventsEnd - readPointer;
		if(count > maxReadBlock) count = maxReadBlock;
		int r = fread(rawEvents, sizeof(RawEventV2), count, dataFile);
		if(r <= 0) break;
		readPointer += r;
		
		for(int j = 0; j < r; j++) {
			RawEventV2 &rawEvent = rawEvents[j];

			if(outBuffer == NULL) {
				outBuffer = new EventBuffer<RawPulse>(outBlockSize);
			}
		

			RawPulse &p = outBuffer->getWriteSlot();
		
			// Carefull with the float/double/integer conversions here..
			p.d.tofpet.T = T * 1E12;
			p.time = (1024LL * rawEvent.frameID + rawEvent.tCoarse) * p.d.tofpet.T;
			p.timeEnd = (1024LL * rawEvent.frameID + rawEvent.eCoarse) * p.d.tofpet.T;
			if((p.timeEnd - p.time) < -256*p.d.tofpet.T) p.timeEnd += (1024LL * p.d.tofpet.T);
			p.channelID = 64 * rawEvent.asicID + rawEvent.channelID;
			p.channelIdleTime = rawEvent.channelIdleTime;
			p.region = (64 * rawEvent.asicID + rawEvent.channelID) / 16;
			p.feType = RawPulse::TOFPET;
			p.d.tofpet.frameID = rawEvent.frameID;
			p.d.tofpet.tac = rawEvent.tacID;
			p.d.tofpet.tcoarse = rawEvent.tCoarse;
			p.d.tofpet.ecoarse = rawEvent.eCoarse;
			p.d.tofpet.tfine =  rawEvent.tFine;
			p.d.tofpet.efine = rawEvent.eFine;
			p.channelIdleTime = rawEvent.channelIdleTime;
			p.d.tofpet.tacIdleTime = rawEvent.tacIdleTime;
			
		
			if(rawEvent.frameID < minFrameID) minFrameID = rawEvent.frameID;
			if(rawEvent.frameID > maxFrameID) maxFrameID = rawEvent.frameID;
				
			if(p.channelID >= 128)
				continue;
		
			if(p.time > tMax)
				tMax = p.time;
		
			outBuffer->pushWriteSlot();
		
			if(outBuffer->getSize() >= (outBlockSize - 512)) {
				outBuffer->setTMin(lastTMax);
				outBuffer->setTMax(tMax);		
				sink->pushEvents(outBuffer);
				outBuffer = NULL;
			}
		}
	}
	
	delete [] rawEvents;

	
	if(outBuffer != NULL) {
		outBuffer->setTMin(lastTMax);
		outBuffer->setTMax(tMax);		
		sink->pushEvents(outBuffer);
		outBuffer = NULL;
		
	}
	
	sink->finish();
	
	fprintf(stderr, "RawReaderV2 report\n");
	fprintf(stderr, "\t%16lld minFrameID\n", minFrameID);
	fprintf(stderr, "\t%16lld maxFrameID\n", maxFrameID);
	sink->report();
}

RawScannerV2::RawScannerV2(FILE *indexFile) :
	steps(vector<Step>())
{
	float step1;
	float step2;
	unsigned long stepBegin;
	unsigned long stepEnd;

	
	while(fscanf(indexFile, "%f %f %llu %llu\n", &step1, &step2, &stepBegin, &stepEnd) == 4) {
		Step step = { step1, step2, stepBegin, stepEnd };
		steps.push_back(step);
	}
}

RawScannerV2::~RawScannerV2()
{
}

int RawScannerV2::getNSteps()
{
	return steps.size();
}


void RawScannerV2::getStep(int stepIndex, float &step1, float &step2, unsigned long long &eventsBegin, unsigned long long &eventsEnd)
{
	Step &step = steps[stepIndex];
	step1 = step.step1;
	step2 = step.step2;
	eventsBegin = step.eventsBegin;
	eventsEnd = step.eventsEnd;
}

