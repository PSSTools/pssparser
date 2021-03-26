#*****************************************************************************
#* 
#*****************************************************************************
cimport cpython.ref as cpy_ref

cdef extern from 'IMarkerListener.h' namespace 'pssp':
    cpdef cppclass IMarkerListener:
        pass
    
cdef extern from "BaseMarkerListener.h" namespace "pssp":
    cpdef cppclass BaseMarkerListener(IMarkerListener):
    
        BaseMarkerListener()
        pass

cdef extern from 'AstBuilder.h' namespace 'pssp':
    cpdef cppclass AstBuilder:
        AstBuilder(IMarkerListener *marker_l)
#        void build(GlobalScope *global, )

cdef extern from 'PyStreamBuf.h' namespace 'pssp':

    cpdef cppclass PyStreamBuf:
        PyStreamBuf(cpy_ref.PyObject *istream)
    
        