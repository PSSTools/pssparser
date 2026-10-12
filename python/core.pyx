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
from libc.stdint cimport int32_t
from libc.stdint cimport uint32_t
from libcpp.vector cimport vector as std_vector
from libcpp.string cimport string as cpp_string
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

    cpdef list collectOccurrences(self, ast.RootSymbolScope root):
        """Raw form of pssparser.refs.occurrences(): one tuple per identifier,
        (id, decl, decl_name, base_decl, is_decl, resolution). The AST objects
        are borrowed from `root`, which must outlive them."""
        cdef decl.IOccurrenceCollector *coll = self._hndl.mkOccurrenceCollector()
        cdef std_vector[decl.Occurrence] occs
        cdef list ret = []
        try:
            coll.collect(root.asRootSymbolScope(), occs)
        finally:
            del coll
        for i in range(occs.size()):
            ret.append((
                _wrapExpr(occs[i].id),
                _wrapScopeChild(occs[i].decl),
                _wrapExpr(occs[i].decl_name),
                _wrapScopeChild(occs[i].base_decl),
                occs[i].is_decl,
                int(occs[i].resolution)))
        return ret

    def mkLintEngine(self):
        """A lint engine with no rules loaded (lint-core-plan.md)."""
        return LintEngine.mk(self._hndl.mkLintEngine())

    def _lintTestHooks(self):
        """PRIVATE: the lint engine's test entry points (lint-core-plan.md
        §5). Not a supported API."""
        return LintTestHooks.mk(self._hndl.mkLintTestHooks())

    cpdef TokenStream mkTokenizer(self, in_s):
        cdef cistream c_in_s
        cdef decl.IFmtTokenStream *hndl

        c_in_s = cistream(in_s)
        hndl = self._hndl.mkTokenizer(c_in_s.stream())

        try:
            return _mkTokenStream(hndl)
        finally:
            del hndl

    cpdef Cst mkCstParser(self, in_s):
        cdef cistream c_in_s
        cdef decl.IFmtCst *hndl
        cdef Cst ret

        c_in_s = cistream(in_s)
        hndl = self._hndl.mkCstParser(c_in_s.stream())

        try:
            ret = Cst.__new__(Cst)
            # Materialize the tokens now, while the C++ object is known good.
            # Raises UnicodeDecodeError for input that is not UTF-8, in which
            # case there is no tree either.
            ret.tokens = _mkTokenStream(hndl.getTokens())
            ret.num_syntax_errors = hndl.getNumSyntaxErrors()
            ret._root = None
        except:
            del hndl
            raise

        # Ownership transfers only once nothing above can raise: the tree is
        # borrowed by every CstNode, so a half-built Cst must not escape.
        ret._hndl = hndl
        return ret

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

            for libdir in ("lib", "lib64", "bin", "src"):
                cand = os.path.join(build_dir, libdir, libname)
                if os.path.isfile(cand):
                    core_lib = cand
                    break

            if core_lib is None:
                core_lib = os.path.join(ext_dir, libname)

            if not os.path.isfile(core_lib):
                raise Exception("Extension library core \"%s\" doesn't exist" % core_lib)

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

    cpdef void setMarkerListener(self, MarkerListener l):
        # Lets a caller reuse one builder across parse calls with a fresh
        # collector each time.  The builder must be reused when compile-time
        # elaboration is in play: it carries the previously-processed source
        # units that `compile if` conditions resolve against (PSS 3.1 19.1.2).
        self._hndl.setMarkerListener(l._hndl)

    cpdef void setCollectDocStrings(self, bool collect):
        self._hndl.setCollectDocStrings(collect)

    cpdef bool getCollectDocStrings(self):
        return self._hndl.getCollectDocStrings()

    cpdef void setCollectComments(self, bool collect):
        self._hndl.setCollectComments(collect)

    cpdef bool getCollectComments(self):
        return self._hndl.getCollectComments()

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


cdef object _wrapScopeChild(ast_decl.IScopeChild *p):
    cdef ast.ObjFactory of
    if p == NULL:
        return None
    of = ast.ObjFactory()
    p.accept(<ast_decl.VisitorBase *>(of._hndl))
    return of._obj

