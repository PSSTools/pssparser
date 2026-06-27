# cython: language_level=3
from enum import IntEnum
from libcpp.cast cimport dynamic_cast
from libcpp.cast cimport reinterpret_cast
from libcpp.cast cimport static_cast
from libcpp.string cimport string as      std_string
from libcpp.map cimport map as            std_map
from libcpp.unordered_map cimport unordered_map as  std_unordered_map
from libcpp.memory cimport unique_ptr, shared_ptr
from libcpp.vector cimport vector as std_vector
from libcpp.utility cimport pair as  std_pair
from libcpp cimport bool as          bool
cimport cpython.ref as cpy_ref
from cython.operator cimport dereference

cdef extern from "pssp/ast/impl/UP.h" namespace "pssp::ast":
    cpdef cppclass UP[T](unique_ptr[T]):
        UP()
        UP(T *, bool)
        T *get()

ctypedef char                 int8_t
ctypedef unsigned char        uint8_t
ctypedef short                int16_t
ctypedef unsigned short       uint16_t
ctypedef int                  int32_t
ctypedef unsigned int         uint32_t
ctypedef long long            int64_t
ctypedef unsigned long long   uint64_t

from pssparser cimport ast_decl
cdef class Location:
    cdef ast_decl.Location _val
    @staticmethod
    cdef Location wrap(const ast_decl.Location &v)

cdef class SymbolRefPathElem:
    cdef ast_decl.SymbolRefPathElem _val
    @staticmethod
    cdef SymbolRefPathElem wrap(const ast_decl.SymbolRefPathElem &v)

cdef class Factory(object):
    cdef ast_decl.IFactory *_hndl
    cpdef TemplateParamDeclList mkTemplateParamDeclList(self)
    cpdef AssocData mkAssocData(self)
    cpdef ExecTargetTemplateParam mkExecTargetTemplateParam(self,
    Expr expr,
    int32_t start,
    int32_t end)
    cpdef Expr mkExpr(self)
    cpdef TemplateParamValue mkTemplateParamValue(self)
    cpdef TemplateParamValueList mkTemplateParamValueList(self)
    cpdef MonitorActivityMatchChoice mkMonitorActivityMatchChoice(self,
    bool is_default,
    ExprOpenRangeList cond,
    ScopeChild body)
    cpdef ExprAggrMapElem mkExprAggrMapElem(self,
    Expr lhs,
    Expr rhs)
    cpdef ExprAggrStructElem mkExprAggrStructElem(self,
    ExprId name,
    Expr value)
    cpdef RefExpr mkRefExpr(self)
    cpdef MonitorActivitySelectBranch mkMonitorActivitySelectBranch(self,
    Expr guard,
    ScopeChild body)
    cpdef ScopeChild mkScopeChild(self)
    cpdef ActivityMatchChoice mkActivityMatchChoice(self,
    bool is_default,
    ExprOpenRangeList cond,
    ScopeChild body)
    cpdef SymbolImportSpec mkSymbolImportSpec(self)
    cpdef SymbolRefPath mkSymbolRefPath(self)
    cpdef ActivitySelectBranch mkActivitySelectBranch(self,
    Expr guard,
    Expr weight,
    ScopeChild body)
    cpdef ActionFieldInitializer mkActionFieldInitializer(self,
    ExprHierarchicalId path,
    Expr value)
    cpdef ActivityJoinSpec mkActivityJoinSpec(self)
    cpdef MonitorActivityStmt mkMonitorActivityStmt(self)
    cpdef NamedScopeChild mkNamedScopeChild(self,
    ExprId name)
    cpdef PackageImportStmt mkPackageImportStmt(self,
    bool wildcard,
    ExprId alias)
    cpdef ActivitySchedulingConstraint mkActivitySchedulingConstraint(self,
    bool is_parallel)
    cpdef ActivityStmt mkActivityStmt(self)
    cpdef ProceduralStmtIfClause mkProceduralStmtIfClause(self,
    Expr cond,
    ScopeChild body)
    cpdef Annotation mkAnnotation(self,
    TypeIdentifier type)
    cpdef AnnotationParam mkAnnotationParam(self,
    Expr value)
    cpdef ConstraintStmt mkConstraintStmt(self)
    cpdef PyImportFromStmt mkPyImportFromStmt(self)
    cpdef PyImportStmt mkPyImportStmt(self)
    cpdef RefExprScopeIndex mkRefExprScopeIndex(self,
    RefExpr base,
    int32_t offset)
    cpdef RefExprTypeScopeContext mkRefExprTypeScopeContext(self,
    RefExpr base,
    int32_t offset)
    cpdef RefExprTypeScopeGlobal mkRefExprTypeScopeGlobal(self,
    int32_t fileid)
    cpdef Scope mkScope(self)
    cpdef CoverStmtInline mkCoverStmtInline(self,
    ScopeChild body)
    cpdef CoverStmtReference mkCoverStmtReference(self,
    ExprRefPath target)
    cpdef DataType mkDataType(self)
    cpdef ScopeChildRef mkScopeChildRef(self,
    ScopeChild target)
    cpdef SymbolChild mkSymbolChild(self)
    cpdef SymbolScopeRef mkSymbolScopeRef(self,
    str name)
    cpdef ExecStmt mkExecStmt(self)
    cpdef ExecTargetTemplateBlock mkExecTargetTemplateBlock(self,
     kind,
    str data)
    cpdef TemplateParamDecl mkTemplateParamDecl(self,
    ExprId name)
    cpdef ExportFunction mkExportFunction(self,
     plat,
    ExprId name)
    cpdef TemplateParamExprValue mkTemplateParamExprValue(self,
    Expr value)
    cpdef TemplateParamTypeValue mkTemplateParamTypeValue(self,
    DataType value)
    cpdef ExprAggrLiteral mkExprAggrLiteral(self)
    cpdef TypeIdentifier mkTypeIdentifier(self)
    cpdef TypeIdentifierElem mkTypeIdentifierElem(self,
    ExprId id,
    TemplateParamValueList params)
    cpdef TypedefDeclaration mkTypedefDeclaration(self,
    ExprId name,
    DataType type)
    cpdef ExprBin mkExprBin(self,
    Expr lhs,
     op,
    Expr rhs)
    cpdef ExprBitSlice mkExprBitSlice(self,
    Expr lhs,
    Expr rhs)
    cpdef ExprBool mkExprBool(self,
    bool value)
    cpdef ExprCast mkExprCast(self,
    DataType casting_type,
    Expr expr)
    cpdef ExprCompileHas mkExprCompileHas(self,
    ExprRefPathStatic ref)
    cpdef ExprCond mkExprCond(self,
    Expr cond_e,
    Expr true_e,
    Expr false_e)
    cpdef ExprDomainOpenRangeList mkExprDomainOpenRangeList(self)
    cpdef ExprDomainOpenRangeValue mkExprDomainOpenRangeValue(self,
    bool single,
    Expr lhs,
    Expr rhs)
    cpdef ExprHierarchicalId mkExprHierarchicalId(self)
    cpdef ExprId mkExprId(self,
    str id,
    bool is_escaped)
    cpdef ExprIn mkExprIn(self,
    Expr lhs,
    ExprOpenRangeList rhs,
    Expr collection)
    cpdef ExprListLiteral mkExprListLiteral(self)
    cpdef ExprMemberPathElem mkExprMemberPathElem(self,
    ExprId id,
    MethodParameterList params)
    cpdef ExprNull mkExprNull(self)
    cpdef ExprNumber mkExprNumber(self)
    cpdef ExprOpenRangeList mkExprOpenRangeList(self)
    cpdef ExprOpenRangeValue mkExprOpenRangeValue(self,
    Expr lhs,
    Expr rhs)
    cpdef ExprRefPath mkExprRefPath(self)
    cpdef ExprRefPathElem mkExprRefPathElem(self)
    cpdef ExprStaticRefPath mkExprStaticRefPath(self,
    bool is_global,
    ExprMemberPathElem leaf)
    cpdef ExprString mkExprString(self,
    str value,
    bool is_raw)
    cpdef ExprStructLiteral mkExprStructLiteral(self)
    cpdef ExprStructLiteralItem mkExprStructLiteralItem(self,
    ExprId id,
    Expr value)
    cpdef ExprSubscript mkExprSubscript(self,
    Expr expr,
    Expr subscript)
    cpdef ExprSubstring mkExprSubstring(self,
    Expr expr,
    Expr start,
    Expr end)
    cpdef ExprUnary mkExprUnary(self,
     op,
    Expr rhs)
    cpdef ExtendEnum mkExtendEnum(self,
    TypeIdentifier target)
    cpdef FunctionDefinition mkFunctionDefinition(self,
    FunctionPrototype proto,
    ExecScope body,
     plat)
    cpdef FunctionImport mkFunctionImport(self,
     plat,
    str lang)
    cpdef FunctionParamDecl mkFunctionParamDecl(self,
     kind,
    ExprId name,
    DataType type,
     dir,
    Expr dflt)
    cpdef GenericConstraintDeclValue mkGenericConstraintDeclValue(self)
    cpdef GenericConstraintParam mkGenericConstraintParam(self,
    ExprId name,
    bool is_const,
    bool is_numeric,
    DataType type)
    cpdef MethodParameterList mkMethodParameterList(self)
    cpdef MonitorActivityActionTraversal mkMonitorActivityActionTraversal(self,
    ExprRefPath target,
    ConstraintStmt with_c)
    cpdef ActionHandleField mkActionHandleField(self,
    ExprId name,
    DataType type)
    cpdef MonitorActivityConcat mkMonitorActivityConcat(self,
    MonitorActivityStmt lhs,
    MonitorActivityStmt rhs)
    cpdef MonitorActivityEventually mkMonitorActivityEventually(self,
    Expr condition,
    MonitorActivityStmt body)
    cpdef MonitorActivityIfElse mkMonitorActivityIfElse(self,
    Expr cond,
    MonitorActivityStmt true_s,
    MonitorActivityStmt false_s)
    cpdef ActivityBindStmt mkActivityBindStmt(self,
    ExprHierarchicalId lhs)
    cpdef ActivityConstraint mkActivityConstraint(self,
    ConstraintStmt constraint)
    cpdef MonitorActivityMatch mkMonitorActivityMatch(self,
    Expr cond)
    cpdef MonitorActivityMonitorTraversal mkMonitorActivityMonitorTraversal(self,
    ExprRefPath target,
    ConstraintStmt with_c)
    cpdef MonitorActivityOverlap mkMonitorActivityOverlap(self,
    MonitorActivityStmt lhs,
    MonitorActivityStmt rhs)
    cpdef MonitorActivityRepeatCount mkMonitorActivityRepeatCount(self,
    ExprId loop_var,
    Expr count,
    ScopeChild body)
    cpdef ActivityJoinSpecBranch mkActivityJoinSpecBranch(self)
    cpdef ActivityJoinSpecFirst mkActivityJoinSpecFirst(self,
    Expr count)
    cpdef ActivityJoinSpecNone mkActivityJoinSpecNone(self)
    cpdef ActivityJoinSpecSelect mkActivityJoinSpecSelect(self,
    Expr count)
    cpdef MonitorActivityRepeatWhile mkMonitorActivityRepeatWhile(self,
    Expr cond,
    ScopeChild body)
    cpdef ActivityLabeledStmt mkActivityLabeledStmt(self)
    cpdef MonitorActivitySelect mkMonitorActivitySelect(self)
    cpdef MonitorConstraint mkMonitorConstraint(self,
    ConstraintStmt constraint)
    cpdef NamedScope mkNamedScope(self,
    ExprId name)
    cpdef PackageScope mkPackageScope(self)
    cpdef ProceduralStmtAssignment mkProceduralStmtAssignment(self,
    Expr lhs,
     op,
    Expr rhs)
    cpdef ProceduralStmtBody mkProceduralStmtBody(self,
    ScopeChild body)
    cpdef ProceduralStmtBreak mkProceduralStmtBreak(self)
    cpdef ProceduralStmtContinue mkProceduralStmtContinue(self)
    cpdef ProceduralStmtDataDeclaration mkProceduralStmtDataDeclaration(self,
    ExprId name,
    DataType datatype,
    Expr init)
    cpdef ProceduralStmtExpr mkProceduralStmtExpr(self,
    Expr expr)
    cpdef ProceduralStmtFunctionCall mkProceduralStmtFunctionCall(self,
    ExprRefPathStaticRooted prefix)
    cpdef ProceduralStmtIfElse mkProceduralStmtIfElse(self)
    cpdef ProceduralStmtMatch mkProceduralStmtMatch(self,
    Expr expr)
    cpdef ProceduralStmtMatchChoice mkProceduralStmtMatchChoice(self,
    bool is_default,
    ExprOpenRangeList cond,
    ScopeChild body)
    cpdef ProceduralStmtRandomize mkProceduralStmtRandomize(self,
    Expr target)
    cpdef ConstraintScope mkConstraintScope(self)
    cpdef ProceduralStmtReturn mkProceduralStmtReturn(self,
    Expr expr)
    cpdef ConstraintStmtDefault mkConstraintStmtDefault(self,
    ExprHierarchicalId hid,
    Expr expr)
    cpdef ConstraintStmtDefaultDisable mkConstraintStmtDefaultDisable(self,
    ExprHierarchicalId hid)
    cpdef ConstraintStmtExpr mkConstraintStmtExpr(self,
    Expr expr)
    cpdef ConstraintStmtField mkConstraintStmtField(self,
    ExprId name,
    DataType type)
    cpdef ProceduralStmtYield mkProceduralStmtYield(self)
    cpdef ConstraintStmtIf mkConstraintStmtIf(self,
    Expr cond,
    ConstraintScope true_c,
    ConstraintScope false_c)
    cpdef ConstraintStmtUnique mkConstraintStmtUnique(self)
    cpdef DataTypeBool mkDataTypeBool(self)
    cpdef DataTypeChandle mkDataTypeChandle(self)
    cpdef DataTypeEnum mkDataTypeEnum(self,
    DataTypeUserDefined tid,
    ExprOpenRangeList in_rangelist)
    cpdef DataTypeInt mkDataTypeInt(self,
    bool is_signed,
    Expr width,
    ExprDomainOpenRangeList in_range)
    cpdef DataTypePyObj mkDataTypePyObj(self)
    cpdef DataTypeRef mkDataTypeRef(self,
    DataTypeUserDefined type)
    cpdef DataTypeString mkDataTypeString(self,
    bool has_range)
    cpdef DataTypeUserDefined mkDataTypeUserDefined(self,
    bool is_global,
    TypeIdentifier type_id)
    cpdef EnumDecl mkEnumDecl(self,
    ExprId name)
    cpdef EnumItem mkEnumItem(self,
    ExprId name,
    Expr value)
    cpdef SymbolChildrenScope mkSymbolChildrenScope(self,
    str name)
    cpdef TemplateCategoryTypeParamDecl mkTemplateCategoryTypeParamDecl(self,
    ExprId name,
     category,
    TypeIdentifier restriction,
    DataType dflt)
    cpdef TemplateGenericTypeParamDecl mkTemplateGenericTypeParamDecl(self,
    ExprId name,
    DataType dflt)
    cpdef ExprAggrEmpty mkExprAggrEmpty(self)
    cpdef ExprAggrList mkExprAggrList(self)
    cpdef TemplateValueParamDecl mkTemplateValueParamDecl(self,
    ExprId name,
    DataType type,
    Expr dflt)
    cpdef ExprAggrMap mkExprAggrMap(self)
    cpdef ExprAggrStruct mkExprAggrStruct(self)
    cpdef ExprRefPathContext mkExprRefPathContext(self,
    ExprHierarchicalId hier_id)
    cpdef ExprRefPathId mkExprRefPathId(self,
    ExprId id)
    cpdef ExprRefPathStatic mkExprRefPathStatic(self,
    bool is_global)
    cpdef ExprRefPathStaticRooted mkExprRefPathStaticRooted(self,
    ExprRefPathStatic root,
    ExprHierarchicalId leaf)
    cpdef ExprSignedNumber mkExprSignedNumber(self,
    str image,
    int32_t width,
    int64_t value)
    cpdef ExprUnsignedNumber mkExprUnsignedNumber(self,
    str image,
    int32_t width,
    uint64_t value)
    cpdef ExtendType mkExtendType(self,
     kind,
    TypeIdentifier target)
    cpdef Field mkField(self,
    ExprId name,
    DataType type,
     attr,
    Expr init)
    cpdef FieldClaim mkFieldClaim(self,
    ExprId name,
    DataTypeUserDefined type,
    bool is_lock)
    cpdef FieldCompRef mkFieldCompRef(self,
    ExprId name,
    DataTypeUserDefined type)
    cpdef FieldPool mkFieldPool(self,
    ExprId name,
    DataTypeUserDefined type,
    Expr size)
    cpdef FieldRef mkFieldRef(self,
    ExprId name,
    DataTypeUserDefined type,
    bool is_input)
    cpdef FunctionImportProto mkFunctionImportProto(self,
     plat,
    str lang,
    FunctionPrototype proto)
    cpdef FunctionImportType mkFunctionImportType(self,
     plat,
    str lang,
    TypeIdentifier type)
    cpdef FunctionPrototype mkFunctionPrototype(self,
    ExprId name,
    DataType rtype,
    bool is_target,
    bool is_solve)
    cpdef GlobalScope mkGlobalScope(self,
    int32_t fileid)
    cpdef ActivityActionHandleTraversal mkActivityActionHandleTraversal(self,
    ExprRefPathContext target,
    ConstraintStmt with_c)
    cpdef ActivityActionTypeTraversal mkActivityActionTypeTraversal(self,
    DataTypeUserDefined target,
    ConstraintStmt with_c)
    cpdef ActivityAtomicBlock mkActivityAtomicBlock(self,
    ScopeChild body)
    cpdef ActivityForeach mkActivityForeach(self,
    ExprId it_id,
    ExprId idx_id,
    ExprRefPathContext target,
    ScopeChild body)
    cpdef ActivityIfElse mkActivityIfElse(self,
    Expr cond,
    ActivityStmt true_s,
    ActivityStmt false_s)
    cpdef ActivityMatch mkActivityMatch(self,
    Expr cond)
    cpdef ActivityRepeatCount mkActivityRepeatCount(self,
    ExprId loop_var,
    Expr count,
    ScopeChild body)
    cpdef ActivityRepeatWhile mkActivityRepeatWhile(self,
    Expr cond,
    ScopeChild body)
    cpdef ActivityReplicate mkActivityReplicate(self,
    ExprId idx_id,
    ExprId it_label,
    ScopeChild body)
    cpdef ActivitySelect mkActivitySelect(self)
    cpdef ActivitySuper mkActivitySuper(self)
    cpdef ConstraintBlock mkConstraintBlock(self,
    str name,
    bool is_dynamic)
    cpdef ProceduralStmtRepeatWhile mkProceduralStmtRepeatWhile(self,
    ScopeChild body,
    Expr expr)
    cpdef ProceduralStmtWhile mkProceduralStmtWhile(self,
    ScopeChild body,
    Expr expr)
    cpdef ConstraintStmtForall mkConstraintStmtForall(self,
    ExprId iterator_id,
    DataTypeUserDefined type_id,
    ExprRefPath ref_path)
    cpdef ConstraintStmtForeach mkConstraintStmtForeach(self,
    Expr expr)
    cpdef ConstraintStmtImplication mkConstraintStmtImplication(self,
    Expr cond)
    cpdef SymbolScope mkSymbolScope(self,
    str name)
    cpdef TypeScope mkTypeScope(self,
    ExprId name,
    TypeIdentifier super_t)
    cpdef ExprRefPathStaticFunc mkExprRefPathStaticFunc(self,
    bool is_global,
    MethodParameterList params)
    cpdef ExprRefPathSuper mkExprRefPathSuper(self,
    ExprHierarchicalId hier_id)
    cpdef Action mkAction(self,
    ExprId name,
    TypeIdentifier super_t,
    bool is_abstract)
    cpdef Monitor mkMonitor(self,
    ExprId name,
    TypeIdentifier super_t)
    cpdef MonitorActivityDecl mkMonitorActivityDecl(self,
    str name)
    cpdef ActivityDecl mkActivityDecl(self,
    str name)
    cpdef MonitorActivitySchedule mkMonitorActivitySchedule(self,
    str name)
    cpdef MonitorActivitySequence mkMonitorActivitySequence(self,
    str name)
    cpdef ActivityLabeledScope mkActivityLabeledScope(self,
    str name)
    cpdef AnnotationDecl mkAnnotationDecl(self,
    ExprId name,
    TypeIdentifier super_t)
    cpdef Component mkComponent(self,
    ExprId name,
    TypeIdentifier super_t)
    cpdef ProceduralStmtSymbolBodyScope mkProceduralStmtSymbolBodyScope(self,
    str name,
    ScopeChild body)
    cpdef RootSymbolScope mkRootSymbolScope(self,
    str name)
    cpdef ConstraintSymbolScope mkConstraintSymbolScope(self,
    str name)
    cpdef Struct mkStruct(self,
    ExprId name,
    TypeIdentifier super_t,
     kind)
    cpdef SymbolEnumScope mkSymbolEnumScope(self,
    str name)
    cpdef SymbolExtendScope mkSymbolExtendScope(self,
    str name)
    cpdef SymbolFunctionScope mkSymbolFunctionScope(self,
    str name)
    cpdef SymbolTypeScope mkSymbolTypeScope(self,
    str name,
    SymbolScope plist)
    cpdef ExecScope mkExecScope(self,
    str name)
    cpdef GenericConstraintDeclBool mkGenericConstraintDeclBool(self,
    str name,
    bool is_dynamic)
    cpdef ProceduralStmtRepeat mkProceduralStmtRepeat(self,
    str name,
    ScopeChild body,
    ExprId it_id,
    Expr count)
    cpdef ActivitySequence mkActivitySequence(self,
    str name)
    cpdef ActivityParallel mkActivityParallel(self,
    str name,
    ActivityJoinSpec join_spec)
    cpdef ActivitySchedule mkActivitySchedule(self,
    str name,
    ActivityJoinSpec join_spec)
    cpdef ProceduralStmtForeach mkProceduralStmtForeach(self,
    str name,
    ScopeChild body,
    ExprRefPath path,
    ExprId it_id,
    ExprId idx_id)
    cpdef ExecBlock mkExecBlock(self,
    str name,
     kind)
    @staticmethod
    cdef mk(ast_decl.IFactory *hndl)
