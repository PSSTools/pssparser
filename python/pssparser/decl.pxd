

from libcpp.pair cimport pair as cpp_pair
from libcpp.set cimport set as cpp_set
from libcpp.string cimport string as cpp_string
from libcpp.vector cimport vector as cpp_vector
from libcpp.memory cimport unique_ptr
from libc.stdint cimport intptr_t
from libc.stdint cimport int32_t
from libc.stdint cimport uint32_t
from libc.stdint cimport uint64_t
from libc.stdint cimport int64_t
from libcpp cimport bool
cimport cpython.ref as cpy_ref
cimport pssast_decl as ast
cimport ciostream


cdef extern from "pssp/IFactory.h" namespace "pssp":
    cdef cppclass IFactory:
        IAstBuilder *mkAstBuilder()

cdef extern from "pssp/IAstBuilder.h" namespace "pssp":
    cdef cppclass IAstBuilder:

        void build(
            ast.IGlobalScope        *scope,
            ciostream.istream       *in_s,
            IMarkerListener         *marker_l)


cdef extern from "pssp/IMarker.h" namespace "pssp":
    cdef enum MarkerSeverityE:
        Error "pssp::MarkerSeverityE::Error"
        Warn "pssp::MarkerSeverityE::Warn"
        Info "pssp::MarkerSeverityE::Info"
        Hint "pssp::MarkerSeverityE::Hint"
        NumLevels "pssp::MarkerSeverityE::NumLevels"

    cdef cppclass Location:
        int32_t            file;
        int32_t            line;
        int32_t            pos;

    cdef cppclass IMarker:
        const cpp_string &msg() const
        MarkerSeverityE severity() const
        const Location &loc() const;
        IMarker *clone() const

cdef extern from "pssp/IMarkerListener.h" namespace "pssp":
    cdef cppclass IMarkerListener:
        void marker(const IMarker *m)
        bool hasSeverity(MarkerSeverityE s)
