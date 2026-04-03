# cython: language_level=3

import ctypes
from enum import IntEnum
import os
import sys
cimport debug_mgr.core as dm_core
cimport debug_mgr.decl as dm_decl
cimport pssparser.ast as ast
cimport pssparser.ast_decl as ast_decl
cimport pssparser.decl as decl
from ciostream.core cimport cistream
from libc.stdint cimport intptr_t
from libcpp.vector cimport vector as std_vector
from libcpp.cast cimport dynamic_cast

# Import the C++ resolveSymbolPathRef function
cdef extern from "PyParserUtils.h" namespace "pssp":
    ast_decl.IScopeChild *c_resolveSymbolPathRef "pssp::PyParserUtils::resolveSymbolPathRef" (
        dm_decl.IDebugMgr              *dmgr,
        ast_decl.ISymbolChildrenScope    *root,
        const ast_decl.ISymbolRefPath    *ref)

cdef Factory _inst = None
cdef class Factory(object):
    def __init__(self):
        self._hndl = NULL
        pass

    cpdef ast.Factory getAstFactory(self):
        return ast.Factory.mk(self._hndl.getAstFactory())

    cpdef dm_core.DebugMgr getDebugMgr(self):
        return dm_core.DebugMgr.mk(self._hndl.getDebugMgr(), False)

    cpdef void loadStandardLibrary(self,
        AstBuilder          ast_builder,
        ast.GlobalScope     glbl_scope):
        self._hndl.loadStandardLibrary(
            ast_builder._hndl,
            glbl_scope.asGlobalScope())

    cpdef LookupLocationResult lookupLocation(
        self,
        ast.RootSymbolScope     root,
        ast.Scope               scope,
        int                     lineno,
        int                     linepos):
        cdef decl.ILookupLocationResult *res
        res = self._hndl.lookupLocation(
            root.asRootSymbolScope(),
            scope.asScope(),
            lineno,
            linepos)
        
        if res != NULL:
            return LookupLocationResult.mk(res, True)
        else:
            return None

    cpdef AstBuilder mkAstBuilder(self, MarkerListener marker_l):
        return AstBuilder.mk(self._hndl.mkAstBuilder(marker_l._hndl))

    cpdef Linker mkAstLinker(self):
        return Linker.mk(self._hndl.mkAstLinker(), True)

    cpdef SymbolTableIterator mkAstSymbolTableIterator(self,
        ast.SymbolScope     root):
        return SymbolTableIterator.mk(self._hndl.mkAstSymbolTableIterator(root.asSymbolScope()))

    cpdef MarkerCollector mkMarkerCollector(self):
        return MarkerCollector.mk(self._hndl.mkMarkerCollector(), True)

    cpdef TaskFindElementByLocation mkTaskFindElementByLocation(self):
        return TaskFindElementByLocation.mk(
            self._hndl.mkTaskFindElementByLocation(), True)

    cdef init(self, dm_core.Factory f, ast.Factory ast_f):
        self._hndl.init(f._hndl.getDebugMgr(), ast_f._hndl)

    @staticmethod
    def inst():
        cdef Factory factory
        global _inst
        if _inst is None:
            ext_dir = os.path.dirname(os.path.abspath(__file__))
            build_dir = os.path.abspath(os.path.join(ext_dir, "../../build"))

            if sys.platform == 'darwin':
                libname = "libpssparser.dylib"
            elif sys.platform == 'win32':
                libname = "pssparser.dll"
            else:
                libname = "libpssparser.so"
            core_lib = None

            for libdir in ("lib", "lib64", "src"):
                cand = os.path.join(build_dir, libdir, libname)
                if os.path.isfile(cand):
                    core_lib = cand
                    break

            if core_lib is None:
                core_lib = os.path.join(ext_dir, libname)

            if not os.path.isfile(core_lib):
                raise Exception("Extension library core \"%s\" doesn't exist" % core_lib)

            # On macOS, preload antlr4 runtime from the same directory so that
            # libpssparser.dylib and libast.dylib can find it (RPATH $ORIGIN is Linux-only).
            if sys.platform == 'darwin':
                import glob as _glob
                for _al in _glob.glob(os.path.join(os.path.dirname(core_lib), 'libantlr4-runtime*.dylib')):
                    ctypes.cdll.LoadLibrary(_al)

            # Workaround: debug_mgr.core.Factory.inst() looks for 'libdebug-mgr.so'
            # but some platform wheels (e.g. Windows) ship 'debug-mgr.dll' instead.
            # Create an alias so the load succeeds.
            if sys.platform == 'win32':
                import debug_mgr as _dm_pkg
                import shutil as _shutil
                _dm_dir = os.path.dirname(os.path.abspath(_dm_pkg.__file__))
                _dm_so = os.path.join(_dm_dir, 'libdebug-mgr.so')
                if not os.path.isfile(_dm_so):
                    _dm_dll = os.path.join(_dm_dir, 'debug-mgr.dll')
                    if os.path.isfile(_dm_dll):
                        _shutil.copy(_dm_dll, _dm_so)
                # Ensure build/lib and build/bin are in the DLL search path
                if hasattr(os, 'add_dll_directory'):
                    os.add_dll_directory(_dm_dir)
                    os.add_dll_directory(os.path.join(build_dir, "lib"))
                    os.add_dll_directory(os.path.join(build_dir, "bin"))

            so = ctypes.cdll.LoadLibrary(core_lib)
            func = so.pssparser_getFactory
            func.restype = ctypes.c_void_p

            hndl = <decl.IFactoryP>(<intptr_t>(func()))
            factory = Factory()
            factory._hndl = hndl
            factory.init(
                dm_core.Factory.inst(),
                ast.Factory.inst())
            _inst = factory

        return _inst