cdef class TemplateParamDeclList(object):
    cdef ast_decl.ITemplateParamDeclList    *_hndl
    cdef bool           _owned
    
    cpdef void accept(self, VisitorBase v)
    cpdef int id(self)
    cdef ast_decl.ITemplateParamDeclList *asTemplateParamDeclList(self)
    @staticmethod
    cdef TemplateParamDeclList mk(ast_decl.ITemplateParamDeclList *hndl, bool owned)
    cpdef getParams(self)
    cpdef getParam(self, i)
    cpdef void addParam(self, TemplateParamDecl i)
    cpdef numParams(self)
    cpdef bool getSpecialized(self)

cdef class AssocData(object):
    cdef ast_decl.IAssocData    *_hndl
    cdef bool           _owned
    
    cpdef void accept(self, VisitorBase v)
    cpdef int id(self)
    cdef ast_decl.IAssocData *asAssocData(self)
    @staticmethod
    cdef AssocData mk(ast_decl.IAssocData *hndl, bool owned)

cdef class ExecTargetTemplateParam(object):
    cdef ast_decl.IExecTargetTemplateParam    *_hndl
    cdef bool           _owned
    
    cpdef void accept(self, VisitorBase v)
    cpdef int id(self)
    cdef ast_decl.IExecTargetTemplateParam *asExecTargetTemplateParam(self)
    @staticmethod
    cdef ExecTargetTemplateParam mk(ast_decl.IExecTargetTemplateParam *hndl, bool owned)
    cpdef Expr getExpr(self)
    cpdef int32_t getStart(self)
    cpdef int32_t getEnd(self)

cdef class Expr(object):
    cdef ast_decl.IExpr    *_hndl
    cdef bool           _owned
    
    cpdef void accept(self, VisitorBase v)
    cpdef int id(self)
    cdef ast_decl.IExpr *asExpr(self)
    @staticmethod
    cdef Expr mk(ast_decl.IExpr *hndl, bool owned)

cdef class TemplateParamValue(object):
    cdef ast_decl.ITemplateParamValue    *_hndl
    cdef bool           _owned
    
    cpdef void accept(self, VisitorBase v)
    cpdef int id(self)
    cdef ast_decl.ITemplateParamValue *asTemplateParamValue(self)
    @staticmethod
    cdef TemplateParamValue mk(ast_decl.ITemplateParamValue *hndl, bool owned)

cdef class TemplateParamValueList(object):
    cdef ast_decl.ITemplateParamValueList    *_hndl
    cdef bool           _owned
    
    cpdef void accept(self, VisitorBase v)
    cpdef int id(self)
    cdef ast_decl.ITemplateParamValueList *asTemplateParamValueList(self)
    @staticmethod
    cdef TemplateParamValueList mk(ast_decl.ITemplateParamValueList *hndl, bool owned)
    cpdef getValues(self)
    cpdef getValue(self, i)
    cpdef void addValue(self, TemplateParamValue i)
    cpdef numValues(self)

cdef class MonitorActivityMatchChoice(object):
    cdef ast_decl.IMonitorActivityMatchChoice    *_hndl
    cdef bool           _owned
    
    cpdef void accept(self, VisitorBase v)
    cpdef int id(self)
    cdef ast_decl.IMonitorActivityMatchChoice *asMonitorActivityMatchChoice(self)
    @staticmethod
    cdef MonitorActivityMatchChoice mk(ast_decl.IMonitorActivityMatchChoice *hndl, bool owned)
    cpdef bool getIs_default(self)
    cpdef ExprOpenRangeList getCond(self)
    cpdef ScopeChild getBody(self)

cdef class ExprAggrMapElem(object):
    cdef ast_decl.IExprAggrMapElem    *_hndl
    cdef bool           _owned
    
    cpdef void accept(self, VisitorBase v)
    cpdef int id(self)
    cdef ast_decl.IExprAggrMapElem *asExprAggrMapElem(self)
    @staticmethod
    cdef ExprAggrMapElem mk(ast_decl.IExprAggrMapElem *hndl, bool owned)
    cpdef Expr getLhs(self)
    cpdef Expr getRhs(self)

cdef class ExprAggrStructElem(object):
    cdef ast_decl.IExprAggrStructElem    *_hndl
    cdef bool           _owned
    
    cpdef void accept(self, VisitorBase v)
    cpdef int id(self)
    cdef ast_decl.IExprAggrStructElem *asExprAggrStructElem(self)
    @staticmethod
    cdef ExprAggrStructElem mk(ast_decl.IExprAggrStructElem *hndl, bool owned)
    cpdef ExprId getName(self)
    cpdef int32_t getTarget(self)
    cpdef Expr getValue(self)

cdef class RefExpr(object):
    cdef ast_decl.IRefExpr    *_hndl
    cdef bool           _owned
    
    cpdef void accept(self, VisitorBase v)
    cpdef int id(self)
    cdef ast_decl.IRefExpr *asRefExpr(self)
    @staticmethod
    cdef RefExpr mk(ast_decl.IRefExpr *hndl, bool owned)

cdef class MonitorActivitySelectBranch(object):
    cdef ast_decl.IMonitorActivitySelectBranch    *_hndl
    cdef bool           _owned
    
    cpdef void accept(self, VisitorBase v)
    cpdef int id(self)
    cdef ast_decl.IMonitorActivitySelectBranch *asMonitorActivitySelectBranch(self)
    @staticmethod
    cdef MonitorActivitySelectBranch mk(ast_decl.IMonitorActivitySelectBranch *hndl, bool owned)
    cpdef Expr getGuard(self)
    cpdef ScopeChild getBody(self)

cdef class ScopeChild(object):
    cdef ast_decl.IScopeChild    *_hndl
    cdef bool           _owned
    
    cpdef void accept(self, VisitorBase v)
    cpdef int id(self)
    cdef ast_decl.IScopeChild *asScopeChild(self)
    @staticmethod
    cdef ScopeChild mk(ast_decl.IScopeChild *hndl, bool owned)
    cpdef str getDocstring(self)
    cpdef void setDocstring(self, str v)
    cpdef Location getLocation(self)
    cpdef Scope getParent(self)
    cpdef int32_t getIndex(self)
    cpdef AssocData getAssocData(self)
    cpdef getAnnotations(self)
    cpdef getAnnotation(self, i)
    cpdef void addAnnotation(self, Annotation i)
    cpdef numAnnotations(self)

cdef class ActivityMatchChoice(object):
    cdef ast_decl.IActivityMatchChoice    *_hndl
    cdef bool           _owned
    
    cpdef void accept(self, VisitorBase v)
    cpdef int id(self)
    cdef ast_decl.IActivityMatchChoice *asActivityMatchChoice(self)
    @staticmethod
    cdef ActivityMatchChoice mk(ast_decl.IActivityMatchChoice *hndl, bool owned)
    cpdef bool getIs_default(self)
    cpdef ExprOpenRangeList getCond(self)
    cpdef ScopeChild getBody(self)

cdef class SymbolImportSpec(object):
    cdef ast_decl.ISymbolImportSpec    *_hndl
    cdef bool           _owned
    
    cpdef void accept(self, VisitorBase v)
    cpdef int id(self)
    cdef ast_decl.ISymbolImportSpec *asSymbolImportSpec(self)
    @staticmethod
    cdef SymbolImportSpec mk(ast_decl.ISymbolImportSpec *hndl, bool owned)
    cpdef getImports(self)
    cpdef getImport(self, i)
    cpdef void addImport(self, PackageImportStmt i)
    cpdef numImports(self)
    cpdef bool symtabHas(self, str i)
    cpdef SymbolRefPath symtabAt(self, str i)

cdef class SymbolRefPath(object):
    cdef ast_decl.ISymbolRefPath    *_hndl
    cdef bool           _owned
    
    cpdef void accept(self, VisitorBase v)
    cpdef int id(self)
    cdef ast_decl.ISymbolRefPath *asSymbolRefPath(self)
    @staticmethod
    cdef SymbolRefPath mk(ast_decl.ISymbolRefPath *hndl, bool owned)
    cpdef int32_t getPyref_idx(self)

cdef class ActivitySelectBranch(object):
    cdef ast_decl.IActivitySelectBranch    *_hndl
    cdef bool           _owned
    
    cpdef void accept(self, VisitorBase v)
    cpdef int id(self)
    cdef ast_decl.IActivitySelectBranch *asActivitySelectBranch(self)
    @staticmethod
    cdef ActivitySelectBranch mk(ast_decl.IActivitySelectBranch *hndl, bool owned)
    cpdef Expr getGuard(self)
    cpdef Expr getWeight(self)
    cpdef ScopeChild getBody(self)

cdef class ActionFieldInitializer(ScopeChild):
    
    cdef ast_decl.IActionFieldInitializer *asActionFieldInitializer(self)
    @staticmethod
    cdef ActionFieldInitializer mk(ast_decl.IActionFieldInitializer *hndl, bool owned)
    cpdef ExprHierarchicalId getPath(self)
    cpdef Expr getValue(self)

cdef class ActivityJoinSpec(ScopeChild):
    
    cdef ast_decl.IActivityJoinSpec *asActivityJoinSpec(self)
    @staticmethod
    cdef ActivityJoinSpec mk(ast_decl.IActivityJoinSpec *hndl, bool owned)

cdef class MonitorActivityStmt(ScopeChild):
    
    cdef ast_decl.IMonitorActivityStmt *asMonitorActivityStmt(self)
    @staticmethod
    cdef MonitorActivityStmt mk(ast_decl.IMonitorActivityStmt *hndl, bool owned)

cdef class NamedScopeChild(ScopeChild):
    
    cdef ast_decl.INamedScopeChild *asNamedScopeChild(self)
    @staticmethod
    cdef NamedScopeChild mk(ast_decl.INamedScopeChild *hndl, bool owned)
    cpdef ExprId getName(self)

cdef class PackageImportStmt(ScopeChild):
    
    cdef ast_decl.IPackageImportStmt *asPackageImportStmt(self)
    @staticmethod
    cdef PackageImportStmt mk(ast_decl.IPackageImportStmt *hndl, bool owned)
    cpdef bool getWildcard(self)
    cpdef ExprId getAlias(self)
    cpdef TypeIdentifier getPath(self)

cdef class ActivitySchedulingConstraint(ScopeChild):
    
    cdef ast_decl.IActivitySchedulingConstraint *asActivitySchedulingConstraint(self)
    @staticmethod
    cdef ActivitySchedulingConstraint mk(ast_decl.IActivitySchedulingConstraint *hndl, bool owned)
    cpdef bool getIs_parallel(self)
    cpdef getTargets(self)
    cpdef getTarget(self, i)
    cpdef void addTarget(self, ExprHierarchicalId i)
    cpdef numTargets(self)