cdef object _wrapExpr(ast_decl.IExprId *p):
    cdef ast.ObjFactory of
    if p == NULL:
        return None
    of = ast.ObjFactory()
    p.accept(<ast_decl.VisitorBase *>(of._hndl))
    return of._obj

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

    cpdef str id(self):
        return self._hndl.id().decode()

    cpdef int extent(self):
        cdef const ast_decl.Location *loc_ref = &(self._hndl.loc())
        return loc_ref.extent

    cpdef list related(self):
        ret = []
        cdef const decl.MarkerRelation *rel
        for i in range(self._hndl.related().size()):
            rel = &(self._hndl.related()[i])
            ret.append({
                "loc": Location(rel.loc.fileid, rel.loc.lineno, rel.loc.linepos),
                "label": rel.label.decode(),
            })
        return ret

    cpdef list fixes(self):
        """Machine-applicable repairs: span (with its own extent) + text."""
        ret = []
        cdef const decl.MarkerFix *fix
        for i in range(self._hndl.fixes().size()):
            fix = &(self._hndl.fixes()[i])
            ret.append({
                "span": Location(fix.span.fileid, fix.span.lineno,
                                 fix.span.linepos),
                "extent": fix.span.extent,
                "replacement": fix.replacement.decode(),
            })
        return ret

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

    cpdef setMaxErrors(self, int max_errors):
        self.asCollector().setMaxErrors(max_errors)

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

cdef class DecisionEventInfo(object):
    """One profiler event, resolved to a source location.

    Never owns its handle: events belong to the DecisionProfileInfo that
    produced them, which in turn belongs to the ParseProfileInfo.
    """

    @property
    def kind(self):
        return self._hndl.getKindName().decode()

    @property
    def start_line(self):
        return self._hndl.getStartLine()

    @property
    def start_column(self):
        return self._hndl.getStartColumn()

    @property
    def stop_line(self):
        return self._hndl.getStopLine()

    @property
    def stop_column(self):
        return self._hndl.getStopColumn()

    @property
    def token_count(self):
        return self._hndl.getTokenCount()

    @property
    def text(self):
        return self._hndl.getText().decode()

    def __repr__(self):
        return "DecisionEventInfo(%s, %d:%d, %d tokens)" % (
            self.kind, self.start_line, self.start_column, self.token_count)

    @staticmethod
    cdef DecisionEventInfo mk(decl.IDecisionEventInfo *hndl):
        ret = DecisionEventInfo()
        ret._hndl = hndl
        return ret

cdef class DecisionProfileInfo(object):

    def __dealloc__(self):
        if self._owned:
            del self._hndl

    @property
    def decision(self):
        return self._hndl.getDecision()

    @property
    def rule_index(self):
        return self._hndl.getRuleIndex()

    @property
    def rule_name(self):
        return self._hndl.getRuleName().decode()

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
    def predicate_eval_count(self):
        return self._hndl.getPredicateEvalCount()

    @property
    def sll_min_lookahead(self):
        return self._hndl.getSLLMinLookahead()

    @property
    def sll_max_lookahead(self):
        return self._hndl.getSLLMaxLookahead()

    @property
    def ll_min_lookahead(self):
        return self._hndl.getLLMinLookahead()

    @property
    def ll_max_lookahead(self):
        return self._hndl.getLLMaxLookahead()

    @property
    def max_lookahead(self):
        return self._hndl.getMaxLookahead()

    def get_events(self):
        """Resolved profiler events for this decision.

        Capped in the C++ layer -- see kMaxEventsPerDecision.  The counts
        above are not capped, so ``len(get_events()) < ambiguity_count`` is
        expected on a decision that misbehaves often.
        """
        cdef size_t i
        cdef size_t n = self._hndl.getNumEvents()
        return [DecisionEventInfo.mk(self._hndl.getEvent(i)) for i in range(n)]

    def __repr__(self):
        return "DecisionProfileInfo(%d, %s, %d invocations)" % (
            self.decision, self.rule_name, self.invocations)

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

    def get_rule_invocations(self):
        """``{rule name: contexts in the parse tree}`` for every parser rule,
        zeros included. The grammar-coverage measure: a decision's
        invocation count is zero for any LL(1) decision, used or not."""
        cdef size_t i
        return {
            self._hndl.getRuleName(i).decode(): self._hndl.getRuleInvocations(i)
            for i in range(self._hndl.getNumRules())
        }

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
        """Total DFA states across every decision.

        Process-global and cumulative -- the generated parser holds the DFA in
        static data shared by every parser instance -- so this grows as files
        are parsed and never resets.  It measures the process, not the file.
        """
        return self._hndl.getDFASize()

    @property
    def token_count(self):
        return self._hndl.getTokenCount()

    @staticmethod
    cdef ParseProfileInfo mk(decl.IParseProfileInfo *hndl, bool owned=True):
        ret = ParseProfileInfo()
        ret._hndl = hndl
        ret._owned = owned
        return ret