cdef class AstBuilder(object):

    def __dealloc__(self):
        if self._owned:
            del self._hndl

    cpdef build(self,
        ast.GlobalScope         root,
                                in_s):
        cdef cistream c_in_s
        
        c_in_s = cistream(in_s)

        self._hndl.build(
            root.asGlobalScope(),
            c_in_s.stream())

    cpdef void setCollectDocStrings(self, bool collect):
        self._hndl.setCollectDocStrings(collect)

    cpdef bool getCollectDocStrings(self):
        return self._hndl.getCollectDocStrings()

    cpdef void setEnableProfile(self, bool enable):
        self._hndl.setEnableProfile(enable)

    cpdef bool getEnableProfile(self):
        return self._hndl.getEnableProfile()

    cpdef ParseProfileInfo getProfileInfo(self):
        cdef decl.IParseProfileInfo *profile_info
        profile_info = self._hndl.getProfileInfo()
        if profile_info != NULL:
            return ParseProfileInfo.mk(profile_info, True)
        return None

    @staticmethod
    cdef AstBuilder mk(decl.IAstBuilder *hndl, bool owned=False):
        ret = AstBuilder()
        ret._hndl = hndl
        ret._owned = owned
        return ret

cdef class Linker(object):
    def __dealloc__(self):
        if self._owned:
            del self._hndl

    cpdef ast.RootSymbolScope link(self,
        MarkerListener          marker_l,
        scopes):
        cdef std_vector[ast_decl.IGlobalScopeP] scopes_n
        cdef ast_decl.IRootSymbolScope *ret_h

        for s in scopes:
            scope = <ast.GlobalScope>(s)
            scope._owned = False
            scopes_n.push_back(scope.asGlobalScope())

        ret_h = self._hndl.link(marker_l._hndl, scopes_n)

        if ret_h == NULL:
            return None
        else:
            return ast.RootSymbolScope.mk(ret_h, True)

    cpdef ast.RootSymbolScope linkOverlay(self,
        MarkerListener          marker_l,
        ast.RootSymbolScope     base_symtab,
        ast.GlobalScope         overlay):
        cdef ast_decl.IRootSymbolScope *ret_h

        ret_h = self._hndl.linkOverlay(
            marker_l._hndl,
            base_symtab.asRootSymbolScope(),
            overlay.asGlobalScope())

        if ret_h == NULL:
            return None
        else:
            return ast.RootSymbolScope.mk(ret_h, True)

    @staticmethod
    cdef Linker mk(decl.ILinker *hndl, bool owned=True):
        ret = Linker()
        ret._hndl = hndl
        ret._owned = owned
        return ret