cdef class ActivityStmt(ScopeChild):
    
    cdef ast_decl.IActivityStmt *asActivityStmt(self)
    @staticmethod
    cdef ActivityStmt mk(ast_decl.IActivityStmt *hndl, bool owned)

cdef class ProceduralStmtIfClause(ScopeChild):
    
    cdef ast_decl.IProceduralStmtIfClause *asProceduralStmtIfClause(self)
    @staticmethod
    cdef ProceduralStmtIfClause mk(ast_decl.IProceduralStmtIfClause *hndl, bool owned)
    cpdef Expr getCond(self)
    cpdef ScopeChild getBody(self)

cdef class Annotation(ScopeChild):
    
    cdef ast_decl.IAnnotation *asAnnotation(self)
    @staticmethod
    cdef Annotation mk(ast_decl.IAnnotation *hndl, bool owned)
    cpdef TypeIdentifier getType(self)
    cpdef getParameters(self)
    cpdef getParameter(self, i)
    cpdef void addParameter(self, AnnotationParam i)
    cpdef numParameters(self)

cdef class AnnotationParam(ScopeChild):
    
    cdef ast_decl.IAnnotationParam *asAnnotationParam(self)
    @staticmethod
    cdef AnnotationParam mk(ast_decl.IAnnotationParam *hndl, bool owned)
    cpdef ExprId getName(self)
    cpdef Expr getValue(self)

cdef class ConstraintStmt(ScopeChild):
    
    cdef ast_decl.IConstraintStmt *asConstraintStmt(self)
    @staticmethod
    cdef ConstraintStmt mk(ast_decl.IConstraintStmt *hndl, bool owned)

cdef class PyImportFromStmt(ScopeChild):
    
    cdef ast_decl.IPyImportFromStmt *asPyImportFromStmt(self)
    @staticmethod
    cdef PyImportFromStmt mk(ast_decl.IPyImportFromStmt *hndl, bool owned)
    cpdef getPathList(self)
    cpdef getPath(self, i)
    cpdef void addPath(self, ExprId i)
    cpdef numPath(self)
    cpdef getTargets(self)
    cpdef getTarget(self, i)
    cpdef void addTarget(self, ExprId i)
    cpdef numTargets(self)

cdef class PyImportStmt(ScopeChild):
    
    cdef ast_decl.IPyImportStmt *asPyImportStmt(self)
    @staticmethod
    cdef PyImportStmt mk(ast_decl.IPyImportStmt *hndl, bool owned)
    cpdef getPathList(self)
    cpdef getPath(self, i)
    cpdef void addPath(self, ExprId i)
    cpdef numPath(self)
    cpdef ExprId getAlias(self)

cdef class RefExprScopeIndex(RefExpr):
    
    cdef ast_decl.IRefExprScopeIndex *asRefExprScopeIndex(self)
    @staticmethod
    cdef RefExprScopeIndex mk(ast_decl.IRefExprScopeIndex *hndl, bool owned)
    cpdef RefExpr getBase(self)
    cpdef int32_t getOffset(self)

cdef class RefExprTypeScopeContext(RefExpr):
    
    cdef ast_decl.IRefExprTypeScopeContext *asRefExprTypeScopeContext(self)
    @staticmethod
    cdef RefExprTypeScopeContext mk(ast_decl.IRefExprTypeScopeContext *hndl, bool owned)
    cpdef RefExpr getBase(self)
    cpdef int32_t getOffset(self)

cdef class RefExprTypeScopeGlobal(RefExpr):
    
    cdef ast_decl.IRefExprTypeScopeGlobal *asRefExprTypeScopeGlobal(self)
    @staticmethod
    cdef RefExprTypeScopeGlobal mk(ast_decl.IRefExprTypeScopeGlobal *hndl, bool owned)
    cpdef int32_t getFileid(self)

cdef class Scope(ScopeChild):
    
    cdef ast_decl.IScope *asScope(self)
    @staticmethod
    cdef Scope mk(ast_decl.IScope *hndl, bool owned)
    cpdef Location getEndLocation(self)
    cpdef getChildren(self)
    cpdef getChild(self, i)
    cpdef void addChild(self, ScopeChild i)
    cpdef numChildren(self)

cdef class CoverStmtInline(ScopeChild):
    
    cdef ast_decl.ICoverStmtInline *asCoverStmtInline(self)
    @staticmethod
    cdef CoverStmtInline mk(ast_decl.ICoverStmtInline *hndl, bool owned)
    cpdef ScopeChild getBody(self)

cdef class CoverStmtReference(ScopeChild):
    
    cdef ast_decl.ICoverStmtReference *asCoverStmtReference(self)
    @staticmethod
    cdef CoverStmtReference mk(ast_decl.ICoverStmtReference *hndl, bool owned)
    cpdef ExprRefPath getTarget(self)

cdef class DataType(ScopeChild):
    
    cdef ast_decl.IDataType *asDataType(self)
    @staticmethod
    cdef DataType mk(ast_decl.IDataType *hndl, bool owned)

cdef class ScopeChildRef(ScopeChild):
    
    cdef ast_decl.IScopeChildRef *asScopeChildRef(self)
    @staticmethod
    cdef ScopeChildRef mk(ast_decl.IScopeChildRef *hndl, bool owned)
    cpdef ScopeChild getTarget(self)

cdef class SymbolChild(ScopeChild):
    
    cdef ast_decl.ISymbolChild *asSymbolChild(self)
    @staticmethod
    cdef SymbolChild mk(ast_decl.ISymbolChild *hndl, bool owned)
    cpdef int32_t getId(self)
    cpdef SymbolScope getUpper(self)

cdef class SymbolScopeRef(ScopeChild):
    
    cdef ast_decl.ISymbolScopeRef *asSymbolScopeRef(self)
    @staticmethod
    cdef SymbolScopeRef mk(ast_decl.ISymbolScopeRef *hndl, bool owned)
    cpdef str getName(self)
    cpdef void setName(self, str v)

cdef class ExecStmt(ScopeChild):
    
    cdef ast_decl.IExecStmt *asExecStmt(self)
    @staticmethod
    cdef ExecStmt mk(ast_decl.IExecStmt *hndl, bool owned)
    cpdef SymbolScope getUpper(self)

cdef class ExecTargetTemplateBlock(ScopeChild):
    
    cdef ast_decl.IExecTargetTemplateBlock *asExecTargetTemplateBlock(self)
    @staticmethod
    cdef ExecTargetTemplateBlock mk(ast_decl.IExecTargetTemplateBlock *hndl, bool owned)
    cpdef  getKind(self)
    cpdef str getData(self)
    cpdef void setData(self, str v)
    cpdef getParameters(self)
    cpdef getParameter(self, i)
    cpdef void addParameter(self, ExecTargetTemplateParam i)
    cpdef numParameters(self)

cdef class TemplateParamDecl(ScopeChild):
    
    cdef ast_decl.ITemplateParamDecl *asTemplateParamDecl(self)
    @staticmethod
    cdef TemplateParamDecl mk(ast_decl.ITemplateParamDecl *hndl, bool owned)
    cpdef ExprId getName(self)

cdef class ExportFunction(ScopeChild):
    
    cdef ast_decl.IExportFunction *asExportFunction(self)
    @staticmethod
    cdef ExportFunction mk(ast_decl.IExportFunction *hndl, bool owned)
    cpdef  getPlat(self)
    cpdef ExprId getName(self)

cdef class TemplateParamExprValue(TemplateParamValue):
    
    cdef ast_decl.ITemplateParamExprValue *asTemplateParamExprValue(self)
    @staticmethod
    cdef TemplateParamExprValue mk(ast_decl.ITemplateParamExprValue *hndl, bool owned)
    cpdef Expr getValue(self)

cdef class TemplateParamTypeValue(TemplateParamValue):
    
    cdef ast_decl.ITemplateParamTypeValue *asTemplateParamTypeValue(self)
    @staticmethod
    cdef TemplateParamTypeValue mk(ast_decl.ITemplateParamTypeValue *hndl, bool owned)
    cpdef DataType getValue(self)

cdef class ExprAggrLiteral(Expr):
    
    cdef ast_decl.IExprAggrLiteral *asExprAggrLiteral(self)
    @staticmethod
    cdef ExprAggrLiteral mk(ast_decl.IExprAggrLiteral *hndl, bool owned)

cdef class TypeIdentifier(Expr):
    
    cdef ast_decl.ITypeIdentifier *asTypeIdentifier(self)
    @staticmethod
    cdef TypeIdentifier mk(ast_decl.ITypeIdentifier *hndl, bool owned)
    cpdef getElems(self)
    cpdef getElem(self, i)
    cpdef void addElem(self, TypeIdentifierElem i)
    cpdef numElems(self)
    cpdef SymbolRefPath getTarget(self)

cdef class TypeIdentifierElem(Expr):
    
    cdef ast_decl.ITypeIdentifierElem *asTypeIdentifierElem(self)
    @staticmethod
    cdef TypeIdentifierElem mk(ast_decl.ITypeIdentifierElem *hndl, bool owned)
    cpdef ExprId getId(self)
    cpdef TemplateParamValueList getParams(self)

cdef class TypedefDeclaration(ScopeChild):
    
    cdef ast_decl.ITypedefDeclaration *asTypedefDeclaration(self)
    @staticmethod
    cdef TypedefDeclaration mk(ast_decl.ITypedefDeclaration *hndl, bool owned)
    cpdef ExprId getName(self)
    cpdef DataType getType(self)

cdef class ExprBin(Expr):
    
    cdef ast_decl.IExprBin *asExprBin(self)
    @staticmethod
    cdef ExprBin mk(ast_decl.IExprBin *hndl, bool owned)
    cpdef Expr getLhs(self)
    cpdef  getOp(self)
    cpdef Expr getRhs(self)

cdef class ExprBitSlice(Expr):
    
    cdef ast_decl.IExprBitSlice *asExprBitSlice(self)
    @staticmethod
    cdef ExprBitSlice mk(ast_decl.IExprBitSlice *hndl, bool owned)
    cpdef Expr getLhs(self)
    cpdef Expr getRhs(self)

cdef class ExprBool(Expr):
    
    cdef ast_decl.IExprBool *asExprBool(self)
    @staticmethod
    cdef ExprBool mk(ast_decl.IExprBool *hndl, bool owned)
    cpdef bool getValue(self)

cdef class ExprCast(Expr):
    
    cdef ast_decl.IExprCast *asExprCast(self)
    @staticmethod
    cdef ExprCast mk(ast_decl.IExprCast *hndl, bool owned)
    cpdef DataType getCasting_type(self)
    cpdef Expr getExpr(self)

cdef class ExprCompileHas(Expr):
    
    cdef ast_decl.IExprCompileHas *asExprCompileHas(self)
    @staticmethod
    cdef ExprCompileHas mk(ast_decl.IExprCompileHas *hndl, bool owned)
    cpdef ExprRefPathStatic getRef(self)

cdef class ExprCond(Expr):
    
    cdef ast_decl.IExprCond *asExprCond(self)
    @staticmethod
    cdef ExprCond mk(ast_decl.IExprCond *hndl, bool owned)
    cpdef Expr getCond_e(self)
    cpdef Expr getTrue_e(self)
    cpdef Expr getFalse_e(self)

cdef class ExprDomainOpenRangeList(Expr):
    
    cdef ast_decl.IExprDomainOpenRangeList *asExprDomainOpenRangeList(self)
    @staticmethod
    cdef ExprDomainOpenRangeList mk(ast_decl.IExprDomainOpenRangeList *hndl, bool owned)
    cpdef getValues(self)
    cpdef getValue(self, i)
    cpdef void addValue(self, ExprDomainOpenRangeValue i)
    cpdef numValues(self)

cdef class ExprDomainOpenRangeValue(Expr):
    
    cdef ast_decl.IExprDomainOpenRangeValue *asExprDomainOpenRangeValue(self)
    @staticmethod
    cdef ExprDomainOpenRangeValue mk(ast_decl.IExprDomainOpenRangeValue *hndl, bool owned)
    cpdef bool getSingle(self)
    cpdef Expr getLhs(self)
    cpdef Expr getRhs(self)

cdef class ExprHierarchicalId(Expr):
    
    cdef ast_decl.IExprHierarchicalId *asExprHierarchicalId(self)
    @staticmethod
    cdef ExprHierarchicalId mk(ast_decl.IExprHierarchicalId *hndl, bool owned)
    cpdef getElems(self)
    cpdef getElem(self, i)
    cpdef void addElem(self, ExprMemberPathElem i)
    cpdef numElems(self)

cdef class ExprId(Expr):
    
    cdef ast_decl.IExprId *asExprId(self)
    @staticmethod
    cdef ExprId mk(ast_decl.IExprId *hndl, bool owned)
    cpdef str getId(self)
    cpdef void setId(self, str v)
    cpdef bool getIs_escaped(self)
    cpdef Location getLocation(self)

cdef class ExprIn(Expr):
    
    cdef ast_decl.IExprIn *asExprIn(self)
    @staticmethod
    cdef ExprIn mk(ast_decl.IExprIn *hndl, bool owned)
    cpdef Expr getLhs(self)
    cpdef ExprOpenRangeList getRhs(self)
    cpdef Expr getCollection(self)

cdef class ExprListLiteral(Expr):
    
    cdef ast_decl.IExprListLiteral *asExprListLiteral(self)
    @staticmethod
    cdef ExprListLiteral mk(ast_decl.IExprListLiteral *hndl, bool owned)
    cpdef getValueList(self)
    cpdef getValue(self, i)
    cpdef void addValue(self, Expr i)
    cpdef numValue(self)

cdef class ExprMemberPathElem(Expr):
    
    cdef ast_decl.IExprMemberPathElem *asExprMemberPathElem(self)
    @staticmethod
    cdef ExprMemberPathElem mk(ast_decl.IExprMemberPathElem *hndl, bool owned)
    cpdef ExprId getId(self)
    cpdef MethodParameterList getParams(self)
    cpdef getSubscriptList(self)
    cpdef getSubscript(self, i)
    cpdef void addSubscript(self, Expr i)
    cpdef numSubscript(self)
    cpdef int32_t getTarget(self)
    cpdef int32_t getSuper(self)
    cpdef  getString_method_id(self)

cdef class ExprNull(Expr):
    
    cdef ast_decl.IExprNull *asExprNull(self)
    @staticmethod
    cdef ExprNull mk(ast_decl.IExprNull *hndl, bool owned)

cdef class ExprNumber(Expr):
    
    cdef ast_decl.IExprNumber *asExprNumber(self)
    @staticmethod
    cdef ExprNumber mk(ast_decl.IExprNumber *hndl, bool owned)

cdef class ExprOpenRangeList(Expr):
    
    cdef ast_decl.IExprOpenRangeList *asExprOpenRangeList(self)
    @staticmethod
    cdef ExprOpenRangeList mk(ast_decl.IExprOpenRangeList *hndl, bool owned)
    cpdef getValues(self)
    cpdef getValue(self, i)
    cpdef void addValue(self, ExprOpenRangeValue i)
    cpdef numValues(self)

cdef class ExprOpenRangeValue(Expr):
    
    cdef ast_decl.IExprOpenRangeValue *asExprOpenRangeValue(self)
    @staticmethod
    cdef ExprOpenRangeValue mk(ast_decl.IExprOpenRangeValue *hndl, bool owned)
    cpdef Expr getLhs(self)
    cpdef Expr getRhs(self)

cdef class ExprRefPath(Expr):
    
    cdef ast_decl.IExprRefPath *asExprRefPath(self)
    @staticmethod
    cdef ExprRefPath mk(ast_decl.IExprRefPath *hndl, bool owned)
    cpdef SymbolRefPath getTarget(self)

cdef class ExprRefPathElem(Expr):
    
    cdef ast_decl.IExprRefPathElem *asExprRefPathElem(self)
    @staticmethod
    cdef ExprRefPathElem mk(ast_decl.IExprRefPathElem *hndl, bool owned)

cdef class ExprStaticRefPath(Expr):
    
    cdef ast_decl.IExprStaticRefPath *asExprStaticRefPath(self)
    @staticmethod
    cdef ExprStaticRefPath mk(ast_decl.IExprStaticRefPath *hndl, bool owned)
    cpdef bool getIs_global(self)
    cpdef getBaseList(self)
    cpdef getBase(self, i)
    cpdef void addBase(self, TypeIdentifierElem i)
    cpdef numBase(self)
    cpdef ExprMemberPathElem getLeaf(self)

