#****************************************************************************
#* pssparser.pyx
#*
#* pssparser extension source
#****************************************************************************
cimport pssparser_decl
cimport cpython.ref as cpy_ref
cimport iostream

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
    
    cpdef parse(self, GlobalScope glbl, in_s):
        cdef iostream.istream *is_w
        is_w = new iostream.istream(<cpy_ref.PyObject *>(in_s)) 

   #     print("thisptr %p" % str(self.thisptr))
   #     print("glbl.thisptr %p" % str(glbl.thisptr))        
        self.thisptr.build(
            <pssast_decl.GlobalScope *>(glbl.thisptr), 
            is_w)
        
        del is_w
        
cpdef GlobalScope mkGlobalScope(int fileid):
    """Create a new GlobalScope object"""
    ret = GlobalScope()
    ret.owned = True
    ret.thisptr = new pssast_decl.GlobalScope(fileid)
    return ret


