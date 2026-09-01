#****************************************************************************
#* zsp_parser core.pxd
#****************************************************************************
cimport pssparser.decl as decl
cimport debug_mgr.core as dm_core
cimport pssparser.ast as ast
from libc.stdint cimport int32_t
from libcpp cimport bool

cdef class Factory(object):
    cdef decl.IFactory      *_hndl

    cpdef ast.Factory getAstFactory(self)

    cpdef dm_core.DebugMgr getDebugMgr(self)

    cpdef void loadStandardLibrary(self,
        AstBuilder          ast_builder,
        ast.GlobalScope     glbl_scope)

    cpdef LookupLocationResult lookupLocation(
        self,
        ast.RootSymbolScope     root,
        ast.Scope               scope,
        int                     lineno,
        int                     linepos)

    cpdef AstBuilder mkAstBuilder(self, MarkerListener marker_l)

    cpdef Linker mkAstLinker(self)

    cpdef SymbolTableIterator mkAstSymbolTableIterator(self,
        ast.SymbolScope     root)

    cpdef MarkerCollector mkMarkerCollector(self)

    cpdef TaskFindElementByLocation mkTaskFindElementByLocation(self)

    cpdef TokenStream mkTokenizer(self, in_s)

    cpdef Cst mkCstParser(self, in_s)

    cdef init(self, dm_core.Factory f, ast.Factory ast_f)

cdef Factory _factoryInst = None


cdef class AstBuilder(object):
    cdef decl.IAstBuilder      *_hndl
    cdef bool                  _owned

    cpdef build(self,
        ast.GlobalScope         root,
                                in_s)

    cpdef void setMarkerListener(self, MarkerListener l)

    cpdef void setCollectDocStrings(self, bool collect)

    cpdef void setCollectComments(self, bool collect)

    cpdef bool getCollectComments(self)

    cpdef bool getCollectDocStrings(self)

    cpdef void setEnableProfile(self, bool enable)

    cpdef bool getEnableProfile(self)

    cpdef ParseProfileInfo getProfileInfo(self)

    @staticmethod
    cdef AstBuilder mk(decl.IAstBuilder *hndl, bool owned=*)

cdef class Linker(object):
    cdef decl.ILinker           *_hndl
    cdef bool                   _owned

    cpdef ast.RootSymbolScope link(self,
        MarkerListener         marker_l,
        scopes)

    cpdef ast.RootSymbolScope linkOverlay(self,
        MarkerListener         marker_l,
        ast.RootSymbolScope    base_symtab,
        ast.GlobalScope        overlay)

    @staticmethod
    cdef Linker mk(decl.ILinker *hndl, bool owned=*)

cdef class Location(object):
    cdef int32_t        _file
    cdef int32_t        _line
    cdef int32_t        _pos

cdef class LookupLocationResult(object):
    cdef decl.ILookupLocationResult     *_hndl
    cdef bool                           _owned

    @staticmethod
    cdef LookupLocationResult mk(decl.ILookupLocationResult *hndl, bool owned=*)

cdef class TaskFindElementByLocation(object):
    cdef decl.ITaskFindElementByLocation    *_hndl
    cdef bool                               _owned

    cpdef TaskFindElementResult find(self,
        ast.SymbolScope   root,
        ast.GlobalScope   file,
        int               lineno,
        int               linepos,
        int               fuzz=*)

    @staticmethod
    cdef TaskFindElementByLocation mk(decl.ITaskFindElementByLocation *hndl, bool owned=*)

cdef class TaskFindElementResult(object):
    cdef decl.ITaskFindElementByLocationResult _hndl
    cdef object                                _target

    @staticmethod
    cdef TaskFindElementResult mk(decl.ITaskFindElementByLocationResult hndl)

cdef class Marker(object):
    cdef decl.IMarker               *_hndl
    cdef bool                       _owned

    cpdef str msg(self)

    cpdef severity(self)

    cpdef Location loc(self)

    @staticmethod
    cdef Marker mk(decl.IMarker *hndl, bool owned=*)

cdef class MarkerListener(object):
    cdef decl.IMarkerListener       *_hndl
    cdef bool                       _owned

    cpdef bool hasSeverity(self, s)

cdef class MarkerCollector(MarkerListener):

    cpdef markers(self)

    cpdef int numMarkers(self)

    cpdef Marker getMarker(self, int idx)

    cdef decl.IMarkerCollector *asCollector(self)

    @staticmethod
    cdef MarkerCollector mk(decl.IMarkerCollector *hndl, bool owned=*)

cdef class SymbolTableIterator(object):
    cdef decl.ISymbolTableIterator  *_hndl
    cdef bool                       _owned

    @staticmethod
    cdef SymbolTableIterator mk(decl.ISymbolTableIterator *hndl, bool owned=*)

cdef class DecisionEventInfo(object):
    cdef decl.IDecisionEventInfo    *_hndl

    @staticmethod
    cdef DecisionEventInfo mk(decl.IDecisionEventInfo *hndl)

cdef class DecisionProfileInfo(object):
    cdef decl.IDecisionProfileInfo  *_hndl
    cdef bool                       _owned

    @staticmethod
    cdef DecisionProfileInfo mk(decl.IDecisionProfileInfo *hndl, bool owned=*)

cdef class ParseProfileInfo(object):
    cdef decl.IParseProfileInfo     *_hndl
    cdef bool                       _owned

    @staticmethod
    cdef ParseProfileInfo mk(decl.IParseProfileInfo *hndl, bool owned=*)


cdef class Token(object):
    cdef readonly int32_t   index
    cdef readonly int32_t   type
    cdef readonly str       type_name
    cdef readonly int32_t   channel
    cdef readonly int32_t   start
    cdef readonly int32_t   stop
    cdef readonly int32_t   line
    cdef readonly int32_t   col
    cdef readonly str       text

    @staticmethod
    cdef Token mk(decl.FmtToken &tok, str type_name)


cdef class TokenStream(object):
    cdef readonly tuple     tokens
    cdef readonly int32_t   num_errors
    cdef readonly bool      valid_utf8

    @staticmethod
    cdef TokenStream mk(tuple tokens, int32_t num_errors, bool valid_utf8)


cdef class CstNode(object):
    cdef decl.IFmtCstNode   *_hndl
    # Keeps the tree alive.  Nodes are borrowed views into a C++ tree owned by
    # the Cst, so a node outliving its Cst would be a dangling pointer.
    cdef Cst                _cst

    @staticmethod
    cdef CstNode mk(decl.IFmtCstNode *hndl, Cst cst)


cdef class Cst(object):
    cdef decl.IFmtCst       *_hndl
    cdef readonly TokenStream   tokens
    cdef readonly int32_t       num_syntax_errors
    cdef object                 _root