cdef class ExprString(Expr):
    
    cdef ast_decl.IExprString *asExprString(self)
    @staticmethod
    cdef ExprString mk(ast_decl.IExprString *hndl, bool owned)
    cpdef str getValue(self)
    cpdef void setValue(self, str v)
    cpdef bool getIs_raw(self)

cdef class ExprStructLiteral(Expr):
    
    cdef ast_decl.IExprStructLiteral *asExprStructLiteral(self)
    @staticmethod
    cdef ExprStructLiteral mk(ast_decl.IExprStructLiteral *hndl, bool owned)
    cpdef getValues(self)
    cpdef getValue(self, i)
    cpdef void addValue(self, ExprStructLiteralItem i)
    cpdef numValues(self)

cdef class ExprStructLiteralItem(Expr):
    
    cdef ast_decl.IExprStructLiteralItem *asExprStructLiteralItem(self)
    @staticmethod
    cdef ExprStructLiteralItem mk(ast_decl.IExprStructLiteralItem *hndl, bool owned)
    cpdef ExprId getId(self)
    cpdef Expr getValue(self)

cdef class ExprSubscript(Expr):
    
    cdef ast_decl.IExprSubscript *asExprSubscript(self)
    @staticmethod
    cdef ExprSubscript mk(ast_decl.IExprSubscript *hndl, bool owned)
    cpdef Expr getExpr(self)
    cpdef Expr getSubscript(self)

cdef class ExprSubstring(Expr):
    
    cdef ast_decl.IExprSubstring *asExprSubstring(self)
    @staticmethod
    cdef ExprSubstring mk(ast_decl.IExprSubstring *hndl, bool owned)
    cpdef Expr getExpr(self)
    cpdef Expr getStart(self)
    cpdef Expr getEnd(self)

cdef class ExprUnary(Expr):
    
    cdef ast_decl.IExprUnary *asExprUnary(self)
    @staticmethod
    cdef ExprUnary mk(ast_decl.IExprUnary *hndl, bool owned)
    cpdef  getOp(self)
    cpdef Expr getRhs(self)

cdef class ExtendEnum(ScopeChild):
    
    cdef ast_decl.IExtendEnum *asExtendEnum(self)
    @staticmethod
    cdef ExtendEnum mk(ast_decl.IExtendEnum *hndl, bool owned)
    cpdef TypeIdentifier getTarget(self)
    cpdef getItems(self)
    cpdef getItem(self, i)
    cpdef void addItem(self, EnumItem i)
    cpdef numItems(self)

cdef class FunctionDefinition(ScopeChild):
    
    cdef ast_decl.IFunctionDefinition *asFunctionDefinition(self)
    @staticmethod
    cdef FunctionDefinition mk(ast_decl.IFunctionDefinition *hndl, bool owned)
    cpdef Location getEndLocation(self)
    cpdef FunctionPrototype getProto(self)
    cpdef ExecScope getBody(self)
    cpdef  getPlat(self)

cdef class FunctionImport(ScopeChild):
    
    cdef ast_decl.IFunctionImport *asFunctionImport(self)
    @staticmethod
    cdef FunctionImport mk(ast_decl.IFunctionImport *hndl, bool owned)
    cpdef  getPlat(self)
    cpdef str getLang(self)
    cpdef void setLang(self, str v)

cdef class FunctionParamDecl(ScopeChild):
    
    cdef ast_decl.IFunctionParamDecl *asFunctionParamDecl(self)
    @staticmethod
    cdef FunctionParamDecl mk(ast_decl.IFunctionParamDecl *hndl, bool owned)
    cpdef  getKind(self)
    cpdef ExprId getName(self)
    cpdef DataType getType(self)
    cpdef  getDir(self)
    cpdef Expr getDflt(self)
    cpdef bool getIs_varargs(self)

cdef class GenericConstraintDeclValue(ScopeChild):
    
    cdef ast_decl.IGenericConstraintDeclValue *asGenericConstraintDeclValue(self)
    @staticmethod
    cdef GenericConstraintDeclValue mk(ast_decl.IGenericConstraintDeclValue *hndl, bool owned)
    cpdef bool getIs_static(self)
    cpdef bool getIs_return_numeric(self)
    cpdef DataType getReturn_type(self)
    cpdef ExprId getName(self)
    cpdef getParameters(self)
    cpdef getParameter(self, i)
    cpdef void addParameter(self, GenericConstraintParam i)
    cpdef numParameters(self)
    cpdef Expr getExpr(self)

cdef class GenericConstraintParam(ScopeChild):
    
    cdef ast_decl.IGenericConstraintParam *asGenericConstraintParam(self)
    @staticmethod
    cdef GenericConstraintParam mk(ast_decl.IGenericConstraintParam *hndl, bool owned)
    cpdef ExprId getName(self)
    cpdef bool getIs_const(self)
    cpdef bool getIs_numeric(self)
    cpdef DataType getType(self)

cdef class MethodParameterList(Expr):
    
    cdef ast_decl.IMethodParameterList *asMethodParameterList(self)
    @staticmethod
    cdef MethodParameterList mk(ast_decl.IMethodParameterList *hndl, bool owned)
    cpdef getParameters(self)
    cpdef getParameter(self, i)
    cpdef void addParameter(self, Expr i)
    cpdef numParameters(self)

cdef class MonitorActivityActionTraversal(MonitorActivityStmt):
    
    cdef ast_decl.IMonitorActivityActionTraversal *asMonitorActivityActionTraversal(self)
    @staticmethod
    cdef MonitorActivityActionTraversal mk(ast_decl.IMonitorActivityActionTraversal *hndl, bool owned)
    cpdef ExprRefPath getTarget(self)
    cpdef ConstraintStmt getWith_c(self)

cdef class ActionHandleField(NamedScopeChild):
    
    cdef ast_decl.IActionHandleField *asActionHandleField(self)
    @staticmethod
    cdef ActionHandleField mk(ast_decl.IActionHandleField *hndl, bool owned)
    cpdef DataType getType(self)
    cpdef getInitializers(self)
    cpdef getInitializer(self, i)
    cpdef void addInitializer(self, ActionFieldInitializer i)
    cpdef numInitializers(self)

cdef class MonitorActivityConcat(MonitorActivityStmt):
    
    cdef ast_decl.IMonitorActivityConcat *asMonitorActivityConcat(self)
    @staticmethod
    cdef MonitorActivityConcat mk(ast_decl.IMonitorActivityConcat *hndl, bool owned)
    cpdef MonitorActivityStmt getLhs(self)
    cpdef MonitorActivityStmt getRhs(self)

cdef class MonitorActivityEventually(MonitorActivityStmt):
    
    cdef ast_decl.IMonitorActivityEventually *asMonitorActivityEventually(self)
    @staticmethod
    cdef MonitorActivityEventually mk(ast_decl.IMonitorActivityEventually *hndl, bool owned)
    cpdef Expr getCondition(self)
    cpdef MonitorActivityStmt getBody(self)

cdef class MonitorActivityIfElse(MonitorActivityStmt):
    
    cdef ast_decl.IMonitorActivityIfElse *asMonitorActivityIfElse(self)
    @staticmethod
    cdef MonitorActivityIfElse mk(ast_decl.IMonitorActivityIfElse *hndl, bool owned)
    cpdef Expr getCond(self)
    cpdef MonitorActivityStmt getTrue_s(self)
    cpdef MonitorActivityStmt getFalse_s(self)

cdef class ActivityBindStmt(ActivityStmt):
    
    cdef ast_decl.IActivityBindStmt *asActivityBindStmt(self)
    @staticmethod
    cdef ActivityBindStmt mk(ast_decl.IActivityBindStmt *hndl, bool owned)
    cpdef ExprHierarchicalId getLhs(self)
    cpdef getRhs(self)
    cpdef getRh(self, i)
    cpdef void addRh(self, ExprHierarchicalId i)
    cpdef numRhs(self)

cdef class ActivityConstraint(ActivityStmt):
    
    cdef ast_decl.IActivityConstraint *asActivityConstraint(self)
    @staticmethod
    cdef ActivityConstraint mk(ast_decl.IActivityConstraint *hndl, bool owned)
    cpdef ConstraintStmt getConstraint(self)

cdef class MonitorActivityMatch(MonitorActivityStmt):
    
    cdef ast_decl.IMonitorActivityMatch *asMonitorActivityMatch(self)
    @staticmethod
    cdef MonitorActivityMatch mk(ast_decl.IMonitorActivityMatch *hndl, bool owned)
    cpdef Expr getCond(self)
    cpdef getChoices(self)
    cpdef getChoice(self, i)
    cpdef void addChoice(self, MonitorActivityMatchChoice i)
    cpdef numChoices(self)

cdef class MonitorActivityMonitorTraversal(MonitorActivityStmt):
    
    cdef ast_decl.IMonitorActivityMonitorTraversal *asMonitorActivityMonitorTraversal(self)
    @staticmethod
    cdef MonitorActivityMonitorTraversal mk(ast_decl.IMonitorActivityMonitorTraversal *hndl, bool owned)
    cpdef ExprRefPath getTarget(self)
    cpdef ConstraintStmt getWith_c(self)

cdef class MonitorActivityOverlap(MonitorActivityStmt):
    
    cdef ast_decl.IMonitorActivityOverlap *asMonitorActivityOverlap(self)
    @staticmethod
    cdef MonitorActivityOverlap mk(ast_decl.IMonitorActivityOverlap *hndl, bool owned)
    cpdef MonitorActivityStmt getLhs(self)
    cpdef MonitorActivityStmt getRhs(self)

cdef class MonitorActivityRepeatCount(MonitorActivityStmt):
    
    cdef ast_decl.IMonitorActivityRepeatCount *asMonitorActivityRepeatCount(self)
    @staticmethod
    cdef MonitorActivityRepeatCount mk(ast_decl.IMonitorActivityRepeatCount *hndl, bool owned)
    cpdef ExprId getLoop_var(self)
    cpdef Expr getCount(self)
    cpdef ScopeChild getBody(self)

cdef class ActivityJoinSpecBranch(ActivityJoinSpec):
    
    cdef ast_decl.IActivityJoinSpecBranch *asActivityJoinSpecBranch(self)
    @staticmethod
    cdef ActivityJoinSpecBranch mk(ast_decl.IActivityJoinSpecBranch *hndl, bool owned)
    cpdef getBranches(self)
    cpdef getBranche(self, i)
    cpdef void addBranche(self, ExprRefPathContext i)
    cpdef numBranches(self)

cdef class ActivityJoinSpecFirst(ActivityJoinSpec):
    
    cdef ast_decl.IActivityJoinSpecFirst *asActivityJoinSpecFirst(self)
    @staticmethod
    cdef ActivityJoinSpecFirst mk(ast_decl.IActivityJoinSpecFirst *hndl, bool owned)
    cpdef Expr getCount(self)

cdef class ActivityJoinSpecNone(ActivityJoinSpec):
    
    cdef ast_decl.IActivityJoinSpecNone *asActivityJoinSpecNone(self)
    @staticmethod
    cdef ActivityJoinSpecNone mk(ast_decl.IActivityJoinSpecNone *hndl, bool owned)

cdef class ActivityJoinSpecSelect(ActivityJoinSpec):
    
    cdef ast_decl.IActivityJoinSpecSelect *asActivityJoinSpecSelect(self)
    @staticmethod
    cdef ActivityJoinSpecSelect mk(ast_decl.IActivityJoinSpecSelect *hndl, bool owned)
    cpdef Expr getCount(self)

cdef class MonitorActivityRepeatWhile(MonitorActivityStmt):
    
    cdef ast_decl.IMonitorActivityRepeatWhile *asMonitorActivityRepeatWhile(self)
    @staticmethod
    cdef MonitorActivityRepeatWhile mk(ast_decl.IMonitorActivityRepeatWhile *hndl, bool owned)
    cpdef Expr getCond(self)
    cpdef ScopeChild getBody(self)

cdef class ActivityLabeledStmt(ActivityStmt):
    
    cdef ast_decl.IActivityLabeledStmt *asActivityLabeledStmt(self)
    @staticmethod
    cdef ActivityLabeledStmt mk(ast_decl.IActivityLabeledStmt *hndl, bool owned)
    cpdef ExprId getLabel(self)

cdef class MonitorActivitySelect(MonitorActivityStmt):
    
    cdef ast_decl.IMonitorActivitySelect *asMonitorActivitySelect(self)
    @staticmethod
    cdef MonitorActivitySelect mk(ast_decl.IMonitorActivitySelect *hndl, bool owned)
    cpdef ExprId getLabel(self)
    cpdef getBranches(self)
    cpdef getBranche(self, i)
    cpdef void addBranche(self, MonitorActivitySelectBranch i)
    cpdef numBranches(self)

cdef class MonitorConstraint(MonitorActivityStmt):
    
    cdef ast_decl.IMonitorConstraint *asMonitorConstraint(self)
    @staticmethod
    cdef MonitorConstraint mk(ast_decl.IMonitorConstraint *hndl, bool owned)
    cpdef ConstraintStmt getConstraint(self)

cdef class NamedScope(Scope):
    
    cdef ast_decl.INamedScope *asNamedScope(self)
    @staticmethod
    cdef NamedScope mk(ast_decl.INamedScope *hndl, bool owned)
    cpdef ExprId getName(self)

cdef class PackageScope(Scope):
    
    cdef ast_decl.IPackageScope *asPackageScope(self)
    @staticmethod
    cdef PackageScope mk(ast_decl.IPackageScope *hndl, bool owned)
    cpdef getIdList(self)
    cpdef getId(self, i)
    cpdef void addId(self, ExprId i)
    cpdef numId(self)
    cpdef PackageScope getSibling(self)

cdef class ProceduralStmtAssignment(ExecStmt):
    
    cdef ast_decl.IProceduralStmtAssignment *asProceduralStmtAssignment(self)
    @staticmethod
    cdef ProceduralStmtAssignment mk(ast_decl.IProceduralStmtAssignment *hndl, bool owned)
    cpdef Expr getLhs(self)
    cpdef  getOp(self)
    cpdef Expr getRhs(self)

cdef class ProceduralStmtBody(ExecStmt):
    
    cdef ast_decl.IProceduralStmtBody *asProceduralStmtBody(self)
    @staticmethod
    cdef ProceduralStmtBody mk(ast_decl.IProceduralStmtBody *hndl, bool owned)
    cpdef ScopeChild getBody(self)

cdef class ProceduralStmtBreak(ExecStmt):
    
    cdef ast_decl.IProceduralStmtBreak *asProceduralStmtBreak(self)
    @staticmethod
    cdef ProceduralStmtBreak mk(ast_decl.IProceduralStmtBreak *hndl, bool owned)

cdef class ProceduralStmtContinue(ExecStmt):
    
    cdef ast_decl.IProceduralStmtContinue *asProceduralStmtContinue(self)
    @staticmethod
    cdef ProceduralStmtContinue mk(ast_decl.IProceduralStmtContinue *hndl, bool owned)

cdef class ProceduralStmtDataDeclaration(ExecStmt):
    
    cdef ast_decl.IProceduralStmtDataDeclaration *asProceduralStmtDataDeclaration(self)
    @staticmethod
    cdef ProceduralStmtDataDeclaration mk(ast_decl.IProceduralStmtDataDeclaration *hndl, bool owned)
    cpdef ExprId getName(self)
    cpdef DataType getDatatype(self)
    cpdef Expr getInit(self)

cdef class ProceduralStmtExpr(ExecStmt):
    
    cdef ast_decl.IProceduralStmtExpr *asProceduralStmtExpr(self)
    @staticmethod
    cdef ProceduralStmtExpr mk(ast_decl.IProceduralStmtExpr *hndl, bool owned)
    cpdef Expr getExpr(self)

cdef class ProceduralStmtFunctionCall(ExecStmt):
    
    cdef ast_decl.IProceduralStmtFunctionCall *asProceduralStmtFunctionCall(self)
    @staticmethod
    cdef ProceduralStmtFunctionCall mk(ast_decl.IProceduralStmtFunctionCall *hndl, bool owned)
    cpdef ExprRefPathStaticRooted getPrefix(self)
    cpdef getParams(self)
    cpdef getParam(self, i)
    cpdef void addParam(self, Expr i)
    cpdef numParams(self)

cdef class ProceduralStmtIfElse(ExecStmt):
    
    cdef ast_decl.IProceduralStmtIfElse *asProceduralStmtIfElse(self)
    @staticmethod
    cdef ProceduralStmtIfElse mk(ast_decl.IProceduralStmtIfElse *hndl, bool owned)
    cpdef getIf_thenList(self)
    cpdef getIf_then(self, i)
    cpdef void addIf_then(self, ProceduralStmtIfClause i)
    cpdef numIf_then(self)
    cpdef ScopeChild getElse_then(self)

