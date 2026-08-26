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
