#include <boost/python.hpp>
using namespace boost::python;

#include "SHM.hpp"

BOOST_PYTHON_MODULE(DSHM) 
{
	class_<SHM>("SHM", init<std::string>())
		.def("getSize", &SHM::getSize)
		.def("getFrameID", &SHM::getFrameID)
		.def("getFrameLost", &SHM::getFrameLost)
		.def("getNEvents", &SHM::getNEvents)
		.def("getEventType", &SHM::getEventType)
		.def("getTCoarse", &SHM::getTCoarse)
		.def("getECoarse", &SHM::getECoarse)
		.def("getTFine", &SHM::getTFine)
		.def("getEFine", &SHM::getEFine)
		.def("getAsicID", &SHM::getAsicID)
		.def("getChannelID", &SHM::getChannelID)
		.def("getTACID", &SHM::getTACID)
		.def("getTACIdleTime", &SHM::getTACIdleTime)
		.def("getChannelIdleTime", &SHM::getChannelIdleTime)
	;
}