cdef class ProceduralStmtMatch(ExecStmt):
    
    cdef ast_decl.IProceduralStmtMatch *asProceduralStmtMatch(self)
    @staticmethod
    cdef ProceduralStmtMatch mk(ast_decl.IProceduralStmtMatch *hndl, bool owned)
    cpdef Expr getExpr(self)
    cpdef getChoices(self)
    cpdef getChoice(self, i)
    cpdef void addChoice(self, ProceduralStmtMatchChoice i)
    cpdef numChoices(self)

cdef class ProceduralStmtMatchChoice(ExecStmt):
    
    cdef ast_decl.IProceduralStmtMatchChoice *asProceduralStmtMatchChoice(self)
    @staticmethod
    cdef ProceduralStmtMatchChoice mk(ast_decl.IProceduralStmtMatchChoice *hndl, bool owned)
    cpdef bool getIs_default(self)
    cpdef ExprOpenRangeList getCond(self)
    cpdef ScopeChild getBody(self)

cdef class ProceduralStmtRandomize(ExecStmt):
    
    cdef ast_decl.IProceduralStmtRandomize *asProceduralStmtRandomize(self)
    @staticmethod
    cdef ProceduralStmtRandomize mk(ast_decl.IProceduralStmtRandomize *hndl, bool owned)
    cpdef Expr getTarget(self)
    cpdef getConstraints(self)
    cpdef getConstraint(self, i)
    cpdef void addConstraint(self, ConstraintStmt i)
    cpdef numConstraints(self)

cdef class ConstraintScope(ConstraintStmt):
    
    cdef ast_decl.IConstraintScope *asConstraintScope(self)
    @staticmethod
    cdef ConstraintScope mk(ast_decl.IConstraintScope *hndl, bool owned)
    cpdef Location getEndLocation(self)
    cpdef getConstraints(self)
    cpdef getConstraint(self, i)
    cpdef void addConstraint(self, ConstraintStmt i)
    cpdef numConstraints(self)

cdef class ProceduralStmtReturn(ExecStmt):
    
    cdef ast_decl.IProceduralStmtReturn *asProceduralStmtReturn(self)
    @staticmethod
    cdef ProceduralStmtReturn mk(ast_decl.IProceduralStmtReturn *hndl, bool owned)
    cpdef Expr getExpr(self)

cdef class ConstraintStmtDefault(ConstraintStmt):
    
    cdef ast_decl.IConstraintStmtDefault *asConstraintStmtDefault(self)
    @staticmethod
    cdef ConstraintStmtDefault mk(ast_decl.IConstraintStmtDefault *hndl, bool owned)
    cpdef ExprHierarchicalId getHid(self)
    cpdef Expr getExpr(self)

cdef class ConstraintStmtDefaultDisable(ConstraintStmt):
    
    cdef ast_decl.IConstraintStmtDefaultDisable *asConstraintStmtDefaultDisable(self)
    @staticmethod
    cdef ConstraintStmtDefaultDisable mk(ast_decl.IConstraintStmtDefaultDisable *hndl, bool owned)
    cpdef ExprHierarchicalId getHid(self)

cdef class ConstraintStmtExpr(ConstraintStmt):
    
    cdef ast_decl.IConstraintStmtExpr *asConstraintStmtExpr(self)
    @staticmethod
    cdef ConstraintStmtExpr mk(ast_decl.IConstraintStmtExpr *hndl, bool owned)
    cpdef Expr getExpr(self)

cdef class ConstraintStmtField(ConstraintStmt):
    
    cdef ast_decl.IConstraintStmtField *asConstraintStmtField(self)
    @staticmethod
    cdef ConstraintStmtField mk(ast_decl.IConstraintStmtField *hndl, bool owned)
    cpdef ExprId getName(self)
    cpdef DataType getType(self)

cdef class ProceduralStmtYield(ExecStmt):
    
    cdef ast_decl.IProceduralStmtYield *asProceduralStmtYield(self)
    @staticmethod
    cdef ProceduralStmtYield mk(ast_decl.IProceduralStmtYield *hndl, bool owned)

cdef class ConstraintStmtIf(ConstraintStmt):
    
    cdef ast_decl.IConstraintStmtIf *asConstraintStmtIf(self)
    @staticmethod
    cdef ConstraintStmtIf mk(ast_decl.IConstraintStmtIf *hndl, bool owned)
    cpdef Expr getCond(self)
    cpdef ConstraintScope getTrue_c(self)
    cpdef ConstraintScope getFalse_c(self)

cdef class ConstraintStmtUnique(ConstraintStmt):
    
    cdef ast_decl.IConstraintStmtUnique *asConstraintStmtUnique(self)
    @staticmethod
    cdef ConstraintStmtUnique mk(ast_decl.IConstraintStmtUnique *hndl, bool owned)
    cpdef getListList(self)
    cpdef getList(self, i)
    cpdef void addList(self, ExprHierarchicalId i)
    cpdef numList(self)

cdef class DataTypeBool(DataType):
    
    cdef ast_decl.IDataTypeBool *asDataTypeBool(self)
    @staticmethod
    cdef DataTypeBool mk(ast_decl.IDataTypeBool *hndl, bool owned)

cdef class DataTypeChandle(DataType):
    
    cdef ast_decl.IDataTypeChandle *asDataTypeChandle(self)
    @staticmethod
    cdef DataTypeChandle mk(ast_decl.IDataTypeChandle *hndl, bool owned)

cdef class DataTypeEnum(DataType):
    
    cdef ast_decl.IDataTypeEnum *asDataTypeEnum(self)
    @staticmethod
    cdef DataTypeEnum mk(ast_decl.IDataTypeEnum *hndl, bool owned)
    cpdef DataTypeUserDefined getTid(self)
    cpdef ExprOpenRangeList getIn_rangelist(self)

cdef class DataTypeInt(DataType):
    
    cdef ast_decl.IDataTypeInt *asDataTypeInt(self)
    @staticmethod
    cdef DataTypeInt mk(ast_decl.IDataTypeInt *hndl, bool owned)
    cpdef bool getIs_signed(self)
    cpdef Expr getWidth(self)
    cpdef ExprDomainOpenRangeList getIn_range(self)

cdef class DataTypePyObj(DataType):
    
    cdef ast_decl.IDataTypePyObj *asDataTypePyObj(self)
    @staticmethod
    cdef DataTypePyObj mk(ast_decl.IDataTypePyObj *hndl, bool owned)

cdef class DataTypeRef(DataType):
    
    cdef ast_decl.IDataTypeRef *asDataTypeRef(self)
    @staticmethod
    cdef DataTypeRef mk(ast_decl.IDataTypeRef *hndl, bool owned)
    cpdef DataTypeUserDefined getType(self)

cdef class DataTypeString(DataType):
    
    cdef ast_decl.IDataTypeString *asDataTypeString(self)
    @staticmethod
    cdef DataTypeString mk(ast_decl.IDataTypeString *hndl, bool owned)
    cpdef bool getHas_range(self)

cdef class DataTypeUserDefined(DataType):
    
    cdef ast_decl.IDataTypeUserDefined *asDataTypeUserDefined(self)
    @staticmethod
    cdef DataTypeUserDefined mk(ast_decl.IDataTypeUserDefined *hndl, bool owned)
    cpdef bool getIs_global(self)
    cpdef TypeIdentifier getType_id(self)

cdef class EnumDecl(NamedScopeChild):
    
    cdef ast_decl.IEnumDecl *asEnumDecl(self)
    @staticmethod
    cdef EnumDecl mk(ast_decl.IEnumDecl *hndl, bool owned)
    cpdef getItems(self)
    cpdef getItem(self, i)
    cpdef void addItem(self, EnumItem i)
    cpdef numItems(self)

cdef class EnumItem(NamedScopeChild):
    
    cdef ast_decl.IEnumItem *asEnumItem(self)
    @staticmethod
    cdef EnumItem mk(ast_decl.IEnumItem *hndl, bool owned)
    cpdef Expr getValue(self)
    cpdef SymbolEnumScope getUpper(self)

cdef class SymbolChildrenScope(SymbolChild):
    
    cdef ast_decl.ISymbolChildrenScope *asSymbolChildrenScope(self)
    @staticmethod
    cdef SymbolChildrenScope mk(ast_decl.ISymbolChildrenScope *hndl, bool owned)
    cpdef str getName(self)
    cpdef void setName(self, str v)
    cpdef getChildren(self)
    cpdef getChild(self, i)
    cpdef void addChild(self, ScopeChild i)
    cpdef numChildren(self)
    cpdef ScopeChild getTarget(self)

cdef class TemplateCategoryTypeParamDecl(TemplateParamDecl):
    
    cdef ast_decl.ITemplateCategoryTypeParamDecl *asTemplateCategoryTypeParamDecl(self)
    @staticmethod
    cdef TemplateCategoryTypeParamDecl mk(ast_decl.ITemplateCategoryTypeParamDecl *hndl, bool owned)
    cpdef  getCategory(self)
    cpdef TypeIdentifier getRestriction(self)
    cpdef DataType getDflt(self)

cdef class TemplateGenericTypeParamDecl(TemplateParamDecl):
    
    cdef ast_decl.ITemplateGenericTypeParamDecl *asTemplateGenericTypeParamDecl(self)
    @staticmethod
    cdef TemplateGenericTypeParamDecl mk(ast_decl.ITemplateGenericTypeParamDecl *hndl, bool owned)
    cpdef DataType getDflt(self)

cdef class ExprAggrEmpty(ExprAggrLiteral):
    
    cdef ast_decl.IExprAggrEmpty *asExprAggrEmpty(self)
    @staticmethod
    cdef ExprAggrEmpty mk(ast_decl.IExprAggrEmpty *hndl, bool owned)

cdef class ExprAggrList(ExprAggrLiteral):
    
    cdef ast_decl.IExprAggrList *asExprAggrList(self)
    @staticmethod
    cdef ExprAggrList mk(ast_decl.IExprAggrList *hndl, bool owned)
    cpdef getElems(self)
    cpdef getElem(self, i)
    cpdef void addElem(self, Expr i)
    cpdef numElems(self)

cdef class TemplateValueParamDecl(TemplateParamDecl):
    
    cdef ast_decl.ITemplateValueParamDecl *asTemplateValueParamDecl(self)
    @staticmethod
    cdef TemplateValueParamDecl mk(ast_decl.ITemplateValueParamDecl *hndl, bool owned)
    cpdef DataType getType(self)
    cpdef Expr getDflt(self)

cdef class ExprAggrMap(ExprAggrLiteral):
    
    cdef ast_decl.IExprAggrMap *asExprAggrMap(self)
    @staticmethod
    cdef ExprAggrMap mk(ast_decl.IExprAggrMap *hndl, bool owned)
    cpdef getElems(self)
    cpdef getElem(self, i)
    cpdef void addElem(self, ExprAggrMapElem i)
    cpdef numElems(self)

cdef class ExprAggrStruct(ExprAggrLiteral):
    
    cdef ast_decl.IExprAggrStruct *asExprAggrStruct(self)
    @staticmethod
    cdef ExprAggrStruct mk(ast_decl.IExprAggrStruct *hndl, bool owned)
    cpdef getElems(self)
    cpdef getElem(self, i)
    cpdef void addElem(self, ExprAggrStructElem i)
    cpdef numElems(self)

cdef class ExprRefPathContext(ExprRefPath):
    
    cdef ast_decl.IExprRefPathContext *asExprRefPathContext(self)
    @staticmethod
    cdef ExprRefPathContext mk(ast_decl.IExprRefPathContext *hndl, bool owned)
    cpdef bool getIs_super(self)
    cpdef ExprHierarchicalId getHier_id(self)
    cpdef ExprBitSlice getSlice(self)

cdef class ExprRefPathId(ExprRefPath):
    
    cdef ast_decl.IExprRefPathId *asExprRefPathId(self)
    @staticmethod
    cdef ExprRefPathId mk(ast_decl.IExprRefPathId *hndl, bool owned)
    cpdef ExprId getId(self)
    cpdef ExprBitSlice getSlice(self)

cdef class ExprRefPathStatic(ExprRefPath):
    
    cdef ast_decl.IExprRefPathStatic *asExprRefPathStatic(self)
    @staticmethod
    cdef ExprRefPathStatic mk(ast_decl.IExprRefPathStatic *hndl, bool owned)
    cpdef bool getIs_global(self)
    cpdef getBaseList(self)
    cpdef getBase(self, i)
    cpdef void addBase(self, TypeIdentifierElem i)
    cpdef numBase(self)
    cpdef ExprBitSlice getSlice(self)

cdef class ExprRefPathStaticRooted(ExprRefPath):
    
    cdef ast_decl.IExprRefPathStaticRooted *asExprRefPathStaticRooted(self)
    @staticmethod
    cdef ExprRefPathStaticRooted mk(ast_decl.IExprRefPathStaticRooted *hndl, bool owned)
    cpdef ExprRefPathStatic getRoot(self)
    cpdef ExprHierarchicalId getLeaf(self)
    cpdef ExprBitSlice getSlice(self)

cdef class ExprSignedNumber(ExprNumber):
    
    cdef ast_decl.IExprSignedNumber *asExprSignedNumber(self)
    @staticmethod
    cdef ExprSignedNumber mk(ast_decl.IExprSignedNumber *hndl, bool owned)
    cpdef str getImage(self)
    cpdef void setImage(self, str v)
    cpdef int32_t getWidth(self)
    cpdef int64_t getValue(self)

cdef class ExprUnsignedNumber(ExprNumber):
    
    cdef ast_decl.IExprUnsignedNumber *asExprUnsignedNumber(self)
    @staticmethod
    cdef ExprUnsignedNumber mk(ast_decl.IExprUnsignedNumber *hndl, bool owned)
    cpdef str getImage(self)
    cpdef void setImage(self, str v)
    cpdef int32_t getWidth(self)
    cpdef uint64_t getValue(self)

cdef class ExtendType(Scope):
    
    cdef ast_decl.IExtendType *asExtendType(self)
    @staticmethod
    cdef ExtendType mk(ast_decl.IExtendType *hndl, bool owned)
    cpdef  getKind(self)
    cpdef TypeIdentifier getTarget(self)
    cpdef bool symtabHas(self, str i)
    cpdef int32_t symtabAt(self, str i)
    cpdef SymbolImportSpec getImports(self)

cdef class Field(NamedScopeChild):
    
    cdef ast_decl.IField *asField(self)
    @staticmethod
    cdef Field mk(ast_decl.IField *hndl, bool owned)
    cpdef DataType getType(self)
    cpdef  getAttr(self)
    cpdef Expr getInit(self)

cdef class FieldClaim(NamedScopeChild):
    
    cdef ast_decl.IFieldClaim *asFieldClaim(self)
    @staticmethod
    cdef FieldClaim mk(ast_decl.IFieldClaim *hndl, bool owned)
    cpdef DataTypeUserDefined getType(self)
    cpdef bool getIs_lock(self)

cdef class FieldCompRef(NamedScopeChild):
    
    cdef ast_decl.IFieldCompRef *asFieldCompRef(self)
    @staticmethod
    cdef FieldCompRef mk(ast_decl.IFieldCompRef *hndl, bool owned)
    cpdef DataTypeUserDefined getType(self)

cdef class FieldPool(NamedScopeChild):
    
    cdef ast_decl.IFieldPool *asFieldPool(self)
    @staticmethod
    cdef FieldPool mk(ast_decl.IFieldPool *hndl, bool owned)
    cpdef DataTypeUserDefined getType(self)
    cpdef Expr getSize(self)

cdef class FieldRef(NamedScopeChild):
    
    cdef ast_decl.IFieldRef *asFieldRef(self)
    @staticmethod
    cdef FieldRef mk(ast_decl.IFieldRef *hndl, bool owned)
    cpdef DataTypeUserDefined getType(self)
    cpdef bool getIs_input(self)

cdef class FunctionImportProto(FunctionImport):
    
    cdef ast_decl.IFunctionImportProto *asFunctionImportProto(self)
    @staticmethod
    cdef FunctionImportProto mk(ast_decl.IFunctionImportProto *hndl, bool owned)
    cpdef FunctionPrototype getProto(self)

cdef class FunctionImportType(FunctionImport):
    
    cdef ast_decl.IFunctionImportType *asFunctionImportType(self)
    @staticmethod
    cdef FunctionImportType mk(ast_decl.IFunctionImportType *hndl, bool owned)
    cpdef TypeIdentifier getType(self)