#***************************************************************************
#* Lossless token stream (formatters, highlighters, comment tools)
#***************************************************************************

#: Channel carrying everything the parser sees.
CHANNEL_DEFAULT = <int32_t>(decl.FmtTokenChannel_Default)
#: Channel carrying whitespace runs.
CHANNEL_WS = <int32_t>(decl.FmtTokenChannel_WS)
#: Channel carrying ``//`` comments.  The token includes its newline.
CHANNEL_SL_COMMENT = <int32_t>(decl.FmtTokenChannel_SlComment)
#: Channel carrying ``/* */`` comments.
CHANNEL_ML_COMMENT = <int32_t>(decl.FmtTokenChannel_MlComment)
#: Channel carrying text no lexer rule matched.
CHANNEL_ERROR = <int32_t>(decl.FmtTokenChannel_Error)
#: Channel carrying a leading byte-order mark.
CHANNEL_BOM = <int32_t>(decl.FmtTokenChannel_Bom)

#: Token type of text no lexer rule matched.
TYPE_ERROR_CHAR = <int32_t>(decl.FmtToken_TYPE_ERROR_CHAR)
#: Token type of a leading byte-order mark.
TYPE_BOM = <int32_t>(decl.FmtToken_TYPE_BOM)

cdef frozenset _TRIVIA_CHANNELS = frozenset((
    <int32_t>(decl.FmtTokenChannel_WS),
    <int32_t>(decl.FmtTokenChannel_SlComment),
    <int32_t>(decl.FmtTokenChannel_MlComment),
    <int32_t>(decl.FmtTokenChannel_Bom)))


cdef class Token(object):
    """One token, including whitespace and comments.

    Immutable.  ``start`` and ``stop`` are both **inclusive** offsets into the
    source, counted in code points -- which is what a Python ``str`` counts, so
    ``src[t.start:t.stop+1] == t.text`` always holds.
    """

    def __repr__(self):
        return "Token(%d, %s, ch=%d, %d:%d, %r)" % (
            self.index, self.type_name, self.channel,
            self.line, self.col, self.text)

    @property
    def is_trivia(self):
        """True for whitespace, comments and the byte-order mark.

        Error tokens are deliberately *not* trivia: a consumer that skips
        trivia must still see them, because ignoring them is how text gets
        silently dropped.
        """
        return self.channel in _TRIVIA_CHANNELS

    @property
    def is_comment(self):
        return (self.channel == <int32_t>(decl.FmtTokenChannel_SlComment) or
                self.channel == <int32_t>(decl.FmtTokenChannel_MlComment))

    @property
    def is_error(self):
        return self.channel == <int32_t>(decl.FmtTokenChannel_Error)

    @staticmethod
    cdef Token mk(decl.FmtToken &tok, str type_name):
        cdef Token ret = Token.__new__(Token)
        ret.index = tok.index
        ret.type = tok.type
        ret.type_name = type_name
        ret.channel = tok.channel
        ret.start = tok.start
        ret.stop = tok.stop
        ret.line = tok.line
        ret.col = tok.col
        ret.text = bytes(tok.text).decode("utf-8")
        return ret


cdef class TokenStream(object):
    """The complete token stream for one source unit.

    Complete in the strong sense: ``"".join(t.text for t in stream)`` is the
    input, exactly.  Everything a formatter does is a transformation of that
    identity, so it is worth asserting in tests rather than assuming.
    """

    def __len__(self):
        return len(self.tokens)

    def __iter__(self):
        return iter(self.tokens)

    def __getitem__(self, idx):
        return self.tokens[idx]

    def __repr__(self):
        return "TokenStream(%d tokens, %d errors)" % (
            len(self.tokens), self.num_errors)

    @property
    def text(self):
        """The source, reassembled from the tokens."""
        return "".join([t.text for t in self.tokens])

    def code(self):
        """The default-channel tokens, in order -- what the parser would see."""
        return [t for t in self.tokens
                if t.channel == <int32_t>(decl.FmtTokenChannel_Default)]

    @staticmethod
    cdef TokenStream mk(tuple tokens, int32_t num_errors, bool valid_utf8):
        cdef TokenStream ret = TokenStream.__new__(TokenStream)
        ret.tokens = tokens
        ret.num_errors = num_errors
        ret.valid_utf8 = valid_utf8
        return ret


