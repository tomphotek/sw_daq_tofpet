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

/**
Wraps SHM::getRawFrame() but packages the PackedEventVec memory region
in a numpy array object.
*/
numpy::ndarray frame2numpy(SHM& obj, int index) {
    // Get one frame of data, the PackedEventVec contains a continuous
    // region of structs with even packing. A shared_ptr must be used
    // here as otherwise C++ would free the Vector's memory once this
    // func returns.
    std::shared_ptr<PackedEventVec> frame = obj.getRawFrame(index);

    // Setup up numpy array parameters
    tuple shape = make_tuple(frame->size(), 7);
    tuple stride = make_tuple(sizeof(PackedEvent), sizeof(uint16_t));
    numpy::dtype dt = numpy::dtype(str("u2"), false);

    // The created numpy array must have a way to indicate to C++ that
    // the created python object has been destroyed. To do this an empty
    // PyObject (or python::object to boost) is created, that when the
    // the numpy array's ref count in python reaches zero it calls a
    // destruction function (destroyArrayOwnerPtr), that deletes it's
    // reference to the shared_ptr, then C++ can decrement its reference
    // counter and free memory if required.
    object own = makeArrayOwner(frame);

    // Finally build the numpy array
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