cdef class FunctionPrototype(NamedScopeChild):
    
    cdef ast_decl.IFunctionPrototype *asFunctionPrototype(self)
    @staticmethod
    cdef FunctionPrototype mk(ast_decl.IFunctionPrototype *hndl, bool owned)
    cpdef DataType getRtype(self)
    cpdef getParameters(self)
    cpdef getParameter(self, i)
    cpdef void addParameter(self, FunctionParamDecl i)
    cpdef numParameters(self)
    cpdef bool getIs_pure(self)
    cpdef bool getIs_target(self)
    cpdef bool getIs_solve(self)
    cpdef bool getIs_core(self)

cdef class GlobalScope(Scope):
    
    cdef ast_decl.IGlobalScope *asGlobalScope(self)
    @staticmethod
    cdef GlobalScope mk(ast_decl.IGlobalScope *hndl, bool owned)
    cpdef int32_t getFileid(self)
    cpdef str getFilename(self)
    cpdef void setFilename(self, str v)

cdef class ActivityActionHandleTraversal(ActivityLabeledStmt):
    
    cdef ast_decl.IActivityActionHandleTraversal *asActivityActionHandleTraversal(self)
    @staticmethod
    cdef ActivityActionHandleTraversal mk(ast_decl.IActivityActionHandleTraversal *hndl, bool owned)
    cpdef ExprRefPathContext getTarget(self)
    cpdef ConstraintStmt getWith_c(self)
    cpdef getInitializers(self)
    cpdef getInitializer(self, i)
    cpdef void addInitializer(self, ActionFieldInitializer i)
    cpdef numInitializers(self)

cdef class ActivityActionTypeTraversal(ActivityLabeledStmt):
    
    cdef ast_decl.IActivityActionTypeTraversal *asActivityActionTypeTraversal(self)
    @staticmethod
    cdef ActivityActionTypeTraversal mk(ast_decl.IActivityActionTypeTraversal *hndl, bool owned)
    cpdef DataTypeUserDefined getTarget(self)
    cpdef ConstraintStmt getWith_c(self)
    cpdef getInitializers(self)
    cpdef getInitializer(self, i)
    cpdef void addInitializer(self, ActionFieldInitializer i)
    cpdef numInitializers(self)

cdef class ActivityAtomicBlock(ActivityLabeledStmt):
    
    cdef ast_decl.IActivityAtomicBlock *asActivityAtomicBlock(self)
    @staticmethod
    cdef ActivityAtomicBlock mk(ast_decl.IActivityAtomicBlock *hndl, bool owned)
    cpdef ScopeChild getBody(self)

cdef class ActivityForeach(ActivityLabeledStmt):
    
    cdef ast_decl.IActivityForeach *asActivityForeach(self)
    @staticmethod
    cdef ActivityForeach mk(ast_decl.IActivityForeach *hndl, bool owned)
    cpdef ExprId getIt_id(self)
    cpdef ExprId getIdx_id(self)
    cpdef ExprRefPathContext getTarget(self)
    cpdef ScopeChild getBody(self)

cdef class ActivityIfElse(ActivityLabeledStmt):
    
    cdef ast_decl.IActivityIfElse *asActivityIfElse(self)
    @staticmethod
    cdef ActivityIfElse mk(ast_decl.IActivityIfElse *hndl, bool owned)
    cpdef Expr getCond(self)
    cpdef ActivityStmt getTrue_s(self)
    cpdef ActivityStmt getFalse_s(self)

cdef class ActivityMatch(ActivityLabeledStmt):
    
    cdef ast_decl.IActivityMatch *asActivityMatch(self)
    @staticmethod
    cdef ActivityMatch mk(ast_decl.IActivityMatch *hndl, bool owned)
    cpdef Expr getCond(self)
    cpdef getChoices(self)
    cpdef getChoice(self, i)
    cpdef void addChoice(self, ActivityMatchChoice i)
    cpdef numChoices(self)

cdef class ActivityRepeatCount(ActivityLabeledStmt):
    
    cdef ast_decl.IActivityRepeatCount *asActivityRepeatCount(self)
    @staticmethod
    cdef ActivityRepeatCount mk(ast_decl.IActivityRepeatCount *hndl, bool owned)
    cpdef ExprId getLoop_var(self)
    cpdef Expr getCount(self)
    cpdef ScopeChild getBody(self)

cdef class ActivityRepeatWhile(ActivityLabeledStmt):
    
    cdef ast_decl.IActivityRepeatWhile *asActivityRepeatWhile(self)
    @staticmethod
    cdef ActivityRepeatWhile mk(ast_decl.IActivityRepeatWhile *hndl, bool owned)
    cpdef Expr getCond(self)
    cpdef ScopeChild getBody(self)

cdef class ActivityReplicate(ActivityLabeledStmt):
    
    cdef ast_decl.IActivityReplicate *asActivityReplicate(self)
    @staticmethod
    cdef ActivityReplicate mk(ast_decl.IActivityReplicate *hndl, bool owned)
    cpdef ExprId getIdx_id(self)
    cpdef ExprId getIt_label(self)
    cpdef ScopeChild getBody(self)

cdef class ActivitySelect(ActivityLabeledStmt):
    
    cdef ast_decl.IActivitySelect *asActivitySelect(self)
    @staticmethod
    cdef ActivitySelect mk(ast_decl.IActivitySelect *hndl, bool owned)
    cpdef getBranches(self)
    cpdef getBranche(self, i)
    cpdef void addBranche(self, ActivitySelectBranch i)
    cpdef numBranches(self)

cdef class ActivitySuper(ActivityLabeledStmt):
    
    cdef ast_decl.IActivitySuper *asActivitySuper(self)
    @staticmethod
    cdef ActivitySuper mk(ast_decl.IActivitySuper *hndl, bool owned)

cdef class ConstraintBlock(ConstraintScope):
    
    cdef ast_decl.IConstraintBlock *asConstraintBlock(self)
    @staticmethod
    cdef ConstraintBlock mk(ast_decl.IConstraintBlock *hndl, bool owned)
    cpdef str getName(self)
    cpdef void setName(self, str v)
    cpdef bool getIs_dynamic(self)

cdef class ProceduralStmtRepeatWhile(ProceduralStmtBody):
    
    cdef ast_decl.IProceduralStmtRepeatWhile *asProceduralStmtRepeatWhile(self)
    @staticmethod
    cdef ProceduralStmtRepeatWhile mk(ast_decl.IProceduralStmtRepeatWhile *hndl, bool owned)
    cpdef Expr getExpr(self)

cdef class ProceduralStmtWhile(ProceduralStmtBody):
    
    cdef ast_decl.IProceduralStmtWhile *asProceduralStmtWhile(self)
    @staticmethod
    cdef ProceduralStmtWhile mk(ast_decl.IProceduralStmtWhile *hndl, bool owned)
    cpdef Expr getExpr(self)

cdef class ConstraintStmtForall(ConstraintScope):
    
    cdef ast_decl.IConstraintStmtForall *asConstraintStmtForall(self)
    @staticmethod
    cdef ConstraintStmtForall mk(ast_decl.IConstraintStmtForall *hndl, bool owned)
    cpdef ExprId getIterator_id(self)
    cpdef DataTypeUserDefined getType_id(self)
    cpdef ExprRefPath getRef_path(self)
    cpdef ConstraintSymbolScope getSymtab(self)

cdef class ConstraintStmtForeach(ConstraintScope):
    
    cdef ast_decl.IConstraintStmtForeach *asConstraintStmtForeach(self)
    @staticmethod
    cdef ConstraintStmtForeach mk(ast_decl.IConstraintStmtForeach *hndl, bool owned)
    cpdef ConstraintStmtField getIt(self)
    cpdef ConstraintStmtField getIdx(self)
    cpdef Expr getExpr(self)
    cpdef ConstraintSymbolScope getSymtab(self)

cdef class ConstraintStmtImplication(ConstraintScope):
    
    cdef ast_decl.IConstraintStmtImplication *asConstraintStmtImplication(self)
    @staticmethod
    cdef ConstraintStmtImplication mk(ast_decl.IConstraintStmtImplication *hndl, bool owned)
    cpdef Expr getCond(self)

cdef class SymbolScope(SymbolChildrenScope):
    
    cdef ast_decl.ISymbolScope *asSymbolScope(self)
    @staticmethod
    cdef SymbolScope mk(ast_decl.ISymbolScope *hndl, bool owned)
    cpdef bool symtabHas(self, str i)
    cpdef int32_t symtabAt(self, str i)
    cpdef SymbolImportSpec getImports(self)
    cpdef bool getSynthetic(self)
    cpdef bool getOpaque(self)

cdef class TypeScope(NamedScope):
    
    cdef ast_decl.ITypeScope *asTypeScope(self)
    @staticmethod
    cdef TypeScope mk(ast_decl.ITypeScope *hndl, bool owned)
    cpdef TypeIdentifier getSuper_t(self)
    cpdef TemplateParamDeclList getParams(self)
    cpdef bool getOpaque(self)

cdef class ExprRefPathStaticFunc(ExprRefPathStatic):
    
    cdef ast_decl.IExprRefPathStaticFunc *asExprRefPathStaticFunc(self)
    @staticmethod
    cdef ExprRefPathStaticFunc mk(ast_decl.IExprRefPathStaticFunc *hndl, bool owned)
    cpdef MethodParameterList getParams(self)

cdef class ExprRefPathSuper(ExprRefPathContext):
    
    cdef ast_decl.IExprRefPathSuper *asExprRefPathSuper(self)
    @staticmethod
    cdef ExprRefPathSuper mk(ast_decl.IExprRefPathSuper *hndl, bool owned)

cdef class Action(TypeScope):
    
    cdef ast_decl.IAction *asAction(self)
    @staticmethod
    cdef Action mk(ast_decl.IAction *hndl, bool owned)
    cpdef bool getIs_abstract(self)
    cpdef bool getIs_override(self)

cdef class Monitor(TypeScope):
    
    cdef ast_decl.IMonitor *asMonitor(self)
    @staticmethod
    cdef Monitor mk(ast_decl.IMonitor *hndl, bool owned)
    cpdef bool getIs_abstract(self)

cdef class MonitorActivityDecl(SymbolScope):
    
    cdef ast_decl.IMonitorActivityDecl *asMonitorActivityDecl(self)
    @staticmethod
    cdef MonitorActivityDecl mk(ast_decl.IMonitorActivityDecl *hndl, bool owned)

cdef class ActivityDecl(SymbolScope):
    
    cdef ast_decl.IActivityDecl *asActivityDecl(self)
    @staticmethod
    cdef ActivityDecl mk(ast_decl.IActivityDecl *hndl, bool owned)

cdef class MonitorActivitySchedule(SymbolScope):
    
    cdef ast_decl.IMonitorActivitySchedule *asMonitorActivitySchedule(self)
    @staticmethod
    cdef MonitorActivitySchedule mk(ast_decl.IMonitorActivitySchedule *hndl, bool owned)
    cpdef ExprId getLabel(self)

cdef class MonitorActivitySequence(SymbolScope):
    
    cdef ast_decl.IMonitorActivitySequence *asMonitorActivitySequence(self)
    @staticmethod
    cdef MonitorActivitySequence mk(ast_decl.IMonitorActivitySequence *hndl, bool owned)
    cpdef ExprId getLabel(self)

cdef class ActivityLabeledScope(SymbolScope):
    
    cdef ast_decl.IActivityLabeledScope *asActivityLabeledScope(self)
    @staticmethod
    cdef ActivityLabeledScope mk(ast_decl.IActivityLabeledScope *hndl, bool owned)
    cpdef ExprId getLabel(self)

cdef class AnnotationDecl(TypeScope):
    
    cdef ast_decl.IAnnotationDecl *asAnnotationDecl(self)
    @staticmethod
    cdef AnnotationDecl mk(ast_decl.IAnnotationDecl *hndl, bool owned)

cdef class Component(TypeScope):
    
    cdef ast_decl.IComponent *asComponent(self)
    @staticmethod
    cdef Component mk(ast_decl.IComponent *hndl, bool owned)

cdef class ProceduralStmtSymbolBodyScope(SymbolScope):
    
    cdef ast_decl.IProceduralStmtSymbolBodyScope *asProceduralStmtSymbolBodyScope(self)
    @staticmethod
    cdef ProceduralStmtSymbolBodyScope mk(ast_decl.IProceduralStmtSymbolBodyScope *hndl, bool owned)
    cpdef ScopeChild getBody(self)

cdef class RootSymbolScope(SymbolScope):
    
    cdef ast_decl.IRootSymbolScope *asRootSymbolScope(self)
    @staticmethod
    cdef RootSymbolScope mk(ast_decl.IRootSymbolScope *hndl, bool owned)
    cpdef getUnits(self)
    cpdef getUnit(self, i)
    cpdef void addUnit(self, GlobalScope i)
    cpdef numUnits(self)
    cpdef bool filenamesHas(self, int32_t i)
    cpdef str filenamesAt(self, int32_t i)
    cpdef bool id2idxHas(self, int32_t i)
    cpdef int32_t id2idxAt(self, int32_t i)

cdef class ConstraintSymbolScope(SymbolScope):
    
    cdef ast_decl.IConstraintSymbolScope *asConstraintSymbolScope(self)
    @staticmethod
    cdef ConstraintSymbolScope mk(ast_decl.IConstraintSymbolScope *hndl, bool owned)
    cpdef ConstraintStmt getConstraint(self)

cdef class Struct(TypeScope):
    
    cdef ast_decl.IStruct *asStruct(self)
    @staticmethod
    cdef Struct mk(ast_decl.IStruct *hndl, bool owned)
    cpdef  getKind(self)

cdef class SymbolEnumScope(SymbolScope):
    
    cdef ast_decl.ISymbolEnumScope *asSymbolEnumScope(self)
    @staticmethod
    cdef SymbolEnumScope mk(ast_decl.ISymbolEnumScope *hndl, bool owned)

cdef class SymbolExtendScope(SymbolScope):
    
    cdef ast_decl.ISymbolExtendScope *asSymbolExtendScope(self)
    @staticmethod
    cdef SymbolExtendScope mk(ast_decl.ISymbolExtendScope *hndl, bool owned)

cdef class SymbolFunctionScope(SymbolScope):
    
    cdef ast_decl.ISymbolFunctionScope *asSymbolFunctionScope(self)
    @staticmethod
    cdef SymbolFunctionScope mk(ast_decl.ISymbolFunctionScope *hndl, bool owned)
    cpdef getPrototypes(self)
    cpdef getPrototype(self, i)
    cpdef void addPrototype(self, FunctionPrototype i)
    cpdef numPrototypes(self)
    cpdef getImport_specs(self)
    cpdef getImport_spec(self, i)
    cpdef void addImport_spec(self, FunctionImport i)
    cpdef numImport_specs(self)
    cpdef FunctionDefinition getDefinition(self)
    cpdef SymbolScope getPlist(self)
    cpdef ExecScope getBody(self)

cdef class SymbolTypeScope(SymbolScope):
    
    cdef ast_decl.ISymbolTypeScope *asSymbolTypeScope(self)
    @staticmethod
    cdef SymbolTypeScope mk(ast_decl.ISymbolTypeScope *hndl, bool owned)
    cpdef SymbolScope getPlist(self)
    cpdef getSpec_types(self)
    cpdef getSpec_type(self, i)
    cpdef void addSpec_type(self, SymbolTypeScope i)
    cpdef numSpec_types(self)

cdef class ExecScope(SymbolScope):
    
    cdef ast_decl.IExecScope *asExecScope(self)
    @staticmethod
    cdef ExecScope mk(ast_decl.IExecScope *hndl, bool owned)
    cpdef Location getEndLocation(self)

cdef class GenericConstraintDeclBool(ConstraintBlock):
    
    cdef ast_decl.IGenericConstraintDeclBool *asGenericConstraintDeclBool(self)
    @staticmethod
    cdef GenericConstraintDeclBool mk(ast_decl.IGenericConstraintDeclBool *hndl, bool owned)
    cpdef bool getIs_static(self)
    cpdef getParameters(self)
    cpdef getParameter(self, i)
    cpdef void addParameter(self, GenericConstraintParam i)
    cpdef numParameters(self)

cdef class ProceduralStmtRepeat(ProceduralStmtSymbolBodyScope):
    
    cdef ast_decl.IProceduralStmtRepeat *asProceduralStmtRepeat(self)
    @staticmethod
    cdef ProceduralStmtRepeat mk(ast_decl.IProceduralStmtRepeat *hndl, bool owned)
    cpdef ExprId getIt_id(self)
    cpdef Expr getCount(self)