cdef TokenStream _mkTokenStream(decl.IFmtTokenStream *hndl):
    """Copies a C++ token stream into Python objects.

    Eager rather than lazy on purpose.  Tokens are small immutable values, and
    materializing them means the Python objects have no lifetime relationship
    with the C++ stream at all -- which is what lets the caller free it as soon
    as this returns.
    """
    cdef decl.FmtToken tok
    cdef uint32_t i
    cdef uint32_t n

    if not hndl.isValidUtf8():
        # The C++ side degraded to a single verbatim token rather than
        # substituting replacement characters.  Surface that as the exception
        # Python already has for it, instead of handing back a stream whose
        # offsets mean something different.
        raise UnicodeDecodeError(
            "utf-8", bytes(hndl.at(0).text) if hndl.size() else b"",
            0, 1, "PSS source must be valid UTF-8")

    # Token type names are few and repeat constantly, so resolve each once and
    # share the string.  Without this, a large file allocates one identical str
    # per token.
    names = {}
    toks = []
    n = hndl.size()
    for i in range(n):
        tok = hndl.at(i)
        name = names.get(tok.type)
        if name is None:
            name = bytes(hndl.getTypeName(tok.type)).decode("utf-8")
            names[tok.type] = name
        toks.append(Token.mk(tok, name))

    return TokenStream.mk(tuple(toks), hndl.getNumErrors(), True)


cdef class CstNode(object):
    """A node in the concrete syntax tree: a grammar rule or a token.

    A view onto the C++ tree, created on demand.  Two ``CstNode`` objects for
    the same position are equal but not identical, so compare with ``==``.
    """

    def __repr__(self):
        if self.is_rule:
            return "CstNode(%s, %d children)" % (
                self.rule_name, self.num_children)
        return "CstNode(token %d)" % self.token_index

    def __richcmp__(self, other, int op):
        if not isinstance(other, CstNode):
            return NotImplemented
        same = ((<CstNode>self)._hndl == (<CstNode>other)._hndl)
        if op == 2:
            return same
        elif op == 3:
            return not same
        return NotImplemented

    def __hash__(self):
        return hash(<intptr_t>(self._hndl))

    @property
    def is_rule(self):
        return self._hndl.isRule()

    @property
    def is_error(self):
        """True for a token the parser did not expect.

        The tree around an error node is a guess, so a consumer that rewrites
        layout should decline rather than trust the structure.
        """
        return self._hndl.isError()

    @property
    def rule_index(self):
        """Grammar rule index, or -1 for a token.

        Prefer :attr:`rule_name`: these are generated and renumber whenever
        the grammar grows.
        """
        return self._hndl.getRuleIndex()

    @property
    def rule_name(self):
        """Grammar rule name, or ``""`` for a token."""
        return bytes(self._hndl.getRuleName()).decode("utf-8")

    @property
    def token_index(self):
        """Index into :attr:`Cst.tokens`, or -1 for a rule."""
        return self._hndl.getTokenIndex()

    @property
    def token(self):
        """The :class:`Token` this node is, or ``None`` for a rule."""
        cdef int32_t idx = self._hndl.getTokenIndex()
        return self._cst.tokens[idx] if idx >= 0 else None

    @property
    def num_children(self):
        return self._hndl.getNumChildren()

    @property
    def children(self):
        cdef uint32_t i
        return tuple([CstNode.mk(self._hndl.getChild(i), self._cst)
                      for i in range(self._hndl.getNumChildren())])

    @property
    def start_token(self):
        """First token index this node spans, or -1 if it spans none."""
        return self._hndl.getStartToken()

    @property
    def stop_token(self):
        """Last token index this node spans, inclusive, or -1."""
        return self._hndl.getStopToken()

    @property
    def text(self):
        """The source this node spans, trivia included, or ``""``.

        Everything between the first and last token, verbatim -- so for a rule
        this is what the author wrote for that construct, comments and all.
        """
        cdef int32_t start = self._hndl.getStartToken()
        cdef int32_t stop = self._hndl.getStopToken()
        if start < 0 or stop < start:
            return ""
        return "".join(
            [t.text for t in self._cst.tokens[start:stop + 1]])

    def walk(self):
        """Yields this node and every node below it, depth first."""
        yield self
        for c in self.children:
            for n in c.walk():
                yield n

    def __len__(self):
        return self._hndl.getNumChildren()

    def __getitem__(self, int idx):
        if idx < 0:
            idx += self._hndl.getNumChildren()
        if idx < 0 or idx >= <int>(self._hndl.getNumChildren()):
            raise IndexError("no child %d" % idx)
        return CstNode.mk(self._hndl.getChild(idx), self._cst)

    def __iter__(self):
        return iter(self.children)

    @staticmethod
    cdef CstNode mk(decl.IFmtCstNode *hndl, Cst cst):
        cdef CstNode ret = CstNode.__new__(CstNode)
        ret._hndl = hndl
        ret._cst = cst
        return ret


