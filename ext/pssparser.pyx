#****************************************************************************
#* pssparser.pyx
#*
#* pssparser extension source
#****************************************************************************
cimport pssparser_decl
cimport cpython.ref as cpy_ref

cpdef doit(int a):
    print("doit: " + str(a))
    
cdef class BaseMarkerListener(object):
    cdef pssparser_decl.BaseMarkerListener *thisptr

    def __cinit__(self):
        self.thisptr = new pssparser_decl.BaseMarkerListener()
        pass

cdef class AstBuilder(object):
    cdef pssparser_decl.AstBuilder      *thisptr
   
    def __cinit__(self, BaseMarkerListener marker_l):
        self.thisptr = new pssparser_decl.AstBuilder(marker_l.thisptr)
        pass

cdef class PyStreamBuf(object):
    cdef pssparser_decl.PyStreamBuf     *thisptr
    
    def __cinit__(self, istream):
        self.thisptr = new pssparser_decl.PyStreamBuf(<cpy_ref.PyObject *>(istream))
        
cdef public api void cy_cls_call_my_method1(object self, int a):
    self.my_method1(a)