cdef class ActivitySequence(ActivityLabeledScope):
    
    cdef ast_decl.IActivitySequence *asActivitySequence(self)
    @staticmethod
    cdef ActivitySequence mk(ast_decl.IActivitySequence *hndl, bool owned)

cdef class ActivityParallel(ActivityLabeledScope):
    
    cdef ast_decl.IActivityParallel *asActivityParallel(self)
    @staticmethod
    cdef ActivityParallel mk(ast_decl.IActivityParallel *hndl, bool owned)
    cpdef ActivityJoinSpec getJoin_spec(self)

cdef class ActivitySchedule(ActivityLabeledScope):
    
    cdef ast_decl.IActivitySchedule *asActivitySchedule(self)
    @staticmethod
    cdef ActivitySchedule mk(ast_decl.IActivitySchedule *hndl, bool owned)
    cpdef ActivityJoinSpec getJoin_spec(self)

cdef class ProceduralStmtForeach(ProceduralStmtSymbolBodyScope):
    
    cdef ast_decl.IProceduralStmtForeach *asProceduralStmtForeach(self)
    @staticmethod
    cdef ProceduralStmtForeach mk(ast_decl.IProceduralStmtForeach *hndl, bool owned)
    cpdef ExprRefPath getPath(self)
    cpdef ExprId getIt_id(self)
    cpdef ExprId getIdx_id(self)

cdef class ExecBlock(ExecScope):
    
    cdef ast_decl.IExecBlock *asExecBlock(self)
    @staticmethod
    cdef ExecBlock mk(ast_decl.IExecBlock *hndl, bool owned)
    cpdef  getKind(self)

cdef class VisitorBase(object):
    cdef ast_decl.PyBaseVisitor *_hndl
    cdef bool                  _owned
    cpdef void visitTemplateParamDeclList(self, TemplateParamDeclList i)
    cpdef void visitAssocData(self, AssocData i)
    cpdef void visitExecTargetTemplateParam(self, ExecTargetTemplateParam i)
    cpdef void visitExpr(self, Expr i)
    cpdef void visitTemplateParamValue(self, TemplateParamValue i)
    cpdef void visitTemplateParamValueList(self, TemplateParamValueList i)
    cpdef void visitMonitorActivityMatchChoice(self, MonitorActivityMatchChoice i)
    cpdef void visitExprAggrMapElem(self, ExprAggrMapElem i)
    cpdef void visitExprAggrStructElem(self, ExprAggrStructElem i)
    cpdef void visitRefExpr(self, RefExpr i)
    cpdef void visitMonitorActivitySelectBranch(self, MonitorActivitySelectBranch i)
    cpdef void visitScopeChild(self, ScopeChild i)
    cpdef void visitActivityMatchChoice(self, ActivityMatchChoice i)
    cpdef void visitSymbolImportSpec(self, SymbolImportSpec i)
    cpdef void visitSymbolRefPath(self, SymbolRefPath i)
    cpdef void visitActivitySelectBranch(self, ActivitySelectBranch i)
    cpdef void visitActionFieldInitializer(self, ActionFieldInitializer i)
    cpdef void visitActivityJoinSpec(self, ActivityJoinSpec i)
    cpdef void visitMonitorActivityStmt(self, MonitorActivityStmt i)
    cpdef void visitNamedScopeChild(self, NamedScopeChild i)
    cpdef void visitPackageImportStmt(self, PackageImportStmt i)
    cpdef void visitActivitySchedulingConstraint(self, ActivitySchedulingConstraint i)
    cpdef void visitActivityStmt(self, ActivityStmt i)
    cpdef void visitProceduralStmtIfClause(self, ProceduralStmtIfClause i)
    cpdef void visitAnnotation(self, Annotation i)
    cpdef void visitAnnotationParam(self, AnnotationParam i)
    cpdef void visitConstraintStmt(self, ConstraintStmt i)
    cpdef void visitPyImportFromStmt(self, PyImportFromStmt i)
    cpdef void visitPyImportStmt(self, PyImportStmt i)
    cpdef void visitRefExprScopeIndex(self, RefExprScopeIndex i)
    cpdef void visitRefExprTypeScopeContext(self, RefExprTypeScopeContext i)
    cpdef void visitRefExprTypeScopeGlobal(self, RefExprTypeScopeGlobal i)
    cpdef void visitScope(self, Scope i)
    cpdef void visitCoverStmtInline(self, CoverStmtInline i)
    cpdef void visitCoverStmtReference(self, CoverStmtReference i)
    cpdef void visitDataType(self, DataType i)
    cpdef void visitScopeChildRef(self, ScopeChildRef i)
    cpdef void visitSymbolChild(self, SymbolChild i)
    cpdef void visitSymbolScopeRef(self, SymbolScopeRef i)
    cpdef void visitExecStmt(self, ExecStmt i)
    cpdef void visitExecTargetTemplateBlock(self, ExecTargetTemplateBlock i)
    cpdef void visitTemplateParamDecl(self, TemplateParamDecl i)
    cpdef void visitExportFunction(self, ExportFunction i)
    cpdef void visitTemplateParamExprValue(self, TemplateParamExprValue i)
    cpdef void visitTemplateParamTypeValue(self, TemplateParamTypeValue i)
    cpdef void visitExprAggrLiteral(self, ExprAggrLiteral i)
    cpdef void visitTypeIdentifier(self, TypeIdentifier i)
    cpdef void visitTypeIdentifierElem(self, TypeIdentifierElem i)
    cpdef void visitTypedefDeclaration(self, TypedefDeclaration i)
    cpdef void visitExprBin(self, ExprBin i)
    cpdef void visitExprBitSlice(self, ExprBitSlice i)
    cpdef void visitExprBool(self, ExprBool i)
    cpdef void visitExprCast(self, ExprCast i)
    cpdef void visitExprCompileHas(self, ExprCompileHas i)
    cpdef void visitExprCond(self, ExprCond i)
    cpdef void visitExprDomainOpenRangeList(self, ExprDomainOpenRangeList i)
    cpdef void visitExprDomainOpenRangeValue(self, ExprDomainOpenRangeValue i)
    cpdef void visitExprHierarchicalId(self, ExprHierarchicalId i)
    cpdef void visitExprId(self, ExprId i)
    cpdef void visitExprIn(self, ExprIn i)
    cpdef void visitExprListLiteral(self, ExprListLiteral i)
    cpdef void visitExprMemberPathElem(self, ExprMemberPathElem i)
    cpdef void visitExprNull(self, ExprNull i)
    cpdef void visitExprNumber(self, ExprNumber i)
    cpdef void visitExprOpenRangeList(self, ExprOpenRangeList i)
    cpdef void visitExprOpenRangeValue(self, ExprOpenRangeValue i)
    cpdef void visitExprRefPath(self, ExprRefPath i)
    cpdef void visitExprRefPathElem(self, ExprRefPathElem i)
    cpdef void visitExprStaticRefPath(self, ExprStaticRefPath i)
    cpdef void visitExprString(self, ExprString i)
    cpdef void visitExprStructLiteral(self, ExprStructLiteral i)
    cpdef void visitExprStructLiteralItem(self, ExprStructLiteralItem i)
    cpdef void visitExprSubscript(self, ExprSubscript i)
    cpdef void visitExprSubstring(self, ExprSubstring i)
    cpdef void visitExprUnary(self, ExprUnary i)
    cpdef void visitExtendEnum(self, ExtendEnum i)
    cpdef void visitFunctionDefinition(self, FunctionDefinition i)
    cpdef void visitFunctionImport(self, FunctionImport i)
    cpdef void visitFunctionParamDecl(self, FunctionParamDecl i)
    cpdef void visitGenericConstraintDeclValue(self, GenericConstraintDeclValue i)
    cpdef void visitGenericConstraintParam(self, GenericConstraintParam i)
    cpdef void visitMethodParameterList(self, MethodParameterList i)
    cpdef void visitMonitorActivityActionTraversal(self, MonitorActivityActionTraversal i)
    cpdef void visitActionHandleField(self, ActionHandleField i)
    cpdef void visitMonitorActivityConcat(self, MonitorActivityConcat i)
    cpdef void visitMonitorActivityEventually(self, MonitorActivityEventually i)
    cpdef void visitMonitorActivityIfElse(self, MonitorActivityIfElse i)
    cpdef void visitActivityBindStmt(self, ActivityBindStmt i)
    cpdef void visitActivityConstraint(self, ActivityConstraint i)
    cpdef void visitMonitorActivityMatch(self, MonitorActivityMatch i)
    cpdef void visitMonitorActivityMonitorTraversal(self, MonitorActivityMonitorTraversal i)
    cpdef void visitMonitorActivityOverlap(self, MonitorActivityOverlap i)
    cpdef void visitMonitorActivityRepeatCount(self, MonitorActivityRepeatCount i)
    cpdef void visitActivityJoinSpecBranch(self, ActivityJoinSpecBranch i)
    cpdef void visitActivityJoinSpecFirst(self, ActivityJoinSpecFirst i)
    cpdef void visitActivityJoinSpecNone(self, ActivityJoinSpecNone i)
    cpdef void visitActivityJoinSpecSelect(self, ActivityJoinSpecSelect i)
    cpdef void visitMonitorActivityRepeatWhile(self, MonitorActivityRepeatWhile i)
    cpdef void visitActivityLabeledStmt(self, ActivityLabeledStmt i)
    cpdef void visitMonitorActivitySelect(self, MonitorActivitySelect i)
    cpdef void visitMonitorConstraint(self, MonitorConstraint i)
    cpdef void visitNamedScope(self, NamedScope i)
    cpdef void visitPackageScope(self, PackageScope i)
    cpdef void visitProceduralStmtAssignment(self, ProceduralStmtAssignment i)
    cpdef void visitProceduralStmtBody(self, ProceduralStmtBody i)
    cpdef void visitProceduralStmtBreak(self, ProceduralStmtBreak i)
    cpdef void visitProceduralStmtContinue(self, ProceduralStmtContinue i)
    cpdef void visitProceduralStmtDataDeclaration(self, ProceduralStmtDataDeclaration i)
    cpdef void visitProceduralStmtExpr(self, ProceduralStmtExpr i)
    cpdef void visitProceduralStmtFunctionCall(self, ProceduralStmtFunctionCall i)
    cpdef void visitProceduralStmtIfElse(self, ProceduralStmtIfElse i)
    cpdef void visitProceduralStmtMatch(self, ProceduralStmtMatch i)
    cpdef void visitProceduralStmtMatchChoice(self, ProceduralStmtMatchChoice i)
    cpdef void visitProceduralStmtRandomize(self, ProceduralStmtRandomize i)
    cpdef void visitConstraintScope(self, ConstraintScope i)
    cpdef void visitProceduralStmtReturn(self, ProceduralStmtReturn i)
    cpdef void visitConstraintStmtDefault(self, ConstraintStmtDefault i)
    cpdef void visitConstraintStmtDefaultDisable(self, ConstraintStmtDefaultDisable i)
    cpdef void visitConstraintStmtExpr(self, ConstraintStmtExpr i)
    cpdef void visitConstraintStmtField(self, ConstraintStmtField i)
    cpdef void visitProceduralStmtYield(self, ProceduralStmtYield i)
    cpdef void visitConstraintStmtIf(self, ConstraintStmtIf i)
    cpdef void visitConstraintStmtUnique(self, ConstraintStmtUnique i)
    cpdef void visitDataTypeBool(self, DataTypeBool i)
    cpdef void visitDataTypeChandle(self, DataTypeChandle i)
    cpdef void visitDataTypeEnum(self, DataTypeEnum i)
    cpdef void visitDataTypeInt(self, DataTypeInt i)
    cpdef void visitDataTypePyObj(self, DataTypePyObj i)
    cpdef void visitDataTypeRef(self, DataTypeRef i)
    cpdef void visitDataTypeString(self, DataTypeString i)
    cpdef void visitDataTypeUserDefined(self, DataTypeUserDefined i)
    cpdef void visitEnumDecl(self, EnumDecl i)
    cpdef void visitEnumItem(self, EnumItem i)
    cpdef void visitSymbolChildrenScope(self, SymbolChildrenScope i)
    cpdef void visitTemplateCategoryTypeParamDecl(self, TemplateCategoryTypeParamDecl i)
    cpdef void visitTemplateGenericTypeParamDecl(self, TemplateGenericTypeParamDecl i)
    cpdef void visitExprAggrEmpty(self, ExprAggrEmpty i)
    cpdef void visitExprAggrList(self, ExprAggrList i)
    cpdef void visitTemplateValueParamDecl(self, TemplateValueParamDecl i)
    cpdef void visitExprAggrMap(self, ExprAggrMap i)
    cpdef void visitExprAggrStruct(self, ExprAggrStruct i)
    cpdef void visitExprRefPathContext(self, ExprRefPathContext i)
    cpdef void visitExprRefPathId(self, ExprRefPathId i)
    cpdef void visitExprRefPathStatic(self, ExprRefPathStatic i)
    cpdef void visitExprRefPathStaticRooted(self, ExprRefPathStaticRooted i)
    cpdef void visitExprSignedNumber(self, ExprSignedNumber i)
    cpdef void visitExprUnsignedNumber(self, ExprUnsignedNumber i)
    cpdef void visitExtendType(self, ExtendType i)
    cpdef void visitField(self, Field i)
    cpdef void visitFieldClaim(self, FieldClaim i)
    cpdef void visitFieldCompRef(self, FieldCompRef i)
    cpdef void visitFieldPool(self, FieldPool i)
    cpdef void visitFieldRef(self, FieldRef i)
    cpdef void visitFunctionImportProto(self, FunctionImportProto i)
    cpdef void visitFunctionImportType(self, FunctionImportType i)
    cpdef void visitFunctionPrototype(self, FunctionPrototype i)
    cpdef void visitGlobalScope(self, GlobalScope i)
    cpdef void visitActivityActionHandleTraversal(self, ActivityActionHandleTraversal i)
    cpdef void visitActivityActionTypeTraversal(self, ActivityActionTypeTraversal i)
    cpdef void visitActivityAtomicBlock(self, ActivityAtomicBlock i)
    cpdef void visitActivityForeach(self, ActivityForeach i)
    cpdef void visitActivityIfElse(self, ActivityIfElse i)
    cpdef void visitActivityMatch(self, ActivityMatch i)
    cpdef void visitActivityRepeatCount(self, ActivityRepeatCount i)
    cpdef void visitActivityRepeatWhile(self, ActivityRepeatWhile i)
    cpdef void visitActivityReplicate(self, ActivityReplicate i)
    cpdef void visitActivitySelect(self, ActivitySelect i)
    cpdef void visitActivitySuper(self, ActivitySuper i)
    cpdef void visitConstraintBlock(self, ConstraintBlock i)
    cpdef void visitProceduralStmtRepeatWhile(self, ProceduralStmtRepeatWhile i)
    cpdef void visitProceduralStmtWhile(self, ProceduralStmtWhile i)
    cpdef void visitConstraintStmtForall(self, ConstraintStmtForall i)
    cpdef void visitConstraintStmtForeach(self, ConstraintStmtForeach i)
    cpdef void visitConstraintStmtImplication(self, ConstraintStmtImplication i)
    cpdef void visitSymbolScope(self, SymbolScope i)
    cpdef void visitTypeScope(self, TypeScope i)
    cpdef void visitExprRefPathStaticFunc(self, ExprRefPathStaticFunc i)
    cpdef void visitExprRefPathSuper(self, ExprRefPathSuper i)
    cpdef void visitAction(self, Action i)
    cpdef void visitMonitor(self, Monitor i)
    cpdef void visitMonitorActivityDecl(self, MonitorActivityDecl i)
    cpdef void visitActivityDecl(self, ActivityDecl i)
    cpdef void visitMonitorActivitySchedule(self, MonitorActivitySchedule i)
    cpdef void visitMonitorActivitySequence(self, MonitorActivitySequence i)
    cpdef void visitActivityLabeledScope(self, ActivityLabeledScope i)
    cpdef void visitAnnotationDecl(self, AnnotationDecl i)
    cpdef void visitComponent(self, Component i)
    cpdef void visitProceduralStmtSymbolBodyScope(self, ProceduralStmtSymbolBodyScope i)
    cpdef void visitRootSymbolScope(self, RootSymbolScope i)
    cpdef void visitConstraintSymbolScope(self, ConstraintSymbolScope i)
    cpdef void visitStruct(self, Struct i)
    cpdef void visitSymbolEnumScope(self, SymbolEnumScope i)
    cpdef void visitSymbolExtendScope(self, SymbolExtendScope i)
    cpdef void visitSymbolFunctionScope(self, SymbolFunctionScope i)
    cpdef void visitSymbolTypeScope(self, SymbolTypeScope i)
    cpdef void visitExecScope(self, ExecScope i)
    cpdef void visitGenericConstraintDeclBool(self, GenericConstraintDeclBool i)
    cpdef void visitProceduralStmtRepeat(self, ProceduralStmtRepeat i)
    cpdef void visitActivitySequence(self, ActivitySequence i)
    cpdef void visitActivityParallel(self, ActivityParallel i)
    cpdef void visitActivitySchedule(self, ActivitySchedule i)
    cpdef void visitProceduralStmtForeach(self, ProceduralStmtForeach i)
    cpdef void visitExecBlock(self, ExecBlock i)
