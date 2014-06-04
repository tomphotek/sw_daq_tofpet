#ifndef __TOFPET__RAWV2_HPP__DEFINED__
#define __TOFPET__RAWV2_HPP__DEFINED__
#include <Common/Task.hpp>
#include <Core/EventSourceSink.hpp>
#include <Core/Event.hpp>
#include <stdio.h>
#include <string>
#include <vector>
#include <stdio.h>
#include <stdint.h>

namespace DAQ { namespace TOFPET { 
	using namespace ::DAQ::Common;
	using namespace ::DAQ::Core;
	using namespace std;
	
	struct RawEventV2 {
		uint32_t frameID;
		uint16_t asicID;
		uint16_t channelID;
		uint16_t tacID;
		uint16_t tCoarse;
		uint16_t eCoarse;
		uint16_t tFine;
		uint16_t eFine;
		int64_t channelIdleTime;
		int64_t tacIdleTime;
	};

	
	class RawScannerV2 {
	public:
		RawScannerV2(FILE *indexFile);
		~RawScannerV2();
		
		int getNSteps();
		void getStep(int stepIndex, float &step1, float &step2, unsigned long long &eventsBegin, unsigned long long &eventsEnd);
	private:
		struct Step {
			float step1;
			float step2;
			unsigned long long eventsBegin;
			unsigned long long eventsEnd;
		};
		
		vector<Step> steps;
		
	};
	
	class RawReaderV2 : public ThreadedTask, public EventSource<RawPulse> {
	
	public:
		RawReaderV2(FILE *dataFile, float T, unsigned long long eventsBegin, unsigned long long eventsEnd, EventSink<RawPulse> *sink);
		~RawReaderV2();
		
		virtual void run();

	private:
		unsigned long eventsBegin;
		unsigned long eventsEnd;
		FILE *dataFile;
		double T;
		bool isOutlier(long long currentFrameID, FILE *dataFile, int entry, int N);
	};
	
}}
#endif