#****************************************************************************
#* iostream.pyx
#*
#* Python I/O stream to C++ I/O stream bridge
#****************************************************************************

# cython: language=c++

cimport cpython.ref as cpy_ref
cimport iostream_decl

cdef extern from 'pyiostream.h' namespace "pyiostream":
    cpdef cppclass istream(iostream_decl.istream):
        istream(cpy_ref.PyObject *)