class MarkerSeverityE(IntEnum):
    Error = decl.MarkerSeverityE.Severity_Error
    Warn = decl.MarkerSeverityE.Severity_Warn
    Info = decl.MarkerSeverityE.Severity_Info
    Hint = decl.MarkerSeverityE.Severity_Hint
    NumLevels = decl.MarkerSeverityE.Severity_NumLevels


class FindElementKindE(IntEnum):
    Expr = decl.FindElementKindE_Expr
    Field = decl.FindElementKindE_Field
    Type = decl.FindElementKindE_Type

cdef class Location(object):

    def __init__(self, file, line, pos):
        self._file = file
        self._line = line
        self._pos = pos

    @property
    def file(self):
        return self._file

    @property
    def line(self):
        return self._line

    @property
    def pos(self):
        return self._pos

cdef class LookupLocationResult(object):

    @staticmethod
    cdef LookupLocationResult mk(decl.ILookupLocationResult *hndl, bool owned=True):
        ret = LookupLocationResult()
        ret._hndl = hndl
        ret._owned = owned
        return ret


cdef class TaskFindElementByLocation(object):
    cpdef TaskFindElementResult find(self,
        ast.SymbolScope         root,
        ast.GlobalScope         file,
        int                     lineno,
        int                     linepos,
        int                     fuzz=0):
        cdef decl.ITaskFindElementByLocationResult res
        res = self._hndl.find(
            root.asSymbolScope(),
            file.asGlobalScope(),
            lineno,
            linepos,
            fuzz)
        return TaskFindElementResult.mk(res)

    @staticmethod
    cdef TaskFindElementByLocation mk(decl.ITaskFindElementByLocation *hndl, bool owned=True):
        ret = TaskFindElementByLocation()
        ret._hndl = hndl
        ret._owned = owned
        return ret


cdef class TaskFindElementResult(object):
    @property
    def is_valid(self):
        return self._hndl.isValid

    @property
    def target_kind(self):
        return FindElementKindE(int(self._hndl.targetKind))

    @property
    def target(self):
        return self._target

    @staticmethod
    cdef TaskFindElementResult mk(decl.ITaskFindElementByLocationResult hndl):
        cdef TaskFindElementResult ret = TaskFindElementResult()
        cdef ast.ObjFactory of
        ret._hndl = hndl
        ret._target = None
        if hndl.target != NULL:
            of = ast.ObjFactory()
            hndl.target.accept(<ast_decl.VisitorBase *>(of._hndl))
            ret._target = of._obj
        return ret

cdef class Marker(object):

    cpdef str msg(self):
        return self._hndl.msg().decode()

    cpdef severity(self):
        cdef int severity_i = int(self._hndl.severity())
        return MarkerSeverityE(severity_i)

    cpdef Location loc(self):
        cdef const ast_decl.Location *loc_ref = &(self._hndl.loc())
        return Location(loc_ref.fileid, loc_ref.lineno, loc_ref.linepos)

    @staticmethod
    cdef Marker mk(decl.IMarker *hndl, bool owned=True):
        ret = Marker()
        ret._hndl = hndl
        ret._owned = owned
        return ret

cdef class MarkerListener(object):

    cpdef bool hasSeverity(self, s):
        cdef int s_i = int(s)
        return self._hndl.hasSeverity(<decl.MarkerSeverityE>(s_i))
    pass

cdef class MarkerCollector(MarkerListener):

    cpdef markers(self):
        ret = []
        for i in range(self.asCollector().markers().size()):
            ret.append(Marker.mk(
                self.asCollector().markers().at(i).get(),
                False
            ))
        return ret

    cpdef int numMarkers(self):
        return self.asCollector().markers().size()

    cpdef Marker getMarker(self, int idx):
        cdef decl.IMarkerP marker = self.asCollector().markers().at(idx).get()
        return Marker.mk(marker, False)

    cdef decl.IMarkerCollector *asCollector(self):
        return <decl.IMarkerCollector *>dynamic_cast[decl.IMarkerCollectorP](self._hndl)

    @staticmethod
    cdef MarkerCollector mk(decl.IMarkerCollector *hndl, bool owned=True):
        ret = MarkerCollector()
        ret._hndl = hndl
        ret._owned = owned
        return ret

