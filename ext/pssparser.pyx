#****************************************************************************
#* pssparser.pyx
#*
#* pssparser extension source
#****************************************************************************
cimport pssparser_decl

cdef doit(int a):
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
    


