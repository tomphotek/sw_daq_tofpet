#include <TFile.h>
#include <TNtuple.h>
#include <Common/Constants.hpp>
#include <TOFPET/RawV2.hpp>
#include <TOFPET/P2Extract.hpp>
#include <Core/SingleReadoutGrouper.hpp>
#include <Core/FakeCrystalPositions.hpp>
#include <Core/ComptonGrouper.hpp>
#include <Core/CoincidenceGrouper.hpp>
#include <assert.h>
#include <math.h>
#include <string.h>

using namespace DAQ;
using namespace DAQ::Core;
using namespace DAQ::TOFPET;
using namespace std;

struct EventOut {
	float		step1;
	float 		step2;
	long long	time;			// Absolute event time, in ps
	unsigned short	channel;		// Channel ID
	float		tot;			// Time-over-Threshold, in ns
	unsigned char	tac;			// TAC ID
	unsigned char 	badEvent;		// 0 if OK, 1 if bad
} __attribute__((packed));


class EventWriter : public EventSink<Pulse> {
public:
	EventWriter(FILE *dataFile, float step1, float step2) 
	: dataFile(dataFile), step1(step1), step2(step2) {
		
	};
	
	~EventWriter() {
		
	};

	void pushEvents(EventBuffer<Pulse> *buffer) {
		if(buffer == NULL) return;	
		
		unsigned nEvents = buffer->getSize();
		for(unsigned i = 0; i < nEvents; i++) {
			Pulse & p = buffer->get(i);
			EventOut e = { step1, step2, p.time, p.channelID, p.energy, p.raw.d.tofpet.tac, p.badEvent ? 1 : 0 };
			fwrite(&e, sizeof(e), 1, dataFile);
		}
		
		delete buffer;
	};
	
	void pushT0(double t0) { };
	void finish() { };
	void report() { };
private: 
	FILE *dataFile;
	float step1;
	float step2;
};

int main(int argc, char *argv[])
{
	if (argc != 4) {
		fprintf(stderr, "USAGE: %s <setup_file> <rawfiles_prefix> <output_file.root>\n", argv[0]);
		fprintf(stderr, "setup_file - File containing paths to tdc calibration files and tq correction files (optional)\n");
		fprintf(stderr, "rawfiles_prefix - Path to raw data files prefix\n");
		fprintf(stderr, "output_file.root - ROOT output file containing binary single events\n");
		return 1;
	}
	assert(argc == 4);
	char *inputFilePrefix = argv[2];

	char dataFileName[512];
	char indexFileName[512];
	sprintf(dataFileName, "%s.raw2", inputFilePrefix);
	sprintf(indexFileName, "%s.idx2", inputFilePrefix);
	FILE *inputDataFile = fopen(dataFileName, "r");
	FILE *inputIndexFile = fopen(indexFileName, "r");
	
	DAQ::TOFPET::RawScannerV2 * scanner = new DAQ::TOFPET::RawScannerV2(inputIndexFile);
	

	TOFPET::P2 *lut = new TOFPET::P2(SYSTEM_NCRYSTALS);

	if (strcmp(argv[1], "none") == 0) {
		lut->setAll(2.0);
		printf("BIG FAT WARNING: no calibration\n");
	} 
	else {
		lut->loadFiles(argv[1], true, false, 0,0);
	}
	
	FILE *lmFile = fopen(argv[3], "w");
	
	int N = scanner->getNSteps();
	for(int step = 0; step < N; step++) {
		Float_t step1;
		Float_t step2;
		unsigned long long eventsBegin;
		unsigned long long eventsEnd;
		scanner->getStep(step, step1, step2, eventsBegin, eventsEnd);
		printf("Step %3d of %3d: %f %f (%llu to %llu)\n", step+1, scanner->getNSteps(), step1, step2, eventsBegin, eventsEnd);
		if(N!=1){
			if (strcmp(argv[1], "none") == 0) {
				lut->setAll(2.0);
				printf("BIG FAT WARNING: no calibration file\n");
			} 
			else{
				lut->loadFiles(argv[1], true, true,step1,step2);
			}
		}

		DAQ::TOFPET::RawReaderV2 *reader = new DAQ::TOFPET::RawReaderV2(inputDataFile, 6.25E-9,  eventsBegin, eventsEnd, 
				new P2Extract(lut, false, 0.0, 0.20,
				new EventWriter(lmFile, step1, step2

		)));
		
		reader->wait();
		delete reader;
	}
	

	fclose(lmFile);
	fclose(inputDataFile);
	fclose(inputIndexFile);
	return 0;
	
}