cdef class SymbolTableIterator(object):

    @staticmethod
    cdef SymbolTableIterator mk(decl.ISymbolTableIterator *hndl, bool owned=True):
        ret = SymbolTableIterator()
        ret._hndl = hndl
        ret._owned = owned
        return ret

cpdef ast.ScopeChild resolveSymbolPathRef(
    ast.SymbolChildrenScope         root,
    ast.SymbolRefPath               ref):
    cdef dm_core.DebugMgr dmgr = Factory.inst().getDebugMgr()
    cdef ast_decl.IScopeChild *ret
    cdef ast.ObjFactory of

    if ref is None:
        raise Exception("Cannot resolve a None ref")
    else:
        ret = c_resolveSymbolPathRef(
            dmgr._hndl,
            root.asSymbolChildrenScope(),
            ref.asSymbolRefPath())

        if ret == NULL:
            return None
        else:
            of = ast.ObjFactory()
            ret.accept(<ast_decl.VisitorBase *>(of._hndl))
            return of._obj

cdef class DecisionProfileInfo(object):

    def __dealloc__(self):
        if self._owned:
            del self._hndl

    @property
    def decision(self):
        return self._hndl.getDecision()

    @property
    def invocations(self):
        return self._hndl.getInvocations()

    @property
    def time_in_prediction(self):
        return self._hndl.getTimeInPrediction()

    @property
    def sll_lookahead_ops(self):
        return self._hndl.getSLLLookaheadOps()

    @property
    def ll_lookahead_ops(self):
        return self._hndl.getLLLookaheadOps()

    @property
    def sll_atn_transitions(self):
        return self._hndl.getSLLATNTransitions()

    @property
    def ll_atn_transitions(self):
        return self._hndl.getLLATNTransitions()

    @property
    def ll_fallback(self):
        return self._hndl.getLLFallback()

    @property
    def ambiguity_count(self):
        return self._hndl.getAmbiguityCount()

    @property
    def context_sensitivity_count(self):
        return self._hndl.getContextSensitivityCount()

    @property
    def error_count(self):
        return self._hndl.getErrorCount()

    @property
    def max_lookahead(self):
        return self._hndl.getMaxLookahead()

    @staticmethod
    cdef DecisionProfileInfo mk(decl.IDecisionProfileInfo *hndl, bool owned=True):
        ret = DecisionProfileInfo()
        ret._hndl = hndl
        ret._owned = owned
        return ret

cdef class ParseProfileInfo(object):

    def __dealloc__(self):
        if self._owned:
            del self._hndl

    def get_decision_info(self):
        cdef std_vector[decl.IDecisionProfileInfo*] decisions
        cdef size_t i
        decisions = self._hndl.getDecisionInfo()
        
        result = []
        for i in range(decisions.size()):
            # owned=False because ParseProfileInfo owns these pointers
            result.append(DecisionProfileInfo.mk(decisions[i], False))
        
        return result

    def get_ll_decisions(self):
        return self._hndl.getLLDecisions()

    @property
    def total_time_in_prediction(self):
        return self._hndl.getTotalTimeInPrediction()

    @property
    def total_sll_lookahead_ops(self):
        return self._hndl.getTotalSLLLookaheadOps()

    @property
    def total_ll_lookahead_ops(self):
        return self._hndl.getTotalLLLookaheadOps()

    @property
    def total_sll_atn_lookahead_ops(self):
        return self._hndl.getTotalSLLATNLookaheadOps()

    @property
    def total_ll_atn_lookahead_ops(self):
        return self._hndl.getTotalLLATNLookaheadOps()

    @property
    def total_atn_lookahead_ops(self):
        return self._hndl.getTotalATNLookaheadOps()

    @property
    def dfa_size(self):
        return self._hndl.getDFASize()

    @staticmethod
    cdef ParseProfileInfo mk(decl.IParseProfileInfo *hndl, bool owned=True):
        ret = ParseProfileInfo()
        ret._hndl = hndl
        ret._owned = owned
        return ret