cdef class Cst(object):
    """A parsed source unit: the token stream and the tree over it.

    Parsed without building an AST, which is what keeps both branches of a
    ``compile if`` and the parentheses the author wrote.
    """

    def __dealloc__(self):
        if self._hndl != NULL:
            del self._hndl
            self._hndl = NULL

    def __repr__(self):
        return "Cst(%d tokens, %d syntax errors)" % (
            len(self.tokens), self.num_syntax_errors)

    @property
    def root(self):
        """The ``compilation_unit`` node, or ``None`` if nothing was parsed."""
        cdef decl.IFmtCstNode *r
        if self._root is None:
            r = self._hndl.getRoot()
            self._root = CstNode.mk(r, self) if r != NULL else False
        return self._root or None

    @property
    def text(self):
        """The source, reassembled from the tokens."""
        return self.tokens.text


cdef ast_decl.IRootSymbolScope *_model(model) except? NULL:
    """The C++ root of a linked model (a RootSymbolScope), or NULL for None."""
    cdef ast.RootSymbolScope m
    if model is None:
        return NULL
    m = model
    return m.asRootSymbolScope()


cdef class LintEngine(object):
    """The C++ lint engine (lint-core-plan.md). Owns the rule sets loaded
    into it."""
    cdef decl.ILintEngine *_hndl

    def __dealloc__(self):
        if self._hndl != NULL:
            del self._hndl

    @staticmethod
    cdef LintEngine mk(decl.ILintEngine *hndl):
        ret = LintEngine()
        ret._hndl = hndl
        return ret

    @property
    def rule_format_version(self):
        """The pss-rules format version this engine reads."""
        return self._hndl.ruleFormatVersion()

    def num_rule_sets(self):
        return self._hndl.numRuleSets()

    def load_rules(self, str name, str text, builtin=False):
        """Loads one rule file (pss-rules-format.md) from its text; `name` is
        shown in diagnostics. Returns False if the file as a whole was
        refused. Problems are in rule_diagnostics(); a bad rule is left out
        and the rest of the file loads."""
        cdef decl.LintSource src
        src.name = name.encode("utf-8")
        src.text = text.encode("utf-8")
        return self._hndl.loadRules(src, builtin) != NULL

    def load_builtin_rules(self):
        """Loads the built-in rule files embedded in the core, once; a second
        call does nothing. Returns the number of files this call loaded."""
        return self._hndl.loadBuiltinRules()

    @property
    def num_builtin_rule_files(self):
        """The number of built-in rule files embedded in the core."""
        return self._hndl.numBuiltinRuleFiles()

    def probe_rules(self, str text):
        """Whether `text` is a rule file, without loading it: "rule-file",
        "empty", "not-yaml", "not-mapping" or "no-key" (no top-level
        `pss-rules`). Text that is not valid YAML is a "rule-file" when a
        line starts `pss-rules:`, so loading it reports the YAML errors."""
        cdef decl.RuleProbeE p = self._hndl.probeRules(text.encode("utf-8"))
        if p == decl.RuleProbe_RuleFile:
            return "rule-file"
        if p == decl.RuleProbe_Empty:
            return "empty"
        if p == decl.RuleProbe_NotYaml:
            return "not-yaml"
        if p == decl.RuleProbe_NotMapping:
            return "not-mapping"
        return "no-key"

    def rule_diagnostics(self):
        """Every rule-file diagnostic so far: a list of dicts with `code`,
        `severity`, `message`, `file`, `line`, `col`, `rule`, and `related`
        when there is a second location."""
        import json
        return json.loads(self._hndl.diagnosticsJson().decode("utf-8"))

    def rules(self):
        """Every loaded rule, with its metadata, match, options, examples,
        and computed level and scope, as a list of dicts."""
        import json
        return json.loads(self._hndl.rulesJson().decode("utf-8"))

    def set_host_markers(self, markers, refused=()):
        """The host's own markers, for selection (lint-core-plan.md C7.1):
        what a selector may name besides the loaded rules. `markers` is a
        list of dicts with ``id`` and any of ``name``, ``tier``, ``family``,
        ``since``, ``status``, ``severity``, ``aliases``, ``replaced_by``,
        ``default_enabled``, ``minimal``; `refused` lists loaded rules to
        leave out. Replaces an earlier call's. Returns the problems."""
        import json
        text = json.dumps({"markers": list(markers), "refused": list(refused)})
        return json.loads(self._hndl.setHostMarkers(text.encode("utf-8")).decode("utf-8"))

    def resolve_selection(self, selection):
        """Resolves a rule selection (C7.1): profiles, select/ignore, the
        per-path overrides, the command line's layer, ``[severity]`` and
        ``-W`` groups, for the files in ``selection["paths"]``. See
        ILintEngine::resolveSelection for the dict's keys and the result."""
        import json
        text = json.dumps(selection).encode("utf-8")
        return json.loads(self._hndl.resolveSelection(text).decode("utf-8"))

    def collect_waivers(self, roots, texts, files=None):
        """The source waivers in `texts` (``{path: source}``) and, for the
        annotation form, in `roots` (the GlobalScope of each file; empty
        without an AST), whose paths `files` (``{fileid: path}``) gives
        (lint-core-plan.md C7.2). Returns ``{"ok", "waivers"}``; see
        ILintEngine::collectWaivers."""
        import json
        cdef std_vector[ast_decl.IScopeChildP] v
        cdef ast.ScopeChild r
        for r in roots:
            v.push_back(r.asScopeChild())
        req = {"texts": dict(texts), "files": {str(k): p for k, p in (files or {}).items()}}
        text = json.dumps(req, ensure_ascii=False).encode("utf-8", "surrogatepass")
        return json.loads(self._hndl.collectWaivers(v, text).decode("utf-8"))

    def apply_waivers(self, waivers, diagnostics, ran=None):
        """Applies `waivers` (collect_waivers()'s) to `diagnostics` (dicts
        with ``code``, ``file``, ``line``, ``col``) (C7.2). `ran` is the
        codes whose rule ran, or None when unknown. Returns ``{"ok", "kept",
        "waived", "waivers", "markers"}``; see ILintEngine::applyWaivers."""
        import json
        req = {"waivers": list(waivers), "diagnostics": list(diagnostics),
               "ran": sorted(ran) if ran is not None else None}
        text = json.dumps(req, ensure_ascii=False).encode("utf-8", "surrogatepass")
        return json.loads(self._hndl.applyWaivers(text).decode("utf-8"))

    def finish(self, request):
        """Finishes a run's diagnostics as the CLI does before printing them
        (lint-core-plan.md C7.4): lint selection per file and ownership,
        ``[severity]``, source waivers and the ``-W`` policy. `request` is a
        dict with ``diagnostics``, ``selection``, ``stages``, ``owned``,
        ``waivers``, ``ran``, ``paths`` and ``policy``. Returns ``{"ok",
        "diagnostics", "waived", "waivers", "dropped", "problems"}``; see
        ILintEngine::finish."""
        import json
        text = json.dumps(request, ensure_ascii=False).encode("utf-8", "surrogatepass")
        return json.loads(self._hndl.finish(text).decode("utf-8"))

    def catalog(self):
        """The marker catalogue (lint-core-plan.md C7.3): every marker the
        engine knows -- the embedded core catalogue's, the host's
        (set_host_markers()) and the loaded rules' -- with its metadata and
        documentation, and the lint taxonomy. ``{"schema", "taxonomy",
        "markers"}``; see ILintEngine::catalogJson."""
        import json
        return json.loads(self._hndl.catalogJson().decode("utf-8"))

    def core_code(self, message):
        """The code the catalogue's message patterns give a core marker's
        `message`, or "" (C7.3)."""
        return self._hndl.coreCode(message.encode("utf-8", "surrogatepass")).decode("utf-8")

    def run(self, roots, request=None, model=None):
        """Runs the loaded rules over `roots` (the GlobalScope of each file
        the caller owns) (lint-core-plan.md C5.4). `request` is a dict:
        ``enabled`` (rule IDs; absent or None: all), ``options``
        (``{id: {name: value}}``), ``max_steps``, ``gate_errors``, ``files``,
        ``base_dir``, or ``selection`` (resolve_selection's dict, C7.1) in
        place of ``enabled`` and ``options``. `model`
        is the linked ``RootSymbolScope`` (``Parser.link()``'s result) the
        files belong to; without it, rules that need symbols are not run
        (C6.2). Returns ``{"ok", "markers", "stats", "problems"}``; see
        ILintEngine::run."""
        import json
        cdef std_vector[ast_decl.IScopeChildP] v
        cdef ast.ScopeChild r
        for r in roots:
            v.push_back(r.asScopeChild())
        text = json.dumps(request or {}).encode("utf-8")
        return json.loads(self._hndl.run(v, text, _model(model)).decode("utf-8"))


