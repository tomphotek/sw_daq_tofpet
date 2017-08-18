#include <boost/python.hpp>
#include <boost/python/suite/indexing/vector_indexing_suite.hpp>
#include <boost/python/numpy.hpp>
using namespace boost::python;

#include <memory>

#include "SHM.hpp"

using namespace DAQd;

inline void destroyArrayOwnerPtr(void *p) {
   std::shared_ptr<PackedEventVec> *b = reinterpret_cast<std::shared_ptr<PackedEventVec>*>(p);
   delete b;
}

inline boost::python::object makeArrayOwner(std::shared_ptr<PackedEventVec> & x) {
    boost::python::handle<> h(PyCObject_FromVoidPtr(new std::shared_ptr<PackedEventVec>(x),
        &destroyArrayOwnerPtr));
    return boost::python::object(h);
}

numpy::ndarray frame2numpy(SHM& obj, int index) {
    std::shared_ptr<PackedEventVec> frame = obj.getRawFrame(index);
    tuple shape = make_tuple(frame->size(), 7);
    tuple stride = make_tuple(sizeof(PackedEvent), sizeof(uint16_t));
    numpy::dtype dt = numpy::dtype(str("u2"), false);

    object own = makeArrayOwner(frame);
    numpy::ndarray arr = numpy::from_data(frame->data(), dt, shape, stride, own);
    return arr;
}

BOOST_PYTHON_MODULE(DSHM) 
{
    numpy::initialize();

	class_<SHM>("SHM", init<std::string>())
		.def("getSizeInBytes", &SHM::getSizeInBytes)
		.def("getSizeInFrames", &SHM::getSizeInFrames)
		.def("getFrameSize", &SHM::getFrameSize)
		.def("getFrameWord", &SHM::getFrameWord)
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
		//.def("getRawFrame", &SHM::getRawFrame)
		.def("getNumpyFrame", &frame2numpy)
	;
}
