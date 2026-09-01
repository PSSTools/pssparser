

cimport debug_mgr.decl as dm
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
from pssparser cimport ast_decl as ast
from ciostream.core cimport istream

ctypedef IFactory *IFactoryP
ctypedef IMarker *IMarkerP
ctypedef IMarkerCollector *IMarkerCollectorP
ctypedef unique_ptr[IMarker] IMarkerUP


cdef extern from "pssp/IFactory.h" namespace "pssp":
    cdef cppclass IFactory:

        void init(dm.IDebugMgr *dmgr, ast.IFactory *ast_factory)

        ast.IFactory *getAstFactory()

        dm.IDebugMgr *getDebugMgr()

        void loadStandardLibrary(
            IAstBuilder             *ast_builder,
            ast.IGlobalScope        *glbl_scope)

        ILookupLocationResult *lookupLocation(
            ast.IRootSymbolScope    *root,
            ast.IScope              *scope,
            int                     lineno,
            int                     linepos
        )

        IAstBuilder *mkAstBuilder(IMarkerListener *)

        ILinker *mkAstLinker()

        ISymbolTableIterator *mkAstSymbolTableIterator(
            ast.ISymbolScope        *root)

        IMarkerCollector *mkMarkerCollector()

        ITaskFindElementByLocation *mkTaskFindElementByLocation()

        IFmtTokenStream *mkTokenizer(istream *in_s)

        IFmtCst *mkCstParser(istream *in_s)

cdef extern from "pssp/IFmtTokenStream.h" namespace "pssp":
    cdef enum FmtTokenChannelE:
        FmtTokenChannel_Default "pssp::FmtTokenChannel_Default"
        FmtTokenChannel_WS "pssp::FmtTokenChannel_WS"
        FmtTokenChannel_SlComment "pssp::FmtTokenChannel_SlComment"
        FmtTokenChannel_MlComment "pssp::FmtTokenChannel_MlComment"
        FmtTokenChannel_Error "pssp::FmtTokenChannel_Error"
        FmtTokenChannel_Bom "pssp::FmtTokenChannel_Bom"

    cdef cppclass FmtToken:
        int32_t index
        int32_t type
        int32_t channel
        int32_t start
        int32_t stop
        int32_t line
        int32_t col
        cpp_string text

    cdef cppclass IFmtTokenStream:
        uint32_t size()
        const FmtToken &at(uint32_t idx)
        const cpp_string &getTypeName(int32_t type)
        uint32_t getNumErrors()
        bool isValidUtf8()

# The synthetic token types, taken from the header rather than restated, so a
# change there cannot leave the Python side quietly disagreeing.
cdef extern from "pssp/IFmtTokenStream.h" namespace "pssp::IFmtTokenStream":
    cdef const int32_t FmtToken_TYPE_ERROR_CHAR "pssp::IFmtTokenStream::TYPE_ERROR_CHAR"
    cdef const int32_t FmtToken_TYPE_BOM "pssp::IFmtTokenStream::TYPE_BOM"

cdef extern from "pssp/IFmtCst.h" namespace "pssp":
    cdef cppclass IFmtCstNode:
        bool isRule()
        bool isError()
        int32_t getRuleIndex()
        const cpp_string &getRuleName()
        int32_t getTokenIndex()
        uint32_t getNumChildren()
        IFmtCstNode *getChild(uint32_t idx)
        int32_t getStartToken()
        int32_t getStopToken()

    cdef cppclass IFmtCst:
        IFmtTokenStream *getTokens()
        IFmtCstNode *getRoot()
        uint32_t getNumSyntaxErrors()

cdef extern from "pssp/IParseProfileInfo.h" namespace "pssp":
    cdef cppclass IDecisionEventInfo:
        const cpp_string &getKindName()
        uint32_t getStartLine()
        uint32_t getStartColumn()
        uint32_t getStopLine()
        uint32_t getStopColumn()
        uint32_t getTokenCount()
        const cpp_string &getText()

    cdef cppclass IDecisionProfileInfo:
        size_t getDecision()
        size_t getRuleIndex()
        const cpp_string &getRuleName()
        int64_t getInvocations()
        int64_t getTimeInPrediction()
        int64_t getSLLLookaheadOps()
        int64_t getLLLookaheadOps()
        int64_t getSLLATNTransitions()
        int64_t getLLATNTransitions()
        int64_t getLLFallback()
        size_t getAmbiguityCount()
        size_t getContextSensitivityCount()
        size_t getErrorCount()
        size_t getPredicateEvalCount()
        size_t getSLLMinLookahead()
        size_t getSLLMaxLookahead()
        size_t getLLMinLookahead()
        size_t getLLMaxLookahead()
        size_t getMaxLookahead()
        size_t getNumEvents()
        IDecisionEventInfo *getEvent(size_t idx)

    cdef cppclass IParseProfileInfo:
        cpp_vector[IDecisionProfileInfo*] getDecisionInfo()
        cpp_vector[size_t] getLLDecisions()
        int64_t getTotalTimeInPrediction()
        int64_t getTotalSLLLookaheadOps()
        int64_t getTotalLLLookaheadOps()
        int64_t getTotalSLLATNLookaheadOps()
        int64_t getTotalLLATNLookaheadOps()
        int64_t getTotalATNLookaheadOps()
        size_t getDFASize()
        size_t getTokenCount()