cdef class LintTestHooks(object):
    """PRIVATE test entry points into the C++ lint engine's internals (YAML
    layer, regex engine, CEL parser and evaluator). Each returns the decoded
    JSON the core produced; the WASM build produces the same text. Not a
    supported API (lint-core-plan.md §5)."""
    cdef decl.ILintTestHooks *_hndl

    def __dealloc__(self):
        if self._hndl != NULL:
            del self._hndl

    @staticmethod
    cdef LintTestHooks mk(decl.ILintTestHooks *hndl):
        ret = LintTestHooks()
        ret._hndl = hndl
        return ret

    @staticmethod
    def _decode(bytes b):
        import json
        return json.loads(b.decode("utf-8", "surrogateescape"))

    def yaml_load(self, str name, str text):
        return LintTestHooks._decode(self._hndl.yamlLoad(
            name.encode("utf-8"), text.encode("utf-8")))

    def yaml_source_maps(self, str name, str text):
        return LintTestHooks._decode(self._hndl.yamlSourceMaps(
            name.encode("utf-8"), text.encode("utf-8")))

    def yaml_cel_parse(self, str name, str text, str key):
        return LintTestHooks._decode(self._hndl.yamlCelParse(
            name.encode("utf-8"), text.encode("utf-8"), key.encode("utf-8")))

    def cel_parse(self, str text):
        return LintTestHooks._decode(self._hndl.celParse(text.encode("utf-8")))

    def cel_eval(self, str text, max_steps=0, bindings=None):
        """`bindings`: a dict of variables, passed as JSON."""
        return LintTestHooks._decode(self._hndl.celEval(
            text.encode("utf-8"), LintTestHooks._bindings(bindings), max_steps))

    def cel_functions(self):
        """The function registry: every overload, in registration order."""
        return LintTestHooks._decode(self._hndl.celFunctions())

    def cel_check(self, doc, str name="check.yaml"):
        """Type-checks (and runs) a rule-shaped document: a dict, passed as
        JSON, or YAML text. See ILintTestHooks::celCheck for the keys."""
        return LintTestHooks._decode(self._hndl.celCheck(
            name.encode("utf-8"), LintTestHooks._doc(doc)))

    def cel_check_node(self, doc, ast.ScopeChild root, str name="check.yaml", model=None):
        """cel_check with `node` bound to `root` (native only); `model` is
        the linked RootSymbolScope, for the symbol functions."""
        return LintTestHooks._decode(self._hndl.celCheckNode(
            name.encode("utf-8"), LintTestHooks._doc(doc), root.asScopeChild(),
            _model(model)))

    def decl_paths(self, ast.ScopeChild root):
        """Every scope under `root` with a declaration path of its own:
        [{"path", "class", "line", "col"}] (C6.2)."""
        return LintTestHooks._decode(self._hndl.declPaths(root.asScopeChild()))

    @staticmethod
    def _doc(doc):
        import json
        return (doc if isinstance(doc, str) else json.dumps(doc)).encode("utf-8")

    def cel_eval_node(self, str text, ast.ScopeChild root, max_steps=0, bindings=None,
                      model=None):
        """cel_eval with `node` bound to `root` (native only)."""
        return LintTestHooks._decode(self._hndl.celEvalNode(
            text.encode("utf-8"), root.asScopeChild(), LintTestHooks._bindings(bindings),
            max_steps, _model(model)))

    @staticmethod
    def _bindings(bindings):
        import json
        return json.dumps(bindings).encode("utf-8") if bindings else b""

    def rule_load(self, str name, str text, builtin=False):
        """Loads one rule file into a fresh engine: {"loaded", "rules",
        "diagnostics"}."""
        return LintTestHooks._decode(self._hndl.ruleLoad(
            name.encode("utf-8"), text.encode("utf-8"), builtin))

    def rules_schema(self):
        """The JSON Schema of a rule file, written from the loader's field
        table (C4.4); scripts/gen_rules_schema.py publishes it."""
        return LintTestHooks._decode(self._hndl.rulesSchema())

    def regex_search(self, str pattern, str text):
        return LintTestHooks._decode(self._hndl.regexSearch(
            pattern.encode("utf-8"), text.encode("utf-8")))

    def reflect_schema(self):
        return LintTestHooks._decode(self._hndl.reflectSchema())

    def reflect_census(self, ast.ScopeChild root):
        return LintTestHooks._decode(self._hndl.reflectCensus(root.asScopeChild()))

    def lint_walk(self, str name, str text, roots):
        """Loads one rule file and walks `roots` (GlobalScope nodes) with its
        rules (C5.1): every (rule, node) match, `where:` not evaluated."""
        cdef std_vector[ast_decl.IScopeChildP] v
        cdef ast.ScopeChild r
        for r in roots:
            v.push_back(r.asScopeChild())
        return LintTestHooks._decode(self._hndl.lintWalk(
            name.encode("utf-8"), text.encode("utf-8"), v))

    def lint_run(self, str name, str text, roots, enabled=None, int max_steps=0,
                 int gate_errors=0, model=None):
        """Loads one rule file and runs its rules over `roots` (GlobalScope
        nodes, one per file) (C5.2, C5.3): the findings, the rule failures,
        and per-rule counts and first error. `enabled` lists the IDs that
        run (None: all); `max_steps` is the budget per rule per file (0: the
        default); `gate_errors` > 0 runs nothing and returns the PSSP230
        marker as "skipped"."""
        cdef std_vector[ast_decl.IScopeChildP] v
        cdef std_vector[cpp_string] ids
        cdef ast.ScopeChild r
        for r in roots:
            v.push_back(r.asScopeChild())
        for i in (enabled or ()):
            ids.push_back(i.encode("utf-8"))
        return LintTestHooks._decode(self._hndl.lintRun(
            name.encode("utf-8"), text.encode("utf-8"), v, enabled is None, ids,
            max_steps, gate_errors, _model(model)))

    def raw(self, str fn, *args):
        """The undecoded JSON text of one call, for the native/WASM parity
        fixture: `fn` is the WASM binding's name less `_lint`
        (`YamlLoad`, `YamlSourceMaps`, `YamlCelParse`, `CelParse`, `CelEval`,
        `CelFunctions`, `CelCheck`, `ReflectSchema`, `RegexSearch`, `RuleLoad`)."""
        cdef bytes out
        if fn == "YamlLoad":
            out = self._hndl.yamlLoad(args[0].encode("utf-8"), args[1].encode("utf-8"))
        elif fn == "YamlSourceMaps":
            out = self._hndl.yamlSourceMaps(args[0].encode("utf-8"), args[1].encode("utf-8"))
        elif fn == "YamlCelParse":
            out = self._hndl.yamlCelParse(args[0].encode("utf-8"), args[1].encode("utf-8"),
                                          args[2].encode("utf-8"))
        elif fn == "CelParse":
            out = self._hndl.celParse(args[0].encode("utf-8"))
        elif fn == "CelEval":
            out = self._hndl.celEval(args[0].encode("utf-8"), args[1].encode("utf-8"), args[2])
        elif fn == "CelFunctions":
            out = self._hndl.celFunctions()
        elif fn == "CelCheck":
            out = self._hndl.celCheck(args[0].encode("utf-8"), args[1].encode("utf-8"))
        elif fn == "ReflectSchema":
            out = self._hndl.reflectSchema()
        elif fn == "RegexSearch":
            out = self._hndl.regexSearch(args[0].encode("utf-8"), args[1].encode("utf-8"))
        elif fn == "RuleLoad":
            out = self._hndl.ruleLoad(args[0].encode("utf-8"), args[1].encode("utf-8"),
                                      True if args[2] else False)
        else:
            raise ValueError("unknown lint test hook %r" % fn)
        return out.decode("utf-8", "surrogateescape")