cdef class ObjFactory(VisitorBase):
    cdef bool _obj_owned
    cdef object _obj
    cpdef void visitTemplateParamDeclList(self, TemplateParamDeclList i)
    cpdef void visitAssocData(self, AssocData i)
    cpdef void visitExecTargetTemplateParam(self, ExecTargetTemplateParam i)
    cpdef void visitExpr(self, Expr i)
    cpdef void visitTemplateParamValue(self, TemplateParamValue i)
    cpdef void visitTemplateParamValueList(self, TemplateParamValueList i)
    cpdef void visitMonitorActivityMatchChoice(self, MonitorActivityMatchChoice i)
    cpdef void visitExprAggrMapElem(self, ExprAggrMapElem i)
    cpdef void visitExprAggrStructElem(self, ExprAggrStructElem i)
    cpdef void visitRefExpr(self, RefExpr i)
    cpdef void visitMonitorActivitySelectBranch(self, MonitorActivitySelectBranch i)
    cpdef void visitScopeChild(self, ScopeChild i)
    cpdef void visitActivityMatchChoice(self, ActivityMatchChoice i)
    cpdef void visitSymbolImportSpec(self, SymbolImportSpec i)
    cpdef void visitSymbolRefPath(self, SymbolRefPath i)
    cpdef void visitActivitySelectBranch(self, ActivitySelectBranch i)
    cpdef void visitActionFieldInitializer(self, ActionFieldInitializer i)
    cpdef void visitActivityJoinSpec(self, ActivityJoinSpec i)
    cpdef void visitMonitorActivityStmt(self, MonitorActivityStmt i)
    cpdef void visitNamedScopeChild(self, NamedScopeChild i)
    cpdef void visitPackageImportStmt(self, PackageImportStmt i)
    cpdef void visitActivitySchedulingConstraint(self, ActivitySchedulingConstraint i)
    cpdef void visitActivityStmt(self, ActivityStmt i)
    cpdef void visitProceduralStmtIfClause(self, ProceduralStmtIfClause i)
    cpdef void visitAnnotation(self, Annotation i)
    cpdef void visitAnnotationParam(self, AnnotationParam i)
    cpdef void visitConstraintStmt(self, ConstraintStmt i)
    cpdef void visitPyImportFromStmt(self, PyImportFromStmt i)
    cpdef void visitPyImportStmt(self, PyImportStmt i)
    cpdef void visitRefExprScopeIndex(self, RefExprScopeIndex i)
    cpdef void visitRefExprTypeScopeContext(self, RefExprTypeScopeContext i)
    cpdef void visitRefExprTypeScopeGlobal(self, RefExprTypeScopeGlobal i)
    cpdef void visitScope(self, Scope i)
    cpdef void visitCoverStmtInline(self, CoverStmtInline i)
    cpdef void visitCoverStmtReference(self, CoverStmtReference i)
    cpdef void visitDataType(self, DataType i)
    cpdef void visitScopeChildRef(self, ScopeChildRef i)
    cpdef void visitSymbolChild(self, SymbolChild i)
    cpdef void visitSymbolScopeRef(self, SymbolScopeRef i)
    cpdef void visitExecStmt(self, ExecStmt i)
    cpdef void visitExecTargetTemplateBlock(self, ExecTargetTemplateBlock i)
    cpdef void visitTemplateParamDecl(self, TemplateParamDecl i)
    cpdef void visitExportFunction(self, ExportFunction i)
    cpdef void visitTemplateParamExprValue(self, TemplateParamExprValue i)
    cpdef void visitTemplateParamTypeValue(self, TemplateParamTypeValue i)
    cpdef void visitExprAggrLiteral(self, ExprAggrLiteral i)
    cpdef void visitTypeIdentifier(self, TypeIdentifier i)
    cpdef void visitTypeIdentifierElem(self, TypeIdentifierElem i)
    cpdef void visitTypedefDeclaration(self, TypedefDeclaration i)
    cpdef void visitExprBin(self, ExprBin i)
    cpdef void visitExprBitSlice(self, ExprBitSlice i)
    cpdef void visitExprBool(self, ExprBool i)
    cpdef void visitExprCast(self, ExprCast i)
    cpdef void visitExprCompileHas(self, ExprCompileHas i)
    cpdef void visitExprCond(self, ExprCond i)
    cpdef void visitExprDomainOpenRangeList(self, ExprDomainOpenRangeList i)
    cpdef void visitExprDomainOpenRangeValue(self, ExprDomainOpenRangeValue i)
    cpdef void visitExprHierarchicalId(self, ExprHierarchicalId i)
    cpdef void visitExprId(self, ExprId i)
    cpdef void visitExprIn(self, ExprIn i)
    cpdef void visitExprListLiteral(self, ExprListLiteral i)
    cpdef void visitExprMemberPathElem(self, ExprMemberPathElem i)
    cpdef void visitExprNull(self, ExprNull i)
    cpdef void visitExprNumber(self, ExprNumber i)
    cpdef void visitExprOpenRangeList(self, ExprOpenRangeList i)
    cpdef void visitExprOpenRangeValue(self, ExprOpenRangeValue i)
    cpdef void visitExprRefPath(self, ExprRefPath i)
    cpdef void visitExprRefPathElem(self, ExprRefPathElem i)
    cpdef void visitExprStaticRefPath(self, ExprStaticRefPath i)
    cpdef void visitExprString(self, ExprString i)
    cpdef void visitExprStructLiteral(self, ExprStructLiteral i)
    cpdef void visitExprStructLiteralItem(self, ExprStructLiteralItem i)
    cpdef void visitExprSubscript(self, ExprSubscript i)
    cpdef void visitExprSubstring(self, ExprSubstring i)
    cpdef void visitExprUnary(self, ExprUnary i)
    cpdef void visitExtendEnum(self, ExtendEnum i)
    cpdef void visitFunctionDefinition(self, FunctionDefinition i)
    cpdef void visitFunctionImport(self, FunctionImport i)
    cpdef void visitFunctionParamDecl(self, FunctionParamDecl i)
    cpdef void visitGenericConstraintDeclValue(self, GenericConstraintDeclValue i)
    cpdef void visitGenericConstraintParam(self, GenericConstraintParam i)
    cpdef void visitMethodParameterList(self, MethodParameterList i)
    cpdef void visitMonitorActivityActionTraversal(self, MonitorActivityActionTraversal i)
    cpdef void visitActionHandleField(self, ActionHandleField i)
    cpdef void visitMonitorActivityConcat(self, MonitorActivityConcat i)
    cpdef void visitMonitorActivityEventually(self, MonitorActivityEventually i)
    cpdef void visitMonitorActivityIfElse(self, MonitorActivityIfElse i)
    cpdef void visitActivityBindStmt(self, ActivityBindStmt i)
    cpdef void visitActivityConstraint(self, ActivityConstraint i)
    cpdef void visitMonitorActivityMatch(self, MonitorActivityMatch i)
    cpdef void visitMonitorActivityMonitorTraversal(self, MonitorActivityMonitorTraversal i)
    cpdef void visitMonitorActivityOverlap(self, MonitorActivityOverlap i)
    cpdef void visitMonitorActivityRepeatCount(self, MonitorActivityRepeatCount i)
    cpdef void visitActivityJoinSpecBranch(self, ActivityJoinSpecBranch i)
    cpdef void visitActivityJoinSpecFirst(self, ActivityJoinSpecFirst i)
    cpdef void visitActivityJoinSpecNone(self, ActivityJoinSpecNone i)
    cpdef void visitActivityJoinSpecSelect(self, ActivityJoinSpecSelect i)
    cpdef void visitMonitorActivityRepeatWhile(self, MonitorActivityRepeatWhile i)
    cpdef void visitActivityLabeledStmt(self, ActivityLabeledStmt i)
    cpdef void visitMonitorActivitySelect(self, MonitorActivitySelect i)
    cpdef void visitMonitorConstraint(self, MonitorConstraint i)
    cpdef void visitNamedScope(self, NamedScope i)
    cpdef void visitPackageScope(self, PackageScope i)
    cpdef void visitProceduralStmtAssignment(self, ProceduralStmtAssignment i)
    cpdef void visitProceduralStmtBody(self, ProceduralStmtBody i)
    cpdef void visitProceduralStmtBreak(self, ProceduralStmtBreak i)
    cpdef void visitProceduralStmtContinue(self, ProceduralStmtContinue i)
    cpdef void visitProceduralStmtDataDeclaration(self, ProceduralStmtDataDeclaration i)
    cpdef void visitProceduralStmtExpr(self, ProceduralStmtExpr i)
    cpdef void visitProceduralStmtFunctionCall(self, ProceduralStmtFunctionCall i)
    cpdef void visitProceduralStmtIfElse(self, ProceduralStmtIfElse i)
    cpdef void visitProceduralStmtMatch(self, ProceduralStmtMatch i)
    cpdef void visitProceduralStmtMatchChoice(self, ProceduralStmtMatchChoice i)
    cpdef void visitProceduralStmtRandomize(self, ProceduralStmtRandomize i)
    cpdef void visitConstraintScope(self, ConstraintScope i)
    cpdef void visitProceduralStmtReturn(self, ProceduralStmtReturn i)
    cpdef void visitConstraintStmtDefault(self, ConstraintStmtDefault i)
    cpdef void visitConstraintStmtDefaultDisable(self, ConstraintStmtDefaultDisable i)
    cpdef void visitConstraintStmtExpr(self, ConstraintStmtExpr i)
    cpdef void visitConstraintStmtField(self, ConstraintStmtField i)
    cpdef void visitProceduralStmtYield(self, ProceduralStmtYield i)
    cpdef void visitConstraintStmtIf(self, ConstraintStmtIf i)
    cpdef void visitConstraintStmtUnique(self, ConstraintStmtUnique i)
    cpdef void visitDataTypeBool(self, DataTypeBool i)
    cpdef void visitDataTypeChandle(self, DataTypeChandle i)
    cpdef void visitDataTypeEnum(self, DataTypeEnum i)
    cpdef void visitDataTypeInt(self, DataTypeInt i)
    cpdef void visitDataTypePyObj(self, DataTypePyObj i)
    cpdef void visitDataTypeRef(self, DataTypeRef i)
    cpdef void visitDataTypeString(self, DataTypeString i)
    cpdef void visitDataTypeUserDefined(self, DataTypeUserDefined i)
    cpdef void visitEnumDecl(self, EnumDecl i)
    cpdef void visitEnumItem(self, EnumItem i)
    cpdef void visitSymbolChildrenScope(self, SymbolChildrenScope i)
    cpdef void visitTemplateCategoryTypeParamDecl(self, TemplateCategoryTypeParamDecl i)
    cpdef void visitTemplateGenericTypeParamDecl(self, TemplateGenericTypeParamDecl i)
    cpdef void visitExprAggrEmpty(self, ExprAggrEmpty i)
    cpdef void visitExprAggrList(self, ExprAggrList i)
    cpdef void visitTemplateValueParamDecl(self, TemplateValueParamDecl i)
    cpdef void visitExprAggrMap(self, ExprAggrMap i)
    cpdef void visitExprAggrStruct(self, ExprAggrStruct i)
    cpdef void visitExprRefPathContext(self, ExprRefPathContext i)
    cpdef void visitExprRefPathId(self, ExprRefPathId i)
    cpdef void visitExprRefPathStatic(self, ExprRefPathStatic i)
    cpdef void visitExprRefPathStaticRooted(self, ExprRefPathStaticRooted i)
    cpdef void visitExprSignedNumber(self, ExprSignedNumber i)
    cpdef void visitExprUnsignedNumber(self, ExprUnsignedNumber i)
    cpdef void visitExtendType(self, ExtendType i)
    cpdef void visitField(self, Field i)
    cpdef void visitFieldClaim(self, FieldClaim i)
    cpdef void visitFieldCompRef(self, FieldCompRef i)
    cpdef void visitFieldPool(self, FieldPool i)
    cpdef void visitFieldRef(self, FieldRef i)
    cpdef void visitFunctionImportProto(self, FunctionImportProto i)
    cpdef void visitFunctionImportType(self, FunctionImportType i)
    cpdef void visitFunctionPrototype(self, FunctionPrototype i)
    cpdef void visitGlobalScope(self, GlobalScope i)
    cpdef void visitActivityActionHandleTraversal(self, ActivityActionHandleTraversal i)
    cpdef void visitActivityActionTypeTraversal(self, ActivityActionTypeTraversal i)
    cpdef void visitActivityAtomicBlock(self, ActivityAtomicBlock i)
    cpdef void visitActivityForeach(self, ActivityForeach i)
    cpdef void visitActivityIfElse(self, ActivityIfElse i)
    cpdef void visitActivityMatch(self, ActivityMatch i)
    cpdef void visitActivityRepeatCount(self, ActivityRepeatCount i)
    cpdef void visitActivityRepeatWhile(self, ActivityRepeatWhile i)
    cpdef void visitActivityReplicate(self, ActivityReplicate i)
    cpdef void visitActivitySelect(self, ActivitySelect i)
    cpdef void visitActivitySuper(self, ActivitySuper i)
    cpdef void visitConstraintBlock(self, ConstraintBlock i)
    cpdef void visitProceduralStmtRepeatWhile(self, ProceduralStmtRepeatWhile i)
    cpdef void visitProceduralStmtWhile(self, ProceduralStmtWhile i)
    cpdef void visitConstraintStmtForall(self, ConstraintStmtForall i)
    cpdef void visitConstraintStmtForeach(self, ConstraintStmtForeach i)
    cpdef void visitConstraintStmtImplication(self, ConstraintStmtImplication i)
    cpdef void visitSymbolScope(self, SymbolScope i)
    cpdef void visitTypeScope(self, TypeScope i)
    cpdef void visitExprRefPathStaticFunc(self, ExprRefPathStaticFunc i)
    cpdef void visitExprRefPathSuper(self, ExprRefPathSuper i)
    cpdef void visitAction(self, Action i)
    cpdef void visitMonitor(self, Monitor i)
    cpdef void visitMonitorActivityDecl(self, MonitorActivityDecl i)
    cpdef void visitActivityDecl(self, ActivityDecl i)
    cpdef void visitMonitorActivitySchedule(self, MonitorActivitySchedule i)
    cpdef void visitMonitorActivitySequence(self, MonitorActivitySequence i)
    cpdef void visitActivityLabeledScope(self, ActivityLabeledScope i)
    cpdef void visitAnnotationDecl(self, AnnotationDecl i)
    cpdef void visitComponent(self, Component i)
    cpdef void visitProceduralStmtSymbolBodyScope(self, ProceduralStmtSymbolBodyScope i)
    cpdef void visitRootSymbolScope(self, RootSymbolScope i)
    cpdef void visitConstraintSymbolScope(self, ConstraintSymbolScope i)
    cpdef void visitStruct(self, Struct i)
    cpdef void visitSymbolEnumScope(self, SymbolEnumScope i)
    cpdef void visitSymbolExtendScope(self, SymbolExtendScope i)
    cpdef void visitSymbolFunctionScope(self, SymbolFunctionScope i)
    cpdef void visitSymbolTypeScope(self, SymbolTypeScope i)
    cpdef void visitExecScope(self, ExecScope i)
    cpdef void visitGenericConstraintDeclBool(self, GenericConstraintDeclBool i)
    cpdef void visitProceduralStmtRepeat(self, ProceduralStmtRepeat i)
    cpdef void visitActivitySequence(self, ActivitySequence i)
    cpdef void visitActivityParallel(self, ActivityParallel i)
    cpdef void visitActivitySchedule(self, ActivitySchedule i)
    cpdef void visitProceduralStmtForeach(self, ProceduralStmtForeach i)
    cpdef void visitExecBlock(self, ExecBlock i)