cdef extern from "pssp/IAstBuilder.h" namespace "pssp":
    cdef cppclass IAstBuilder:

        void build(
            ast.IGlobalScope        *scope,
            istream                 *in_s)

        void setMarkerListener(IMarkerListener *)

        void setCollectDocStrings(bool)
        void setCollectComments(bool)
        bool getCollectComments()

        bool getCollectDocStrings()

        void setEnableProfile(bool)

        bool getEnableProfile()

        IParseProfileInfo *getProfileInfo()

cdef extern from "pssp/ILinker.h" namespace "pssp":
    cdef cppclass ILinker:

        ast.IRootSymbolScope *link(
            IMarkerListener         *marker_l,
            const cpp_vector[ast.IGlobalScopeP] &scopes)

        ast.IRootSymbolScope *linkOverlay(
            IMarkerListener         *marker_l,
            ast.IRootSymbolScope    *base_symtab,
            ast.IGlobalScope        *overlay)

        pass

cdef extern from "pssp/ILookupLocationResult.h" namespace "pssp":
    cdef cppclass ILookupLocationResult:
        pass

cdef extern from "pssp/ITaskFindElementByLocation.h" namespace "pssp":
    cdef enum FindElementKindE "pssp::ITaskFindElementByLocation::ElemKind":
        FindElementKindE_Expr "pssp::ITaskFindElementByLocation::ElemKind::Expr"
        FindElementKindE_Field "pssp::ITaskFindElementByLocation::ElemKind::Field"
        FindElementKindE_Type "pssp::ITaskFindElementByLocation::ElemKind::Type"

    cdef cppclass ITaskFindElementByLocationResult "pssp::ITaskFindElementByLocation::Result":
        bool isValid
        ast.IScopeChild *target
        FindElementKindE targetKind

    cdef cppclass ITaskFindElementByLocation:
        ITaskFindElementByLocationResult find(
            ast.ISymbolScope       *root,
            ast.IGlobalScope       *file,
            int32_t                lineno,
            int32_t                linepos,
            int32_t                fuzz)

cdef extern from "pssp/IMarker.h" namespace "pssp":
    cdef enum MarkerSeverityE:
        Severity_Error "pssp::MarkerSeverityE::Error"
        Severity_Warn "pssp::MarkerSeverityE::Warn"
        Severity_Info "pssp::MarkerSeverityE::Info"
        Severity_Hint "pssp::MarkerSeverityE::Hint"
        Severity_NumLevels "pssp::MarkerSeverityE::NumLevels"

    cdef cppclass IMarker:
        const cpp_string &msg() const
        MarkerSeverityE severity() const
        const ast.Location &loc() const;
        IMarker *clone() const

cdef extern from "pssp/IMarkerListener.h" namespace "pssp":
    cdef cppclass IMarkerListener:
        void marker(const IMarker *m)
        bool hasSeverity(MarkerSeverityE s)

cdef extern from "pssp/IMarkerCollector.h" namespace "pssp":
    cdef cppclass IMarkerCollector(IMarkerListener):
        const cpp_vector[IMarkerUP] &markers() const

cdef extern from "pssp/ISymbolTableIterator.h" namespace "pssp":
    cdef cppclass ISymbolTableIterator:
        int32_t findLocalSymbol(const cpp_string &name)

cdef extern from "PyParserUtils.h" namespace "pssp":
    ast.IScopeChild *resolveSymbolPathRef "pssp::PyParserUtils::resolveSymbolPathRef" (
        dm.IDebugMgr                *dmgr,
        ast.ISymbolChildrenScope    *root,
        const ast.ISymbolRefPath    *ref)
