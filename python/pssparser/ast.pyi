from enum import IntEnum
from typing import Dict, Generic, Iterator, List, Tuple, TypeVar

_T = TypeVar("_T")

class ListUtil(Generic[_T]):
    def __iter__(self) -> Iterator[_T]: ...
    def __len__(self) -> int: ...
    def __getitem__(self, i: int) -> _T: ...

class AssignOp(IntEnum):
    AssignOp_Eq = 0
    AssignOp_PlusEq = 1
    AssignOp_MinusEq = 2
    AssignOp_ShlEq = 3
    AssignOp_ShrEq = 4
    AssignOp_OrEq = 5
    AssignOp_AndEq = 6
    
class CommentPlacement(IntEnum):
    CommentPlacement_Leading = 0
    CommentPlacement_Trailing = 1
    CommentPlacement_Orphan = 2
    
class CompileCondKind(IntEnum):
    CompileCondKind_If = 0
    CompileCondKind_Assert = 1
    
class CovergroupBinsKindE(IntEnum):
    Bins = 0
    IllegalBins = 1
    IgnoreBins = 2
    
class CoverpointBinsFormE(IntEnum):
    Ranges = 0
    Coverpoint = 1
    Default = 2
    
class DocCommentForm(IntEnum):
    DocForm_None = 0
    DocForm_Line = 1
    DocForm_DocLine = 2
    DocForm_Block = 3
    DocForm_DocBlock = 4
    
class ExecKind(IntEnum):
    ExecKind_Body = 0
    ExecKind_Header = 1
    ExecKind_Declaration = 2
    ExecKind_RunStart = 3
    ExecKind_RunEnd = 4
    ExecKind_InitDown = 5
    ExecKind_InitUp = 6
    ExecKind_PreSolve = 7
    ExecKind_PostSolve = 8
    ExecKind_PreBody = 9
    ExecKind_File = 10
    
class ExprBinOp(IntEnum):
    BinOp_LogOr = 0
    BinOp_LogAnd = 1
    BinOp_BitOr = 2
    BinOp_BitXor = 3
    BinOp_BitAnd = 4
    BinOp_Lt = 5
    BinOp_Le = 6
    BinOp_Gt = 7
    BinOp_Ge = 8
    BinOp_Exp = 9
    BinOp_Mul = 10
    BinOp_Div = 11
    BinOp_Mod = 12
    BinOp_Add = 13
    BinOp_Sub = 14
    BinOp_Shl = 15
    BinOp_Shr = 16
    BinOp_Eq = 17
    BinOp_Ne = 18
    
class ExprUnaryOp(IntEnum):
    UnaryOp_Plus = 0
    UnaryOp_Minus = 1
    UnaryOp_LogNot = 2
    UnaryOp_BitNeg = 3
    UnaryOp_BitAnd = 4
    UnaryOp_BitOr = 5
    UnaryOp_BitXor = 6
    
class ExtendTargetE(IntEnum):
    Action = 0
    Annotation = 1
    Buffer = 2
    Component = 3
    Enum = 4
    Resource = 5
    State = 6
    Stream = 7
    Struct = 8
    Monitor = 9
    
class FunctionParamDeclKind(IntEnum):
    ParamKind_DataType = 0
    ParamKind_Type = 1
    ParamKind_RefAction = 2
    ParamKind_RefComponent = 3
    ParamKind_RefBuffer = 4
    ParamKind_RefResource = 5
    ParamKind_RefState = 6
    ParamKind_RefStream = 7
    ParamKind_RefStruct = 8
    ParamKind_Struct = 9
    ParamKind_RefMonitor = 10
    ParamKind_Numeric = 11
    
class ParamDir(IntEnum):
    ParamDir_Default = 0
    ParamDir_In = 1
    ParamDir_Out = 2
    ParamDir_InOut = 3
    
class PlatQual(IntEnum):
    PlatQual_None = 0
    PlatQual_Target = 1
    PlatQual_Solve = 2
    
class StringMethodId(IntEnum):
    StringMethod_None = 0
    StringMethod_Size = 1
    StringMethod_Find = 2
    StringMethod_FindLast = 3
    StringMethod_FindAll = 4
    StringMethod_Lower = 5
    StringMethod_Upper = 6
    StringMethod_Split = 7
    StringMethod_Chars = 8
    
class StructKind(IntEnum):
    Buffer = 0
    Struct = 1
    Resource = 2
    Stream = 3
    State = 4
    
class SymbolRefPathElemKind(IntEnum):
    ElemKind_ChildIdx = 0
    ElemKind_ArgIdx = 1
    ElemKind_Inline = 2
    ElemKind_ParamIdx = 3
    ElemKind_Super = 4
    ElemKind_TypeSpec = 5
    ElemKind_TemplateScope = 6
    ElemKind_This = 7
    
class TypeCategory(IntEnum):
    Action = 0
    Component = 1
    Buffer = 2
    Resource = 3
    State = 4
    Stream = 5
    Struct = 6
    Monitor = 7
    Numeric = 8
    
class Location:
    fileid: int
    lineno: int
    linepos: int
    extent: int

class SourceRange:
    fileid: int
    start_line: int
    start_col: int
    end_line: int
    end_col: int

class SymbolRefPathElem:
    kind: int
    idx: int

class FieldAttr(IntEnum):
    Action = 1
    Builtin = 2
    Rand = 4
    Const = 8
    Static = 16
    Instance = 32
    Private = 64
    Protected = 128
    Mutable = 256
    
class Factory(object):
    def mkExprAggrStructElem(self,
        name : ExprRefName,
        value : Expr) -> 'ExprAggrStructElem': ...
    def mkAssocData(self) -> 'AssocData': ...
    def mkSymbolExtMember(self,
        name : str,
        idx : int,
        pkg : SymbolScope) -> 'SymbolExtMember': ...
    def mkCompileCond(self) -> 'CompileCond': ...
    def mkSymbolImportSpec(self) -> 'SymbolImportSpec': ...
    def mkSymbolRefPath(self) -> 'SymbolRefPath': ...
    def mkTemplateParamValue(self) -> 'TemplateParamValue': ...
    def mkActivityMatchChoice(self,
        is_default : bool,
        cond : ExprOpenRangeList,
        body : ScopeChild) -> 'ActivityMatchChoice': ...
    def mkTemplateParamDeclList(self) -> 'TemplateParamDeclList': ...
    def mkExpr(self) -> 'Expr': ...
    def mkTemplateParamValueList(self) -> 'TemplateParamValueList': ...
    def mkActivitySelectBranch(self,
        guard : Expr,
        weight : Expr,
        body : ScopeChild) -> 'ActivitySelectBranch': ...
    def mkScopeChild(self) -> 'ScopeChild': ...
    def mkExprAggrMapElem(self,
        lhs : Expr,
        rhs : Expr) -> 'ExprAggrMapElem': ...
    def mkActionFieldInitializer(self,
        path : ExprRefPathContext,
        value : Expr) -> 'ActionFieldInitializer': ...
    def mkFunctionDefinition(self,
        proto : FunctionPrototype,
        body : ExecScope,
        plat : PlatQual) -> 'FunctionDefinition': ...
    def mkFunctionImport(self,
        plat : PlatQual,
        lang : str) -> 'FunctionImport': ...
    def mkFunctionParamDecl(self,
        kind : FunctionParamDeclKind,
        name : ExprId,
        type : DataType,
        dir : ParamDir,
        dflt : Expr) -> 'FunctionParamDecl': ...
    def mkActivityJoinSpec(self) -> 'ActivityJoinSpec': ...
    def mkGenericConstraintDeclValue(self) -> 'GenericConstraintDeclValue': ...
    def mkGenericConstraintParam(self,
        name : ExprId,
        is_const : bool,
        is_numeric : bool,
        type : DataType) -> 'GenericConstraintParam': ...
    def mkMethodParameterList(self) -> 'MethodParameterList': ...
    def mkActivitySchedulingConstraint(self,
        is_parallel : bool) -> 'ActivitySchedulingConstraint': ...
    def mkActivityStmt(self) -> 'ActivityStmt': ...
    def mkMonitorActivityStmt(self) -> 'MonitorActivityStmt': ...
    def mkAnnotation(self,
        type : TypeIdentifier) -> 'Annotation': ...
    def mkNamedScopeChild(self,
        name : ExprId) -> 'NamedScopeChild': ...
    def mkAnnotationParam(self,
        name : ExprRefName,
        value : Expr) -> 'AnnotationParam': ...
    def mkOverrideStmt(self) -> 'OverrideStmt': ...
    def mkComment(self,
        text : str,
        placement : CommentPlacement) -> 'Comment': ...
    def mkPackageImportStmt(self,
        wildcard : bool,
        alias : ExprId) -> 'PackageImportStmt': ...
    def mkComponentBind(self,
        pool_path : ExprRefPathContext,
        is_wildcard : bool) -> 'ComponentBind': ...
    def mkComponentBindTarget(self,
        is_wildcard : bool) -> 'ComponentBindTarget': ...
    def mkComponentPathElem(self,
        id : ExprRefName) -> 'ComponentPathElem': ...
    def mkConstraintStmt(self) -> 'ConstraintStmt': ...
    def mkProceduralStmtIfClause(self,
        cond : Expr,
        body : ScopeChild) -> 'ProceduralStmtIfClause': ...
    def mkPyImportFromStmt(self) -> 'PyImportFromStmt': ...
    def mkPyImportStmt(self) -> 'PyImportStmt': ...
    def mkCoverStmtReference(self,
        target : TypeIdentifier) -> 'CoverStmtReference': ...
    def mkScope(self) -> 'Scope': ...
    def mkScopeChildRef(self,
        target : ScopeChild) -> 'ScopeChildRef': ...
    def mkSymbolChild(self) -> 'SymbolChild': ...
    def mkCovergroupOption(self,
        name : ExprId,
        value : Expr) -> 'CovergroupOption': ...
    def mkCovergroupPortmap(self,
        name : ExprRefName,
        target : ExprRefPathContext) -> 'CovergroupPortmap': ...
    def mkDataType(self) -> 'DataType': ...
    def mkTargetTemplateFunction(self,
        proto : FunctionPrototype,
        language : str,
        data : str) -> 'TargetTemplateFunction': ...
    def mkDistItem(self,
        range : ExprOpenRangeValue,
        weight : DistWeight) -> 'DistItem': ...
    def mkDistWeight(self,
        is_dividing : bool,
        expr : Expr) -> 'DistWeight': ...
    def mkExecBlockTag(self,
        type : TypeIdentifier) -> 'ExecBlockTag': ...
    def mkExecStmt(self) -> 'ExecStmt': ...
    def mkExecTargetTemplateBlock(self,
        kind : ExecKind,
        data : str) -> 'ExecTargetTemplateBlock': ...
    def mkExportAction(self,
        plat : PlatQual,
        target : TypeIdentifier) -> 'ExportAction': ...
    def mkExportFunction(self,
        plat : PlatQual,
        name : ExprRefName) -> 'ExportFunction': ...
    def mkTemplateParamDecl(self,
        name : ExprId) -> 'TemplateParamDecl': ...
    def mkTemplateParamExprValue(self,
        value : Expr) -> 'TemplateParamExprValue': ...
    def mkTemplateParamTypeValue(self,
        value : DataType) -> 'TemplateParamTypeValue': ...
    def mkExprAggrLiteral(self) -> 'ExprAggrLiteral': ...
    def mkTypeIdentifier(self) -> 'TypeIdentifier': ...
    def mkExprBin(self,
        lhs : Expr,
        op : ExprBinOp,
        rhs : Expr) -> 'ExprBin': ...
    def mkExprBitSlice(self,
        lhs : Expr,
        rhs : Expr) -> 'ExprBitSlice': ...
    def mkExprBool(self,
        value : bool) -> 'ExprBool': ...
    def mkExprCast(self,
        casting_type : DataType,
        expr : Expr) -> 'ExprCast': ...
    def mkExprCompileHas(self,
        ref : ExprRefPath) -> 'ExprCompileHas': ...
    def mkExprCond(self,
        cond_e : Expr,
        true_e : Expr,
        false_e : Expr) -> 'ExprCond': ...
    def mkExprDomainOpenRangeList(self) -> 'ExprDomainOpenRangeList': ...
    def mkExprDomainOpenRangeValue(self,
        single : bool,
        lhs : Expr,
        rhs : Expr) -> 'ExprDomainOpenRangeValue': ...
    def mkExprFloatLiteral(self,
        value : float,
        image : str,
        is_scientific : bool) -> 'ExprFloatLiteral': ...
    def mkExprHierarchicalId(self) -> 'ExprHierarchicalId': ...
    def mkExprId(self,
        id : str,
        is_escaped : bool) -> 'ExprId': ...
    def mkExprIn(self,
        lhs : Expr,
        rhs : ExprOpenRangeList,
        collection : Expr) -> 'ExprIn': ...
    def mkExprMemberCall(self,
        receiver : Expr) -> 'ExprMemberCall': ...
    def mkExprMemberPathElem(self,
        id : ExprId,
        params : MethodParameterList) -> 'ExprMemberPathElem': ...
    def mkExprNull(self) -> 'ExprNull': ...
    def mkExprNumber(self) -> 'ExprNumber': ...
    def mkExprOpenRangeList(self) -> 'ExprOpenRangeList': ...
    def mkExprOpenRangeValue(self,
        lhs : Expr,
        rhs : Expr) -> 'ExprOpenRangeValue': ...
    def mkExprRefName(self,
        id : ExprId) -> 'ExprRefName': ...
    def mkExprRefPath(self) -> 'ExprRefPath': ...
    def mkTypeIdentifierElem(self,
        id : ExprId,
        params : TemplateParamValueList) -> 'TypeIdentifierElem': ...
    def mkExprSliceRange(self) -> 'ExprSliceRange': ...
    def mkExprString(self,
        value : str,
        is_raw : bool) -> 'ExprString': ...
    def mkTypedefDeclaration(self,
        name : ExprId,
        type : DataType) -> 'TypedefDeclaration': ...
    def mkExprUnary(self,
        op : ExprUnaryOp,
        rhs : Expr) -> 'ExprUnary': ...
    def mkExtendEnum(self,
        target : TypeIdentifier) -> 'ExtendEnum': ...
    def mkActionHandleField(self,
        name : ExprId,
        type : DataType) -> 'ActionHandleField': ...
    def mkActivityBindStmt(self,
        lhs : ExprRefPathContext) -> 'ActivityBindStmt': ...
    def mkActivityConstraint(self,
        constraint : ConstraintStmt) -> 'ActivityConstraint': ...
    def mkActivityJoinSpecBranch(self) -> 'ActivityJoinSpecBranch': ...
    def mkActivityJoinSpecFirst(self,
        count : Expr) -> 'ActivityJoinSpecFirst': ...
    def mkActivityJoinSpecNone(self) -> 'ActivityJoinSpecNone': ...
    def mkActivityJoinSpecSelect(self,
        count : Expr) -> 'ActivityJoinSpecSelect': ...
    def mkActivityLabeledStmt(self) -> 'ActivityLabeledStmt': ...
    def mkActivitySymbolCall(self,
        target : ExprRefName) -> 'ActivitySymbolCall': ...
    def mkConstraintScope(self) -> 'ConstraintScope': ...
    def mkConstraintStmtDefault(self,
        hid : ExprRefPathContext,
        expr : Expr) -> 'ConstraintStmtDefault': ...
    def mkConstraintStmtDefaultDisable(self,
        hid : ExprRefPathContext) -> 'ConstraintStmtDefaultDisable': ...
    def mkConstraintStmtDist(self,
        lhs : Expr) -> 'ConstraintStmtDist': ...
    def mkConstraintStmtExpr(self,
        expr : Expr) -> 'ConstraintStmtExpr': ...
    def mkConstraintStmtField(self,
        name : ExprId,
        type : DataType) -> 'ConstraintStmtField': ...
    def mkConstraintStmtIf(self,
        cond : Expr,
        true_c : ConstraintScope,
        false_c : ConstraintScope) -> 'ConstraintStmtIf': ...
    def mkConstraintStmtSoft(self,
        expr : Expr) -> 'ConstraintStmtSoft': ...
    def mkConstraintStmtUnique(self) -> 'ConstraintStmtUnique': ...
    def mkCoverStmtInline(self) -> 'CoverStmtInline': ...
    def mkCovergroup(self,
        name : ExprId) -> 'Covergroup': ...
    def mkCovergroupCoverpoint(self,
        name : ExprId,
        target : Expr) -> 'CovergroupCoverpoint': ...
    def mkCovergroupCross(self,
        name : ExprId) -> 'CovergroupCross': ...
    def mkCovergroupCrossBins(self,
        name : ExprId,
        kind : CovergroupBinsKindE,
        target : ExprRefName,
        with_expr : Expr) -> 'CovergroupCrossBins': ...
    def mkCovergroupInstantiation(self,
        name : ExprId,
        type : TypeIdentifier) -> 'CovergroupInstantiation': ...
    def mkCoverpointBins(self,
        name : ExprId,
        kind : CovergroupBinsKindE,
        form : CoverpointBinsFormE) -> 'CoverpointBins': ...
    def mkDataTypeBool(self) -> 'DataTypeBool': ...
    def mkDataTypeChandle(self) -> 'DataTypeChandle': ...
    def mkDataTypeEnum(self,
        tid : DataTypeUserDefined,
        in_rangelist : ExprDomainOpenRangeList) -> 'DataTypeEnum': ...
    def mkDataTypeFloat(self,
        is_float64 : bool) -> 'DataTypeFloat': ...
    def mkDataTypeInt(self,
        is_signed : bool,
        width : Expr,
        in_range : ExprDomainOpenRangeList) -> 'DataTypeInt': ...
    def mkDataTypePyObj(self) -> 'DataTypePyObj': ...
    def mkDataTypeRef(self,
        type : DataTypeUserDefined) -> 'DataTypeRef': ...
    def mkDataTypeString(self,
        has_range : bool) -> 'DataTypeString': ...
    def mkDataTypeUserDefined(self,
        is_global : bool,
        type_id : TypeIdentifier) -> 'DataTypeUserDefined': ...
    def mkEnumDecl(self,
        name : ExprId) -> 'EnumDecl': ...
    def mkEnumItem(self,
        name : ExprId,
        value : Expr) -> 'EnumItem': ...
    def mkExprAggrEmpty(self) -> 'ExprAggrEmpty': ...
    def mkExprAggrList(self) -> 'ExprAggrList': ...
    def mkExprAggrMap(self) -> 'ExprAggrMap': ...
    def mkExprAggrStruct(self) -> 'ExprAggrStruct': ...
    def mkExprRefPathContext(self,
        hier_id : ExprHierarchicalId) -> 'ExprRefPathContext': ...
    def mkExprRefPathStatic(self,
        is_global : bool) -> 'ExprRefPathStatic': ...
    def mkExprRefPathStaticRooted(self,
        root : ExprRefPathStatic,
        leaf : ExprHierarchicalId) -> 'ExprRefPathStaticRooted': ...
    def mkExprSignedNumber(self,
        image : str,
        width : int,
        value : int) -> 'ExprSignedNumber': ...
    def mkExprTemplateString(self,
        value : str,
        is_raw : bool) -> 'ExprTemplateString': ...
    def mkExprUnsignedNumber(self,
        image : str,
        width : int,
        value : int) -> 'ExprUnsignedNumber': ...
    def mkExtendType(self,
        kind : ExtendTargetE,
        target : TypeIdentifier) -> 'ExtendType': ...
    def mkField(self,
        name : ExprId,
        type : DataType,
        attr : FieldAttr,
        init : Expr) -> 'Field': ...
    def mkFieldClaim(self,
        name : ExprId,
        type : DataTypeUserDefined,
        is_lock : bool) -> 'FieldClaim': ...
    def mkFieldCompRef(self,
        name : ExprId,
        type : DataTypeUserDefined) -> 'FieldCompRef': ...
    def mkFieldPool(self,
        name : ExprId,
        type : DataTypeUserDefined,
        size : Expr) -> 'FieldPool': ...
    def mkFieldRef(self,
        name : ExprId,
        type : DataTypeUserDefined,
        is_input : bool) -> 'FieldRef': ...
    def mkFunctionImportProto(self,
        plat : PlatQual,
        lang : str,
        proto : FunctionPrototype) -> 'FunctionImportProto': ...
    def mkFunctionImportType(self,
        plat : PlatQual,
        lang : str,
        type : TypeIdentifier) -> 'FunctionImportType': ...
    def mkFunctionPrototype(self,
        name : ExprId,
        rtype : DataType,
        is_target : bool,
        is_solve : bool) -> 'FunctionPrototype': ...
    def mkGlobalScope(self,
        fileid : int) -> 'GlobalScope': ...
    def mkInstanceOverride(self,
        target : ExprRefPathContext,
        with_t : TypeIdentifier) -> 'InstanceOverride': ...
    def mkMonitorActivityLabeledStmt(self) -> 'MonitorActivityLabeledStmt': ...
    def mkMonitorConstraint(self,
        constraint : ConstraintStmt) -> 'MonitorConstraint': ...
    def mkNamedScope(self,
        name : ExprId) -> 'NamedScope': ...
    def mkOverrideDecl(self) -> 'OverrideDecl': ...
    def mkPackageScope(self) -> 'PackageScope': ...
    def mkProceduralStmtAssignment(self,
        lhs : Expr,
        op : AssignOp,
        rhs : Expr) -> 'ProceduralStmtAssignment': ...
    def mkProceduralStmtBody(self,
        body : ScopeChild) -> 'ProceduralStmtBody': ...
    def mkProceduralStmtBreak(self) -> 'ProceduralStmtBreak': ...
    def mkProceduralStmtContinue(self) -> 'ProceduralStmtContinue': ...
    def mkProceduralStmtDataDeclaration(self,
        name : ExprId,
        datatype : DataType,
        init : Expr) -> 'ProceduralStmtDataDeclaration': ...
    def mkProceduralStmtExpr(self,
        expr : Expr) -> 'ProceduralStmtExpr': ...
    def mkProceduralStmtIfElse(self) -> 'ProceduralStmtIfElse': ...
    def mkProceduralStmtMatch(self,
        expr : Expr) -> 'ProceduralStmtMatch': ...
    def mkProceduralStmtMatchChoice(self,
        is_default : bool,
        cond : ExprOpenRangeList,
        body : ScopeChild) -> 'ProceduralStmtMatchChoice': ...
    def mkProceduralStmtRandomize(self) -> 'ProceduralStmtRandomize': ...
    def mkProceduralStmtReturn(self,
        expr : Expr) -> 'ProceduralStmtReturn': ...
    def mkProceduralStmtSuper(self) -> 'ProceduralStmtSuper': ...
    def mkProceduralStmtYield(self) -> 'ProceduralStmtYield': ...
    def mkSymbolChildrenScope(self,
        name : str) -> 'SymbolChildrenScope': ...
    def mkTemplateCategoryTypeParamDecl(self,
        name : ExprId,
        category : TypeCategory,
        restriction : TypeIdentifier,
        dflt : DataType) -> 'TemplateCategoryTypeParamDecl': ...
    def mkTemplateGenericTypeParamDecl(self,
        name : ExprId,
        dflt : DataType) -> 'TemplateGenericTypeParamDecl': ...
    def mkTemplateValueParamDecl(self,
        name : ExprId,
        type : DataType,
        dflt : Expr) -> 'TemplateValueParamDecl': ...
    def mkTypeOverride(self,
        target : TypeIdentifier,
        with_t : TypeIdentifier) -> 'TypeOverride': ...
    def mkActivityActionHandleTraversal(self,
        target : ExprRefPathContext,
        with_c : ConstraintStmt) -> 'ActivityActionHandleTraversal': ...
    def mkActivityActionTypeTraversal(self,
        target : DataTypeUserDefined,
        with_c : ConstraintStmt) -> 'ActivityActionTypeTraversal': ...
    def mkTypeScope(self,
        name : ExprId,
        super_t : TypeIdentifier) -> 'TypeScope': ...
    def mkSymbolScope(self,
        name : str) -> 'SymbolScope': ...
    def mkConstraintBlock(self,
        name : ExprId,
        is_dynamic : bool) -> 'ConstraintBlock': ...
    def mkConstraintStmtForall(self,
        iterator_id : ExprId,
        type_id : DataTypeUserDefined,
        ref_path : ExprRefPath) -> 'ConstraintStmtForall': ...
    def mkConstraintStmtForeach(self,
        expr : Expr) -> 'ConstraintStmtForeach': ...
    def mkProceduralStmtRepeatWhile(self,
        body : ScopeChild,
        expr : Expr) -> 'ProceduralStmtRepeatWhile': ...
    def mkConstraintStmtImplication(self,
        cond : Expr) -> 'ConstraintStmtImplication': ...
    def mkProceduralStmtWhile(self,
        body : ScopeChild,
        expr : Expr) -> 'ProceduralStmtWhile': ...
    def mkExprRefPathSuper(self,
        hier_id : ExprHierarchicalId) -> 'ExprRefPathSuper': ...
    def mkActivitySuper(self) -> 'ActivitySuper': ...
    def mkAction(self,
        name : ExprId,
        super_t : TypeIdentifier,
        is_abstract : bool) -> 'Action': ...
    def mkActivityDecl(self,
        name : str) -> 'ActivityDecl': ...
    def mkGenericConstraintDeclBool(self,
        name : ExprId,
        is_dynamic : bool) -> 'GenericConstraintDeclBool': ...
    def mkActivityLabeledScope(self,
        name : str) -> 'ActivityLabeledScope': ...
    def mkImportClass(self,
        name : ExprId,
        super_t : TypeIdentifier) -> 'ImportClass': ...
    def mkMonitor(self,
        name : ExprId,
        super_t : TypeIdentifier) -> 'Monitor': ...
    def mkMonitorActivityDecl(self,
        name : str) -> 'MonitorActivityDecl': ...
    def mkMonitorActivityLabeledScope(self,
        name : str) -> 'MonitorActivityLabeledScope': ...
    def mkAnnotationDecl(self,
        name : ExprId,
        super_t : TypeIdentifier) -> 'AnnotationDecl': ...
    def mkComponent(self,
        name : ExprId,
        super_t : TypeIdentifier) -> 'Component': ...
    def mkProceduralStmtSymbolBodyScope(self,
        name : str,
        body : ScopeChild) -> 'ProceduralStmtSymbolBodyScope': ...
    def mkConstraintSymbolScope(self,
        name : str) -> 'ConstraintSymbolScope': ...
    def mkRootSymbolScope(self,
        name : str) -> 'RootSymbolScope': ...
    def mkStruct(self,
        name : ExprId,
        super_t : TypeIdentifier,
        kind : StructKind) -> 'Struct': ...
    def mkSymbolDeclaration(self,
        name : str) -> 'SymbolDeclaration': ...
    def mkCovergroupType(self,
        name : ExprId,
        super_t : TypeIdentifier) -> 'CovergroupType': ...
    def mkSymbolEnumScope(self,
        name : str) -> 'SymbolEnumScope': ...
    def mkSymbolExtendScope(self,
        name : str) -> 'SymbolExtendScope': ...
    def mkSymbolFunctionScope(self,
        name : str) -> 'SymbolFunctionScope': ...
    def mkSymbolTypeScope(self,
        name : str,
        plist : SymbolScope) -> 'SymbolTypeScope': ...
    def mkTemplateElem(self,
        name : str,
        offset : int,
        extent : int) -> 'TemplateElem': ...
    def mkExecScope(self,
        name : str) -> 'ExecScope': ...
    def mkTemplateString(self,
        name : str,
        raw : str) -> 'TemplateString': ...
    def mkActivityAtomicBlock(self,
        name : str,
        body : ScopeChild) -> 'ActivityAtomicBlock': ...
    def mkActivityForeach(self,
        name : str,
        it_id : ExprId,
        idx_id : ExprId,
        path : ExprRefPathContext,
        body : ScopeChild) -> 'ActivityForeach': ...
    def mkActivityIfElse(self,
        name : str,
        cond : Expr,
        true_s : ScopeChild,
        false_s : ScopeChild) -> 'ActivityIfElse': ...
    def mkActivityMatch(self,
        name : str,
        cond : Expr) -> 'ActivityMatch': ...
    def mkActivityParallel(self,
        name : str,
        join_spec : ActivityJoinSpec) -> 'ActivityParallel': ...
    def mkActivityRepeatCount(self,
        name : str,
        loop_var : ExprId,
        count : Expr,
        body : ScopeChild) -> 'ActivityRepeatCount': ...
    def mkActivityRepeatWhile(self,
        name : str,
        cond : Expr,
        body : ScopeChild) -> 'ActivityRepeatWhile': ...
    def mkActivityReplicate(self,
        name : str,
        idx_id : ExprId,
        count : Expr,
        it_label : ExprId,
        body : ScopeChild) -> 'ActivityReplicate': ...
    def mkActivitySchedule(self,
        name : str,
        join_spec : ActivityJoinSpec) -> 'ActivitySchedule': ...
    def mkMonitorActivityOverlap(self,
        name : str) -> 'MonitorActivityOverlap': ...
    def mkMonitorActivitySchedule(self,
        name : str) -> 'MonitorActivitySchedule': ...
    def mkMonitorActivitySelect(self,
        name : str) -> 'MonitorActivitySelect': ...
    def mkMonitorActivitySequence(self,
        name : str) -> 'MonitorActivitySequence': ...
    def mkMonitorActivityConcat(self,
        name : str) -> 'MonitorActivityConcat': ...
    def mkActivitySelect(self,
        name : str) -> 'ActivitySelect': ...
    def mkMonitorActivityEventually(self,
        name : str,
        body : ScopeChild) -> 'MonitorActivityEventually': ...
    def mkActivitySequence(self,
        name : str) -> 'ActivitySequence': ...
    def mkProceduralStmtForeach(self,
        name : str,
        body : ScopeChild,
        path : ExprRefPath,
        it_id : ExprId,
        idx_id : ExprId) -> 'ProceduralStmtForeach': ...
    def mkProceduralStmtRepeat(self,
        name : str,
        body : ScopeChild,
        it_id : ExprId,
        count : Expr) -> 'ProceduralStmtRepeat': ...
    def mkTemplateAssign(self,
        name : str,
        offset : int,
        extent : int,
        lhs : ExprRefName,
        rhs : Expr) -> 'TemplateAssign': ...
    def mkTemplateBlock(self,
        name : str,
        offset : int,
        extent : int) -> 'TemplateBlock': ...
    def mkTemplateComment(self,
        name : str,
        offset : int,
        extent : int,
        text : str) -> 'TemplateComment': ...
    def mkTemplateExpr(self,
        name : str,
        offset : int,
        extent : int,
        expr : Expr) -> 'TemplateExpr': ...
    def mkExecBlock(self,
        name : str,
        kind : ExecKind) -> 'ExecBlock': ...
    def mkTemplateIf(self,
        name : str,
        offset : int,
        extent : int) -> 'TemplateIf': ...
    def mkTemplateText(self,
        name : str,
        offset : int,
        extent : int,
        text : str) -> 'TemplateText': ...
    def mkTemplateVarDecl(self,
        name : str,
        offset : int,
        extent : int) -> 'TemplateVarDecl': ...
    def mkTemplateForeach(self,
        name : str,
        offset : int,
        extent : int,
        expr : Expr) -> 'TemplateForeach': ...
    def mkTemplateRepeat(self,
        name : str,
        offset : int,
        extent : int,
        expr : Expr) -> 'TemplateRepeat': ...
    def mkTemplateIfClause(self,
        name : str,
        offset : int,
        extent : int) -> 'TemplateIfClause': ...
    @staticmethod
    def inst() -> 'Factory': ...
    
class ExprAggrStructElem(object):
    pass
    
    def getName(self) -> ExprRefName: ...
    
    def getValue(self) -> Expr: ...
    
class AssocData(object):
    pass
    
class SymbolExtMember(object):
    pass
    
    def getName(self) -> str: ...
    
    def setName(self, v : str): ...
    
    def getPkg(self) -> SymbolScope: ...
    
class CompileCond(object):
    pass
    
    def getKind(self) -> int: ...
    def setKind(self, v : CompileCondKind | int) -> None: ...
    
    def getCond(self) -> Expr: ...
    
    def inactive(self) -> ListUtil[SourceRange]: ...
    def getInactiveList(self) -> List[SourceRange]: ...
    def getInactive(self, i: int) -> SourceRange: ...
    def addInactive(self, i: SourceRange) -> None: ...
    def numInactive(self) -> int: ...
    
    def getLocation(self) -> 'Location': ...
    
    def getMsg(self) -> str: ...
    
    def setMsg(self, v : str): ...
    
class SymbolImportSpec(object):
    pass
    
    def imports(self) -> ListUtil[PackageImportStmt]: ...
    def getImports(self) -> List[PackageImportStmt]: ...
    def getImport(self, i: int) -> PackageImportStmt: ...
    def addImport(self, i: PackageImportStmt) -> None: ...
    def numImports(self) -> int: ...
    
class SymbolRefPath(object):
    pass
    
    def path(self) -> ListUtil[SymbolRefPathElem]: ...
    def getPathList(self) -> List[SymbolRefPathElem]: ...
    def getPath(self, i: int) -> SymbolRefPathElem: ...
    def addPath(self, i: SymbolRefPathElem) -> None: ...
    def numPath(self) -> int: ...
    
class TemplateParamValue(object):
    pass
    
class ActivityMatchChoice(object):
    pass
    
    def getCond(self) -> ExprOpenRangeList: ...
    
    def getBody(self) -> ScopeChild: ...
    
class TemplateParamDeclList(object):
    pass
    
    def params(self) -> ListUtil[TemplateParamDecl]: ...
    def getParams(self) -> List[TemplateParamDecl]: ...
    def getParam(self, i: int) -> TemplateParamDecl: ...
    def addParam(self, i: TemplateParamDecl) -> None: ...
    def numParams(self) -> int: ...
    
class Expr(object):
    pass
    
class TemplateParamValueList(object):
    pass
    
    def values(self) -> ListUtil[TemplateParamValue]: ...
    def getValues(self) -> List[TemplateParamValue]: ...
    def getValue(self, i: int) -> TemplateParamValue: ...
    def addValue(self, i: TemplateParamValue) -> None: ...
    def numValues(self) -> int: ...
    
class ActivitySelectBranch(object):
    pass
    
    def getGuard(self) -> Expr: ...
    
    def getWeight(self) -> Expr: ...
    
    def getBody(self) -> ScopeChild: ...
    
class ScopeChild(object):
    pass
    
    def getDocstring(self) -> str: ...
    
    def setDocstring(self, v : str): ...
    
    def getDocRaw(self) -> str: ...
    
    def setDocRaw(self, v : str): ...
    
    def getDocForm(self) -> int: ...
    def setDocForm(self, v : DocCommentForm | int) -> None: ...
    
    def getDocLocation(self) -> 'Location': ...
    
    def getLocation(self) -> 'Location': ...
    
    def getEndLocation(self) -> 'Location': ...
    
    def getParent(self) -> Scope: ...
    
    def getAssocData(self) -> AssocData: ...
    
    def annotations(self) -> ListUtil[Annotation]: ...
    def getAnnotations(self) -> List[Annotation]: ...
    def getAnnotation(self, i: int) -> Annotation: ...
    def addAnnotation(self, i: Annotation) -> None: ...
    def numAnnotations(self) -> int: ...
    
    def comments(self) -> ListUtil[Comment]: ...
    def getComments(self) -> List[Comment]: ...
    def getComment(self, i: int) -> Comment: ...
    def addComment(self, i: Comment) -> None: ...
    def numComments(self) -> int: ...
    
    def trailing_comments(self) -> ListUtil[Comment]: ...
    def getTrailing_comments(self) -> List[Comment]: ...
    def getTrailing_comment(self, i: int) -> Comment: ...
    def addTrailing_comment(self, i: Comment) -> None: ...
    def numTrailing_comments(self) -> int: ...
    
class ExprAggrMapElem(object):
    pass
    
    def getLhs(self) -> Expr: ...
    
    def getRhs(self) -> Expr: ...
    
class ActionFieldInitializer(ScopeChild):
    """
    One assignment `.x = value` of an action initializer list -- LRM
    11.3.1.2, `action_initializer`.
    
    An initializer list gives initial values to attributes of an action as
    it is traversed (or declared), passing data from the activity to the
    sub-action. Entries appear on action traversals
    (ActivityActionHandleTraversal, ActivityActionTypeTraversal), on
    action-handle declarations (ActionHandleField) and on a handle
    declaration in an action body that parses as data (Field).
    
    PSS Example::
    
        activity {
            do A {.x = 1, .cfg.mode = FAST};
            a1 {.x = n + 1};
        }
    
    See Also:
        ActivityActionHandleTraversal, ActivityActionTypeTraversal, ActionHandleField, Field
    
    """
    pass
    
    def getPath(self) -> ExprRefPathContext: ...
    
    def getValue(self) -> Expr: ...
    
class FunctionDefinition(ScopeChild):
    """
    A native PSS function: a prototype with a body of procedural
    statements -- LRM 20.3, `function_decl` ending in
    `{ procedural_stmt ... }`.
    
    Declares and defines a function in one place, in a package or
    component (20.2.1, 20.3). Its parameters take no direction
    qualifiers (20.2.2). A prototype without a body
    (`function ... ;`) is a bare FunctionPrototype instead.
    
    PSS Example::
    
        package p {
            function int add(int a, int b) {
                return a + b;
            }
    
            // Target-only function
            target function void program(bit[32] addr) {
                return;
            }
    
            // Solve-only function
            solve function int calculate(int value) {
                return value + 100;
            }
        }
    
    Attributes:
        endLocation: Location of the function's closing brace
            (inherited from ScopeChild)
        proto: The function's prototype -- return type, name,
            parameters, and the `pure`, `static` and platform flags
        body: The function body: an ExecScope named `<func-body>`
            holding the statements in source order
        plat: The `platform_qualifier`: PlatQual_None when none is
            written; PlatQual_Target for `target`, and also for
            `target solve` (the prototype records both flags)
    
    See Also:
        FunctionPrototype, ExecScope, PlatQual, FunctionImportProto, TargetTemplateFunction
    
    """
    pass
    
    def getProto(self) -> FunctionPrototype: ...
    
    def getBody(self) -> ExecScope: ...
    
    def getPlat(self) -> int: ...
    def setPlat(self, v : PlatQual | int) -> None: ...
    
class FunctionImport(ScopeChild):
    """
    Base class of the foreign-function imports -- LRM 20.4.1,
    `import_function` -- and the record of one import of a function.
    
    An import says that a function is implemented in a foreign
    language, optionally restricting it to the solve or target
    platform and naming the language. The parser builds one of the two
    subclasses: FunctionImportProto for the one-step form that also
    declares the function, FunctionImportType for the two-step form
    that names a function declared elsewhere. The linker builds bare
    FunctionImport nodes as the import records of a
    SymbolFunctionScope (its `import_specs`).
    
    PSS Example::
    
        package p {
            function int ext_func(int x);
    
            // Two-step: FunctionImportType
            import solve C function ext_func;
    
            // One-step: FunctionImportProto
            import target C function void write_reg(bit[32] addr,
                                                    bit[32] data);
        }
    
    Attributes:
        plat: The `platform_qualifier`, or PlatQual_None when none is
            written
        lang: The `language_identifier` (e.g. `C`, `CPP`), or empty
            when none is written. A record built by TaskBuildSymbolTree
            for a one-step import always has it empty.
    
    See Also:
        FunctionImportType, FunctionImportProto, PlatQual, SymbolFunctionScope
    
    """
    pass
    
    def getPlat(self) -> int: ...
    def setPlat(self, v : PlatQual | int) -> None: ...
    
    def getLang(self) -> str: ...
    
    def setLang(self, v : str): ...
    
class FunctionParamDecl(ScopeChild):
    """
    One parameter of a function prototype -- LRM 20.2.1,
    `function_parameter` and `varargs_parameter`.
    
    A parameter either states a data type (with an optional direction
    or `const`, and an optional default value), or is generic and names
    only a kind: `type`, `ref` with a reference category, or a plain
    category (`struct`, `numeric`). The last parameter may be a varargs
    parameter (`int ... rest`), which collects any number of trailing
    arguments (20.2.5).
    
    The same class holds the parameters of an ExportAction and of an
    activity symbol (SymbolDeclaration), and of the built-in methods
    the linker synthesizes.
    
    PSS Example::
    
        package p {
            // Imported: directions are allowed
            import function void transfer(input int src, output int dst,
                                          inout int count);
    
            // Default value and const parameter
            function int scale(const int factor, int x = 10);
    
            // Generic parameters
            function void inspect(type T, ref action a, struct s,
                                  numeric n);
    
            // Varargs
            function void log_all(string fmt, int ... rest);
        }
    
    Attributes:
        kind: Which parameter form was written (data type, `type`,
            `ref` category, plain category)
        name: The parameter's name. Always set.
        type: The parameter's data type; null for the generic forms
            (any kind but ParamKind_DataType)
        dir: The direction qualifier, or ParamDir_Default when none is
            written. Always ParamDir_Default for a varargs parameter.
        dflt: The default value (`= constant_expression`), or null when
            none is written. Only the data-type form can have one.
        is_varargs: True for the varargs parameter (`... name`), which
            is always the last
        is_const: True if declared `const` (LRM 20.2.3): read-only in
          the function, and the only kind of parameter an aggregate
          constant or literal may be passed to. Never set on a varargs
          parameter, whose syntax has no `const`.
    
    See Also:
        FunctionPrototype, FunctionParamDeclKind, ParamDir, DataType
    
    """
    pass
    
    def getKind(self) -> int: ...
    def setKind(self, v : FunctionParamDeclKind | int) -> None: ...
    
    def getName(self) -> ExprId: ...
    
    def getType(self) -> DataType: ...
    
    def getDir(self) -> int: ...
    def setDir(self, v : ParamDir | int) -> None: ...
    
    def getDflt(self) -> Expr: ...
    
class ActivityJoinSpec(ScopeChild):
    """
    Base class of the join specifications of a `parallel` or `schedule`
    block -- LRM 11.3.6, `activity_join_spec`.
    
    A join specification relaxes the default, under which the statement
    following the block is scheduled after every statement in the block
    has completed: it says which of the block's top-level statements that
    following statement depends on.
    
    PSS Example::
    
        activity {
            parallel join_none { do A; do B; }
            parallel join_first(1) { do A; do B; }
            parallel join_select(1) { do A; do B; }
            parallel join_branch(L1) { L1: do A; do B; }
        }
    
    See Also:
        ActivityJoinSpecNone, ActivityJoinSpecFirst, ActivityJoinSpecSelect, ActivityJoinSpecBranch, ActivityParallel, ActivitySchedule
    
    """
    pass
    
class GenericConstraintDeclValue(ScopeChild):
    """
    Value-returning generic constraint declaration (LRM 13.1.2,
    `generic_constraint_value`).
    
    Represents a declaration of the form
    ``[static] constraint <type> name(params) expr;``. The constraint
    yields the value of a single expression and may be used wherever
    an expression of its result type is legal within a constraint.
    
    PSS Example::
    
        constraint numeric max(numeric a, numeric b)
            (a < b) ? b : a;
    
        struct S {
            rand bit[8] j, k, l;
            constraint j == max(k, l);
        }
    
    See Also:
        GenericConstraintDeclBool, GenericConstraintParam
    
    """
    pass
    
    def getReturn_type(self) -> DataType: ...
    
    def getName(self) -> ExprId: ...
    
    def parameters(self) -> ListUtil[GenericConstraintParam]: ...
    def getParameters(self) -> List[GenericConstraintParam]: ...
    def getParameter(self, i: int) -> GenericConstraintParam: ...
    def addParameter(self, i: GenericConstraintParam) -> None: ...
    def numParameters(self) -> int: ...
    
    def getExpr(self) -> Expr: ...
    
class GenericConstraintParam(ScopeChild):
    """
    One formal parameter of a PSS 3.1 generic constraint
    (LRM 13.1.2, `generic_constraint_param`).
    
    A parameter is typed either with a concrete PSS data type or with
    the `numeric` category, which accepts any integer or
    floating-point expression, and may be marked `const`. Inside the
    constraint's body a parameter is referenced by name like any other
    variable; the linker's name lookup (NameLookup) finds it in the
    enclosing generic constraint's parameter list.
    
    PSS Example::
    
        constraint numeric max(numeric a, numeric b)
            (a < b) ? b : a;
    
        struct S {
            rand bit[8] x;
            constraint in_range(const int lo, int hi) {
                x >= lo;
                x <= hi;
            }
        }
    
    See Also:
        GenericConstraintDeclBool, GenericConstraintDeclValue, DataType
    
    """
    pass
    
    def getName(self) -> ExprId: ...
    
    def getType(self) -> DataType: ...
    
class MethodParameterList(Expr):
    """
    The arguments of a call (Annex B, `function_parameter_list`).
    
    Attached to the called ExprMemberPathElem as its `params`.
    
    PSS Example::
    
        my_function(arg1, arg2, arg3)
        obj.method(x, y)
        f()                 // an empty list
    
    Attributes:
        parameters: The argument expressions, in order; empty for `()`
    
    See Also:
        ExprMemberPathElem, ExprMemberCall
    
    """
    pass
    
    def parameters(self) -> ListUtil[Expr]: ...
    def getParameters(self) -> List[Expr]: ...
    def getParameter(self, i: int) -> Expr: ...
    def addParameter(self, i: Expr) -> None: ...
    def numParameters(self) -> int: ...
    
class ActivitySchedulingConstraint(ScopeChild):
    """
    A scheduling constraint: `constraint parallel { a, b };` or
    `constraint sequence { a, b, c };` -- LRM 13.2,
    `activity_scheduling_constraint`.
    
    Relates two or more action handles or named sub-activities from a
    scheduling point of view, without traversing anything: `sequence`
    orders them so that each completes before the next starts; `parallel`
    starts them in a synchronized way. It may appear among the activity
    statements, where it is a child of the enclosing activity block, or
    directly in the action body, where it is a child of the action.
    
    PSS Example::
    
        action top {
            A a1;
            B b1;
            C c1;
            activity {
                schedule {
                    a1;
                    b1;
                    c1;
                }
                constraint sequence { a1, b1 };
                constraint parallel { b1, c1 };
            }
        }
    
    Attributes:
        is_parallel: True for `constraint parallel`, false for `constraint sequence`.
        targets: The constrained items, one reference path per
            `hierarchical_id` in source order (at least two). Each is a path
            through the named sub-activity tree (`L1.a`) to an action handle
            or label; resolved by the linker (TaskResolveRefs).
    
    See Also:
        ActivitySchedule, ActivityParallel, ActivitySequence
    
    """
    pass
    
    def targets(self) -> ListUtil[ExprRefPathContext]: ...
    def getTargets(self) -> List[ExprRefPathContext]: ...
    def getTarget(self, i: int) -> ExprRefPathContext: ...
    def addTarget(self, i: ExprRefPathContext) -> None: ...
    def numTargets(self) -> int: ...
    
class ActivityStmt(ScopeChild):
    """
    Base class of the activity statements that are not blocks or compound
    statements -- part of LRM 11.2, `activity_stmt`.
    
    Its subclasses are the traversals and `super` (through
    ActivityLabeledStmt), `bind` (ActivityBindStmt), an in-activity
    `constraint` (ActivityConstraint) and a symbol call
    (ActivitySymbolCall). Blocks and compound statements (`sequence`,
    `parallel`, `schedule`, `repeat`, `foreach`, `select`, `if`, `match`,
    `replicate`, `atomic`) introduce a scope and so derive from
    ActivityLabeledScope instead; the two hierarchies share only
    ScopeChild. A scheduling constraint (ActivitySchedulingConstraint) and
    a join specification (ActivityJoinSpec) are ScopeChild directly.
    
    PSS Example::
    
        activity {
            a1;                     // ActivityActionHandleTraversal
            do B;                   // ActivityActionTypeTraversal
            bind a1.out_b b1.in_b;  // ActivityBindStmt
            constraint { a1.x < 4; } // ActivityConstraint
        }
    
    See Also:
        ActivityLabeledStmt, ActivityLabeledScope, ActivityDecl
    
    """
    pass
    
class MonitorActivityStmt(ScopeChild):
    """
    Base class for all monitor activity statements.
    
    MonitorActivityStmt is the abstract base class for the non-scope
    statements that can appear within a monitor's activity block. The
    block-shaped forms (``sequence``, ``concat``, ``overlap``,
    ``schedule``, ``select``) and ``eventually`` descend from
    MonitorActivityLabeledScope instead, because they introduce a scope;
    the two branches meet at ScopeChild. Any field holding an arbitrary
    monitor activity statement must therefore be typed ``ScopeChild``,
    not ``MonitorActivityStmt`` -- typing it narrowly silently discards
    every block-shaped body.
    
    Not every monitor activity statement is one of these: a traversal
    builds the same ActivityActionHandleTraversal or
    ActivityActionTypeTraversal an action activity does, and a handle
    declaration builds an ActionHandleField. Of the classes in this
    hierarchy, only MonitorConstraint is currently built.
    
    PSS Example::
    
        component pss_top {
            action req_a { rand bit[8] len; }
            action ack_a { }
    
            monitor protocol_monitor {
                req_a r;
                ack_a a;
                activity {
                    r;                            // ActivityActionHandleTraversal
                    constraint { r.len > 0; }     // MonitorConstraint
                    eventually a;                 // MonitorActivityEventually
                }
            }
        }
    
    Attributes:
        (base class - no specific attributes)
    
    See Also:
        MonitorConstraint, MonitorActivityLabeledStmt,
        MonitorActivityLabeledScope, MonitorActivityDecl
    
    """
    pass
    
class Annotation(ScopeChild):
    """
    Applied annotation attached to a model element (LRM 7.13,
    `annotation`).
    
    Represents an annotation use such as ``@desc_s {.desc = "hello"}``.
    The annotation type is referenced by name; every parameter is
    name-mapped (PSS 3.1 removed positional annotation parameters).
    
    ``is_standalone`` distinguishes the two application forms of §7.13: a
    standalone annotation is terminated with ``;`` and is anchored to the
    enclosing scope, while an element annotation has no terminator and
    attaches to the model element that follows it. The builder places a
    standalone annotation among the enclosing scope's children, and an
    element annotation in the ``annotations`` list of the element it
    precedes (inherited from ScopeChild); an element annotation with no
    following element in its scope is reported as an error. Annotations
    written in an ``override`` block or a covergroup body are accepted
    but not kept.
    
    Annotations are advisory: an annotation whose type does not resolve
    is disregarded with a warning (LINT403), and its parameters are not
    checked.
    
    PSS Example::
    
        @desc_s {.desc = "Configures the IP"}     // element annotation
        action config {
            @desc_s {.desc = "Scope annotation"};  // standalone annotation
        }
    
    See Also:
        AnnotationDecl, AnnotationParam
    
    """
    pass
    
    def getType(self) -> TypeIdentifier: ...
    
    def parameters(self) -> ListUtil[AnnotationParam]: ...
    def getParameters(self) -> List[AnnotationParam]: ...
    def getParameter(self, i: int) -> AnnotationParam: ...
    def addParameter(self, i: AnnotationParam) -> None: ...
    def numParameters(self) -> int: ...
    
class NamedScopeChild(ScopeChild):
    """
    An AST node with an identifier name that is a child of a scope.
    
    Base class for named declarations that aren't scopes themselves,
    such as fields, enum items, and function prototypes. The name is
    used for symbol lookup within the parent scope.
    
    PSS Example::
    
        struct my_struct {
            int field1;        // NamedScopeChild with name="field1"
            bool field2;       // NamedScopeChild with name="field2"
        }
    
    Attributes:
        name: The declared name, as an identifier with its own location
    
    See Also:
        ScopeChild, NamedScope, Field, EnumItem, FunctionPrototype
    
    """
    pass
    
    def getName(self) -> ExprId: ...
    
class AnnotationParam(ScopeChild):
    """
    Parameter to an applied annotation (LRM 7.13,
    `annotation_param_item`).
    
    ``name`` is the annotation-type field the value is mapped onto. It is
    always set: PSS 3.1 annotation parameters are name-mapped only.
    
    PSS Example::
    
        @desc_s {.desc = "hello", .level = 2}
    
    See Also:
        Annotation, AnnotationDecl
    
    """
    pass
    
    def getName(self) -> ExprRefName: ...
    
    def getValue(self) -> Expr: ...
    
class OverrideStmt(ScopeChild):
    """
    Base class for the two statements an ``override`` block admits
    (LRM 17.5, `override_stmt`).
    
    The two differ in what they select -- a type, or one instance -- and
    share the replacement type. They are separate classes rather than one
    class with a discriminator because the target is a type identifier in
    one and a hierarchical instance path in the other.
    
    See Also:
        TypeOverride, InstanceOverride, OverrideDecl
    
    """
    pass
    
class Comment(ScopeChild):
    """
    A source comment captured verbatim and in normalized form.
    
    Collected only when the builder has ``setCollectComments(true)``
    (`Parser(collect_comments=True)`). Leading and trailing comments,
    and orphans a blank line has detached from the construct below
    them, hang off the ``comments`` list of that ``ScopeChild``;
    comments after a scope's last member, before its closing ``}``,
    collect in that scope's ``trailing_comments``. The comment's own
    ``location`` (with ``extent`` set to the raw text's length) is
    recorded too.
    
    PSS Example::
    
        // A leading comment of C
        component C {   // a trailing comment of C
            int a;
            // an orphan, in C's trailing_comments
        }
    
    Attributes:
        text: normalized content. For a line comment the `//` and
            at most one following space are removed, so a `///` or
            `//!` comment keeps its third character; for a block
            comment the delimiters and the ``*`` gutter are removed
            and the lines re-flushed left
        raw: the untouched source text, delimiters included
        is_block: true for ``/* */``, false for ``//``
        placement: how the comment relates to its owner
    
    See Also:
        CommentPlacement, ScopeChild.comments, ScopeChild.trailing_comments
    
    """
    pass
    
    def getText(self) -> str: ...
    
    def setText(self, v : str): ...
    
    def getPlacement(self) -> int: ...
    def setPlacement(self, v : CommentPlacement | int) -> None: ...
    
    def getRaw(self) -> str: ...
    
    def setRaw(self, v : str): ...
    
class PackageImportStmt(ScopeChild):
    """
    Import statement bringing package symbols into current scope
    (`import_stmt`, LRM 18.1.3, 18.1.4).
    
    Imports types and declarations from another package. Can import
    all symbols with wildcard or create an alias for qualified access.
    The linker records each import on the enclosing symbol scope
    (SymbolImportSpec) and resolves its path (TaskResolveImports).
    
    PSS Example::
    
        import other_pkg::*;              // Wildcard import
        import other_pkg::MyAction;       // Single import
        import other_pkg as op;           // Aliased import
    
    Attributes:
        wildcard: True if the pattern ends in `::*`
        alias: The `as` name (`package_import_alias`); null when there
            is none
        path: The package or member named (the `type_identifier` of
            `package_import_pattern`, without the `::*`). Its target is
            set by the linker (TaskResolveImports)
    
    See Also:
        PackageScope, TypeIdentifier, SymbolImportSpec
    
    """
    pass
    
    def getAlias(self) -> ExprId: ...
    
    def getPath(self) -> TypeIdentifier: ...
    
class ComponentBind(ScopeChild):
    """
    Component-level static pool-binding directive (`object_bind_stmt`,
    LRM 12.3).
    
    Binds a pool to a set of action object-reference fields, or to all
    compatible references via the wildcard form. Every target -- including
    a wildcard -- is a ``ComponentBindTarget``, so a mixed list such as
    ``bind p { a.x, * }`` keeps both entries in source order.
    
    The pool is an ordinary reference from the binding component. A
    target's path elements, action type and field are resolved along
    the component path by the linker (TaskResolveRefs, after the rest
    of the walk): each element in the component the previous one
    reaches, the action type in the last component reached, the field
    in that action type.
    
    PSS Example::
    
        component pss_top {
            pool my_buffer p;
            bind p *;                       // wildcard
            bind p { producer.out };        // explicit target path
            bind p { sub[0..3].prod.out };  // indexed component path
        }
    
    Attributes:
        pool_path: Path to the bound pool (e.g. ``p``, ``sub0.p``).
            Resolved by the linker (TaskResolveRefs), which reports an
            error when it names something other than a FieldPool.
        is_wildcard: True if *any* target is a wildcard -- for the bare
            ``bind p *;`` form, and for a mixed list containing ``*``.
            Equivalent to ``any(t.is_wildcard for t in targets)``, and
            retained as a shorthand for the overwhelmingly common bare
            form.
        targets: The bind targets in source order, one
            ``ComponentBindTarget`` per entry.
    
    See Also:
        ComponentBindTarget, ComponentPathElem, FieldPool
    
    """
    pass
    
    def getPool_path(self) -> ExprRefPathContext: ...
    
    def targets(self) -> ListUtil[ComponentBindTarget]: ...
    def getTargets(self) -> List[ComponentBindTarget]: ...
    def getTarget(self, i: int) -> ComponentBindTarget: ...
    def addTarget(self, i: ComponentBindTarget) -> None: ...
    def numTargets(self) -> int: ...
    
class ComponentBindTarget(ScopeChild):
    """
    One entry in a ``bind`` directive's target list.
    
    Corresponds to ``object_bind_item_path`` in the grammar: a possibly
    empty component-instance path followed by the bind item itself, which
    is either ``*`` or ``ActionType.field`` with an optional index
    selection.
    
    A wildcard entry sets ``is_wildcard`` and leaves ``type_id``,
    ``field`` and ``range`` null. Because the wildcard is a target like
    any other, a mixed list keeps its shape: ``bind p { a.x, * }`` has two
    targets rather than one target plus a flag.
    
    PSS Example::
    
        component pss_top {
            pool my_buffer p;
            bind p { sub[0..3].prod.out };
            //       path -----^     ^--- type_id="prod", field="out"
            bind p { a.x, * };  // two targets, the second a wildcard
        }
    
    Attributes:
        path: Leading component-instance path elements (empty when the
            target names an action in the enclosing component).
        is_wildcard: True for the ``*`` form.
        type_id: Action type of the bind item; null when wildcard.
            Resolved by the linker (TaskResolveRefs) among the action
            types of the last component the path reaches.
        field: Object-reference field on that action; null when
            wildcard. Its target is set by the linker (TaskResolveRefs)
            to a FieldRef or FieldClaim of the action type.
        range: Optional index / index-range selection on the field; null
            when absent or wildcard.
    
    See Also:
        ComponentBind, ComponentPathElem, FieldRef, FieldClaim
    
    """
    pass
    
    def path(self) -> ListUtil[ComponentPathElem]: ...
    def getPathList(self) -> List[ComponentPathElem]: ...
    def getPath(self, i: int) -> ComponentPathElem: ...
    def addPath(self, i: ComponentPathElem) -> None: ...
    def numPath(self) -> int: ...
    
    def getType_id(self) -> TypeIdentifier: ...
    
    def getField(self) -> ExprRefName: ...
    
    def getRange(self) -> ExprDomainOpenRangeList: ...
    
class ComponentPathElem(ScopeChild):
    """
    One component-instance step of a ``bind`` target path.
    
    Corresponds to ``component_path_elem`` in the grammar: a component
    instance name with an optional index or index-range selection. The
    index selection is the reason this class exists -- it was previously
    folded into the target's dotted text, where a consumer could neither
    read the indices nor tell them from part of a name.
    
    PSS Example::
    
        component pss_top {
            pool my_buffer p;
            bind p { sub[0..3].prod.out };
            //       ^^^^^^^^^ one ComponentPathElem, id="sub",
            //                 range=[0..3]
            //                 ^^^^ a second, id="prod", no index
        }
    
    Attributes:
        id: The component instance name. Its target is set by the
            linker (TaskResolveRefs) to the instance field in the
            component reached by the previous element.
        range: Optional index / index-range selection; null when the
            element carries no ``[...]``. Only one bracketed selection
            is accepted.
    
    See Also:
        ComponentBindTarget, ComponentBind, ExprDomainOpenRangeList
    
    """
    pass
    
    def getId(self) -> ExprRefName: ...
    
    def getRange(self) -> ExprDomainOpenRangeList: ...
    
class ConstraintStmt(ScopeChild):
    """
    Base class for all constraint statement types.
    
    Represents any statement that can appear within a constraint body
    (LRM 13.1.1, `constraint_body_item`). The statement's position in
    its enclosing ConstraintScope is recorded in `index` (inherited
    from ScopeChild); soft-constraint priority depends on it.
    
    PSS Example::
    
        constraint example_c {
            // Each line below is a different ConstraintStmt subtype
            value > 0;                    // ConstraintStmtExpr
            if (mode == 1) {              // ConstraintStmtIf
                value < 10;
            }
            unique { id1, id2, id3 };     // ConstraintStmtUnique
        }
    
    See Also:
        ConstraintStmtExpr, ConstraintStmtIf, ConstraintStmtForeach
        ConstraintStmtForall, ConstraintScope
    
    """
    pass
    
class ProceduralStmtIfClause(ScopeChild):
    """
    One condition-and-body branch of a ProceduralStmtIfElse: the `if`
    or one `else if`.
    
    The grammar (LRM 20.7.9) nests `else if` as an `if` statement in
    the `else` branch; the parser flattens that chain into one
    ProceduralStmtIfElse with one clause per condition, in source order.
    This class is not itself a statement.
    
    PSS Example::
    
        component pss_top {
            action my_action {
                int x;
                int size;
                exec post_solve {
                    if (x > 15) {          // first clause
                        size = 2;
                    } else if (x > 5) {    // second clause
                        size = 1;
                    }
                }
            }
        }
    
    Attributes:
        cond: The `bool` condition. Always set.
        body: The statement run when the condition is true, given its
            clause's position as its index. Null if it is an empty
            statement (`;`).
    
    See Also:
        ProceduralStmtIfElse
    
    """
    pass
    
    def getCond(self) -> Expr: ...
    
    def getBody(self) -> ScopeChild: ...
    
class PyImportFromStmt(ScopeChild):
    """
    Python 'from...import' statement for selective imports (a
    zuspec extension, not part of the LRM).
    
    Imports specific symbols from a Python module into PSS context.
    The grammar accepts the statement, but the builder currently
    discards it: no PyImportFromStmt is ever added to the AST.
    
    PSS Example::
    
        from os pyimport path, environ;
    
    Attributes:
        path: Module path (e.g., ["os"])
        targets: List of symbols to import (e.g., ["path", "environ"])
    
    See Also:
        PyImportStmt
    
    """
    pass
    
    def path(self) -> ListUtil[ExprId]: ...
    def getPathList(self) -> List[ExprId]: ...
    def getPath(self, i: int) -> ExprId: ...
    def addPath(self, i: ExprId) -> None: ...
    def numPath(self) -> int: ...
    
    def targets(self) -> ListUtil[ExprId]: ...
    def getTargets(self) -> List[ExprId]: ...
    def getTarget(self, i: int) -> ExprId: ...
    def addTarget(self, i: ExprId) -> None: ...
    def numTargets(self) -> int: ...
    
class PyImportStmt(ScopeChild):
    """
    Python import statement for embedded Python integration (a
    zuspec extension, not part of the LRM).
    
    Imports a Python module into PSS context, so PSS code can refer
    to the module's members. The linker registers the alias, or the
    first element of the module path, as a symbol of the enclosing
    scope; references through it are not checked (Python objects
    are dynamically typed).
    
    PSS Example::
    
        pyimport os;
        pyimport os::path as osp;
    
    Attributes:
        path: The module path (`pyimport_mod_path`), one identifier per
            `::`-separated element (e.g. ["os", "path"])
        alias: The `as` name; null when there is none
    
    See Also:
        PyImportFromStmt
    
    """
    pass
    
    def path(self) -> ListUtil[ExprId]: ...
    def getPathList(self) -> List[ExprId]: ...
    def getPath(self, i: int) -> ExprId: ...
    def addPath(self, i: ExprId) -> None: ...
    def numPath(self) -> int: ...
    
    def getAlias(self) -> ExprId: ...
    
class CoverStmtReference(ScopeChild):
    """
    Instantiates a named monitor type for behavioral coverage
    (LRM 16.1, the first form of `cover_stmt`).
    
    ``cover M;`` requests that the behavior described by monitor type
    ``M`` be covered. Like the inline form, it is a
    ``component_body_item``. ``target`` is the *type* named -- a monitor type
    identifier, resolved at link -- not a reference to an existing
    instance; there is no syntax for covering an instance.
    
    The optional ``label`` comes from the ``label_identifier ':'`` prefix.
    
    PSS Example::
    
        component pss_top {
            action req_a { }
            action ack_a { }
    
            monitor handshake_mon {
                req_a r;
                ack_a a;
                activity {
                    concat {
                        r;
                        a;
                    }
                }
            }
    
            cover handshake_mon;
            hs: cover handshake_mon;
        }
    
    Attributes:
        target: The ``type_identifier`` naming the monitor type being
            covered. Its ``target`` is set by the linker
            (TaskResolveRefs).
        label: Label identifier (``hs`` above), or null if the
            statement is unlabeled. Set by the parser.
    
    See Also:
        CoverStmtInline, Monitor
    
    """
    pass
    
    def getTarget(self) -> TypeIdentifier: ...
    
    def getLabel(self) -> ExprId: ...
    
class Scope(ScopeChild):
    """
    Container for child AST nodes forming a hierarchical scope.
    
    Base class for all AST nodes that can contain other nodes. Provides
    the fundamental tree structure of the AST. Most PSS constructs that
    use braces create a Scope.
    
    PSS Example::
    
        component my_comp {      // Creates Scope
            action a1 { }        // Nested Scope
            struct s1 { }        // Nested Scope
        }
    
    Attributes:
        endLocation: Source position just past the construct's last
            token, usually its closing brace (inherited from
            ScopeChild)
        children: The declarations and statements written in the
            scope, in source order. Each child's `parent` is this
            scope and its `index` its position here. An element
            annotation is not a child (it is held by the element it
            precedes), but a standalone annotation (`@a;`) is. The
            builder also inserts an implicit `comp` FieldCompRef as
            child 0 of every Action. Declarations in an elaborated
            `compile if` branch appear here directly; those in a
            branch not elaborated do not appear at all
        parent: Parent scope (inherited from ScopeChild)
    
    See Also:
        ScopeChild, NamedScope, GlobalScope, CompileCond
    
    """
    pass
    
    def children(self) -> ListUtil[ScopeChild]: ...
    def getChildren(self) -> List[ScopeChild]: ...
    def getChild(self, i: int) -> ScopeChild: ...
    def addChild(self, i: ScopeChild) -> None: ...
    def numChildren(self) -> int: ...
    
    def compile_conds(self) -> ListUtil[CompileCond]: ...
    def getCompile_conds(self) -> List[CompileCond]: ...
    def getCompile_cond(self, i: int) -> CompileCond: ...
    def addCompile_cond(self, i: CompileCond) -> None: ...
    def numCompile_conds(self) -> int: ...
    
class ScopeChildRef(ScopeChild):
    """
    Reference to another AST node, used for type aliases and forwards.
    
    Represents a symbolic reference that will be resolved during linking.
    Used when one AST node needs to reference another without creating
    a direct pointer.
    
    Not built by the parser or the linker: the only use is in
    commented-out code in AstMerger. Reserved.
    
    Attributes:
        target: The referenced AST node
    
    See Also:
        ScopeChild, FieldRef
    
    """
    pass
    
    def getTarget(self) -> ScopeChild: ...
    
class SymbolChild(ScopeChild):
    """
    Base class for nodes that the linker places in a symbol scope and
    addresses by id.
    
    Extends ScopeChild with the two links the linked symbol tree needs:
    the node's position in the symbol scope that holds it, and that
    scope. Every symbol scope derives from it (through
    SymbolChildrenScope), both the scopes the linker builds as a logical
    view of the declarations (RootSymbolScope, SymbolTypeScope,
    SymbolFunctionScope, the merged package scopes, ...) and the parsed
    nodes that are scopes in their own right (ExecScope, ActivityDecl,
    ...).
    
    The fields are filled during linking (TaskBuildSymbolTree, and
    TaskApplyTypeExtensions when an extension's members are merged into
    their type); they are unset on a freshly parsed AST.
    
    Attributes:
        id: Position of this symbol in its `upper` scope: the
            `ElemKind_ChildIdx` step that reaches it. -1 if unassigned
        upper: The symbol scope that holds this one in the linked tree;
            null until linked, and for the root
    
    See Also:
        SymbolScope, SymbolChildrenScope, ScopeChild
    
    """
    pass
    
    def getUpper(self) -> SymbolScope: ...
    
class CovergroupOption(ScopeChild):
    """
    An ``option.<name> = <value>;`` setting (LRM 15.5,
    `covergroup_option`).
    
    Options appear in four places -- a covergroup body, a coverpoint
    body, a cross body, and the ``with { ... }`` of a covergroup
    instantiation -- and mean the same thing in each, so one class
    serves all four. The name is left as written and is not resolved;
    the set of legal option names (LRM Table 25) is a semantic
    question, not a syntactic one.
    
    PSS Example::
    
        covergroup {
            option.weight = 2;
            cp : coverpoint x {
                option.at_least = 4;
            }
        } cg;
    
    Attributes:
        name: The option being set, without the ``option.`` prefix
        value: The value assigned, a constant expression; its
            references are resolved by the linker (TaskResolveRefs)
    
    See Also:
        Covergroup, CovergroupCoverpoint, CovergroupCross
        CovergroupInstantiation
    
    """
    pass
    
    def getName(self) -> ExprId: ...
    
    def getValue(self) -> Expr: ...
    
class CovergroupPortmap(ScopeChild):
    """
    One ``.port(actual)`` binding in a covergroup instantiation
    (LRM 15.2, `covergroup_portmap`).
    
    PSS Example::
    
        cg_t cg(.a(x), .b(y));
    
    Attributes:
        name: The formal port being bound. Its target is set by the
            linker (TaskResolveRefs) to the port's Field in the
            covergroup type; an unknown port is reported as an error
        target: The actual bound to it, a ``hierarchical_id`` in the
            instantiating scope
    
    See Also:
        CovergroupInstantiation, CovergroupType
    
    """
    pass
    
    def getName(self) -> ExprRefName: ...
    
    def getTarget(self) -> ExprRefPathContext: ...
    
class DataType(ScopeChild):
    """
    Base class for all PSS data types (`data_type`, LRM 7.1).
    
    The parser builds one DataType node for each type written in source:
    a scalar type (`int`, `bit`, `bool`, `string`, `chandle`, `float32`,
    `float64`, an enum with a domain), a `ref` reference type, or a
    `type_identifier` naming a user-defined, collection or array type.
    Used in field declarations, typedefs, function signatures and
    template parameters.
    
    See Also:
        DataTypeInt, DataTypeBool, DataTypeString, DataTypeFloat,
        DataTypeChandle, DataTypeEnum, DataTypeRef, DataTypeUserDefined,
        Field
    
    """
    pass
    
class TargetTemplateFunction(ScopeChild):
    """
    Function whose body is target-language template text -- PSS 3.1
    §20.6, ``target_template_function ::= target language_identifier [ static ] function function_prototype = string_literal ;``.
    
    A target-template function declares a PSS prototype but supplies its
    implementation as a string of target-language code rather than as a
    PSS body. It is always a target implementation, and only `void`
    functions are supported. Inside a triple-quoted string the text may
    contain mustache expressions and control-flow directives, which
    resolve against the function's own parameter list (and, for an
    instance function, the instance's attributes). Parameters take no
    direction qualifiers.
    
    PSS Example::
    
        package my_pkg {
            // Parameters are referenced with mustache expressions
            target ASM function void do_stw(bit[32] val, bit[32] vaddr) = \"\"\"
                loadi RA {{val}}
                store RA {{vaddr}}
            \"\"\";
    
            // Plain text: no template is built
            target C function void barrier() = "__sync_synchronize();";
        }
    
        component pss_top {
            target C static function void hello() = \"\"\" puts("hi"); \"\"\";
        }
    
    Attributes:
        proto: Function prototype (return type, name, parameters). Built
            without a platform qualifier, so its `is_target` is false
            and its `is_static` is false even when `static` is written.
        language: The `language_identifier` (e.g. `C`, `ASM`, `SV`)
        data: Raw template text, with the enclosing quotes stripped
        is_static: True if declared ``static``
        template: Scanned template body, present only when the string
            is triple-quoted and contains special elements (§4.7.1);
            null otherwise
    
    See Also:
        FunctionPrototype, ExecTargetTemplateBlock, TemplateString
    
    """
    pass
    
    def getProto(self) -> FunctionPrototype: ...
    
    def getLanguage(self) -> str: ...
    
    def setLanguage(self, v : str): ...
    
    def getData(self) -> str: ...
    
    def setData(self, v : str): ...
    
    def getTemplate(self) -> TemplateString: ...
    
class DistItem(ScopeChild):
    """
    One value-or-range entry in a `dist` directive's distribution list
    (LRM 13.1.13, `dist_item`).
    
    The weight is optional; an item written without one carries the
    default weight (`:= 1`).
    
    PSS Example::
    
        constraint c {
            dist x in [1 := 10,        // single value, weighted
                       2..4 :/ 30,     // range, weight divided
                       5];             // no weight -- defaults to 1
        }
    
    Attributes:
        range: The value or value range this weight applies to
            (`open_range_value`)
        weight: The weight, or null when none was written
    
    See Also:
        DistWeight, ConstraintStmtDist, ExprOpenRangeValue
    
    """
    pass
    
    def getRange(self) -> ExprOpenRangeValue: ...
    
    def getWeight(self) -> DistWeight: ...
    
class DistWeight(ScopeChild):
    """
    Weight applied to one item of a `dist` directive
    (LRM 13.1.13, `dist_weight`).
    
    PSS spells the weight two ways, which mean different things when the
    item covers a range of values:
    
    * ``:=`` gives the stated weight to *each* value in the range
    * ``:/`` divides the stated weight *across* the values in the range
    
    For a single value the two are the same. The distinction is not
    recoverable from the expression alone, so it is carried here
    rather than left to the consumer to infer.
    
    PSS Example::
    
        constraint c {
            dist x in [1 := 10, 2..4 :/ 30];
        }
    
    Attributes:
        is_dividing: True for `:/`, false for `:=`
        expr: The weight expression
    
    See Also:
        DistItem, ConstraintStmtDist
    
    """
    pass
    
    def getExpr(self) -> Expr: ...
    
class ExecBlockTag(ScopeChild):
    """
    Tag on a target-template exec block -- PSS 3.1 §20.5.4.
    
    ``exec_block_tag ::= type_identifier [ struct_literal ]``
    
    A tag exists solely so a code generator can tell whether two exec
    blocks are equivalent and may be coalesced. It has no effect on
    action traversal, solving, or runtime execution.
    
    It is evaluated using a temporary instance of the named struct type,
    initialized from the struct literal when one is written and from the
    field defaults otherwise. Two blocks match only if their tags are the
    same struct type *and* evaluate equal; an untagged block matches
    nothing, not even another untagged block.
    
    Tags are permitted only on ``header``, ``declaration``,
    ``run_start``, ``run_end`` and ``exec file`` blocks -- not on
    ``body`` and not on the solve execs. (The grammar admits a tag only
    on the target-template forms, so a native exec block cannot carry
    one.) The kind restriction is a semantic rule, not a grammatical
    one; the parser reports it as PSS106.
    
    PSS Example::
    
        struct tag_s { string name; }
    
        component pss_top {
            exec header C = tag_s {.name = "hdr"}: \"\"\"
                #include <stdio.h>
            \"\"\";
        }
    
    Attributes:
        type: The struct type naming the tag. Its reference is bound by
            the linker (TaskResolveRefs).
        literal: The struct literal of field initializers, or null when
            none was written. The linker (TaskResolveRefs) types it from
            `type`.
    
    See Also:
        ExecTargetTemplateBlock, ExprAggrStruct
    
    """
    pass
    
    def getType(self) -> TypeIdentifier: ...
    
    def getLiteral(self) -> ExprAggrStruct: ...
    
class ExecStmt(ScopeChild):
    """
    Base class of the procedural statements -- LRM 20.7,
    `procedural_stmt`.
    
    Every statement that can appear in a procedural exec block or a
    native function body derives from this class: assignments, void
    function calls, `return`, control flow, `randomize`, `yield`,
    `break`/`continue` and `super;`. A local variable declaration
    (ProceduralStmtDataDeclaration) is also an ExecStmt. The loop
    statements that declare variables (ProceduralStmtRepeat,
    ProceduralStmtForeach) and a nested `{ ... }` block (ExecScope) are
    symbol scopes instead, and so do not derive from it. The class itself
    is abstract: the parser never builds a bare ExecStmt.
    
    PSS Example::
    
        component pss_top {
            function void my_func();
    
            action my_action {
                int x;
                exec post_solve {
                    int y = 10;          // ProceduralStmtDataDeclaration
                    x += y;              // ProceduralStmtAssignment
                    if (x > 10) { }      // ProceduralStmtIfElse
                    my_func();           // ProceduralStmtExpr
                }
            }
        }
    
    Attributes:
        upper: Intended back-pointer to the enclosing symbol scope. Not
            set by the parser or by any linker task, so it is always
            null; reserved. It is not visited during traversal.
    
    See Also:
        ExecScope, ExecBlock, ProceduralStmtAssignment
    
    """
    pass
    
    def getUpper(self) -> SymbolScope: ...
    
class ExecTargetTemplateBlock(ScopeChild):
    """
    An exec block written as target-language template text -- LRM
    20.5, `target_code_exec_block` and `target_file_exec_block`.
    
    `exec kind Lang = "...";` supplies the block's implementation as a
    string of code in the named target language rather than as PSS
    statements; `exec file "name" = "...";` instead contributes the text
    to the named output file. In either form a triple-quoted string may
    hold mustache references (`{{expr}}`) to PSS attributes, which are
    substituted when code is generated (4.7.1, 20.5.2). An optional exec
    block tag (20.5.4) precedes the string.
    
    PSS Example::
    
        component pss_top {
            action my_action {
                rand bit[32] value;
    
                exec body C = \"\"\"
                    printf("value = %d\\n", {{value}});
                \"\"\";
            }
    
            exec file "out.txt" = \"\"\" generated text \"\"\";
        }
    
    Attributes:
        kind: The `exec_kind` written, or ExecKind_File for
            `exec file`. An unrecognized kind name is built as
            ExecKind_Body without a diagnostic.
        data: The template text, verbatim, with the enclosing quotes
            (`"` or `\"\"\"`) stripped
        template: The scanned template body, present only when the
            string is triple-quoted and contains special elements
            (mustache expressions or directives, 4.7.1); null otherwise
        language: The `language_identifier` (e.g. `C`, `ASM`). Empty
            for `exec file`, which names no language.
        filename: For `exec file`, the destination file name from
            `filename_string`, as raw text with the quotes stripped;
            empty otherwise
        filename_template: Scanned template for the file name, present
            only for `exec file` when the name is triple-quoted and
            holds special elements
            (20.5.3 allows mustache expressions there so that a
            per-instance file can be generated); null otherwise
        tag: The exec block tag written before the string (20.5.4), or
            null when there is none
    
    See Also:
        TemplateString, ExecBlock, ExecBlockTag, ExecKind
    
    """
    pass
    
    def getKind(self) -> int: ...
    def setKind(self, v : ExecKind | int) -> None: ...
    
    def getData(self) -> str: ...
    
    def setData(self, v : str): ...
    
    def getTemplate(self) -> TemplateString: ...
    
    def getLanguage(self) -> str: ...
    
    def setLanguage(self, v : str): ...
    
    def getFilename(self) -> str: ...
    
    def setFilename(self, v : str): ...
    
    def getFilename_template(self) -> TemplateString: ...
    
    def getTag(self) -> ExecBlockTag: ...
    
class ExportAction(ScopeChild):
    """
    Exported action declaration -- LRM 20.10, ``export_action``:
    ``export [ platform_qualifier ] action_type_identifier function_parameter_list_prototype ;``.
    
    ``export A(int x);`` makes action type ``A`` callable from a foreign
    language with the given parameter signature; each call infers an
    independent tree of actions, components and resources. This is the
    action counterpart of ``ExportFunction``, and is modelled on it: the
    same platform qualifier, a type rather than a bare name, and the
    parameter list the export declares.
    
    The parameter list belongs to the export, not to the action: an
    action has fields, and the export names (by matching name) which of
    them the foreign caller supplies, and in what order. The linker
    (TaskBuildSymbolTree) adds the export to its scope without
    visiting the parameters, so they are not mistaken for members of
    the enclosing scope.
    
    PSS Example::
    
        component comp {
            action A1 {
                rand bit mode;
                rand bit[32] val;
            }
        }
    
        package pkg {
            // Export A1, providing a mapping to field 'mode'
            export target comp::A1(bit mode);
        }
    
    Attributes:
        plat: The `platform_qualifier`, or PlatQual_None when none is
            written (the action is then available in all phases)
        target: The exported action type. Bound by the linker
            (TaskResolveRefs).
        parameters: The exported parameter signature, in source
            order. A varargs parameter, which the grammar accepts here,
            is not recorded.
    
    See Also:
        ExportFunction, Action, FunctionParamDecl
    
    """
    pass
    
    def getPlat(self) -> int: ...
    def setPlat(self, v : PlatQual | int) -> None: ...
    
    def getTarget(self) -> TypeIdentifier: ...
    
    def parameters(self) -> ListUtil[FunctionParamDecl]: ...
    def getParameters(self) -> List[FunctionParamDecl]: ...
    def getParameter(self, i: int) -> FunctionParamDecl: ...
    def addParameter(self, i: FunctionParamDecl) -> None: ...
    def numParameters(self) -> int: ...
    
class ExportFunction(ScopeChild):
    """
    Exported function declaration -- LRM 20.4.2, `export_function`:
    `export target function name ;`.
    
    Makes a function callable from the target environment, so that
    foreign code can call back into the PSS model. The function must be
    a static function with a native implementation (a
    FunctionDefinition), declared in a package or component. The
    function itself is declared elsewhere; this node only names it.
    
    PSS Example::
    
        package p {
            function int checksum(int a, int b) {
                return a ^ b;
            }
    
            export target function checksum;
        }
    
    See Also:
        ExportAction, FunctionDefinition, ExprRefName
    
    """
    pass
    
    def getPlat(self) -> int: ...
    def setPlat(self, v : PlatQual | int) -> None: ...
    
    def getName(self) -> ExprRefName: ...
    
class TemplateParamDecl(ScopeChild):
    """
    Base class for one template parameter declaration (LRM 10.3,
    `template_param_decl`).
    
    A template parameter is either a type parameter -- generic (`type T`)
    or restricted to a type category (`action A`, `struct S : base_s`) --
    or a value parameter (`int N`). Every parameter has a name and an
    optional default. The parser sets the node's location to that of the
    name, and attaches a preceding doc comment to it.
    
    PSS Example::
    
        struct my_s <type T, int N = 4> {
            T vals[N];
        }
    
        component pss_top {
            action container <action A> {
                activity { do A; }
            }
        }
    
    Attributes:
        name: The parameter's identifier. In a specialized list built by
            the linker it is a copy of the declaration's name.
    
    See Also:
        TemplateGenericTypeParamDecl, TemplateCategoryTypeParamDecl,
        TemplateValueParamDecl, TemplateParamDeclList
    
    """
    pass
    
    def getName(self) -> ExprId: ...
    
class TemplateParamExprValue(TemplateParamValue):
    """
    A template argument parsed as a constant expression (the
    `constant_expression` alternative of `template_param_value`).
    
    Supplies a value parameter. The parser builds it for anything that is
    not also a data type -- a literal or a compound expression; a bare
    name is parsed as a TemplateParamTypeValue instead. The linker resolves
    the expression at the use site and copies it into the specialization.
    
    PSS Example::
    
        struct my_s <type T, int N = 4> {
            T vals[N];
        }
    
        component pss_top {
            my_s<bit[8], 16>  s1;   // a literal
            my_s<int, 2+3>    s2;   // an expression
        }
    
    Attributes:
        value: The argument expression
    
    See Also:
        TemplateParamValue, TemplateParamTypeValue, Expr, TemplateValueParamDecl
    
    """
    pass
    
    def getValue(self) -> Expr: ...
    
class TemplateParamTypeValue(TemplateParamValue):
    """
    A template argument parsed as a data type (the `data_type`
    alternative of `template_param_value`).
    
    Supplies a type parameter, generic or category-restricted. Because a
    bare identifier parses as a type, it is also what the parser builds for
    a named constant or enum item given to a value parameter; the linker
    treats it as a value when the name resolves to one.
    
    PSS Example::
    
        struct my_s <type T, int N = 4> {
            T vals[N];
        }
        struct inner_s <type T> { T value; }
    
        component pss_top {
            my_s<bit[16]>         s1;   // bit[16]: built-in type
            my_s<inner_s<int>, 2> s2;   // inner_s<int>: user-defined type
        }
    
    Attributes:
        value: The argument's data type
    
    See Also:
        TemplateParamValue, TemplateParamExprValue, DataType,
        TemplateGenericTypeParamDecl, TemplateCategoryTypeParamDecl
    
    """
    pass
    
    def getValue(self) -> DataType: ...
    
class ExprAggrLiteral(Expr):
    """
    Base class for aggregate literals (LRM 4.8, `aggregate_literal`).
    
    An aggregate literal gives the content of a collection or struct
    value. Which subclass is built follows the syntax alone; the type
    the literal initializes comes from its context.
    
    PSS Example::
    
        {}                     // ExprAggrEmpty
        {1, 2, 3}              // ExprAggrList
        {1: true, 2: false}    // ExprAggrMap
        {.a = 1, .b = 2}       // ExprAggrStruct
    
    See Also:
        ExprAggrList, ExprAggrMap, ExprAggrStruct, ExprAggrEmpty
    
    """
    pass
    
class TypeIdentifier(Expr):
    """
    A type name, possibly `::`-qualified and with template arguments
    (LRM 10.4.1, `type_identifier`).
    
    Used wherever a type is named: a base type, a field's
    user-defined type, an `extend` target, an import path, and so
    on.
    
    PSS Example::
    
        my_type_t
        my_pkg::my_component
        addr_reg_pkg::addr_handle_t
        ::global_t                  // is_global
        my_container<int, 4>        // with template arguments
    
    Attributes:
        elems: The `::`-separated elements (at least one)
        is_global: True if the name starts with `::`, meaning the
            unnamed global package only (LRM 18.1.3)
        target: Set by the linker (TaskResolveRefs): the declaration
            of the named type; for a template type with arguments,
            its specialization. Null before linking and when
            resolution fails
    
    See Also:
        TypeIdentifierElem, DataTypeUserDefined, SymbolRefPath
    
    """
    pass
    
    def elems(self) -> ListUtil[TypeIdentifierElem]: ...
    def getElems(self) -> List[TypeIdentifierElem]: ...
    def getElem(self, i: int) -> TypeIdentifierElem: ...
    def addElem(self, i: TypeIdentifierElem) -> None: ...
    def numElems(self) -> int: ...
    
    def getTarget(self) -> SymbolRefPath: ...
    
class ExprBin(Expr):
    """
    A binary operator expression (LRM 8.1, `expression binary_operator
    expression`).
    
    Covers the arithmetic, relational, equality, logical, bitwise,
    shift and exponentiation operators (LRM 8.5). Operator precedence
    is resolved by the grammar, so the tree shape reflects it.
    
    PSS Example::
    
        a + b           // BinOp_Add
        x && y          // BinOp_LogAnd
        value << 2      // BinOp_Shl
        count == 5      // BinOp_Eq
    
    Attributes:
        lhs: Left-hand operand
        op: The operator (ExprBinOp)
        rhs: Right-hand operand
    
    See Also:
        ExprBinOp, ExprUnary, Expr
    
    """
    pass
    
    def getLhs(self) -> Expr: ...
    
    def getOp(self) -> int: ...
    def setOp(self, v : ExprBinOp | int) -> None: ...
    
    def getRhs(self) -> Expr: ...
    
class ExprBitSlice(Expr):
    """
    A bit-select or part-select `[msb : lsb]` (LRM 8.6.1, `bit_slice`).
    
    Appears only as the `slice` of a reference path, never on its own.
    Both bounds are inclusive; a single bit is written with equal
    bounds. A plain `[i]` index is not a bit slice: it is a subscript
    of an ExprMemberPathElem.
    
    PSS Example::
    
        value[7:0]      // bits 7 down to 0
        data[15:8]      // bits 15 down to 8
        flags[3:3]      // bit 3 only
    
    Attributes:
        lhs: The upper (msb) bound, before the `:`
        rhs: The lower (lsb) bound, after the `:`
    
    See Also:
        ExprSliceRange, ExprRefPathContext, ExprRefPathStatic, ExprRefPathStaticRooted
    
    """
    pass
    
    def getLhs(self) -> Expr: ...
    
    def getRhs(self) -> Expr: ...
    
class ExprBool(Expr):
    """
    A Boolean literal, `true` or `false` (`bool_literal`).
    
    PSS Example::
    
        bool flag = true;
        constraint c { enabled == false; }
    
    Attributes:
        value: True for `true`, false for `false`
    
    See Also:
        ExprNumber, ExprString
    
    """
    pass
    
class ExprCast(Expr):
    """
    An explicit type conversion `( casting_type ) expression`
    (LRM 7.12, `cast_expression`).
    
    The target may be an integer, `bool`, enum, floating-point or
    reference type, or a named type.
    
    PSS Example::
    
        bit[8] y = (bit[8])x;           // narrow to 8 bits
        int z = (int)some_enum_value;   // enum to int
    
    Attributes:
        casting_type: The type in parentheses
        expr: The expression being converted
    
    See Also:
        DataType, Expr
    
    """
    pass
    
    def getCasting_type(self) -> DataType: ...
    
    def getExpr(self) -> Expr: ...
    
class ExprCompileHas(Expr):
    """
    A `compile has ( ... )` expression (LRM 19.3, `compile_has_expr`).
    
    A compile-time Boolean that is true when the referenced name
    exists. The LRM allows a `static_ref_path` here; pssparser accepts
    any `ref_path`.
    
    PSS Example::
    
        compile if (compile has(config_pkg::PROTOCOL_VER_1_2)) {
            // ...
        }
    
    Attributes:
        ref: The reference path whose existence is tested. Null only
            after a syntax error. Not walked by the generated
            visitors: the name need not exist, so no pass may report
            it.
    
    See Also:
        ExprRefPathStatic, CompileCond
    
    """
    pass
    
    def getRef(self) -> ExprRefPath: ...
    
class ExprCond(Expr):
    """
    The conditional operator `cond ? a : b` (LRM 8.5.8,
    `conditional_expression`).
    
    Evaluates to `true_e` when the condition is true, else to
    `false_e`.
    
    PSS Example::
    
        int result = (x > 10) ? x : 10;
        bit[8] value = flag ? 8'hFF : 8'h00;
    
    Attributes:
        cond_e: The condition (`cond_predicate`), before the `?`
        true_e: The expression after the `?`
        false_e: The expression after the `:`
    
    See Also:
        ExprBin, ExprBool
    
    """
    pass
    
    def getCond_e(self) -> Expr: ...
    
    def getTrue_e(self) -> Expr: ...
    
    def getFalse_e(self) -> Expr: ...
    
class ExprDomainOpenRangeList(Expr):
    """
    A value domain `in [ ... ]` in a type or path declaration
    (LRM 7.2.1, `domain_open_range_list`).
    
    Restricts the values of an integer or enum type (`int in [...]`,
    `my_enum in [...]`), and also gives the index range of a
    component path element or bind target. It is not used by the
    `in` operator in expressions, which builds an ExprOpenRangeList.
    
    PSS Example::
    
        rand bit[8] in [1..10, 20, 30..40] value;
        rand int in [..0, 100..] limit;
    
    Attributes:
        values: The ranges and single values, in source order
    
    See Also:
        ExprDomainOpenRangeValue, ExprOpenRangeList, DataTypeInt, DataTypeUserDefined
    
    """
    pass
    
    def values(self) -> ListUtil[ExprDomainOpenRangeValue]: ...
    def getValues(self) -> List[ExprDomainOpenRangeValue]: ...
    def getValue(self, i: int) -> ExprDomainOpenRangeValue: ...
    def addValue(self, i: ExprDomainOpenRangeValue) -> None: ...
    def numValues(self) -> int: ...
    
class ExprDomainOpenRangeValue(Expr):
    """
    One item of a value domain (LRM 7.2.1, `domain_open_range_value`):
    a single value, a closed range `a..b`, or a range open at one end
    (`a..` or `..b`).
    
    PSS Example::
    
        int in [1..10] a;    // lhs=1, rhs=10, single=false
        int in [42] b;       // lhs=42, rhs=null, single=true
        int in [5..] c;      // lhs=5, rhs=null, single=false
        int in [..5] d;      // lhs=null, rhs=5, single=false
    
    Attributes:
        single: True for a single value (no `..`), false for any range
        lhs: The single value, or the lower bound; null for `..b`
        rhs: The upper bound; null for a single value and for `a..`
    
    See Also:
        ExprDomainOpenRangeList, ExprOpenRangeValue
    
    """
    pass
    
    def getLhs(self) -> Expr: ...
    
    def getRhs(self) -> Expr: ...
    
class ExprFloatLiteral(Expr):
    """
    Represents a floating-point literal value.
    
    PSS 3.1 §4.6 admits two spellings, both modelled here: a plain
    decimal form (`1.5`) and a scientific form (`1.5e-3`). They differ
    only in notation, not in value, so `is_scientific` exists to let a
    consumer reproduce the source spelling rather than to change how the
    value is interpreted.
    
    Both the parsed value and the source text are kept. `value` is what
    a consumer evaluates; `image` is what it needs to reproduce the
    source, and the two are not interchangeable. Digit separators and
    trailing zeros do not survive a round trip through a double, and not
    every decimal fraction is exactly representable, so `image` is the
    authority on spelling and `value` on magnitude.
    
    PSS Example::
    
        float32 a = 1.5;
        float64 b = 1.0e-9;
        float64 c = 1_000.5;
    
    Attributes:
        value: Parsed value, with digit separators removed
        image: Original text representation from source, separators included
        is_scientific: True when written in exponent notation
    
    See Also:
        ExprNumber, ExprUnsignedNumber
    
    """
    pass
    
    def getImage(self) -> str: ...
    
    def setImage(self, v : str): ...
    
class ExprHierarchicalId(Expr):
    """
    A dotted path of member elements (Annex B, `hierarchical_id`:
    `member_path_elem { . member_path_elem }`).
    
    Each element is a name with optional call arguments and
    subscripts. It is the path part of a context reference
    (ExprRefPathContext.hier_id) and the member part of a
    statically-rooted one (ExprRefPathStaticRooted.leaf). Package and
    type qualification with `::` is not part of it; see
    ExprRefPathStatic and TypeIdentifier.
    
    PSS Example::
    
        comp.sub_c.field
        regs.ctrl.write_val(1)
        arr[i].data
    
    Attributes:
        elems: The path elements, in source order (at least one)
    
    See Also:
        ExprMemberPathElem, ExprRefPathContext, ExprRefPathStaticRooted
    
    """
    pass
    
    def elems(self) -> ListUtil[ExprMemberPathElem]: ...
    def getElems(self) -> List[ExprMemberPathElem]: ...
    def getElem(self, i: int) -> ExprMemberPathElem: ...
    def addElem(self, i: ExprMemberPathElem) -> None: ...
    def numElems(self) -> int: ...
    
class ExprId(Expr):
    """
    An identifier (LRM 4.2 and 4.3, `identifier`): one name as written in
    the source.
    
    An escaped identifier (`\\` followed by any non-whitespace
    characters) names the same thing as the unescaped spelling (LRM
    4.3), so the backslash is not kept in `id`; `is_escaped` records
    that it was there.
    
    PSS Example::
    
        my_variable
        field_name
        \\begin          // id is "begin", is_escaped is true
    
    Attributes:
        id: The name, without the leading backslash of an escaped
            identifier
        is_escaped: True if the identifier was written escaped
        location: Source location of the identifier; the extent
            covers the source text, backslash included. Unset (zero)
            for an identifier the builder or linker synthesizes
            rather than reads from the source
        decl: The declaration this identifier was bound to by the
            linker, where the linker records one: every element of
            a member path, and every element of a qualified type
            name. Null for a declaration's own name, for a name the
            linker did not bind, and before linking. Non-owning; it
            may point into the symbol tree or into a template
            specialization. pssparser.refs normalizes it.
    
    See Also:
        ExprHierarchicalId, ExprRefPath, ExprMemberPathElem, ExprRefName
    
    """
    pass
    
    def getId(self) -> str: ...
    
    def setId(self, v : str): ...
    
    def getLocation(self) -> 'Location': ...
    
    def getDecl(self) -> ScopeChild: ...
    
class ExprIn(Expr):
    """
    The set membership operator `in` (LRM 8.5.9, `in_expression`).
    
    True when the left-hand value is in the right-hand side. Two forms
    exist:
    
    * Range-list form, `x in [1..10, 20]`: `rhs` holds the ranges and
      `collection` is null.
    * Collection form, `x in comp.some_list`: `collection` holds the
      collection expression and `rhs` is an empty list.
    
    PSS Example::
    
        constraint c { x in [1..10, 20, 30..40]; }
        constraint d { y in allowed_values; }
    
    Attributes:
        lhs: The value tested for membership
        rhs: The `open_range_list` in brackets; present but empty in
            the collection form
        collection: The `collection_expression`; null in the
            range-list form
    
    See Also:
        ExprOpenRangeList, ExprOpenRangeValue
    
    """
    pass
    
    def getLhs(self) -> Expr: ...
    
    def getRhs(self) -> ExprOpenRangeList: ...
    
    def getCollection(self) -> Expr: ...
    
class ExprMemberCall(Expr):
    """
    A method call on a receiver that is not a name: a string or
    aggregate literal (LRM Ex. 10). A call on a name is an
    ExprRefPathContext, whose path elements carry the calls.
    
    PSS Example::
    
        "a,b".split(",")            // receiver ExprString
        "a,b".split(",").size()     // two members, chained
    
    Attributes:
        receiver: The literal the first member is applied to
        members: The members applied in order, each with its params
    
    See Also:
        ExprMemberPathElem, ExprRefPathContext
    
    """
    pass
    
    def getReceiver(self) -> Expr: ...
    
    def members(self) -> ListUtil[ExprMemberPathElem]: ...
    def getMembers(self) -> List[ExprMemberPathElem]: ...
    def getMember(self, i: int) -> ExprMemberPathElem: ...
    def addMember(self, i: ExprMemberPathElem) -> None: ...
    def numMembers(self) -> int: ...
    
class ExprMemberPathElem(Expr):
    """
    One element of a member path (Annex B, `member_path_elem`): a
    name, optionally called with arguments, optionally followed by
    index or slice subscripts.
    
    PSS Example::
    
        field                   // name only
        method(a, b)            // params set
        arr[i]                  // one subscript
        mem[0][1..3]            // an index and an ExprSliceRange
    
    Attributes:
        id: The element's name
        params: The call arguments (`function_parameter_list`); null
            when the element is not a call, an empty list for `f()`
        subscript: One entry per bracketed subscript, in order: the
            index expression, or an ExprSliceRange for a `..` slice.
            Empty when there is none
        target: Set by the linker (TaskResolveRefs): the index of
            the member in the scope it was found in; -2 when it
            resolved to a built-in method rather than a member; -1
            when unresolved, and for the first element of a context
            path, which is resolved by ExprRefPath.target instead
        super: Set by the linker with target: how many base types
            were crossed to find the member (0 for the type itself);
            -1 when unresolved
        string_method_id: Not set by the parser or the linker;
            always StringMethod_None
    
    See Also:
        ExprHierarchicalId, ExprId, MethodParameterList, ExprSliceRange
    
    """
    pass
    
    def getId(self) -> ExprId: ...
    
    def getParams(self) -> MethodParameterList: ...
    
    def subscript(self) -> ListUtil[Expr]: ...
    def getSubscriptList(self) -> List[Expr]: ...
    def getSubscript(self, i: int) -> Expr: ...
    def addSubscript(self, i: Expr) -> None: ...
    def numSubscript(self) -> int: ...
    
    def getString_method_id(self) -> int: ...
    def setString_method_id(self, v : StringMethodId | int) -> None: ...
    
class ExprNull(Expr):
    """
    The `null` literal (LRM 7.10, `null_ref`).
    
    The value of a reference that refers to nothing; it may be
    assigned to or compared with a reference-typed attribute.
    
    PSS Example::
    
        ref my_action_t r = null;
        if (r == null) { ... }
    
    See Also:
        ExprBool, ExprNumber
    
    """
    pass
    
class ExprNumber(Expr):
    """
    Base class for integer literals (LRM 4.6.1, `integer_number`).
    
    Never built itself: a literal is an ExprUnsignedNumber, or an
    ExprSignedNumber when written with the `s` base modifier. A
    leading `-` is not part of the literal; `-10` is an ExprUnary
    applied to an ExprUnsignedNumber. Floating-point literals are
    ExprFloatLiteral, which does not derive from this class.
    
    PSS Example::
    
        42              // decimal
        0x2A            // hexadecimal
        8'hFF           // sized, based
        4'sb1010        // signed based (ExprSignedNumber)
    
    See Also:
        ExprSignedNumber, ExprUnsignedNumber, ExprFloatLiteral
    
    """
    pass
    
class ExprOpenRangeList(Expr):
    """
    The bracketed list on the right of the `in` operator (LRM 8.5.9,
    `open_range_list`).
    
    Each item is a single value or a range. The same item class is
    also used, outside this list, for `dist` items and covergroup
    bins ranges.
    
    PSS Example::
    
        constraint c { x in [1..10, 20, 30..40]; }
    
    Attributes:
        values: The items, in source order; empty for the collection
            form of ExprIn
    
    See Also:
        ExprOpenRangeValue, ExprIn, ExprDomainOpenRangeList
    
    """
    pass
    
    def values(self) -> ListUtil[ExprOpenRangeValue]: ...
    def getValues(self) -> List[ExprOpenRangeValue]: ...
    def getValue(self, i: int) -> ExprOpenRangeValue: ...
    def addValue(self, i: ExprOpenRangeValue) -> None: ...
    def numValues(self) -> int: ...
    
class ExprOpenRangeValue(Expr):
    """
    A single value or a `lo .. hi` range (LRM 8.5.9,
    `open_range_value`).
    
    Used in an ExprOpenRangeList, in a `dist` item
    (ConstraintStmtDist), and for the value ranges of covergroup bins
    (CoverpointBins), where a range may also be open at one end.
    
    PSS Example::
    
        x in [5];           // lhs=5, rhs=null
        x in [1..10];       // lhs=1, rhs=10
        bins hi = [200..];  // lhs=200, rhs=null (bins only)
        bins lo = [..10];   // lhs=null, rhs=10 (bins only)
    
    Attributes:
        lhs: The single value or lower bound; null only for a bins
            range written `..hi`
        rhs: The upper bound; null for a single value and for a
            bins range written `lo..`
    
    See Also:
        ExprOpenRangeList, ExprIn, ExprDomainOpenRangeValue
    
    """
    pass
    
    def getLhs(self) -> Expr: ...
    
    def getRhs(self) -> Expr: ...
    
class ExprRefName(Expr):
    """
    A reference written as a single name, where the grammar has no
    path: a symbol call, a function export, a struct-literal field,
    a coverpoint or bins target, a covergroup port map, a bind field
    or component path element, an annotation parameter, a template
    assignment.
    
    It exists to hold a binding (symbol-resolution plan WS3.2): those
    names used to be bare ExprIds, which have nowhere to record what
    they resolve to, so nothing could check that they had been
    resolved at all.
    
    PSS Example::
    
        s s1 = {.a = 1};    // `a` is an ExprRefName
        export target function do_it;   // so is `do_it`
    
    Attributes:
        id: The name as written
        target: What it resolves to, set by the linker
            (TaskResolveRefs); null until resolved, or when its
            resolution belongs to a later pass
        ctx_unknown: The name is resolved in a context the linker
            cannot yet compute (a struct literal whose type is not
            known from its syntax, WS8.9). Set by TaskResolveRefs;
            false otherwise
    
    See Also:
        ExprId, ExprRefPathContext, SymbolRefPath
    
    """
    pass
    
    def getId(self) -> ExprId: ...
    
    def getTarget(self) -> SymbolRefPath: ...
    
class ExprRefPath(Expr):
    """
    Base class for references to named things in expressions
    (Annex B, `ref_path`).
    
    Never built itself. The subclass follows the syntax: a path that
    starts with a plain name or `super.` is an ExprRefPathContext
    (ExprRefPathSuper for `super.`); one that starts with a `::`
    qualified name is an ExprRefPathStatic, or an
    ExprRefPathStaticRooted when a member path follows the qualified
    name or its last element is called or subscripted.
    
    PSS Example::
    
        comp.field              // ExprRefPathContext
        super.parent_field      // ExprRefPathSuper
        my_pkg::MAX_SIZE        // ExprRefPathStatic
        my_pkg::f(1).x          // ExprRefPathStaticRooted
    
    Attributes:
        target: Set by the linker (TaskResolveRefs). For a context
            path, the declaration the first element names; for a
            static path, the declaration the whole path names. Not
            set on an ExprRefPathStaticRooted, whose root carries
            it. Null before linking and when resolution fails
    
    See Also:
        ExprRefPathContext, ExprRefPathStatic, ExprRefPathStaticRooted
        ExprRefPathSuper, SymbolRefPath
    
    """
    pass
    
    def getTarget(self) -> SymbolRefPath: ...
    
class TypeIdentifierElem(Expr):
    """
    One element of a qualified type name (LRM 10.4.1,
    `type_identifier_elem`): an identifier with optional template
    arguments.
    
    PSS Example::
    
        my_pkg              // id only
        my_container<int>   // id with params
    
    Attributes:
        id: The element's name
        params: The template arguments (`template_param_value_list`);
            null when none are written
    
    See Also:
        TypeIdentifier, ExprRefPathStatic, ExprId, TemplateParamValueList
    
    """
    pass
    
    def getId(self) -> ExprId: ...
    
    def getParams(self) -> TemplateParamValueList: ...
    
class ExprSliceRange(Expr):
    """
    A `[ lower .. upper ]` range used to select a sub-range of a
    collection or a string.
    
    Annex B defines two rules with *identical* syntax:
    
    * ``array_slice  ::= expression .. expression | expression .. | .. expression``
    * ``string_slice ::= expression .. expression | expression .. | .. expression``
    
    Which one a given range is cannot be decided while parsing -- it
    depends on the type of the operand being sliced, which is only
    known after name resolution. A single neutral node is therefore the
    only shape the builder can honestly produce; consumers decide
    from the operand's type (the linker records no classification).
    (Contrast ``ExprBitSlice``, which is spelled ``[msb : lsb]``
    and *is* syntactically distinct.)
    
    Either endpoint may be absent, but not both -- ``[..]`` is not a
    legal slice. An absent endpoint means "to the end of the
    collection" in that direction.
    
    The node appears as an element of ``ExprMemberPathElem.subscript``.
    A subscript that is a slice yields the *collection* type, whereas a
    plain index subscript yields the *element* type -- consumers that
    walk subscripts must distinguish the two.
    
    PSS Example::
    
        unique arr[2..5];       // array slice: elements 2 through 5
        string tail = s[3..];   // string slice: from index 3 onward
        string head = s[..3];   // string slice: up to index 3
    
    Attributes:
        lower: Left index, or null when written as ``[..upper]``
        upper: Right index, or null when written as ``[lower..]``
    
    See Also:
        ExprBitSlice, ExprMemberPathElem
    
    """
    pass
    
    def getLower(self) -> Expr: ...
    
    def getUpper(self) -> Expr: ...
    
class ExprString(Expr):
    """
    A string literal (LRM 4.7, `string_literal`), double-quoted or
    triple-quoted.
    
    `value` is the source text between the quotes; escape sequences
    are kept as written, not interpreted. A triple-quoted string that
    contains template special elements is built as the subclass
    ExprTemplateString instead.
    
    PSS Example::
    
        string msg = "Hello, World!\\n";        // is_raw = false
        string doc = \"\"\"Line one
        Line two\"\"\";                           // is_raw = true
    
    Attributes:
        value: The text between the quotes, unprocessed
        is_raw: True for a triple-quoted (`\"\"\"`) string, false for a
            double-quoted one
    
    See Also:
        ExprBool, ExprNumber, ExprTemplateString
    
    """
    pass
    
    def getValue(self) -> str: ...
    
    def setValue(self, v : str): ...
    
class TypedefDeclaration(ScopeChild):
    """
    Type alias declaration (`typedef_declaration`, LRM 7.11).
    
    Declares a new name for an existing data type. A typedef of a scalar
    or aggregate type is itself a scalar or aggregate type. The name is
    registered in the enclosing scope by the linker
    (TaskBuildSymbolTree), so uses resolve to this node.
    
    PSS Example::
    
        typedef bit[8] byte_t;
        typedef list<byte_t> bytes_t;
    
    See Also:
        DataType, DataTypeUserDefined
    
    """
    pass
    
    def getName(self) -> ExprId: ...
    
    def getType(self) -> DataType: ...
    
class ExprUnary(Expr):
    """
    A unary operator applied to one operand (LRM 8.1,
    `unary_operator expression`).
    
    Covers negation, logical and bitwise NOT, and the reduction
    operators `&`, `|` and `^` (LRM 8.5.6).
    
    PSS Example::
    
        -x              // UnaryOp_Minus
        !flag           // UnaryOp_LogNot
        ~bits           // UnaryOp_BitNeg
        &vector         // UnaryOp_BitAnd (reduction)
    
    Attributes:
        op: The operator (ExprUnaryOp)
        rhs: The operand
    
    See Also:
        ExprUnaryOp, ExprBin, Expr
    
    """
    pass
    
    def getOp(self) -> int: ...
    def setOp(self, v : ExprUnaryOp | int) -> None: ...
    
    def getRhs(self) -> Expr: ...
    
class ExtendEnum(ScopeChild):
    """
    Enum extension declaration for adding values to existing enums
    (`extend enum`, LRM 17.2.4).
    
    Represents an 'extend' statement that adds new enumerator values
    to an existing enum type. Enum extensions allow adding values
    without modifying the original enum definition. The linker
    (TaskApplyTypeExtensions) resolves `target` and adds the items to
    the enum's SymbolEnumScope.
    
    PSS Example::
    
        enum status {
            OK,
            ERROR
        }
    
        extend enum status {
            WARNING,
            INFO
        }
    
    Attributes:
        target: The enum type named (`type_identifier`). Its target is
            set by the linker (TaskApplyTypeExtensions)
        items: The enumerators added, in source order; each one's
            location is in the extension, not in the enum declaration
    
    See Also:
        ExtendType, EnumDecl, EnumItem, SymbolEnumScope
    
    """
    pass
    
    def getTarget(self) -> TypeIdentifier: ...
    
    def items(self) -> ListUtil[EnumItem]: ...
    def getItems(self) -> List[EnumItem]: ...
    def getItem(self, i: int) -> EnumItem: ...
    def addItem(self, i: EnumItem) -> None: ...
    def numItems(self) -> int: ...
    
class ActionHandleField(NamedScopeChild):
    """
    Action or monitor handle declared in an activity or a monitor body
    (`action_handle_declaration`, LRM 11.3.1).
    
    Built for each `action_instantiation` of a handle declaration in an
    action activity, a monitor body (`monitor_field_declaration`) or a
    monitor activity, including the PSS 3.1 initializer list and array
    handles. A handle declared directly in an *action* body
    (`A a;`) parses as a data declaration and is a Field instead.
    
    A *monitor* handle (``m1 h1;``) also builds this class, despite the
    name. The two declarations are syntactically identical --
    ``type_identifier identifier ;`` -- so the parser cannot
    distinguish them; which kind of handle it is follows from resolving
    ``type``, and is known only after linking.
    
    PSS Example::
    
        action top {
            activity {
                sub_a a1 {.size = 4};   // single handle, initializer
                sub_a arr[2];           // handle array
                a1;
                arr[0];
            }
        }
    
    See Also:
        Field, ActionFieldInitializer, ActivityActionHandleTraversal,
        DataTypeUserDefined
    
    """
    pass
    
    def getType(self) -> DataType: ...
    
    def initializers(self) -> ListUtil[ActionFieldInitializer]: ...
    def getInitializers(self) -> List[ActionFieldInitializer]: ...
    def getInitializer(self, i: int) -> ActionFieldInitializer: ...
    def addInitializer(self, i: ActionFieldInitializer) -> None: ...
    def numInitializers(self) -> int: ...
    
class ActivityBindStmt(ActivityStmt):
    """
    Explicitly binds flow-object reference fields -- LRM 11.9,
    `activity_bind_stmt`.
    
    `bind x y;` or `bind x { y, z };` states that the input and output
    fields named reference the same flow object: the output of one action
    is the input of another. The bound fields must be of the same object
    type and statically bound to the same pool; the order in which they
    are listed does not matter.
    
    PSS Example::
    
        component pss_top {
            buffer data_buf { }
            pool data_buf data_p;
            bind data_p *;
    
            action producer { output data_buf out_d; }
            action consumer { input data_buf in_d; }
    
            action top {
                producer prod;
                consumer cons;
                activity {
                    prod;
                    cons;
                    bind prod.out_d cons.in_d;
                }
            }
        }
    
    Attributes:
        lhs: The first `hierarchical_id`, as a reference path to a flow-object
            reference field (`prod.out_d`).
        rhs: The remaining reference paths: one element for the single form,
            one per item of the braced `hierarchical_id_list` otherwise.
    
    See Also:
        FieldRef, ExprRefPathContext
    
    """
    pass
    
    def getLhs(self) -> ExprRefPathContext: ...
    
    def rhs(self) -> ListUtil[ExprRefPathContext]: ...
    def getRhs(self) -> List[ExprRefPathContext]: ...
    def getRh(self, i: int) -> ExprRefPathContext: ...
    def addRh(self, i: ExprRefPathContext) -> None: ...
    def numRhs(self) -> int: ...
    
class ActivityConstraint(ActivityStmt):
    """
    A constraint written among the activity statements --
    `constraint constraint_set`, `activity_constraint_stmt` (LRM 11.2).
    
    Its position in the statement order is what distinguishes it from a
    constraint in the action body, so it is a statement node rather than a
    ConstraintBlock. It constrains the action's fields and the handles
    traversed in the activity; names in it are resolved by the linker
    (TaskResolveRefs) in the enclosing activity scope.
    
    PSS Example::
    
        action top {
            rand bit[8] limit;
            A a1;
            activity {
                a1;
                constraint { a1.x < limit; }
                constraint a1.y == 2;
            }
        }
    
    Attributes:
        constraint: The `constraint_set`: a ConstraintScope holding the
            statements of a braced block, or the single constraint statement
            of the unbraced form.
    
    See Also:
        ConstraintStmt, ConstraintScope, ConstraintBlock, MonitorConstraint
    
    """
    pass
    
    def getConstraint(self) -> ConstraintStmt: ...
    
class ActivityJoinSpecBranch(ActivityJoinSpec):
    """
    `join_branch(L1, L2, ...)` -- LRM 11.3.6, `activity_join_branch`.
    
    The statement following the block is scheduled after the listed
    statements have completed; the others are not waited for. Each label
    must be that of a top-level statement of the block the specification
    applies to. A label on an action-array traversal waits for every
    element.
    
    PSS Example::
    
        activity {
            parallel join_branch(L1, L2) {
                L1: do A;
                L2: do B;
                do C;           // not waited for
            }
            do D;               // after L1 and L2
        }
    
    Attributes:
        branches: One single-element reference path per `label_identifier`,
            in source order. Resolved by the linker (TaskResolveRefs) to the
            labeled statements.
    
    See Also:
        ActivityJoinSpec, ActivityParallel, ActivitySchedule
    
    """
    pass
    
    def branches(self) -> ListUtil[ExprRefPathContext]: ...
    def getBranches(self) -> List[ExprRefPathContext]: ...
    def getBranche(self, i: int) -> ExprRefPathContext: ...
    def addBranche(self, i: ExprRefPathContext) -> None: ...
    def numBranches(self) -> int: ...
    
class ActivityJoinSpecFirst(ActivityJoinSpec):
    """
    `join_first(N)` -- LRM 11.3.6, `activity_join_first`.
    
    The statement following the block has a run-time dependency on the
    first N of the block's statements to complete execution, and no
    scheduling dependency on them. Unlike `join_select`, which statements
    count is decided by which finish first, not chosen at solve time. N is
    an integer known at solve time; 0 is equivalent to `join_none`.
    
    PSS Example::
    
        activity {
            parallel join_first(1) {
                do A;
                do B;
            }
            do C;               // after whichever of A, B completes first
        }
    
    Attributes:
        count: The `expression` N: how many statements to wait for.
    
    See Also:
        ActivityJoinSpec, ActivityJoinSpecSelect, ActivityParallel
    
    """
    pass
    
    def getCount(self) -> Expr: ...
    
class ActivityJoinSpecNone(ActivityJoinSpec):
    """
    `join_none` -- LRM 11.3.6, `activity_join_none`.
    
    The statement following the block has no scheduling dependency on the
    statements in the block: it may start without waiting for any of them.
    
    PSS Example::
    
        activity {
            parallel join_none {
                do A;
                do B;
            }
            do C;               // need not wait for A or B
        }
    
    See Also:
        ActivityJoinSpec, ActivityJoinSpecFirst, ActivityParallel
    
    """
    pass
    
class ActivityJoinSpecSelect(ActivityJoinSpec):
    """
    `join_select(N)` -- LRM 11.3.6, `activity_join_select`.
    
    The statement following the block is scheduled after N of the block's
    top-level statements, selected randomly, have completed. Each element
    of a traversed action array counts as a separate statement. N is an
    integer known at solve time; 0 is equivalent to `join_none`.
    
    PSS Example::
    
        activity {
            parallel join_select(1) {
                do A;
                do B;
            }
            do C;               // after one of A, B (chosen randomly)
        }
    
    Attributes:
        count: The `expression` N: how many statements are selected.
    
    See Also:
        ActivityJoinSpec, ActivityJoinSpecFirst, ActivityParallel
    
    """
    pass
    
    def getCount(self) -> Expr: ...
    
class ActivityLabeledStmt(ActivityStmt):
    """
    Base class of the activity statements that take an optional
    `label :` prefix but do not introduce a scope.
    
    Its subclasses are the two traversals and `super`. Blocks and compound
    statements carry their label on ActivityLabeledScope instead. A label
    names the statement for scheduling constraints, `join_branch` and
    hierarchical references (LRM 11.8); the linker (TaskBuildSymbolTree)
    registers it in the enclosing named sub-activity.
    
    PSS Example::
    
        activity {
            L1: do A;
            L2: a1;
        }
    
    Attributes:
        label: The label identifier, or null when the statement has no label.
    
    See Also:
        ActivityActionHandleTraversal, ActivityActionTypeTraversal, ActivitySuper, ActivityLabeledScope
    
    """
    pass
    
    def getLabel(self) -> ExprId: ...
    
class ActivitySymbolCall(ActivityStmt):
    """
    Inlines a symbol at this point in the activity -- ``symbol_call``.
    
    The call is not a function call: the symbol's statements are spliced
    into the activity where the call appears. The AST keeps the call rather
    than the expansion, so a consumer sees what the source wrote.
    
    ``target`` names the symbol. It is not resolved here -- the symbol may
    be declared after the call -- so the reference is left to the linker.
    A symbol activated without an argument list (`s;`) is not a call: it
    parses as an ActivityActionHandleTraversal.
    
    PSS Example::
    
        activity {
            two_of(1);
        }
    
    Attributes:
        target: The `symbol_identifier` being called. Its target is set by
            the linker (TaskResolveRefs) to the SymbolDeclaration. A name that
            is unknown or not a symbol is reported and left unresolved; a call
            with the wrong number of arguments is reported but still resolved.
        params: The call arguments, in order; empty for `s()`.
    
    See Also:
        SymbolDeclaration, ExprRefName, ActivityActionHandleTraversal
    
    """
    pass
    
    def getTarget(self) -> ExprRefName: ...
    
    def params(self) -> ListUtil[Expr]: ...
    def getParams(self) -> List[Expr]: ...
    def getParam(self, i: int) -> Expr: ...
    def addParam(self, i: Expr) -> None: ...
    def numParams(self) -> int: ...
    
class ConstraintScope(ConstraintStmt):
    """
    A sequence of constraint statements.
    
    The base of every construct with a constraint body:
    ConstraintBlock and the `foreach`, `forall` and implication
    statements. Used on its own for each branch of a ConstraintStmtIf
    and for a brace block that is the whole body of a node outside a
    type's constraint declarations: an in-line `with { ... }` on an
    action traversal, an activity `constraint { ... }` statement, or
    a `randomize ... with { ... }`. The statements are kept in source
    order; each one's `index` is its position in `constraints`.
    
    PSS Example::
    
        action sub {
            rand bit[8] value1, value2;
        }
    
        action top {
            activity {
                do sub with {       // the with-body is a ConstraintScope
                    value1 > 0;
                    value1 + value2 == 50;
                };
            }
        }
    
    Attributes:
        endLocation: Source location of the end of the scope
            (inherited from ScopeChild)
        constraints: Ordered list of constraint statements within
            this scope
    
    See Also:
        ConstraintBlock, ConstraintStmt, ConstraintStmtIf
    
    """
    pass
    
    def constraints(self) -> ListUtil[ConstraintStmt]: ...
    def getConstraints(self) -> List[ConstraintStmt]: ...
    def getConstraint(self, i: int) -> ConstraintStmt: ...
    def addConstraint(self, i: ConstraintStmt) -> None: ...
    def numConstraints(self) -> int: ...
    
class ConstraintStmtDefault(ConstraintStmt):
    """
    Default value constraint, `default hid == constant_expression;`
    (LRM 13.1.11).
    
    Fixes a random attribute to a constant value unless the default
    is disabled for that attribute by a `default disable` constraint.
    While active, a default value constraint has the same meaning as
    the corresponding equality: it shall hold, and a conflict with
    another constraint is a contradiction (unlike a soft constraint,
    which would be discarded). When several defaults apply to one
    attribute, one from a higher-level containing context overrides
    one from a lower level, a derived type overrides its base, and
    within one type a later default overrides an earlier one.
    
    PSS Example::
    
        action network_packet {
            rand bit[16] packet_size;
            rand bit[8] priority;
    
            constraint defaults_c {
                default packet_size == 64;
                default priority == 0;
            }
        }
    
        action jumbo_packet : network_packet {
            constraint jumbo_c {
                default disable packet_size;
                packet_size > 1500;
            }
        }
    
    Attributes:
        hid: The attribute receiving the default value (a
            `hierarchical_id`)
        expr: The default value, a constant expression
    
    See Also:
        ConstraintStmtDefaultDisable, ConstraintStmtSoft, ExprRefPathContext
    
    """
    pass
    
    def getHid(self) -> ExprRefPathContext: ...
    
    def getExpr(self) -> Expr: ...
    
class ConstraintStmtDefaultDisable(ConstraintStmt):
    """
    Default disable constraint, `default disable hid;`
    (LRM 13.1.11).
    
    Removes the default value constraints on the designated
    attribute, wherever they were declared. Applied to an attribute
    of an aggregate type, it disables the defaults on every random
    attribute under it.
    
    PSS Example::
    
        action base_transfer {
            rand bit[16] addr;
            rand bit[8] data;
    
            constraint defaults_c {
                default addr == 0x1000;
                default data == 0;
            }
        }
    
        action special_transfer : base_transfer {
            constraint override_defaults_c {
                default disable addr;          // Drop the base default
                addr in [0x2000..0x2FFF];      // Use this range instead
            }
        }
    
    Attributes:
        hid: The attribute whose default is being disabled (a
            `hierarchical_id`)
    
    See Also:
        ConstraintStmtDefault, ExprRefPathContext
    
    """
    pass
    
    def getHid(self) -> ExprRefPathContext: ...
    
class ConstraintStmtDist(ConstraintStmt):
    """
    Distribution directive: a weighted set of values for an expression
    (LRM 13.1.13, `dist_directive`).
    
    A `dist` directive guides the solver: in the absence of
    conflicting constraints, the target expression takes a value in
    the distribution list, with probability proportional to each
    value's weight. It is a kind of soft constraint, with lower
    priority than every other soft constraint, so other constraints
    may force the target outside the list. It is a statement, not an
    expression -- unlike `in` (ExprIn), it does not itself require
    membership.
    
    PSS Example::
    
        action A {
            rand bit[8] kind;
    
            constraint c {
                dist kind in [0 := 10, 1 := 20, 2..7 :/ 30];
            }
        }
    
    Attributes:
        lhs: The expression being distributed
        items: The weighted values and ranges, in source order
    
    See Also:
        DistItem, DistWeight, ExprIn, ConstraintStmtSoft
    
    """
    pass
    
    def getLhs(self) -> Expr: ...
    
    def items(self) -> ListUtil[DistItem]: ...
    def getItems(self) -> List[DistItem]: ...
    def getItem(self, i: int) -> DistItem: ...
    def addItem(self, i: DistItem) -> None: ...
    def numItems(self) -> int: ...
    
class ConstraintStmtExpr(ConstraintStmt):
    """
    Expression constraint (LRM 13.1.5, `expression_constraint_item`).
    
    A Boolean expression that shall hold. This is the most common
    form of constraint: relations, logical operations, set membership
    (`in`) and calls to generic constraints.
    
    PSS Example::
    
        action transfer {
            rand bit[16] addr;
            rand bit[8] size;
    
            constraint valid_transfer_c {
                addr >= 0x1000;                    // Simple relational
                addr + size <= 0xFFFF;             // Arithmetic expression
                size in [1, 2, 4, 8];              // Set membership
                (addr & 0x3) == 0;                 // Address alignment
            }
        }
    
    Attributes:
        expr: The Boolean expression that must hold (without its `;`)
    
    See Also:
        Expr, ConstraintStmt, ConstraintBlock
    
    """
    pass
    
    def getExpr(self) -> Expr: ...
    
class ConstraintStmtField(ConstraintStmt):
    """
    A variable declared by a `foreach` or `forall` constraint.
    
    Represents the iterator or index variable of a
    ConstraintStmtForeach, or the iterator of a ConstraintStmtForall.
    The variable is visible only within the statement's body, where it
    is found through the statement's ConstraintSymbolScope.
    
    Where the node lives differs between the two statements. A
    `foreach` references its variables from `it` and `idx`. A
    `forall` owns its iterator as entry 0 of its own `constraints`,
    ahead of the body, so a consumer walking a forall's constraints
    meets the iterator first.
    
    PSS Example::
    
        constraint iteration_c {
            foreach (e : items[idx]) {
                // 'e' and 'idx' are ConstraintStmtFields
                e != idx;
            }
        }
    
    Attributes:
        name: The name of the variable, with its source location
        type: The variable's data type. For a `forall` iterator,
            the quantified type as written. For a `foreach`
            iterator, null after parsing and set by the linker
            (TaskResolveRefs) to the collection's element type,
            when known. Always null for a `foreach` index.
    
    See Also:
        ConstraintStmtForeach, ConstraintStmtForall, ConstraintSymbolScope
    
    """
    pass
    
    def getName(self) -> ExprId: ...
    
    def getType(self) -> DataType: ...
    
class ConstraintStmtIf(ConstraintStmt):
    """
    Conditional constraint (LRM 13.1.7, `if_constraint_item`).
    
    When the condition is true, the constraints of the first branch
    shall hold; otherwise those of the `else` branch, if one was
    written. Like every constraint, the relation is bidirectional:
    the solver may choose the condition's variables to satisfy a
    branch.
    
    Each branch is a ConstraintScope, even when written as a single
    unbraced constraint; the true branch has `index` 0 and the false
    branch `index` 1.
    
    PSS Example::
    
        action memory_access {
            rand bit is_read;
            rand bit[32] addr;
            rand bit[8] data;
    
            constraint access_type_c {
                if (is_read) {
                    addr in [0x0000..0x0FFF];  // ROM region
                } else {
                    addr in [0x1000..0x1FFF];  // RAM region
                    data != 0;                 // Write non-zero
                }
            }
        }
    
    Attributes:
        cond: The Boolean condition expression
        true_c: Constraints that hold when the condition is true
        false_c: Constraints that hold when the condition is false;
            null when no `else` was written
    
    See Also:
        ConstraintScope, ConstraintStmtExpr, ConstraintStmtImplication
    
    """
    pass
    
    def getCond(self) -> Expr: ...
    
    def getTrue_c(self) -> ConstraintScope: ...
    
    def getFalse_c(self) -> ConstraintScope: ...
    
class ConstraintStmtSoft(ConstraintStmt):
    """
    Soft (overridable) constraint statement -- PSS 3.1, §13.1.12.
    
    A soft constraint expresses a *preference* rather than a
    requirement. It is discarded when it contradicts a hard constraint,
    an active default constraint, or a higher-priority soft constraint,
    instead of producing a solve failure.
    
    Relative priority is determined by *position in the model*, not by
    anything written in the source: a soft constraint declared later
    outranks one declared earlier in the same scope, a derived type
    outranks its base, and a type extension outranks the initial
    declaration. The parser's obligation is therefore to preserve
    declaration order faithfully -- `index` (inherited from
    ScopeChild) records the position within the enclosing scope, and
    priority is derived from it downstream. Reordering
    constraint-scope children would silently change what the model
    means.
    
    PSS Example::
    
        action A {
            rand int x;
    
            constraint c {
                x < 100;            // hard -- always holds
                soft x > 10;        // preference, lower priority
                soft x in [50..60]; // preference, higher priority
            }
        }
    
    Attributes:
        expr: The Boolean expression preferred to hold
    
    See Also:
        ConstraintStmtExpr, ConstraintStmtDefault, ConstraintScope
    
    """
    pass
    
    def getExpr(self) -> Expr: ...
    
class ConstraintStmtUnique(ConstraintStmt):
    """
    Uniqueness constraint (LRM 13.1.10, `unique_constraint_item`).
    
    Constrains a set of values to be mutually distinct.
    
    PSS Example::
    
        action transaction_set {
            rand bit[8] id1, id2, id3, id4;
            rand bit[16] addr[4];
    
            constraint unique_ids_c {
                unique { id1, id2, id3, id4 };
            }
    
            constraint unique_addresses_c {
                unique addr;
            }
        }
    
    PSS 3.1 (§13.1.10) admits a second, single-argument form whose
    meaning is *different*::
    
        unique { a, b, c };   // these three attributes must differ
        unique arr;           // the elements of `arr` must differ
        unique arr[2..5];     // elements 2..5 of `arr` must differ
    
    Both forms populate `list`, so `is_braced` is what distinguishes
    them: with one entry, `unique { a }` constrains a single scalar
    (vacuously true) while `unique a` constrains every element of a
    collection. A consumer that ignores the flag will silently
    mis-interpret one of them.
    
    A slice on the single-argument form is not carried here -- it is
    part of the `hierarchical_id`, as the trailing subscript of its
    last `ExprMemberPathElem` (an `ExprSliceRange`).
    
    Attributes:
        list: The attributes whose values must be unique, one per
            `hierarchical_id` written; a single entry, the
            collection, for the unbraced form
        is_braced: True for the `unique { ... }` form, false for the
            single-argument form
    
    See Also:
        ConstraintStmtExpr, ExprHierarchicalId, ExprSliceRange
    
    """
    pass
    
    def list(self) -> ListUtil[ExprRefPathContext]: ...
    def getListList(self) -> List[ExprRefPathContext]: ...
    def getList(self, i: int) -> ExprRefPathContext: ...
    def addList(self, i: ExprRefPathContext) -> None: ...
    def numList(self) -> int: ...
    
class CoverStmtInline(Scope):
    """
    Anonymous monitor body instantiated for behavioral coverage
    (LRM 16.1, the second form of `cover_stmt`).
    
    ``cover { ... }`` writes a monitor body in place instead of naming a
    previously declared monitor type. The braces admit exactly what a
    ``monitor`` body admits -- handle declarations, constraints,
    covergroups, and one ``activity`` block -- so the statement is a
    scope, and its members are reached through ``getChildren()``.
    It is a plain ``Scope`` rather than a ``SymbolScope``: like every
    other braced declaration body, the linked-tree scope its members
    resolve against is a synthetic mirror the linker builds, not this
    node.
    
    The linker (TaskBuildSymbolTree) gives it an unnamed synthetic
    SymbolScope, so its members are visible inside the braces and not
    in the enclosing component. A cover statement is a
    ``component_body_item``; it is never an activity statement.
    
    The optional ``label`` comes from the ``label_identifier ':'`` prefix.
    
    PSS Example::
    
        component pss_top {
            action A { int len; }
    
            cover {
                A a;
                constraint { a.len > 0; }
                activity { a; }
            }
    
            inline_cov: cover {
                A a;
                activity { a; }
            }
        }
    
    Attributes:
        label: Label identifier (``inline_cov`` above), or null if the
            statement is unlabeled. Set by the parser.
    
    See Also:
        CoverStmtReference, Monitor, MonitorActivityDecl
    
    """
    pass
    
    def getLabel(self) -> ExprId: ...
    
class Covergroup(NamedScopeChild):
    """
    An in-line covergroup: an anonymous covergroup type and its single
    instance, declared in an action, monitor or struct (LRM 15.2,
    `inline_covergroup`).
    
    Corresponds to the PSS ``covergroup { ... } name;`` form. Carries the
    instance name (inherited) plus its coverpoints, crosses and options.
    An in-line covergroup may reference the fields of the scope it is
    declared in. Annotations written in the body are accepted but not
    kept.
    
    PSS Example::
    
        action a {
            rand bit[4] x, y;
            covergroup {
                option.weight = 2;
                coverpoint x;
                coverpoint y;
                xy : cross x, y;
            } cg;
        }
    
    Attributes:
        name: Covergroup instance name (inherited from NamedScopeChild)
        coverpoints: The covergroup's coverpoints, in source order
        crosses: The covergroup's crosses, in source order
        options: ``option.x = y;`` settings from the covergroup body
        body: Set by the linker (TaskBuildSymbolTree): the scope of the
            coverpoint and cross names (LRM 15.3 a, 15.4), a synthetic
            symbol scope whose target is this covergroup and whose
            members are the coverpoints and crosses, not owned. Cross
            items, bin targets and ``with`` expressions are resolved
            (TaskResolveRefs) with it in view; coverpoint targets,
            ``iff`` guards and bin ranges are not. Null before
            linking. Not walked by the generated visitors.
    
    See Also:
        CovergroupType, CovergroupCoverpoint, CovergroupCross
    
    """
    pass
    
    def coverpoints(self) -> ListUtil[CovergroupCoverpoint]: ...
    def getCoverpoints(self) -> List[CovergroupCoverpoint]: ...
    def getCoverpoint(self, i: int) -> CovergroupCoverpoint: ...
    def addCoverpoint(self, i: CovergroupCoverpoint) -> None: ...
    def numCoverpoints(self) -> int: ...
    
    def crosses(self) -> ListUtil[CovergroupCross]: ...
    def getCrosses(self) -> List[CovergroupCross]: ...
    def getCrosse(self, i: int) -> CovergroupCross: ...
    def addCrosse(self, i: CovergroupCross) -> None: ...
    def numCrosses(self) -> int: ...
    
    def options(self) -> ListUtil[CovergroupOption]: ...
    def getOptions(self) -> List[CovergroupOption]: ...
    def getOption(self, i: int) -> CovergroupOption: ...
    def addOption(self, i: CovergroupOption) -> None: ...
    def numOptions(self) -> int: ...
    
    def getBody(self) -> SymbolScope: ...
    
class CovergroupCoverpoint(NamedScopeChild):
    """
    A coverpoint within a covergroup (LRM 15.3,
    `covergroup_coverpoint`).
    
    Samples the value of ``target`` (an integer or enum expression,
    typically a field reference) when the covergroup is sampled. The
    coverpoint name is the label, when one is written. Without a label
    the builder names the coverpoint with the target's source text,
    which is the variable name in the only unlabeled form the LRM
    allows (a coverpoint on a single variable).
    
    PSS Example::
    
        covergroup {
            cp_x : coverpoint x;              // labeled
            coverpoint y;                     // unlabeled (name 'y')
            bit[4] cp_z : coverpoint z        // explicit sample type
                iff (enable) {
                    option.at_least = 2;
                    bins low = [0..3];
                }
        } cg;
    
    Attributes:
        name: Coverpoint name (inherited from NamedScopeChild): the
            label, or the target's text when unlabeled
        target: Expression being sampled
        data_type: Explicit sample type; null when none was written
        iff: Guard expression -- the sample is taken only when it
            holds; null when no ``iff`` was written
        bins: Bin specifications from the coverpoint body, in source
            order; empty when there are none (automatic bins)
        options: ``option.x = y;`` settings from the coverpoint body
    
    See Also:
        Covergroup, CovergroupCross, CoverpointBins, CovergroupOption
    
    """
    pass
    
    def getTarget(self) -> Expr: ...
    
    def getData_type(self) -> DataType: ...
    
    def getIff(self) -> Expr: ...
    
    def bins(self) -> ListUtil[CoverpointBins]: ...
    def getBins(self) -> List[CoverpointBins]: ...
    def getBin(self, i: int) -> CoverpointBins: ...
    def addBin(self, i: CoverpointBins) -> None: ...
    def numBins(self) -> int: ...
    
    def options(self) -> ListUtil[CovergroupOption]: ...
    def getOptions(self) -> List[CovergroupOption]: ...
    def getOption(self, i: int) -> CovergroupOption: ...
    def addOption(self, i: CovergroupOption) -> None: ...
    def numOptions(self) -> int: ...
    
class CovergroupCross(NamedScopeChild):
    """
    A cross of coverpoints within a covergroup (LRM 15.4,
    `covergroup_cross`).
    
    Each crossed item is a coverpoint of the same covergroup or a
    variable, which then acts as an implicit coverpoint.
    
    PSS Example::
    
        covergroup {
            coverpoint a;
            coverpoint b;
            ab : cross a, b iff (enable) {
                option.weight = 3;
                ignore_bins same = ab with (a == b);
            }
        } cg;
    
    Attributes:
        name: Cross name (inherited from NamedScopeChild)
        coverpoint_names: The items being crossed, in source order.
            Each target is set by the linker (TaskResolveRefs) to a
            coverpoint of the covergroup or, failing that, a data
            field
        iff: Guard expression -- the sample is taken only when it
            holds; null when no ``iff`` was written
        bins: Bin specifications from the cross body
        options: ``option.x = y;`` settings from the cross body
    
    See Also:
        Covergroup, CovergroupCoverpoint, CovergroupCrossBins
    
    """
    pass
    
    def coverpoint_names(self) -> ListUtil[ExprRefName]: ...
    def getCoverpoint_names(self) -> List[ExprRefName]: ...
    def getCoverpoint_name(self, i: int) -> ExprRefName: ...
    def addCoverpoint_name(self, i: ExprRefName) -> None: ...
    def numCoverpoint_names(self) -> int: ...
    
    def getIff(self) -> Expr: ...
    
    def bins(self) -> ListUtil[CovergroupCrossBins]: ...
    def getBins(self) -> List[CovergroupCrossBins]: ...
    def getBin(self, i: int) -> CovergroupCrossBins: ...
    def addBin(self, i: CovergroupCrossBins) -> None: ...
    def numBins(self) -> int: ...
    
    def options(self) -> ListUtil[CovergroupOption]: ...
    def getOptions(self) -> List[CovergroupOption]: ...
    def getOption(self, i: int) -> CovergroupOption: ...
    def addOption(self, i: CovergroupOption) -> None: ...
    def numOptions(self) -> int: ...
    
class CovergroupCrossBins(NamedScopeChild):
    """
    A bins specification in a ``cross`` body (LRM 15.4.3,
    `covergroup_cross_binspec`).
    
    The cross form is narrower than the coverpoint form -- LRM B.15 gives
    it exactly one shape, ``<kind> name = <cross> with ( expr );`` -- so
    it is a separate class rather than another ``form`` on
    ``CoverpointBins``, whose optional fields would then all be
    inapplicable. In the ``with`` expression, the names of the crossed
    coverpoints stand for their values.
    
    PSS Example::
    
        covergroup {
            coverpoint a;
            coverpoint b;
            ab : cross a, b {
                ignore_bins skip = ab with (a == b);
            }
        } cg;
    
    Attributes:
        name: The bin name (inherited from NamedScopeChild)
        kind: bins / illegal_bins / ignore_bins
        target: The cross the bins are derived from; its target is set
            by the linker (TaskResolveRefs), which reports an error if
            it names any cross but the bin's own
        with_expr: The filter expression
    
    See Also:
        CovergroupCross, CoverpointBins, CovergroupBinsKindE
    
    """
    pass
    
    def getKind(self) -> int: ...
    def setKind(self, v : CovergroupBinsKindE | int) -> None: ...
    
    def getTarget(self) -> ExprRefName: ...
    
    def getWith_expr(self) -> Expr: ...
    
class CovergroupInstantiation(NamedScopeChild):
    """
    An instance of a named covergroup type -- ``cg_t cg(.a(x));``
    (LRM 15.2, `covergroup_type_instantiation`).
    
    The grammar offers two ways to supply actuals and they are mutually
    exclusive, so exactly one of ``portmap`` and ``targets`` is populated:
    ``portmap`` for the named form, ``targets`` for the positional one.
    
    PSS Example::
    
        struct s {
            rand int x, y;
            cg_t cg1(.a(x), .b(y));                      // named
            cg_t cg2(x, y) with { option.weight = 2; }   // positional
        }
    
    Attributes:
        name: The instance name (inherited from NamedScopeChild)
        type: The covergroup type being instantiated; resolved by the
            linker (TaskResolveRefs)
        portmap: Named actuals, for the ``.port(actual)`` form; empty
            for the positional form
        targets: Positional actuals, for the bare-list form; empty for
            the named form
        options: ``with { option.x = y; }`` settings; empty when the
            instantiation ends in ``;``
    
    See Also:
        CovergroupType, CovergroupPortmap, CovergroupOption
    
    """
    pass
    
    def getType(self) -> TypeIdentifier: ...
    
    def portmap(self) -> ListUtil[CovergroupPortmap]: ...
    def getPortmapList(self) -> List[CovergroupPortmap]: ...
    def getPortmap(self, i: int) -> CovergroupPortmap: ...
    def addPortmap(self, i: CovergroupPortmap) -> None: ...
    def numPortmap(self) -> int: ...
    
    def targets(self) -> ListUtil[ExprRefPathContext]: ...
    def getTargets(self) -> List[ExprRefPathContext]: ...
    def getTarget(self, i: int) -> ExprRefPathContext: ...
    def addTarget(self, i: ExprRefPathContext) -> None: ...
    def numTargets(self) -> int: ...
    
    def options(self) -> ListUtil[CovergroupOption]: ...
    def getOptions(self) -> List[CovergroupOption]: ...
    def getOption(self, i: int) -> CovergroupOption: ...
    def addOption(self, i: CovergroupOption) -> None: ...
    def numOptions(self) -> int: ...
    
class CoverpointBins(NamedScopeChild):
    """
    A ``bins`` / ``illegal_bins`` / ``ignore_bins`` specification in a
    coverpoint body (LRM 15.3.3, `covergroup_coverpoint_binspec`).
    
    The three keywords differ only in what the tool does with the bin, so
    they are one class with a ``kind`` rather than three classes.
    
    ``form`` says which of the three right-hand sides the grammar took,
    and therefore which fields are populated:
    
    * ``Ranges`` -- ``ranges`` holds the value list, and ``with_expr``
      the optional ``with (...)`` filter.
    * ``Coverpoint`` -- ``target`` names the coverpoint the bins are
      derived from, and ``with_expr`` the required filter.
    * ``Default`` -- neither; the bin catches everything unbinned.
    
    ``bins b[] = ...`` and ``bins b[4] = ...`` declare an array of bins;
    ``is_array`` records the brackets and ``array_size`` the optional
    expression inside them.
    
    In a ``with`` filter the coverpoint's own name stands for the
    candidate value (LRM 15.3.3.3).
    
    PSS Example::
    
        covergroup {
            cp : coverpoint x {
                bins low     = [0..3];
                bins high[4] = [8..15] with (cp % 2 == 0);
                bins odd[]   = cp with (cp % 2 == 1);
                ignore_bins  rest = default;
            }
        } cg;
    
    Attributes:
        name: The bin name (inherited from NamedScopeChild)
        kind: bins / illegal_bins / ignore_bins
        form: Which right-hand side was written
        is_array: True if the name was followed by brackets
        array_size: The expression inside the brackets; null for
            ``[]`` and for a bin that is not an array
        ranges: The value list, for the ``Ranges`` form; each entry is
            a value, ``lo..hi``, ``lo..`` or ``..hi``. Empty for the
            other forms
        target: The coverpoint named, for the ``Coverpoint`` form;
            null otherwise. Its target is set by the linker
            (TaskResolveRefs), which reports an error if it names any
            coverpoint but the bin's own
        with_expr: The ``with (...)`` filter; null when none was
            written (always present for the ``Coverpoint`` form)
    
    See Also:
        CovergroupCoverpoint, CovergroupCrossBins, CovergroupBinsKindE
        CoverpointBinsFormE
    
    """
    pass
    
    def getKind(self) -> int: ...
    def setKind(self, v : CovergroupBinsKindE | int) -> None: ...
    
    def getForm(self) -> int: ...
    def setForm(self, v : CoverpointBinsFormE | int) -> None: ...
    
    def getArray_size(self) -> Expr: ...
    
    def ranges(self) -> ListUtil[ExprOpenRangeValue]: ...
    def getRanges(self) -> List[ExprOpenRangeValue]: ...
    def getRange(self, i: int) -> ExprOpenRangeValue: ...
    def addRange(self, i: ExprOpenRangeValue) -> None: ...
    def numRanges(self) -> int: ...
    
    def getTarget(self) -> ExprRefName: ...
    
    def getWith_expr(self) -> Expr: ...
    
class DataTypeBool(DataType):
    """
    Boolean data type: `bool` (`bool_type`, LRM 7.4).
    
    Values are `true` and `false`.
    
    PSS Example::
    
        bool flag;
        rand bool enable;
    
        constraint {
            enable == true;
        }
    
    See Also:
        DataType, DataTypeInt
    
    """
    pass
    
class DataTypeChandle(DataType):
    """
    Opaque handle type: `chandle` (`chandle_type`, LRM 7.7).
    
    An opaque pointer to data managed outside PSS (typically C/C++
    objects), passed through the foreign procedural interface.
    
    PSS Example::
    
        function void use_object(chandle obj);
    
    See Also:
        DataType, DataTypePyObj
    
    """
    pass
    
class DataTypeEnum(DataType):
    """
    Enum type with a value domain (`enum_type`, LRM 7.5.1).
    
    Built only for the `enum_type_identifier in [ ... ]` form, which
    restricts the enum to a subset of its items. A plain use of an enum
    type (`my_enum e;`) is a DataTypeUserDefined, not a DataTypeEnum.
    
    PSS Example::
    
        enum my_enum { A, B, C, D };
    
        rand my_enum in [A, B] value;    // Only A or B allowed
    
    Attributes:
        tid: Reference to the enum type, as a DataTypeUserDefined; its
            target is set by the linker (TaskResolveRefs)
        in_rangelist: The `in [...]` domain. A domain, like an integer
            type's, may have open ranges (7.5.2: `in [..B]`). A bare name
            in it is resolved first as an item of this enum, by the
            linker (TaskResolveRefs). Always set by the parser, since the
            grammar requires the domain for this form
    
    See Also:
        EnumDecl, DataTypeUserDefined, ExprDomainOpenRangeList
    
    """
    pass
    
    def getTid(self) -> DataTypeUserDefined: ...
    
    def getIn_rangelist(self) -> ExprDomainOpenRangeList: ...
    
class DataTypeFloat(DataType):
    """
    Floating-point data type (`float_type`, LRM 7.3).
    
    Represents the PSS 3.1 ``float32`` and ``float64`` types (IEEE 754
    binary32 and binary64). ``is_float64`` distinguishes the two widths;
    they differ only in precision, so a single node carries both.
    
    PSS Example::
    
        float32 ratio;
        float64 tolerance = 1.0e-9;
    
    Attributes:
        is_float64: True for ``float64``, False for ``float32``
    
    See Also:
        DataType, DataTypeInt, ExprFloatLiteral
    
    """
    pass
    
class DataTypeInt(DataType):
    """
    Integer data type: `int` or `bit` (`integer_type`, LRM 7.2).
    
    Carries signedness, width and an optional value domain. With no
    width written, the parser fills in the default: 32 for `int`, 1 for
    `bit`. The non-standard `[msb:0]` form is accepted and stored as the
    width `msb+1`.
    
    PSS Example::
    
        int[8] byte_val;                     // 8-bit signed
        bit[16] word_val;                    // 16-bit unsigned
        bit[7:0] b;                          // same as bit[8]
        rand int in [0x1000..0x2000] addr;   // With a value domain
        int value;                           // 32 bits by default
    
    Attributes:
        is_signed: True for `int`, false for `bit`
        width: Bit-width expression; the default width when none was
            written. Null only on types the tool builds itself (the
            built-in function signatures' `int`)
        in_range: The `in [...]` value domain; null when absent
    
    See Also:
        DataType, ExprDomainOpenRangeList
    
    """
    pass
    
    def getWidth(self) -> Expr: ...
    
    def getIn_range(self) -> ExprDomainOpenRangeList: ...
    
class DataTypePyObj(DataType):
    """
    Python object type, `pyobj` (a zuspec extension, not in the LRM).
    
    An opaque reference to a Python object, for models that call into
    Python through `pyimport`. It has no attributes.
    
    PSS Example::
    
        pyimport numpy;
        function pyobj make_array(int n);
    
    See Also:
        DataTypeChandle, PyImportStmt
    
    """
    pass
    
class DataTypeRef(DataType):
    """
    Reference type: `ref entity_type_identifier` (`reference_type`,
    LRM 7.10).
    
    A reference to an action, monitor, component, flow-object or
    resource instance. Usable for local variables, function parameters
    and return values; only component references may declare fields (in
    components, actions and monitors).
    
    PSS Example::
    
        component sub_c { }
    
        component pss_top {
            ref sub_c peer;                     // component ref field
            function void use(ref sub_c c);     // ref parameter
        }
    
    Attributes:
        type: The referenced entity type. Null only when the
            `entity_type_identifier` did not build a user-defined type,
            which the parser reports as an internal error
    
    See Also:
        DataTypeUserDefined, FieldCompRef
    
    """
    pass
    
    def getType(self) -> DataTypeUserDefined: ...
    
class DataTypeString(DataType):
    """
    String data type, with an optional value domain (`string_type`,
    LRM 7.6).
    
    PSS Example::
    
        string message;
        rand string in ["read", "write", "execute"] mode;
    
    Attributes:
        has_range: True when the `in [...]` domain is present
        in_range: The domain's string literals in source order, with
            their quotes stripped; empty when there is no domain
    
    See Also:
        DataType, ExprString
    
    """
    pass
    
    def in_range(self) -> ListUtil[str]: ...
    def getIn_rangeList(self) -> List[str]: ...
    def getIn_range(self, i: int) -> str: ...
    def addIn_range(self, i: str) -> None: ...
    def numIn_range(self) -> int: ...
    
class DataTypeUserDefined(DataType):
    """
    A type named by a `type_identifier` (LRM 7.1, 7.11).
    
    Names an action, component, struct, flow or resource object, enum,
    typedef, or a template type such as `list<int>`. The identifier may
    be simple or package-qualified, with template arguments. The parser
    also builds one for each array dimension of a declaration
    (`int a[4]` names `array<int,4>`) and for the type inside `ref`, an
    enum domain and object-reference fields. Resolution to the declared
    type is recorded on `type_id`.
    
    PSS Example::
    
        my_pkg::my_action a1;        // Qualified type reference
        my_struct s1;                // Simple type reference
        list<int> values;            // Template type
    
    Attributes:
        is_global: True if the type reference starts with `::`
        type_id: The type identifier. Its target is set by the linker
            (TaskResolveRefs) to the declaration it names
    
    See Also:
        TypeIdentifier, DataType, Action, Component, Struct,
        TypedefDeclaration
    
    """
    pass
    
    def getType_id(self) -> TypeIdentifier: ...
    
class EnumDecl(NamedScopeChild):
    """
    Enum type declaration (`enum_declaration`, LRM 7.5.1).
    
    Declares an enumerated type: a distinct type whose values are a set
    of named integral constants. Enums can be used as field types and in
    constraints.
    
    PSS Example::
    
        enum direction {
            NORTH, SOUTH, EAST, WEST
        };
    
        enum error_code {
            SUCCESS = 0,
            ERR_INVALID = 1,
            ERR_TIMEOUT = 2
        };
    
    An optional base type, which must be an integer type, fixes the
    width and signedness of the enumerators::
    
        enum mode_e : bit[4] {          // With an explicit base type
            IDLE = 0, RUN = 1
        };
    
    Attributes:
        name: Enum type name (inherited from NamedScopeChild)
        items: The enumerators in source order; empty for `enum e { }`.
            Items added by `extend enum` stay on the ExtendEnum, except
            for an enum inside a generic: the linker also appends them here
            (non-owning) so that each specialization's copy has them.
        base_type: Declared base type (`: data_type`), or null when none
            was written. Only an enum that has one may be a member of a
            packed struct (21.13.1).
    
    See Also:
        EnumItem, DataTypeEnum, ExtendEnum
    
    """
    pass
    
    def items(self) -> ListUtil[EnumItem]: ...
    def getItems(self) -> List[EnumItem]: ...
    def getItem(self, i: int) -> EnumItem: ...
    def addItem(self, i: EnumItem) -> None: ...
    def numItems(self) -> int: ...
    
    def getBase_type(self) -> DataType: ...
    
class EnumItem(NamedScopeChild):
    """
    One enumerator in an enum declaration or an `extend enum`
    (`enum_item`, LRM 7.5.1).
    
    An item may have an explicit value; otherwise it takes the previous
    item's value + 1 (0 for the first). The parser precomputes each
    item's value into the inherited `index` where it can evaluate it.
    Items are static constant members of their enum.
    
    PSS Example::
    
        enum status {
            OK = 0,          // Explicit value
            ERROR,           // Auto-assigned value (1)
            PENDING = 100    // Explicit value
        };
    
    Attributes:
        name: Enumerator identifier (inherited from NamedScopeChild)
        value: The `= constant_expression` value; null when absent
        upper: The SymbolEnumScope of the enum that declares the item.
            Not set by the parser; set by the linker (TaskBuildSymbolTree)
            for an item of an EnumDecl. An item contributed by
            `extend enum` is merged into the target enum's scope by
            TaskApplyTypeExtensions, which does not set it
    
    See Also:
        EnumDecl, ExtendEnum, SymbolEnumScope, NamedScopeChild
    
    """
    pass
    
    def getValue(self) -> Expr: ...
    
    def getUpper(self) -> SymbolEnumScope: ...
    
class ExprAggrEmpty(ExprAggrLiteral):
    """
    The empty aggregate literal `{}` (LRM 4.8.1,
    `empty_aggregate_literal`).
    
    Denotes an empty collection when used for a variable-sized
    collection type (list, set, map).
    
    PSS Example::
    
        list<int> l = {};
        map<string, int> m = {};
    
    See Also:
        ExprAggrLiteral, ExprAggrList, ExprAggrMap
    
    """
    pass
    
class ExprAggrList(ExprAggrLiteral):
    """
    A value list literal (LRM 4.8.2, `value_list_literal`): a
    brace-enclosed, comma-separated list of expressions.
    
    Used for arrays, lists and sets; for an array or list the elements
    are in order from element 0. Elements need not be constant.
    
    PSS Example::
    
        int c1[4] = {1, 2, 3, 4};
        list<bit[8]> bytes = {8'hFF, 8'h00, 8'hAA};
    
    Attributes:
        elems: The element expressions, in source order (at least one)
    
    See Also:
        ExprAggrLiteral, ExprAggrEmpty
    
    """
    pass
    
    def elems(self) -> ListUtil[Expr]: ...
    def getElems(self) -> List[Expr]: ...
    def getElem(self, i: int) -> Expr: ...
    def addElem(self, i: Expr) -> None: ...
    def numElems(self) -> int: ...
    
class ExprAggrMap(ExprAggrLiteral):
    """
    A map literal (LRM 4.8.3, `map_literal`): brace-enclosed
    `key : value` pairs.
    
    If a key appears more than once, the last value applies. Keys and
    values need not be constant.
    
    PSS Example::
    
        struct t {
            map<int, bool> m = {1: true, 2: false, 4: true};
        }
    
    Attributes:
        elems: The key-value items, in source order
    
    See Also:
        ExprAggrMapElem, ExprAggrLiteral
    
    """
    pass
    
    def elems(self) -> ListUtil[ExprAggrMapElem]: ...
    def getElems(self) -> List[ExprAggrMapElem]: ...
    def getElem(self, i: int) -> ExprAggrMapElem: ...
    def addElem(self, i: ExprAggrMapElem) -> None: ...
    def numElems(self) -> int: ...
    
class ExprAggrStruct(ExprAggrLiteral):
    """
    A structure literal (LRM 4.8.4, `struct_literal`): named attribute
    values in braces.
    
    Attributes may be given in any order; one that is not given takes
    the default value of its type, and naming one twice is an error.
    
    PSS Example::
    
        struct s {
            int a, b, c, d;
        }
        struct t {
            s s1 = {.a=1, .b=2, .c=0, .d=0};
            s s2 = {.b=2, .a=1};
        }
    
    Attributes:
        elems: The `.name = value` items, in source order
    
    See Also:
        ExprAggrStructElem, ExprAggrLiteral
    
    """
    pass
    
    def elems(self) -> ListUtil[ExprAggrStructElem]: ...
    def getElems(self) -> List[ExprAggrStructElem]: ...
    def getElem(self, i: int) -> ExprAggrStructElem: ...
    def addElem(self, i: ExprAggrStructElem) -> None: ...
    def numElems(self) -> int: ...
    
class ExprRefPathContext(ExprRefPath):
    """
    A reference resolved from the current context: a dotted path that
    starts with a plain name, or with `super.` (Annex B, the second
    form of `ref_path`).
    
    The first element is looked up in the enclosing scopes; each later
    element is a member of the one before. Also used by the builder
    wherever a construct names a hierarchical path (bind targets,
    covergroup port maps, and so on).
    
    PSS Example::
    
        field
        comp.sub.field
        regs.ctrl.write_val(1)
        data[7:0]               // with a bit slice
    
    Attributes:
        is_super: True only on an ExprRefPathSuper (the path was
            written with a leading `super.`); false otherwise
        hier_id: The path elements
        slice: The trailing `[msb : lsb]` bit slice; null when absent
    
    See Also:
        ExprRefPath, ExprHierarchicalId, ExprRefPathSuper
    
    """
    pass
    
    def getHier_id(self) -> ExprHierarchicalId: ...
    
    def getSlice(self) -> ExprBitSlice: ...
    
class ExprRefPathStatic(ExprRefPath):
    """
    A reference through `::`-qualified names (Annex B,
    `static_ref_path`): a package, type or enum-qualified constant,
    function, or enum item.
    
    Built on its own when the last element is a plain name (no call
    arguments or subscripts) and no member path follows; then `base`
    holds every element, the last included. As the root of an
    ExprRefPathStaticRooted it holds only the qualifying elements.
    
    PSS Example::
    
        my_pkg::MAX_SIZE            // base = [my_pkg, MAX_SIZE]
        ::top_pkg::config_t::VAL    // is_global, base = [top_pkg, config_t, VAL]
        color_e::RED                // an enum item
    
    Attributes:
        is_global: True if the path starts with `::` (the unnamed
            global package)
        base: The `::`-separated elements, each with optional
            template arguments. Empty only for the root of a
            path written `::name` followed by a call or member
            path, such as `::f()`
        slice: The trailing `[msb : lsb]` bit slice; null when absent
        target: (inherited) Set by the linker (TaskResolveRefs) to the
            declaration the whole path names
    
    See Also:
        ExprRefPath, TypeIdentifierElem, ExprRefPathStaticRooted
    
    """
    pass
    
    def base(self) -> ListUtil[TypeIdentifierElem]: ...
    def getBaseList(self) -> List[TypeIdentifierElem]: ...
    def getBase(self, i: int) -> TypeIdentifierElem: ...
    def addBase(self, i: TypeIdentifierElem) -> None: ...
    def numBase(self) -> int: ...
    
    def getSlice(self) -> ExprBitSlice: ...
    
class ExprRefPathStaticRooted(ExprRefPath):
    """
    A reference with a static root and a member path (Annex B,
    `static_ref_path` followed by `. hierarchical_id`, or a static
    path whose last element is called or subscripted).
    
    The root names a package or type scope and is resolved first;
    the leaf is then resolved as members of it. The last element of
    the static path is the first element of the leaf. Also built for
    a qualified void function call statement (`p::f(1);`).
    
    PSS Example::
    
        my_pkg::my_type::field.subfield
        // root: my_pkg::my_type
        // leaf: field.subfield
        my_pkg::f(1)
        // root: my_pkg, leaf: f(1)
    
    Attributes:
        root: The qualifying part, as an ExprRefPathStatic whose
            target the linker sets
        leaf: The member path, starting with the static path's last
            element
        slice: The trailing `[msb : lsb]` bit slice, applied to the
            leaf's value; null when absent
    
    See Also:
        ExprRefPathStatic, ExprHierarchicalId
    
    """
    pass
    
    def getRoot(self) -> ExprRefPathStatic: ...
    
    def getLeaf(self) -> ExprHierarchicalId: ...
    
    def getSlice(self) -> ExprBitSlice: ...
    
class ExprSignedNumber(ExprNumber):
    """
    An integer literal written with the signed base modifier `s`
    (LRM 4.6.1), such as `8'sd10` or `'sh7F`.
    
    A literal without `s` is an ExprUnsignedNumber, whatever its
    value; a leading `-` is a separate ExprUnary.
    
    PSS Example::
    
        8'sd10
        4'sb1010
        'sh7F
    
    Attributes:
        image: The literal as written in the source, digit separators
            included
        width: The size prefix (8 in `8'sd10`); 32 when the literal
            has none; -1 if the text could not be read
        value: The digits' value. It is not sign-extended from
            `width`: `4'sb1111` has value 15
    
    See Also:
        ExprNumber, ExprUnsignedNumber
    
    """
    pass
    
    def getImage(self) -> str: ...
    
    def setImage(self, v : str): ...
    
class ExprTemplateString(ExprString):
    """
    A triple-quoted string literal that contains special elements --
    PSS 3.1 §4.7.1.
    
    Subclasses ExprString rather than replacing it, deliberately: every
    existing consumer that dynamic_casts to ExprString or calls
    ``getValue()`` keeps working and sees the raw text, exactly as
    before. Only consumers that care look for the subclass.
    
    A triple-quoted string with **no** special elements stays a plain
    ExprString -- this keeps the common case free of extra nodes and
    makes "has specials" a type test.
    
    Note ``getValue()`` returns the *unexpanded* text.  A front end
    cannot supply the expanded value: expansion needs solve-time data,
    which is a tool's job, not a parser's.
    
    PSS Example::
    
        static const string greeting = \"\"\"Hello, {{name}}!\"\"\";
    
    Attributes:
        template: The scanned template body, set by the parser
        value: Raw text with quotes stripped (inherited from ExprString)
        is_raw: Always true (inherited from ExprString)
    
    See Also:
        ExprString, TemplateString
    
    """
    pass
    
    def getTemplate(self) -> TemplateString: ...
    
class ExprUnsignedNumber(ExprNumber):
    """
    An integer literal without the signed modifier (LRM 4.6.1): any
    unbased decimal, `0x`, `0b` or `0`-octal number, and any based
    literal written without `s`.
    
    The builder also synthesizes these for implied values (for
    example the default width of a bare `int` or `bit`), with an
    image such as "32".
    
    PSS Example::
    
        42
        8'hFF
        32'hDEAD_BEEF
        0b1010
    
    Attributes:
        image: The literal as written in the source, digit separators
            included
        width: The size prefix (8 in `8'hFF`); 32 when the literal
            has none; -1 if the text could not be read
        value: The literal's value
    
    See Also:
        ExprNumber, ExprSignedNumber
    
    """
    pass
    
    def getImage(self) -> str: ...
    
    def setImage(self, v : str): ...
    
class ExtendType(Scope):
    """
    Type extension declaration for adding members to existing types
    (`extend_stmt`, LRM 17.2).
    
    Represents an 'extend' statement that adds new fields, constraints,
    or methods to an existing type (action, component, struct, etc.).
    Extensions are merged with the base type during linking, allowing
    modular enhancement of types without modifying their original
    definition: TaskBuildSymbolTree collects the members in a
    SymbolExtendScope, and TaskApplyTypeExtensions resolves `target`
    and merges them into the type's SymbolTypeScope. Extending a
    template instance (`extend struct s<8>`, LRM 17.2.6) is applied to
    that specialization only.
    
    PSS Example::
    
        component my_comp {
            action base_action { }
        }
    
        extend component my_comp {
            action extended_action { }
        }
    
        extend action my_comp::base_action {
            rand int new_field;
            constraint new_constraint {
                new_field > 0;
            }
        }
    
    Attributes:
        kind: The kind of type being extended: the keyword after
            `extend` (never `Enum`; see ExtendEnum)
        target: The type named after the keyword (`type_identifier`).
            Its target is set by the linker (TaskApplyTypeExtensions)
        imports: Not set by the parser or the linker; always null.
            The extension's imports are recorded on its
            SymbolExtendScope
        children: New members being added, in source order
            (inherited from Scope)
    
    See Also:
        ExtendEnum, ExtendTargetE, TypeIdentifier, SymbolExtendScope
    
    """
    pass
    
    def getKind(self) -> int: ...
    def setKind(self, v : ExtendTargetE | int) -> None: ...
    
    def getTarget(self) -> TypeIdentifier: ...
    
    def getImports(self) -> SymbolImportSpec: ...
    
class Field(NamedScopeChild):
    """
    Data field declaration (`data_declaration`, LRM 7.1).
    
    One Field is built per `data_instantiation` of an `attr_field` (action,
    struct, flow/resource object), a `component_data_declaration`, a
    package or monitor `const_field_declaration`, an annotation's
    `annotation_attr_field` or an `activity_data_field`; so
    `rand bit[8] a, b;` gives two Fields. A covergroup port is also a
    Field. Qualifiers are recorded in `attr`. An action handle declared in
    an action body (`A a;`) parses as a data declaration and is built as
    a Field too; only the linker can tell it is a handle. The tool also
    adds `Builtin` Fields (`uid`, `initial`, `prev`, `instance_id`).
    A local variable in exec or function code is a
    ProceduralStmtDataDeclaration, not a Field.
    
    PSS Example::
    
        struct S {
            rand bit[32] addr;          // attr = Rand
            static const int MAX = 100; // attr = Static | Const
            private bool flag;          // attr = Private
            int arr[4];                 // type is array<int,4>
        }
        component pss_top {
            mutable int count;          // attr = Mutable
        }
    
    Attributes:
        name: Field identifier (inherited from NamedScopeChild)
        type: Declared data type. Array dimensions (`x[4]`) wrap it in
            a DataTypeUserDefined naming `array<T,N>`, one per dimension
        attr: Qualifier flags (FieldAttr); `NoFlags` when the declaration
            has none
        init: The `= constant_expression` initializer; null when absent
        initializers: An action handle's `{.x = v, ...}` list (LRM
            11.3.1). Set only on a handle declared in an action body,
            which is built as a Field; in an activity it is an
            ActionHandleField. Empty otherwise. Resolved against the
            handle's action type by the linker (TaskResolveRefs)
    
    See Also:
        FieldAttr, DataType, DataTypeUserDefined, NamedScopeChild,
        ActionFieldInitializer, ActionHandleField,
        ProceduralStmtDataDeclaration
    
    """
    pass
    
    def getType(self) -> DataType: ...
    
    def getAttr(self) -> int: ...
    def setAttr(self, v : FieldAttr | int) -> None: ...
    
    def getInit(self) -> Expr: ...
    
    def initializers(self) -> ListUtil[ActionFieldInitializer]: ...
    def getInitializers(self) -> List[ActionFieldInitializer]: ...
    def getInitializer(self, i: int) -> ActionFieldInitializer: ...
    def addInitializer(self, i: ActionFieldInitializer) -> None: ...
    def numInitializers(self) -> int: ...
    
class FieldClaim(NamedScopeChild):
    """
    Resource claim field of an action: a `lock` or `share`
    (`resource_ref_field_declaration`, LRM 9.4.2).
    
    Claims a resource object from a pool for the duration of the action.
    A `lock` is exclusive; a `share` permits other sharers but no
    locker. One FieldClaim is built per `object_ref_field`.
    
    PSS Example::
    
        resource bus_r { }
    
        action my_action {
            lock bus_r my_bus;     // Exclusive
            share bus_r my_bus2;   // Shared
        }
    
    Attributes:
        name: Claim identifier (inherited from NamedScopeChild)
        type: The resource type (`resource_object_type`). Array
            dimensions wrap it in an `array<T,N>` DataTypeUserDefined
        is_lock: True for `lock`, false for `share`
    
    See Also:
        Struct, FieldRef, FieldPool
    
    """
    pass
    
    def getType(self) -> DataTypeUserDefined: ...
    
class FieldCompRef(NamedScopeChild):
    """
    The implicit `comp` field of an action (LRM 9.1.5).
    
    Every action -- including an `override` action -- gets this field as
    its first child, inserted by the parser with the name `comp` and no
    type. It refers to the component instance the action executes in.
    It is not the node for a component instance field written in source:
    `sub_c sc1;` in a component is an ordinary Field.
    
    PSS Example::
    
        component pss_top {
            int base;
            action A {
                rand int x;
                constraint { x > comp.base; }  // `comp` is a FieldCompRef
            }
        }
    
    Attributes:
        name: Always `comp` (inherited from NamedScopeChild)
        type: The enclosing component type. Null after parsing; set by
            the linker (TaskLinkActionCompRefFields) when the action is
            declared in a component, and left null for an action
            declared in a package
    
    See Also:
        Action, Component, DataTypeUserDefined, Field
    
    """
    pass
    
    def getType(self) -> DataTypeUserDefined: ...
    
class FieldPool(NamedScopeChild):
    """
    Pool declaration within a component (`component_pool_declaration`,
    LRM 12.1).
    
    Declares a pool of flow or resource objects of a given type, with an
    optional size. Actions' object references are associated with pools
    by `bind` directives.
    
    PSS Example::
    
        component pss_top {
            pool [16] my_resource pool_a;   // sized pool
            pool my_buffer pool_b;          // unsized pool
        }
    
    Attributes:
        name: Pool identifier (inherited from NamedScopeChild)
        type: Element type held by the pool: a buffer, stream, state or
            resource type
        size: The `[expression]` size; null when absent. The LRM gives
            it meaning only for a resource pool, whose size then
            defaults to 1
    
    See Also:
        FieldClaim, FieldRef, ComponentBind
    
    """
    pass
    
    def getType(self) -> DataTypeUserDefined: ...
    
    def getSize(self) -> Expr: ...
    
class FieldRef(NamedScopeChild):
    """
    Flow-object reference field of an action: an `input` or `output`
    (`flow_ref_field_declaration`, LRM 9.3.4).
    
    One FieldRef is built per `object_ref_field` in the declaration. The
    referenced object is a buffer, stream or state object that the
    action consumes or produces; it is bound to a pool (`bind`) or
    supplied by another action's matching reference.
    
    PSS Example::
    
        buffer data_buf { rand bit[32] addr; }
    
        action producer {
            output data_buf out_b;
        }
        action consumer {
            input data_buf in_b;
        }
    
    Attributes:
        name: Reference name (inherited from NamedScopeChild)
        type: The flow-object type (`flow_object_type`). Array
            dimensions wrap it in an `array<T,N>` DataTypeUserDefined
        is_input: True for `input`, false for `output`
    
    See Also:
        FieldClaim, FieldPool, ComponentBind, Struct
    
    """
    pass
    
    def getType(self) -> DataTypeUserDefined: ...
    
class FunctionImportProto(FunctionImport):
    """
    One-step function import -- LRM 20.4.1,
    `import [ platform_qualifier ] [ language_identifier ] [ static ] function function_prototype ;`.
    
    Declares a function by its prototype and states that it is
    implemented in a foreign language. In a component the import must
    be `static` (20.4). The linker (TaskBuildSymbolTree)
    enters the function in the scope's symbol table, or merges with an
    existing declaration, and records the import on its
    SymbolFunctionScope.
    
    PSS Example::
    
        package p {
            import target C function void write_reg(bit[32] addr,
                                                    bit[32] data);
    
            import solve function int optimize(input int limit,
                                               output int best);
        }
    
        component pss_top {
            import static function void dev_init();
    
            action my_action {
                exec body {
                    p::write_reg(0x1000, 0x42);
                }
            }
        }
    
    Attributes:
        plat: Platform qualifier (inherited from FunctionImport)
        lang: Implementation language (inherited from FunctionImport)
        proto: The function's prototype. Its `is_target`/`is_solve`
            come from the platform qualifier and its `is_static` from
            `static`.
    
    See Also:
        FunctionImport, FunctionImportType, FunctionPrototype
    
    """
    pass
    
    def getProto(self) -> FunctionPrototype: ...
    
class FunctionImportType(FunctionImport):
    """
    Two-step function import -- LRM 20.4.1,
    `import [ platform_qualifier ] [ language_identifier ] function type_identifier ;`.
    
    Names a function declared separately (by a FunctionPrototype) and
    states that it is implemented in a foreign language. It declares
    nothing itself. The linker (TaskResolveRefs) binds the name, checks
    the import is legal (a component function may be imported only in
    its own component type, only if static, and not from a template
    component), adds an import record to the function's
    SymbolFunctionScope, and applies the platform qualifier to the
    function's prototypes.
    
    PSS Example::
    
        package p {
            function void write_reg(bit[32] addr, bit[32] data);
            import target C function write_reg;
        }
    
    Attributes:
        plat: Platform qualifier (inherited from FunctionImport)
        lang: Implementation language (inherited from FunctionImport)
        type: The name of the imported function, as a type identifier
            (possibly package-qualified). Bound to the function by the
            linker (TaskResolveRefs).
    
    See Also:
        FunctionImport, FunctionImportProto, FunctionPrototype, TypeIdentifier
    
    """
    pass
    
    def getType(self) -> TypeIdentifier: ...
    
class FunctionPrototype(NamedScopeChild):
    """
    A function signature: return type, name and parameter list -- LRM
    20.2.1, `function_prototype`.
    
    On its own, as a direct child of a package or component, it is a
    function declaration whose definition is given elsewhere
    (`[platform_qualifier] [pure] [static] function prototype ;`).
    It is also the signature inside a FunctionDefinition,
    FunctionImportProto and TargetTemplateFunction, each method of an
    ImportClass, and each built-in method the linker synthesizes for
    the standard types (list, string, ...).
    
    PSS Example::
    
        package p {
            // Declaration, defined elsewhere
            function int multiply(int a, int b);
    
            // Pure function -- callable from a template string
            pure function int addr_of(int idx);
    
            // Platform-qualified declarations
            target function void hw_write(bit[32] addr, bit[32] data);
            solve function int compute_size();
        }
    
        component pss_top {
            static function void reset_all();
        }
    
    Attributes:
        name: Function name (inherited from NamedScopeChild)
        rtype: The return type, or null for `void`
        parameters: The parameter declarations, in source order; a
            varargs parameter is last
        is_pure: True if declared with the `pure` qualifier
            (20.2.6) -- a non-void function whose result depends only
            on its arguments and that has no side effects, which is
            what a template string may call (4.7.1.1)
        is_target: True if the function is restricted to the target
            platform: written `target` (or `target solve`) on the
            declaration or import, or set by the linker when an import
            of the function says `target` (TaskBuildSymbolTree for the
            prototype form, TaskResolveRefs for `import ... function
            name;`). False for a target-template function's prototype.
        is_solve: True if the function is restricted to the solve
            platform, set the same ways as `is_target` from `solve`
        is_core: Meant to mark a function built into the
            implementation (such as the core library), which 20.2.2
            lets declare `output`/`inout` parameters and still be
            defined. Not set by the parser or the linker, so it is
            always false; TaskBuildSymbolTree reads it.
    
    See Also:
        FunctionDefinition, FunctionParamDecl, FunctionImportProto, TargetTemplateFunction
    
    """
    pass
    
    def getRtype(self) -> DataType: ...
    
    def parameters(self) -> ListUtil[FunctionParamDecl]: ...
    def getParameters(self) -> List[FunctionParamDecl]: ...
    def getParameter(self, i: int) -> FunctionParamDecl: ...
    def addParameter(self, i: FunctionParamDecl) -> None: ...
    def numParameters(self) -> int: ...
    
class GlobalScope(Scope):
    """
    Root scope representing a single source file.
    
    The top-level container for all PSS declarations in one compilation
    unit. Each source file parsed creates one GlobalScope containing all
    package declarations, imports, and top-level definitions. The
    caller creates it (`mkGlobalScope(fileid)`) and the builder fills
    it; the linker gathers every unit into a RootSymbolScope.
    
    PSS Example::
    
        // one file: everything below is a child of its GlobalScope
        import std_pkg::*;
        package p { }
        component pss_top { }
    
    Attributes:
        fileid: Id of this source file, given by the caller; it is
            the `fileid` of every Location in the file. The Python
            Parser numbers the standard library 0 and the user files
            after it, in parse order; the linker's builtins unit is -1
        filename: Path to the source file. Not set by the builder or
            by the Python and TypeScript Parser classes, which keep
            file names themselves; empty unless the caller sets it
        children: All top-level declarations (inherited from Scope)
    
    See Also:
        Scope, PackageScope, RootSymbolScope
    
    """
    pass
    
    def getFilename(self) -> str: ...
    
    def setFilename(self, v : str): ...
    
class InstanceOverride(OverrideStmt):
    """
    ``instance p.q with U;`` -- one instance is replaced by ``U``
    (LRM 17.5, `instance_override`).
    
    The target is a hierarchical path to a field, so the override applies
    at that one site rather than to every use of the field's type.
    
    PSS Example::
    
        override {
            instance sub.mem.write_a with mem_write_ecc;
        }
    
    Attributes:
        target: Hierarchical path naming the instance to override,
            starting from the block's containing type. Resolved by the
            linker (TaskResolveRefs) like any other field path written
            there
        with_t: The replacement type; resolved by the linker
            (TaskResolveRefs)
    
    See Also:
        TypeOverride, OverrideDecl
    
    """
    pass
    
    def getTarget(self) -> ExprRefPathContext: ...
    
    def getWith_t(self) -> TypeIdentifier: ...
    
class MonitorActivityLabeledStmt(MonitorActivityStmt):
    """
    Base class for non-scope monitor activity statements that can have
    a label.
    
    Mirrors ActivityLabeledStmt on the action side; the label would come
    from the ``label_identifier :`` prefix on ``monitor_activity_stmt``.
    The class currently has no subclasses, so no node of it is ever
    built: every labelable monitor activity statement is either a scope
    (MonitorActivityLabeledScope, which carries its own ``label``) or a
    traversal (whose label is on the ActivityActionTypeTraversal or
    ActivityActionHandleTraversal). A labeled ``eventually`` such as
    ``wait_ack: eventually a;`` builds a MonitorActivityEventually.
    
    Attributes:
        label: The statement label, or null when unlabeled. Never set,
            since the class is never built.
    
    See Also:
        MonitorActivityLabeledScope, MonitorActivityEventually,
        ActivityLabeledStmt
    
    """
    pass
    
    def getLabel(self) -> ExprId: ...
    
class MonitorConstraint(MonitorActivityStmt):
    """
    A ``constraint`` statement inside a monitor's activity block.
    
    This covers ``monitor_activity_constraint_stmt`` only (LRM 16.4) -- a
    ``constraint`` appearing among the *statements* of a monitor activity,
    where its position in the statement order is meaningful. A
    ``constraint`` in the monitor *body* is a
    ``monitor_constraint_declaration`` and builds an ordinary
    ConstraintBlock, exactly as it does in an action or struct, so the
    linker and every constraint consumer treat it uniformly.
    
    A monitor activity constraint is not labelable, which is why this
    descends from MonitorActivityStmt rather than
    MonitorActivityLabeledStmt.
    
    PSS Example::
    
        component c {
            action req { rand bit[8] priority; }
    
            monitor protocol_monitor {
                req r;
    
                constraint c1 { r.priority > 0; }
    
                activity {
                    constraint { r.priority in [1..8]; }
                    r;
                }
            }
        }
    
    Attributes:
        constraint: The `monitor_constraint_set` after the keyword: a
            ConstraintScope holding the statements of a braced block,
            or the single constraint statement when no braces are
            written. References in it are resolved by the linker
            (TaskResolveRefs).
    
    See Also:
        ConstraintStmt, ConstraintScope, ConstraintBlock, ActivityConstraint
    
    """
    pass
    
    def getConstraint(self) -> ConstraintStmt: ...
    
class NamedScope(Scope):
    """
    A scope with an identifier name.
    
    Base class for scopes that have a name, such as components, actions,
    structs, and other named type declarations. The name is used for
    symbol resolution and type references.
    
    PSS Example::
    
        component pss_top {    // NamedScope with name="pss_top"
            // ...
        }
    
    Attributes:
        name: The declared name, as an identifier with its own location
    
    See Also:
        Scope, NamedScopeChild, TypeScope
    
    """
    pass
    
    def getName(self) -> ExprId: ...
    
class OverrideDecl(Scope):
    """
    An ``override { ... }`` block (LRM 17.5, `override_declaration`).
    
    Overrides replace the declared type of fields with a subtype: a
    type override applies to every field of the target type within the
    subtree of the block's containing type, and an instance override
    to one field.
    They apply to action, monitor, struct attribute and component
    instance fields, not to reference fields (``input``, ``output``,
    ``lock``, ``share``). The block's statements are held in
    ``getChildren()`` in source order, which matters: within one
    container an instance override takes precedence over a type
    override, and among overrides of the same kind a later one wins.
    
    The block declares no names. The linker (TaskBuildSymbolTree) adds
    it to the enclosing symbol scope as a leaf and does not enter its
    statements; TaskResolveRefs resolves the types and paths they name.
    
    PSS Example::
    
        action A { }
        action B : A { }
        action C : A { }
    
        action top {
            A a1, a2;
            activity { a1; a2; }
    
            override {
                type A with B;       // a1 becomes a B
                instance a2 with C;  // a2 becomes a C
            }
        }
    
    See Also:
        TypeOverride, InstanceOverride, OverrideStmt
    
    """
    pass
    
class PackageScope(Scope):
    """
    PSS package scope for organizing and namespacing declarations
    (`package_declaration`, LRM 18.1).
    
    Represents a package declaration in PSS. Packages provide namespace
    management and can be split across multiple files. Each
    declaration is a separate PackageScope in the AST; the linker
    merges declarations with the same name into one SymbolScope
    (TaskBuildSymbolTree::visitPackageScope).
    
    PSS Example::
    
        package my_pkg {
            component C1 { }
            action A1 { }
        }
    
        package my_pkg {       // Same package, merged with above
            action A2 { }
        }
    
        package outer::inner { }   // id = ["outer", "inner"]
    
    Attributes:
        id: The package name as written (`package_id_path`), one
            identifier per `::`-separated element (e.g. ["outer",
            "inner"])
        sibling: Next package scope with the same name. Not set by
            the parser or the linker, which merges same-named
            packages in the symbol tree instead; always null
        children: Package members (inherited from Scope)
    
    See Also:
        Scope, PackageImportStmt, SymbolScope
    
    """
    pass
    
    def id(self) -> ListUtil[ExprId]: ...
    def getIdList(self) -> List[ExprId]: ...
    def getId(self, i: int) -> ExprId: ...
    def addId(self, i: ExprId) -> None: ...
    def numId(self) -> int: ...
    
    def getSibling(self) -> PackageScope: ...
    
class ProceduralStmtAssignment(ExecStmt):
    """
    Assignment statement -- LRM 20.7.3,
    `procedural_assignment_stmt ::= ref_path assign_op expression ;`.
    
    Assigns the value of an expression to a variable or attribute,
    either plainly (`=`) or combined with the target's current value
    (`+=`, `-=`, `<<=`, `>>=`, `|=`, `&=`).
    
    PSS Example::
    
        component pss_top {
            action my_action {
                int x;
                exec post_solve {
                    int y = 20;
    
                    x = y + 5;      // AssignOp_Eq
                    x += 10;        // AssignOp_PlusEq
                    x <<= 2;        // AssignOp_ShlEq
                    x |= 0xFF;      // AssignOp_OrEq
                }
            }
        }
    
    Attributes:
        lhs: The assignment target, from `ref_path`: an
            ExprRefPathContext, an ExprRefPathStaticRooted for a
            `::`-qualified path, or an ExprRefPathSuper for a
            `super.`-prefixed one. Always set.
        op: The assignment operator
        rhs: The value expression. Always set.
    
    See Also:
        AssignOp, ProceduralStmtExpr, ProceduralStmtDataDeclaration
    
    """
    pass
    
    def getLhs(self) -> Expr: ...
    
    def getOp(self) -> int: ...
    def setOp(self, v : AssignOp | int) -> None: ...
    
    def getRhs(self) -> Expr: ...
    
class ProceduralStmtBody(ExecStmt):
    """
    Base class of the procedural loops that hold a single body
    statement and declare no variables: ProceduralStmtWhile and
    ProceduralStmtRepeatWhile (LRM 20.7.7).
    
    The parser never builds a bare ProceduralStmtBody. The body is one
    statement; a `{ ... }` body is an ExecScope holding several.
    
    PSS Example::
    
        component pss_top {
            action my_action {
                int x;
                exec post_solve {
                    while (x > 0) x -= 1;       // single-statement body
    
                    while (x < 4) {             // ExecScope body
                        x += 1;
                    }
                }
            }
        }
    
    Attributes:
        body: The loop body statement, given index 0 within this node.
            Null if the body is an empty statement (`;`).
    
    See Also:
        ProceduralStmtWhile, ProceduralStmtRepeatWhile, ExecScope
    
    """
    pass
    
    def getBody(self) -> ScopeChild: ...
    
class ProceduralStmtBreak(ExecStmt):
    """
    Break statement -- LRM 20.7.11, `break ;`.
    
    Ends the innermost enclosing loop (repeat-count, repeat-while,
    while or foreach); execution continues with the statement after
    the loop. It may appear only inside a loop, possibly nested in an
    if-else or match statement within it; it does not end a match
    statement.
    
    PSS Example::
    
        component pss_top {
            action my_action {
                int i;
                exec post_solve {
                    while (true) {
                        i += 1;
                        if (i >= 10) {
                            break;  // leave the while loop
                        }
                    }
                }
            }
        }
    
    See Also:
        ProceduralStmtContinue, ProceduralStmtWhile, ProceduralStmtForeach
    
    """
    pass
    
class ProceduralStmtContinue(ExecStmt):
    """
    Continue statement -- LRM 20.7.11, `continue ;`.
    
    Skips the rest of the current iteration of the innermost enclosing
    loop (repeat-count, repeat-while, while or foreach) and proceeds to
    the next iteration. It may appear only inside a loop, possibly
    nested in an if-else or match statement within it.
    
    PSS Example::
    
        component pss_top {
            action my_action {
                int odd_sum;
                exec post_solve {
                    repeat (i : 10) {
                        if (i % 2 == 0) {
                            continue;  // skip even numbers
                        }
                        odd_sum += i;
                    }
                }
            }
        }
    
    See Also:
        ProceduralStmtBreak, ProceduralStmtWhile, ProceduralStmtForeach
    
    """
    pass
    
class ProceduralStmtDataDeclaration(ExecStmt):
    """
    Local variable declaration -- LRM 20.7.2,
    `procedural_data_declaration ::= data_type procedural_data_instantiation { , procedural_data_instantiation } ;`.
    
    Declares a variable local to the enclosing procedural scope, with
    an optional initial value. A declaration of several variables
    (`int a, b = 2;`) builds one node per variable, each with its own
    copy of the type; array dimensions written after a name
    (`int a[4];`) are folded into that variable's type. The parser
    enters each variable in the enclosing scope's symbol table and
    reports a duplicate name.
    
    The same class is used, with a null `datatype`, for the variables a
    loop declares: the index of ProceduralStmtRepeat, the iterator and
    index of ProceduralStmtForeach, the loop variables of activity
    loops, and the variables of a template string's foreach directive.
    
    PSS Example::
    
        component pss_top {
            action my_action {
                exec post_solve {
                    int x;                  // no initializer
                    int y = 10, z = 2;      // two declarations
                    string msg = "Hello";
                    bit[8] buf[4];          // array type
                }
            }
        }
    
    Attributes:
        name: The variable's name
        datatype: The variable's type, including any array dimensions
            written after the name. Null for a loop variable; a
            foreach iterator's is filled with the collection's element
            type by the linker (TaskResolveRefs).
        init: The initializer expression after `=`, or null when none
            is written
    
    See Also:
        ProceduralStmtAssignment, ProceduralStmtRepeat, ProceduralStmtForeach, DataType, Field
    
    """
    pass
    
    def getName(self) -> ExprId: ...
    
    def getDatatype(self) -> DataType: ...
    
    def getInit(self) -> Expr: ...
    
class ProceduralStmtExpr(ExecStmt):
    """
    Void function call statement -- LRM 20.7.4,
    `procedural_void_function_call_stmt ::= [ ( void ) ] function_call ;`.
    
    A function called for its effect, with any return value discarded.
    This is the only expression statement procedural code has: `x++;`
    and other bare expressions are not statements in PSS. The optional
    `(void)` cast is recorded in `void_cast`.
    
    PSS Example::
    
        function void log_value(int v);
        function int compute(int v);
    
        component pss_top {
            int x;
            exec init_up {
                log_value(x);           // plain call
                (void) compute(x);      // result explicitly discarded
            }
        }
    
    Attributes:
        expr: The call, as a reference path whose last element carries
            the argument list: an ExprRefPathContext for `f(...)` or
            `a.b.f(...)`, an ExprRefPathStaticRooted for a
            type-qualified call such as `pkg::f(...)` or `::f(...)`,
            or an ExprRefPathSuper for `super.f(...)`. Always set.
        void_cast: True when the call is written with the `(void)`
            cast that discards a return value explicitly (20.7.4)
    
    See Also:
        ProceduralStmtAssignment, ExprRefPathContext, ExprRefPathStaticRooted
    
    """
    pass
    
    def getExpr(self) -> Expr: ...
    
class ProceduralStmtIfElse(ExecStmt):
    """
    If / else-if / else statement -- LRM 20.7.9,
    `if ( expression ) procedural_stmt [ else procedural_stmt ]`.
    
    Evaluates the clause conditions in order and runs the body of the
    first that is true; if none is, runs the final `else` body when
    there is one. A chain of `else if` is held as a list of clauses
    rather than as nested statements.
    
    PSS Example::
    
        component pss_top {
            action my_action {
                int x;
                int size;
                exec post_solve {
                    if (x > 20) {
                        size = 3;
                    } else if (x > 10) {
                        size = 2;
                    } else {
                        size = 0;
                    }
                }
            }
        }
    
    Attributes:
        if_then: The `if` clause followed by each `else if` clause, in
            source order; never empty
        else_then: The final `else` statement, or null when there is no
            plain `else`. Its index is the number of clauses.
    
    See Also:
        ProceduralStmtIfClause, ProceduralStmtMatch
    
    """
    pass
    
    def if_then(self) -> ListUtil[ProceduralStmtIfClause]: ...
    def getIf_thenList(self) -> List[ProceduralStmtIfClause]: ...
    def getIf_then(self, i: int) -> ProceduralStmtIfClause: ...
    def addIf_then(self, i: ProceduralStmtIfClause) -> None: ...
    def numIf_then(self) -> int: ...
    
    def getElse_then(self) -> ScopeChild: ...
    
class ProceduralStmtMatch(ExecStmt):
    """
    Match statement -- LRM 20.7.10,
    `match ( match_expression ) { procedural_match_choice ... }`.
    
    Evaluates the match expression and compares it against each
    choice's open-range list. Exactly one choice may match, and its
    statement runs; more than one match is an error. With no match the
    `default` choice runs; with no match and no `default` it is an
    error. At most one `default` is allowed.
    
    PSS Example::
    
        component pss_top {
            action my_action {
                rand int status;
                int bucket;
                exec post_solve {
                    match (status) {
                        [0..9]:       bucket = 1;
                        [10, 20, 30]: bucket = 2;
                        default:      bucket = 0;
                    }
                }
            }
        }
    
    Attributes:
        expr: The match expression. Always set.
        choices: The choices, in source order; the grammar requires at
            least one
    
    See Also:
        ProceduralStmtMatchChoice, ProceduralStmtIfElse, ExprOpenRangeList
    
    """
    pass
    
    def getExpr(self) -> Expr: ...
    
    def choices(self) -> ListUtil[ProceduralStmtMatchChoice]: ...
    def getChoices(self) -> List[ProceduralStmtMatchChoice]: ...
    def getChoice(self, i: int) -> ProceduralStmtMatchChoice: ...
    def addChoice(self, i: ProceduralStmtMatchChoice) -> None: ...
    def numChoices(self) -> int: ...
    
class ProceduralStmtMatchChoice(ExecStmt):
    """
    One choice of a ProceduralStmtMatch -- LRM 20.7.10,
    `procedural_match_choice ::= [ open_range_list ] : procedural_stmt | default : procedural_stmt`.
    
    Either a bracketed open-range list of values and ranges to compare
    with the match expression, or the `default` choice.
    
    PSS Example::
    
        component pss_top {
            action my_action {
                rand int x;
                int r;
                exec post_solve {
                    match (x) {
                        [0..9]:       r = 1;    // range
                        [10, 20, 30]: r = 2;    // value list
                        default:      r = 0;    // is_default = true
                    }
                }
            }
        }
    
    Attributes:
        is_default: True for the `default` choice
        cond: The open-range list between the brackets; null for the
            `default` choice
        body: The statement run when this choice matches, given the
            choice's position as its index. Null if it is an empty
            statement (`;`).
    
    See Also:
        ProceduralStmtMatch, ExprOpenRangeList, ExprOpenRangeValue
    
    """
    pass
    
    def getCond(self) -> ExprOpenRangeList: ...
    
    def getBody(self) -> ScopeChild: ...
    
class ProceduralStmtRandomize(ExecStmt):
    """
    Procedural randomize statement -- LRM 20.7.12 and 13.4.6,
    `randomize hierarchical_id { , hierarchical_id } ( with constraint_set | ; )`.
    
    Randomizes the named variables together, at this point in the
    procedural code. Each target is treated as random whether or not
    it is declared `rand`; for a struct-typed target its `rand`
    sub-fields are randomized. The constraints declared in the targets'
    types apply, plus any written inline after `with`.
    
    PSS Example::
    
        component pss_top {
            struct pair_s {
                rand bit[8] a, b;
            }
    
            action my_action {
                exec post_solve {
                    int x;
                    pair_s p;
    
                    randomize x;                    // no inline constraints
                    randomize x, p with {
                        x > 0;
                        p.a < x;
                    }
                }
            }
        }
    
    Attributes:
        targets: The variables to randomize, in source order (13.4.6:
            "one or more variables of plain-data type"), each an
            ExprRefPathContext built from its `hierarchical_id`
        constraints: The inline constraint set after `with`: one entry
            (a ConstraintScope for a `{ ... }` block), or empty for
            `randomize ...;`
    
    See Also:
        ConstraintStmt, ConstraintScope, Field
    
    """
    pass
    
    def targets(self) -> ListUtil[Expr]: ...
    def getTargets(self) -> List[Expr]: ...
    def getTarget(self, i: int) -> Expr: ...
    def addTarget(self, i: Expr) -> None: ...
    def numTargets(self) -> int: ...
    
    def constraints(self) -> ListUtil[ConstraintStmt]: ...
    def getConstraints(self) -> List[ConstraintStmt]: ...
    def getConstraint(self, i: int) -> ConstraintStmt: ...
    def addConstraint(self, i: ConstraintStmt) -> None: ...
    def numConstraints(self) -> int: ...
    
class ProceduralStmtReturn(ExecStmt):
    """
    Return statement -- LRM 20.7.5,
    `procedural_return_stmt ::= return [ expression ] ;`.
    
    Ends execution of the enclosing native function, returning the
    value of the expression to the caller; a function returning `void`
    uses `return;`. `return;` may also be used in an exec block, where
    it ends the block (no further statements run).
    
    PSS Example::
    
        function int add(int a, int b) {
            return a + b;      // with a value
        }
    
        function void check(int v) {
            if (v == 0) {
                return;        // without a value
            }
        }
    
    Attributes:
        expr: The returned value, or null for `return;`
    
    See Also:
        FunctionDefinition, FunctionPrototype, ProceduralStmtExpr
    
    """
    pass
    
    def getExpr(self) -> Expr: ...
    
class ProceduralStmtSuper(ExecStmt):
    """
    `super;` in a procedural exec block -- LRM 20.1, `exec_super_stmt`.
    
    Runs the contents of the base type's exec block(s) of the same kind
    at this point (20.1.4.1). Exec blocks are virtual: without `super;`
    a derived type's exec block *replaces* the base type's rather than
    extending it, which silently drops the base behavior.
    
    The statement carries no operands: which exec block it refers to is
    fixed by where it appears -- the same kind, on the base type. The
    parser builds it only as a direct statement of an ExecBlock, which
    is where the grammar admits it.
    
    PSS Example::
    
        component pss_top {
            action base_a {
                int a;
                exec post_solve {
                    a = 1;
                }
            }
    
            action derived_a : base_a {
                int b;
                exec post_solve {
                    super;                  // run base_a's post_solve first
                    b = a + 1;
                }
            }
        }
    
    See Also:
        ActivitySuper, ExecBlock, ExprRefPathSuper
    
    """
    pass
    
class ProceduralStmtYield(ExecStmt):
    """
    Yield statement -- LRM 20.7.14, `yield ;`.
    
    The target exec blocks of all actions assigned to one executor run
    cooperatively. `yield;` temporarily suspends the running exec block
    so that other exec code running in parallel on the same executor
    can run.
    
    PSS Example::
    
        component pss_top {
            function void start_work();
            function void finish_work();
    
            action my_action {
                exec body {
                    start_work();
                    yield;          // let other actions on this executor run
                    finish_work();
                }
            }
        }
    
    See Also:
        ProceduralStmtReturn, ExecBlock
    
    """
    pass
    
class SymbolChildrenScope(SymbolChild):
    """
    Symbol node that contains child scopes and declarations.
    
    Extends SymbolChild to support hierarchical symbol structures with named
    scopes containing child elements. Forms the basis for namespaces, types,
    and other container-like constructs in the linked symbol tree.
    
    During linking, this class manages the collection of child declarations
    and provides the structure for symbol table lookups within a named scope.
    
    Attributes:
        name: Name of this scope (package, type or function name). The
            linker uses placeholders for unnamed scopes, such as
            `<extend>`, `<plist>`, `<root>`; empty for the root scope
        children: The members of the scope. In a linker-built
            (synthetic) scope, pointers to the member declarations and
            nested symbol scopes, mostly not owned (the AST owns them);
            in a parsed scope (an ExecScope, say), its own statements
        target: The AST node this scope stands for (a type, function,
            extension or labeled activity statement); null for a
            package and the root. A traversal edge (visit: true)
    
    See Also:
        SymbolChild, SymbolScope, ScopeChild
    
    """
    pass
    
    def getName(self) -> str: ...
    
    def setName(self, v : str): ...
    
    def children(self) -> ListUtil[ScopeChild]: ...
    def getChildren(self) -> List[ScopeChild]: ...
    def getChild(self, i: int) -> ScopeChild: ...
    def addChild(self, i: ScopeChild) -> None: ...
    def numChildren(self) -> int: ...
    
    def getTarget(self) -> ScopeChild: ...
    
class TemplateCategoryTypeParamDecl(TemplateParamDecl):
    """
    A type parameter restricted to a type category (LRM 10.3.2,
    `category_type_param_decl`).
    
    The keyword before the name -- `action`, `monitor`, `component`,
    `buffer`, `resource`, `state`, `stream`, `struct` or `numeric` -- is
    the category: an argument must be a type of that category. An optional
    `type_restriction` (`: type_identifier`) further requires the argument
    to be that type or derive from it. The linker checks both when it
    specializes the generic (TaskBuildParamValList); the argument check
    only applies to arguments that resolve to a declared type.
    
    PSS Example::
    
        buffer base_buff { rand int x; }
        buffer data_buff : base_buff { }
    
        component pss_top {
            action consumer <buffer B : base_buff = data_buff> {
                input B in_b;
            }
        }
    
        component wrap_c <struct cfg_s, bool full_duplex = true> { }
    
    Attributes:
        name: Identifier for the type parameter (inherited)
        category: The type category keyword. A keyword the builder's
            table does not know falls back to Struct.
        restriction: The type after `:`, or null when the parameter has no
            `type_restriction`. Its target is set by the linker.
        dflt: The default type after `=`, or null when none is written.
            The grammar takes a `type_identifier` here, which the parser
            wraps in a DataTypeUserDefined.
    
    See Also:
        TemplateGenericTypeParamDecl, TypeCategory, TypeIdentifier
    
    """
    pass
    
    def getCategory(self) -> int: ...
    def setCategory(self, v : TypeCategory | int) -> None: ...
    
    def getRestriction(self) -> TypeIdentifier: ...
    
    def getDflt(self) -> DataType: ...
    
class TemplateGenericTypeParamDecl(TemplateParamDecl):
    """
    A generic type parameter, declared with the `type` keyword (LRM 10.3.2,
    `generic_type_param_decl`).
    
    The parameter can be bound to any type. The LRM allows a
    `type_identifier` as the default; the grammar accepts any `data_type`,
    so built-in types such as `bit[32]` are also accepted as defaults.
    
    In a specialized TemplateParamDeclList the linker uses this class for
    *every* type parameter, including one declared with a type category:
    once the argument has been checked against the category, only the
    binding is kept.
    
    PSS Example::
    
        struct gen_s <type T = bit[32]> {
            T data;
        }
    
        component pss_top {
            gen_s<bit[8]> g8;
            gen_s<>       g32;   // T takes its default, bit[32]
        }
    
    Attributes:
        name: Identifier for the type parameter (inherited)
        dflt: The default type after `=`, or null when none is written. In
            a specialized list, the type argument bound to the parameter.
    
    See Also:
        TemplateCategoryTypeParamDecl, TemplateParamDecl, DataType
    
    """
    pass
    
    def getDflt(self) -> DataType: ...
    
class TemplateValueParamDecl(TemplateParamDecl):
    """
    A value template parameter (LRM 10.3.1, `value_param_decl`).
    
    The parameter takes a constant value rather than a type. Its data type
    must be a scalar type other than `chandle`, and it can be referenced
    anywhere a constant expression is allowed in the template type's body
    and super-type specification. A default may refer to earlier
    parameters; a default that is a `<` or `>` comparison must be
    parenthesized.
    
    PSS Example::
    
        struct my_s <type T, int N = 4> {
            T vals[N];
        }
    
        component pss_top {
            action my_a <int width, bool is_wide = (width > 10)> { }
    
            my_s<bit[8], 8> s1;
            my_s<int>       s2;      // N takes its default, 4
        }
    
    Attributes:
        name: Identifier for the value parameter (inherited)
        type: The parameter's declared data type
        dflt: The default `constant_expression` after `=`, or null when
            none is written. In a specialized list, the value argument
            bound to the parameter.
    
    See Also:
        TemplateGenericTypeParamDecl, TemplateParamExprValue, DataType
    
    """
    pass
    
    def getType(self) -> DataType: ...
    
    def getDflt(self) -> Expr: ...
    
class TypeOverride(OverrideStmt):
    """
    ``type T with U;`` -- every field of type ``T`` under the block's
    containing type is instantiated as ``U`` instead (LRM 17.5,
    `type_override`).
    
    PSS Example::
    
        override {
            type mem_write with mem_write_ecc;
        }
    
    Attributes:
        target: The type being overridden; resolved by the linker
            (TaskResolveRefs)
        with_t: The replacement type, a subtype of ``target``; resolved
            by the linker (TaskResolveRefs)
    
    See Also:
        InstanceOverride, OverrideDecl
    
    """
    pass
    
    def getTarget(self) -> TypeIdentifier: ...
    
    def getWith_t(self) -> TypeIdentifier: ...
    
class ActivityActionHandleTraversal(ActivityLabeledStmt):
    """
    Traverses an action handle: `a1;`, `b[2] with { ... }` -- LRM 11.3.1
    and 11.3.2, `action_handle_traversal_stmt`.
    
    The handle is a field of the action (or of the activity block) whose
    type is an action; traversing it executes that sub-action. Element
    subscripts select one element of an action-handle array; without a
    subscript an array traversal traverses every element. An optional
    initializer list sets attributes of the traversed action, and an
    optional `with` block adds in-line constraints. Also built for
    traversals in a monitor activity.
    
    A parameterless symbol activated by name (`s;`, LRM Example 120)
    parses as this statement too; the linker (TaskResolveRefs) recognizes
    the symbol and rejects a `with` block or initializer list on it.
    
    PSS Example::
    
        component pss_top {
            action A { rand bit[16] addr; bit[8] id; }
            action top {
                A a1;
                A arr[4];
                activity {
                    a1;
                    a1 with { addr == 0x1000; }
                    arr[1] {.id = 3} with { addr < 16; }
                    L: arr;
                }
            }
        }
    
    Attributes:
        target: Reference path to the handle: a single path element holding
            the `identifier` and any `[ expression ]` subscripts. Resolved by
            the linker (TaskResolveRefs).
        with_c: The `with constraint_set` in-line constraints, or null when
            the statement ends with `;`. Resolved in the traversed action's
            type.
    
    See Also:
        ActivityActionTypeTraversal, ActionFieldInitializer, ActionHandleField, ExprRefPathContext
    
    """
    pass
    
    def getTarget(self) -> ExprRefPathContext: ...
    
    def getWith_c(self) -> ConstraintStmt: ...
    
    def initializers(self) -> ListUtil[ActionFieldInitializer]: ...
    def getInitializers(self) -> List[ActionFieldInitializer]: ...
    def getInitializer(self, i: int) -> ActionFieldInitializer: ...
    def addInitializer(self, i: ActionFieldInitializer) -> None: ...
    def numInitializers(self) -> int: ...
    
class ActivityActionTypeTraversal(ActivityLabeledStmt):
    """
    Traverses an anonymous action of a given type: `do A;` -- LRM 11.3.1,
    `action_type_traversal_stmt`.
    
    Equivalent to traversing a fresh, implicitly declared handle of the
    named action type. An optional initializer list sets attributes of the
    traversed action, and an optional `with` block adds in-line
    constraints. Also built for `do` traversals in a monitor activity. A
    type that resolves but is not an action is reported by the linker
    (TaskResolveRefs).
    
    PSS Example::
    
        component pss_top {
            action A { rand bit[16] addr; bit[8] id; }
            action top {
                activity {
                    do A;
                    do A with { addr in [0..255]; }
                    L1: do A {.id = 1};
                }
            }
        }
    
    Attributes:
        target: The `type_identifier` naming the action type (possibly
            qualified, `pkg::A`); its type reference is resolved by the
            linker (TaskResolveRefs).
        with_c: The `with constraint_set` in-line constraints, or null when
            the statement ends with `;`. Resolved in the traversed action type.
    
    See Also:
        ActivityActionHandleTraversal, ActionFieldInitializer, DataTypeUserDefined
    
    """
    pass
    
    def getTarget(self) -> DataTypeUserDefined: ...
    
    def getWith_c(self) -> ConstraintStmt: ...
    
    def initializers(self) -> ListUtil[ActionFieldInitializer]: ...
    def getInitializers(self) -> List[ActionFieldInitializer]: ...
    def getInitializer(self, i: int) -> ActionFieldInitializer: ...
    def addInitializer(self, i: ActionFieldInitializer) -> None: ...
    def numInitializers(self) -> int: ...
    
class TypeScope(NamedScope):
    """
    Base class for a named, user-defined type declaration that has a body.
    
    Holds what every such declaration shares: the optional base type
    (`struct_super_spec`, `action_super_spec`, `component_super_spec`
    -- the `: base` after the name), the optional template parameter
    list (LRM 10.2, `template_param_decl_list`), and the inheritance
    state the linker records. Concrete subclasses are the declaration
    forms: Action, Component, Struct (struct and the flow/resource
    object kinds), Monitor, CovergroupType, AnnotationDecl and
    ImportClass. The builtin `pyobj` type is a bare TypeScope built by
    the builtins factory, not by the parser.
    
    PSS Example::
    
        component my_comp : base_comp {     // super_t = base_comp
            // ...
        }
    
        struct my_s<int W = 8> {            // params = <int W = 8>
            bit[W] data;
        }
    
    Attributes:
        name: Type name (inherited from NamedScope)
    
    See Also:
        Action, Component, Struct, Monitor, CovergroupType, AnnotationDecl
        ImportClass, NamedScope, TypeIdentifier, TemplateParamDeclList
    
    """
    pass
    
    def getSuper_t(self) -> TypeIdentifier: ...
    
    def getParams(self) -> TemplateParamDeclList: ...
    
class SymbolScope(SymbolChildrenScope):
    """
    Base class for a node in the fully-linked tree.
    
    Core infrastructure for the linked symbol tree, providing symbol table
    management, import resolution, and scope hierarchy. Extends SymbolChildrenScope
    with linking-specific features including name-to-index mappings and import chains.
    
    The linker builds SymbolScope instances (TaskBuildSymbolTree) to merge
    declarations across compilation units, resolve imports, and create a
    unified namespace view; a package, for instance, is one SymbolScope
    however many `package` declarations contribute to it. Parsed nodes
    that open a scope of their own (ExecScope, ActivityDecl,
    TemplateString, ...) also derive from SymbolScope; their symtab is
    filled during linking.
    
    Attributes:
        symtab: Maps local identifiers to child indices for fast name lookup
        imports: The `import` statements written directly in this scope
            (and, for a type, those of its extensions), in source order;
            null when there are none. Filled by TaskBuildSymbolTree
        synthetic: True for a scope the linker built, which owns its own
            `children` list (a package, the root, a type's, enum's or
            function's symbol scope). False for a parsed scope, whose
            symtab indexes its physical children by their `index`
        opaque: True if names reached through this scope are not
            resolved or checked: reference resolution stops here. Set
            only for the builtin `pyobj` type, whose members are dynamic
    
    See Also:
        SymbolChildrenScope, RootSymbolScope, SymbolTypeScope, SymbolImportSpec
    
    """
    pass
    
    def getImports(self) -> SymbolImportSpec: ...
    
class ConstraintBlock(ConstraintScope):
    """
    Constraint declaration within a type (LRM 13.1.1,
    `constraint_declaration`).
    
    Covers all three non-generic forms: a named block
    `constraint name { ... }`, a deprecated
    `dynamic constraint name { ... }` (replaced in PSS 3.1 by a
    generic constraint with no parameters), and an unnamed
    `constraint { ... }` or
    `constraint expr;`. The body's statements are held directly in
    `constraints`; a brace block does not add a nested
    ConstraintScope. A fixed (non-dynamic) constraint block always
    holds.
    
    PSS Example::
    
        action my_action {
            rand bit[8] value;
    
            constraint valid_range_c {
                value >= 10;
                value <= 100;
            }
    
            dynamic constraint small_c {
                value < 50;
            }
    
            constraint value != 42;
        }
    
    Attributes:
        name: The name of the constraint block, with its source
            location; null for an unnamed block
        is_dynamic: True when the declaration was written with the
            `dynamic` modifier
        constraints: The constraint statements in this block, in
            source order (inherited from ConstraintScope)
    
    See Also:
        ConstraintScope, ConstraintStmt, GenericConstraintDeclBool
    
    """
    pass
    
    def getName(self) -> ExprId: ...
    
class ConstraintStmtForall(ConstraintScope):
    """
    Universal quantification over instances of a type
    (LRM 13.1.9, `forall_constraint_item`).
    
    The body's constraints shall hold for every instance of the named
    type (an action, struct, stream, buffer, state or resource type)
    within the application scope. With `in ref_path`, the scope is the
    subtree under the entity the path designates; without it, the
    subtree of the constraint's enclosing scope.
    
    The iterator variable is a ConstraintStmtField held as entry 0 of
    `constraints`; the body's statements follow it, from index 1.
    
    PSS Example::
    
        action A {
            rand int in [0..9] x;
        }
    
        action entry {
            A a1, a2;
            activity { a1; a2; }
    
            constraint {
                forall (a_it : A) {
                    a_it.x > 2;
                }
            }
            constraint {
                forall (a_it : A in a1) {
                    a_it.x < 8;
                }
            }
        }
    
    Attributes:
        iterator_id: The iterator variable's name as written
        type_id: The quantified type
        ref_path: The path after `in` that limits the application
            scope; null when no `in` clause was written
        symtab: The name scope holding the iterator variable (not
            walked by the generated visitors)
        constraints: The iterator variable (entry 0), then the body's
            constraint statements (inherited)
    
    See Also:
        ConstraintStmtForeach, ConstraintScope, ConstraintStmtField
        ConstraintSymbolScope
    
    """
    pass
    
    def getIterator_id(self) -> ExprId: ...
    
    def getType_id(self) -> DataTypeUserDefined: ...
    
    def getRef_path(self) -> ExprRefPath: ...
    
    def getSymtab(self) -> ConstraintSymbolScope: ...
    
class ConstraintStmtForeach(ConstraintScope):
    """
    Iterative constraint over the elements of a collection
    (LRM 13.1.8, `foreach_constraint_item`).
    
    The body's constraints shall hold for every element of the
    collection. The statement may introduce an iterator variable (an
    alias for the current element) and an index variable (the current
    index, or key for a map); at least one is required. Both forms of
    the index are accepted: `foreach (a[i])` and
    `foreach (e : a[i])`. In both, the parser lifts the trailing `[i]`
    off the collection expression, so `expr` names the collection
    and `idx` holds `i`.
    
    The iterator and index variables are ConstraintStmtField nodes
    registered in `symtab`; they are not entries in `constraints`.
    
    PSS Example::
    
        action packet_sequence {
            rand bit[8] lengths[10];
    
            constraint valid_lengths_c {
                foreach (lengths[i]) {
                    lengths[i] > 0;
                }
            }
    
            constraint increasing_c {
                foreach (len : lengths[i]) {
                    if (i > 0) {
                        len >= lengths[i-1];
                    }
                }
            }
        }
    
    Attributes:
        it: The iterator variable, or null when none was written
        idx: The index variable, or null when none was written
        expr: The collection expression being iterated, without the
            index subscript
        symtab: The name scope holding the iterator and index
            variables (not walked by the generated visitors)
        constraints: Constraint statements applied to each element
            (inherited)
    
    See Also:
        ConstraintStmtForall, ConstraintScope, ConstraintStmtField
        ConstraintSymbolScope
    
    """
    pass
    
    def getIt(self) -> ConstraintStmtField: ...
    
    def getIdx(self) -> ConstraintStmtField: ...
    
    def getExpr(self) -> Expr: ...
    
    def getSymtab(self) -> ConstraintSymbolScope: ...
    
class ProceduralStmtRepeatWhile(ProceduralStmtBody):
    """
    Repeat-while loop -- LRM 20.7.7,
    `repeat procedural_stmt while ( expression ) ;`.
    
    Runs the body, then evaluates the condition after each iteration
    and repeats while it is true, so the body runs at least once.
    
    PSS Example::
    
        component pss_top {
            action my_action {
                int x;
                exec post_solve {
                    repeat {
                        x += 1;
                    } while (x < 5);
                }
            }
        }
    
    Attributes:
        expr: The `bool` loop condition, evaluated after each
            iteration. Always set.
        body: The loop body (inherited from ProceduralStmtBody)
    
    See Also:
        ProceduralStmtWhile, ProceduralStmtRepeat, ProceduralStmtBody
    
    """
    pass
    
    def getExpr(self) -> Expr: ...
    
class ConstraintStmtImplication(ConstraintScope):
    """
    Implication constraint, `expression -> constraint_set`
    (LRM 13.1.6, `implication_constraint_item`).
    
    When the antecedent is true, the constraints in the body shall
    hold; when it is false, they do not apply. `a -> b` is equivalent
    to `!a || b`, and, like every constraint, it is bidirectional: a
    body that cannot hold forces the antecedent false.
    
    PSS Example::
    
        action bus_transaction {
            rand bit burst_mode;
            rand bit[5] burst_length;
            rand bit[32] addr;
    
            constraint burst_constraints_c {
                burst_mode -> {
                    burst_length in [2, 4, 8, 16];
                    (addr & 0xF) == 0;  // 16-byte aligned
                }
            }
    
            constraint normal_mode_c {
                !burst_mode -> burst_length == 1;
            }
        }
    
    Attributes:
        cond: The antecedent expression
        constraints: The consequent constraints (inherited); a single
            unbraced constraint is held here directly
    
    See Also:
        ConstraintStmtIf, ConstraintScope, ConstraintStmtExpr
    
    """
    pass
    
    def getCond(self) -> Expr: ...
    
class ProceduralStmtWhile(ProceduralStmtBody):
    """
    While loop -- LRM 20.7.7, `while ( expression ) procedural_stmt`.
    
    Evaluates the condition before each iteration and runs the body
    while it is true, so the body may not run at all.
    
    PSS Example::
    
        component pss_top {
            action my_action {
                int x;
                exec post_solve {
                    while (x > 0) {
                        x -= 1;
                    }
                }
            }
        }
    
    Attributes:
        expr: The `bool` loop condition, evaluated before each
            iteration. Always set.
        body: The loop body (inherited from ProceduralStmtBody)
    
    See Also:
        ProceduralStmtRepeatWhile, ProceduralStmtRepeat, ProceduralStmtForeach
    
    """
    pass
    
    def getExpr(self) -> Expr: ...
    
class ExprRefPathSuper(ExprRefPathContext):
    """
    A context reference written with a leading `super.`.
    
    Built instead of a plain ExprRefPathContext so that `super.f()`
    binds to the base type's member rather than to an override in
    the derived type. `is_super` is always true. Also built for a
    `super.f();` call statement.
    
    PSS Example::
    
        super.parent_field
        super.pre_solve()
    
    See Also:
        ExprRefPathContext, ExprRefPath
    
    """
    pass
    
class ActivitySuper(ActivityLabeledStmt):
    """
    `super;` in an activity -- LRM 11.6, `activity_super_stmt`.
    
    In an action that inherits from another, traverses the base action's
    activity at this point, so a derived activity can extend the one it
    overrides. Checked by the linker (TaskResolveRefs).
    
    PSS Example::
    
        action base_a {
            activity {
                do A;
            }
        }
    
        action derived_a : base_a {
            activity {
                do B;
                super;
                do C;
            }
        }
    
    See Also:
        ActivityDecl, Action
    
    """
    pass
    
class Action(TypeScope):
    """
    Action declaration defining reusable behavior blocks
    (`action_declaration`, `abstract_action_declaration`,
    `override_action_declaration`, LRM 9.2).
    
    Actions are the fundamental unit of behavior in PSS. They encapsulate
    data (fields), constraints, and activities (control flow). Actions can
    be composed hierarchically and randomized according to constraints.
    The builder inserts an implicit `comp` field (a FieldCompRef whose
    type the linker fills in) as the first child of every action.
    
    PSS Example::
    
        action my_action {
            rand bit[32] addr;
    
            constraint {
                addr >= 0x1000;
                addr < 0x2000;
            }
    
            activity {
                do read_a;
            }
        }
    
    Attributes:
        is_abstract: True if declared as 'abstract action'
        name: Action name (inherited from NamedScope)
        super_t: Optional base action type (inherited from TypeScope).
            For an override action the builder sets it to the
            action's own name, and the linker resolves it in the
            enclosing component's base chain
            (TaskResolveOverrideActions)
        children: Fields, constraints, activities (inherited from Scope)
    
    See Also:
        Component, TypeScope, ActivityDecl, FieldCompRef
    
    """
    pass
    
class ActivityDecl(SymbolScope):
    """
    An action's `activity { ... }` block -- LRM 11.1, `activity_declaration`.
    
    ActivityDecl is the root of an action's activity: the behavioral
    description of a compound action, as a set of scheduling statements
    (traversals, blocks, control flow). It is a scope with an empty name.
    Its `children` are, in source order, the top-level activity statements
    and the action handles and `action` data fields declared directly in
    the block (LRM 11.8.2: every activity block is a variable scope, so
    those declarations belong to the block, not to the action).
    
    The top-level activity scope is unnamed (LRM 11.8.3). Its labeled
    statements are made members of the enclosing action by the linker
    (TaskBuildSymbolTree), so `b1.my_seq` resolves from the action.
    
    PSS Example::
    
        component pss_top {
            action A { }
            action B { }
            action top {
                A a1;
                activity {
                    a1;
                    do B;
                }
            }
        }
    
    See Also:
        ActivityStmt, ActivityLabeledScope, SymbolDeclaration, Action
    
    """
    pass
    
class GenericConstraintDeclBool(ConstraintBlock):
    """
    Boolean generic constraint declaration (LRM 13.1.2,
    `generic_constraint_bool`).
    
    Represents a declaration of the form
    ``[static] constraint name(params) constraint_set``. Unlike a fixed
    constraint block, a generic constraint holds only where it is
    referenced -- from another constraint, by a call such as
    `small_c()`, or from an activity. Its name and body come from
    ConstraintBlock: `name` is always set, `constraints` holds the
    body (the items of a brace block are added directly, with no
    wrapping ConstraintScope), and `is_dynamic` is always false.
    
    PSS Example::
    
        action send_pkt {
            rand bit[16] pkt_sz;
            constraint small_c() { pkt_sz <= 100; }
            constraint sized_c(int lo, int hi) {
                pkt_sz >= lo;
                pkt_sz <= hi;
            }
            constraint pick_c { small_c() || sized_c(1500, 9000); }
        }
    
    See Also:
        GenericConstraintDeclValue, GenericConstraintParam, ConstraintBlock
    
    """
    pass
    
    def parameters(self) -> ListUtil[GenericConstraintParam]: ...
    def getParameters(self) -> List[GenericConstraintParam]: ...
    def getParameter(self, i: int) -> GenericConstraintParam: ...
    def addParameter(self, i: GenericConstraintParam) -> None: ...
    def numParameters(self) -> int: ...
    
class ActivityLabeledScope(SymbolScope):
    """
    Base class for labeled activity scopes.
    
    ActivityLabeledScope represents activity constructs that introduce a new
    scope and can be labeled: sequence, parallel and schedule blocks, and
    every compound statement (repeat, repeat-while, foreach, replicate,
    if-else, select, match, atomic). The label names the statement as a
    named sub-activity (LRM 11.8) for scheduling constraints, `join_branch`
    and hierarchical references.
    
    Every activity block is a variable scope (LRM 11.8.2): action handles
    and ``action`` data fields declared in a block are children of that
    block, not of the enclosing action.
    
    A compound statement's ``children`` are the variables it declares -- a
    loop index or iterator, as ``ProceduralStmtDataDeclaration`` -- and its
    bodies are data fields. For symbol-path addressing the bodies follow
    the children, in declaration order: index ``len(children) + k`` names
    body ``k`` (``true_s`` then ``false_s``; each select branch's or match
    choice's body in turn), the same convention as
    ``ProceduralStmtSymbolBodyScope``.
    
    PSS Example::
    
        action my_action {
            activity {
                my_seq: sequence {
                    do A;
                    do B;
                }
    
                my_par: parallel {
                    do A;
                    do B;
                }
            }
        }
    
    Attributes:
        label: The label identifier, or null when the statement has no label.
        sub_activity: The named sub-activity this statement introduces
            (LRM 11.8), built by the linker: a synthetic scope whose
            target is this statement. Its members are non-owned: the
            action handles and ``action`` fields declared directly under
            the statement, and the labeled statements whose nearest
            labeled ancestor it is. ``b1.my_seq.my_rep.a`` walks these
            scopes. Null on an unlabeled statement, except the body of a
            ``replicate`` with a label array, which is named by that
            array. Not walked by the generated visitors.
    
    See Also:
        ActivitySequence, ActivityParallel, ActivitySchedule, ActivityLabeledStmt
    
    """
    pass
    
    def getLabel(self) -> ExprId: ...
    
    def getSub_activity(self) -> SymbolScope: ...
    
class ImportClass(TypeScope):
    """
    Foreign class declaration -- LRM 20.4.3, ``import_class_decl``.
    
    ``import class C : B { void f(); }`` declares a class implemented in
    the target language, with the method prototypes PSS may call. The
    body admits prototypes only -- no fields, no bodies -- so the
    children of this scope are all ``FunctionPrototype``, built without
    platform qualifiers.
    
    It is a ``TypeScope`` because it declares a type others name: a field
    of an imported class type may be declared in a package (a global
    instance) or a component (one instance per component instance).
    ``super_t`` holds the first entry of the extends list, which is
    where a consumer expecting single inheritance will look; ``extends``
    holds the whole list, because ``import_class_extends`` accepts
    several and the target language may allow it.
    
    PSS Example::
    
        package p {
            import class base { void init(); }
    
            import class dev : base {
                void write(int addr, int data);
                int  read(int addr);
            }
        }
    
    Attributes:
        name: The class name, `import_class_identifier` (inherited)
        super_t: The first type named after ``:``, or null when there
            is no extends list (inherited). It is the same node as
            the first entry of ``extends``.
        extends: Every type named after ``:``, in source order; empty
            when there is no extends list. The list does not own its
            first entry, which ``super_t`` owns.
    
    See Also:
        FunctionPrototype, TypeScope, FunctionImportProto
    
    """
    pass
    
    def extends(self) -> ListUtil[TypeIdentifier]: ...
    def getExtends(self) -> List[TypeIdentifier]: ...
    def getExtend(self, i: int) -> TypeIdentifier: ...
    def addExtend(self, i: TypeIdentifier) -> None: ...
    def numExtends(self) -> int: ...
    
class Monitor(TypeScope):
    """
    A monitor type declaration (LRM 16.1, `monitor_declaration`; PSS 3.0).
    
    A monitor describes a scenario -- an order of action executions,
    with their data -- to be *observed* for behavioral coverage, where an
    action describes one to be generated. Its body admits action and
    monitor handles, constraints, covergroups and one or more
    `activity` blocks (MonitorActivityDecl); several activities combine
    as if in a `schedule`. A monitor is checked only when a `cover`
    statement instantiates it (CoverStmtReference).
    
    The monitor's name, `super_t` (from the `monitor_super_spec`) and
    template `params` are the inherited TypeScope fields; the body
    items are its children.
    
    PSS Example::
    
        component pss_top {
            action req_a { }
            action ack_a { }
    
            monitor handshake {
                req_a r;
                ack_a a;
                activity {
                    r;
                    eventually a;
                }
            }
    
            abstract monitor base_mon { }
    
            monitor derived_mon : base_mon {
                activity { do req_a; }
            }
    
            cover handshake;
        }
    
    Attributes:
        is_abstract: True for an `abstract monitor` declaration
            (`abstract_monitor_declaration`), false otherwise. Set by
            the parser.
    
    See Also:
        MonitorActivityDecl, CoverStmtReference, CoverStmtInline, Action
    
    """
    pass
    
class MonitorActivityDecl(SymbolScope):
    """
    Declares an activity block within a monitor.
    
    MonitorActivityDecl represents a monitor's ``activity { ... }``
    block (LRM 16.3, `monitor_activity_declaration`), which specifies the
    scenario to be observed. It is a symbol scope with an empty name
    whose ``getChildren()`` are the monitor activity statements, in
    source order, together with any handles declared in the activity.
    Unlike action activities, monitor activities observe execution
    patterns rather than causing them. A monitor with more than one
    activity block observes them as if combined in a ``schedule``
    (LRM 16.1). It appears in a Monitor or in an inline ``cover { }``
    body (CoverStmtInline).
    
    PSS Example::
    
        component c {
            action req { }
            action ack { }
    
            monitor handshake_check {
                req r;
                ack a;
    
                activity {
                    sequence {
                        r;
                        eventually a;
                    }
                }
            }
        }
    
    Attributes:
        (inherits symbol scope capabilities)
    
    See Also:
        MonitorActivityStmt, MonitorActivityLabeledScope, Monitor,
        CoverStmtInline, ActivityDecl
    
    """
    pass
    
class MonitorActivityLabeledScope(SymbolScope):
    """
    Base class for labeled monitor activity scopes.
    
    Mirrors ActivityLabeledScope on the action side. Every braced monitor
    activity form -- ``sequence``, ``concat``, ``overlap``, ``schedule``,
    ``select`` -- introduces a scope and holds its body statements in
    ``getChildren()``. The subclass identity, not a field, is what
    distinguishes the five: they differ in temporal semantics, not in
    shape. The scope's ``name`` is empty.
    
    ``eventually`` is a scope too, with its body addressed after its
    (empty) children -- the ActivityLabeledScope convention -- so that a
    block in its body is reachable by symbol path. Handles declared in a
    block are that block's children, not the monitor's (LRM 11.8.2).
    
    PSS Example::
    
        component pss_top {
            action config_valid { }
            action config_ack { }
    
            monitor m {
                config_valid v;
                config_ack a;
                activity {
                    setup: sequence {
                        v;
                        a;
                    }
                }
            }
        }
    
    Attributes:
        label: The ``label_identifier`` written before the statement
            (``setup`` above), or null when unlabeled. Set by the
            parser.
    
    See Also:
        MonitorActivityEventually, MonitorActivitySequence, MonitorActivityConcat,
        MonitorActivityOverlap, MonitorActivitySchedule,
        MonitorActivitySelect, ActivityLabeledScope
    
    """
    pass
    
    def getLabel(self) -> ExprId: ...
    
class AnnotationDecl(TypeScope):
    """
    Annotation type declaration (LRM 7.13, `annotation_declaration`).
    
    Represents a PSS 3.1 ``annotation`` declaration, including optional
    template parameters, inheritance, and body fields. The name,
    template parameters (``params``) and base type (``super_t``, from
    ``: type_identifier``) are inherited from TypeScope. Each
    attribute is a Field in ``getChildren()``; one declared
    ``static const`` carries both attributes. Annotation types may be
    extended with ``extend annotation``.
    
    PSS Example::
    
        annotation desc_s {
            string desc;
        }
    
        annotation tagged_desc_s : desc_s {
            static const int version = 1;
            string tag;
        }
    
    See Also:
        Annotation, ExtendType, Field
    
    """
    pass
    
class Component(TypeScope):
    """
    Component declaration defining test environment structure
    (`component_declaration`, LRM 9.1).
    
    Components represent the static structure of the test environment.
    They contain actions, pools of resources, constraints, and other
    components. Components form the containment hierarchy for actions.
    
    PSS Example::
    
        component pss_top {
            resource r_s { }
            action my_action { lock r_s r; }
            pool [4] r_s r_pool;
    
            bind r_pool *;
        }
    
    Attributes:
        is_pure: True if declared as 'pure component' (LRM 9.1.7)
        name: Component name (inherited from NamedScope)
        super_t: Optional base component type (inherited from TypeScope)
        children: Actions, resources, pools, etc (inherited from Scope)
    
    See Also:
        Action, TypeScope, Field
    
    """
    pass
    
class ProceduralStmtSymbolBodyScope(SymbolScope):
    """
    Base class of the procedural loops that declare variables:
    ProceduralStmtRepeat and ProceduralStmtForeach.
    
    The loop is a symbol scope so that its index and iterator variables
    are visible in the body and nowhere else. Those variables are the
    scope's children (ProceduralStmtDataDeclaration nodes with a null
    type, added by the parser); the body is held separately in `body`
    and is indexed after them. The parser never builds a bare
    ProceduralStmtSymbolBodyScope.
    
    PSS Example::
    
        component pss_top {
            int arr[5];
            int total;
            exec init_up {
                repeat (i : 10) {
                    total += i;         // 'i' is visible here
                }
                // 'i' is not visible here
    
                foreach (elem : arr[idx]) {
                    total += elem * idx;    // 'elem' and 'idx' visible
                }
            }
        }
    
    Attributes:
        body: The loop body statement, indexed after the loop
            variables. Null if the body is an empty statement (`;`).
    
    See Also:
        ProceduralStmtRepeat, ProceduralStmtForeach, SymbolScope
    
    """
    pass
    
    def getBody(self) -> ScopeChild: ...
    
class ConstraintSymbolScope(SymbolScope):
    """
    Name scope of the iterator variables of a `foreach` or `forall`
    constraint.
    
    Built by the AST builder, not the linker, together with the
    ConstraintStmtForeach or ConstraintStmtForall it belongs to, and
    named `<foreach>` or `<forall>`. Its symbol table maps each
    iterator or index variable name to a ConstraintStmtField, which
    the scope references without owning. The linker
    (TaskResolveRefs) pushes this scope while it resolves the
    statement's body, so names in the body find the iterator
    variables before the enclosing scopes.
    
    PSS Example::
    
        constraint loop_constraint {
            foreach (e : items[i]) {
                // 'e' and 'i' are found in the ConstraintSymbolScope
                e > i;
            }
        }
    
    Attributes:
        constraint: The `foreach` or `forall` statement this scope
            belongs to (a back-reference set by the AST builder)
    
    See Also:
        SymbolScope, ConstraintStmtForeach, ConstraintStmtForall
        ConstraintStmtField
    
    """
    pass
    
    def getConstraint(self) -> ConstraintStmt: ...
    
class RootSymbolScope(SymbolScope):
    """
    Root of a resolved symbol tree. Holds references to
    the physical linked-together files in addition to the
    merged contents within the symbol tree.
    
    Serves as the top-level entry point for the fully-linked symbol database,
    managing the collection of compilation units. It is what
    `Parser.link()` returns. Built by TaskBuildSymbolTree::build, with an
    empty name and `synthetic` set; its children are the global names of
    every unit, merged, starting with the linker's builtin types.
    
    The root scope bridges the physical file-based AST representation with the
    logical merged symbol namespace, enabling efficient multi-file symbol resolution.
    
    Attributes:
        units: List of compilation units (GlobalScope) linked into this tree
        filenames: Maps file IDs to their filesystem paths
        id2idx: Maps file IDs to their index in the units list
        fileOutRef: Outbound references from each unit (dependencies)
        fileInRef: Inbound references to each unit (dependents)
    
    See Also:
        SymbolScope, GlobalScope, SymbolImportSpec
    
    """
    pass
    
    def units(self) -> ListUtil[GlobalScope]: ...
    def getUnits(self) -> List[GlobalScope]: ...
    def getUnit(self, i: int) -> GlobalScope: ...
    def addUnit(self, i: GlobalScope) -> None: ...
    def numUnits(self) -> int: ...
    
    def fileOutRef(self) -> ListUtil[List[int]]: ...
    def getFileOutRefList(self) -> List[List[int]]: ...
    def getFileOutRef(self, i: int) -> List[int]: ...
    def addFileOutRef(self, i: List[int]) -> None: ...
    def numFileOutRef(self) -> int: ...
    
    def fileInRef(self) -> ListUtil[List[int]]: ...
    def getFileInRefList(self) -> List[List[int]]: ...
    def getFileInRef(self, i: int) -> List[int]: ...
    def addFileInRef(self, i: List[int]) -> None: ...
    def numFileInRef(self) -> int: ...
    
class Struct(TypeScope):
    """
    A struct-like type declaration: `struct`, `buffer`, `stream`, `state`
    or `resource` (LRM 7.8, `struct_declaration`).
    
    All five share one syntax; `kind` records which keyword was used,
    and so whether the type is plain data, a flow object (LRM 9.3) or a
    resource object (LRM 9.4). Body items (attribute fields,
    constraints, exec blocks, covergroups, ...) are the children.
    
    PSS Example::
    
        struct packet_s {
            bit[8] header;
            bit[32] payload;
        }
    
        buffer dma_buf_t {
            rand int in [1..64] size;
        }
    
        resource bus_t {
            int bandwidth;
        }
    
        stream data_stream_t {
            bit[16] samples;
        }
    
        state session_state_t {
            bool connected;
        }
    
    Attributes:
        name: Type name (inherited from NamedScope via TypeScope)
        super_t: Optional base type (inherited from TypeScope)
        children: Body items (inherited from Scope)
    
    See Also:
        StructKind, TypeScope, Field
    
    """
    pass
    
    def getKind(self) -> int: ...
    def setKind(self, v : StructKind | int) -> None: ...
    
class SymbolDeclaration(SymbolScope):
    """
    A named, reusable activity fragment -- LRM 11.7, ``symbol_declaration``.
    
    ``symbol s(int n) { do A; do B; }`` declares a fragment that a
    ``symbol_call`` inlines at its call site. It is a scope so its
    parameters and the labels of its body statements resolve, and so a call
    can name it. Its name is the scope name.
    
    Its body statements are ``getChildren()``, exactly as for
    ``ActivityDecl`` -- a symbol body is an activity body, and reuses the
    same statement classes rather than a parallel set.
    
    PSS Example::
    
        component c {
            action A { }
            action B { }
    
            action top {
                symbol two_of(int unused) {
                    do A;
                    do B;
                }
    
                activity {
                    two_of(1);
                }
            }
        }
    
    Attributes:
        params: The declared parameters, in order: one FunctionParamDecl
            per `symbol_param` (`data_type identifier`), with default
            direction. Empty when the symbol has no parameter list.
        sub_activity: The labels of the body (LRM 11.8), built by the
            linker as for a labeled statement's: a synthetic scope whose
            target is this symbol, holding the labeled statements whose
            nearest labeled ancestor is the symbol, non-owned. So
            ``l1: do A; constraint { l1.x < 3; }`` resolves in a symbol
            body as it does in an activity. Not walked by the generated
            visitors.
    
    See Also:
        ActivitySymbolCall, ActivityDecl, FunctionParamDecl
    
    """
    pass
    
    def params(self) -> ListUtil[FunctionParamDecl]: ...
    def getParams(self) -> List[FunctionParamDecl]: ...
    def getParam(self, i: int) -> FunctionParamDecl: ...
    def addParam(self, i: FunctionParamDecl) -> None: ...
    def numParams(self) -> int: ...
    
    def getSub_activity(self) -> SymbolScope: ...
    
class CovergroupType(TypeScope):
    """
    A named covergroup *type* -- ``covergroup cg_t(int a) { ... }``
    (LRM 15.1, `covergroup_declaration`).
    
    Declared once and instantiated by name, unlike the inline form, which
    is a single anonymous instance. It is a ``TypeScope`` because it
    declares a type others name; the body is held in the same typed lists
    the inline form uses rather than in ``getChildren()``, so a consumer
    reads one covergroup body shape and not two.
    
    The formal parameters are ``Field`` children in ``getChildren()``,
    not a separate list. ``covergroup_port`` is ``data_type identifier``
    -- a field declaration -- and putting them in the scope is what lets
    the port's *type* resolve: a list hung off the side is not walked
    with the covergroup's scope current, so ``covergroup cg(Mode m)``
    reported ``type 'Mode' is never resolved``. An instantiation supplies
    an actual for each port, either by name or positionally.
    
    PSS Example::
    
        package p {
            covergroup cg_t(int a, int b) {
                cp_a : coverpoint a;
                cp_b : coverpoint b;
                ab   : cross cp_a, cp_b;
            }
        }
    
    Attributes:
        name: The covergroup type name (inherited from TypeScope)
        coverpoints: The covergroup's coverpoints, in source order
        crosses: The covergroup's crosses, in source order
        options: ``option.x = y;`` settings from the covergroup body
        body: Set by the linker (TaskBuildSymbolTree): the scope of the
            coverpoint and cross names (LRM 15.3 a, 15.4), a synthetic
            symbol scope whose target is this covergroup and whose
            members are the coverpoints and crosses, not owned. It sits
            inside the type's own symbol scope, after the ports. Cross
            items, bin targets and ``with`` expressions are resolved
            (TaskResolveRefs) with it in view; coverpoint targets,
            ``iff`` guards and bin ranges are not. Null before
            linking. Not walked by the generated visitors.
    
    See Also:
        Covergroup, CovergroupInstantiation, Field
    
    """
    pass
    
    def coverpoints(self) -> ListUtil[CovergroupCoverpoint]: ...
    def getCoverpoints(self) -> List[CovergroupCoverpoint]: ...
    def getCoverpoint(self, i: int) -> CovergroupCoverpoint: ...
    def addCoverpoint(self, i: CovergroupCoverpoint) -> None: ...
    def numCoverpoints(self) -> int: ...
    
    def crosses(self) -> ListUtil[CovergroupCross]: ...
    def getCrosses(self) -> List[CovergroupCross]: ...
    def getCrosse(self, i: int) -> CovergroupCross: ...
    def addCrosse(self, i: CovergroupCross) -> None: ...
    def numCrosses(self) -> int: ...
    
    def options(self) -> ListUtil[CovergroupOption]: ...
    def getOptions(self) -> List[CovergroupOption]: ...
    def getOption(self, i: int) -> CovergroupOption: ...
    def addOption(self, i: CovergroupOption) -> None: ...
    def numOptions(self) -> int: ...
    
    def getBody(self) -> SymbolScope: ...
    
class SymbolEnumScope(SymbolScope):
    """
    Symbol scope for enumeration type declarations.
    
    Represents an enum definition in the linked symbol tree, managing the
    namespace for enum items and their associated values. Provides symbol
    resolution for enum member access during type checking.
    
    The scope contains the enum's items as children, enabling qualified
    name lookup (e.g., MyEnum::ItemName) during compilation. Built by
    TaskBuildSymbolTree::visitEnumDecl; items added by `extend enum`
    are merged in by TaskApplyTypeExtensions.
    
    PSS Example::
    
        enum color_e { RED, GREEN = 4, BLUE }   // one SymbolEnumScope
    
    See Also:
        SymbolScope, EnumDecl, EnumItem, ExtendEnum
    
    Attributes:
        decl: The EnumDecl this scope was built from. A back-pointer
            only (visit: false) -- see TaskBuildSymbolTree::visitEnumDecl
            for why this must not be a traversal edge. Used to reach the
            enum's base type (packed-struct and sizeof_s checks).
    
    """
    pass
    
    def getDecl(self) -> EnumDecl: ...
    
class SymbolExtendScope(SymbolScope):
    """
    Symbol scope for PSS extend statements.
    
    Represents one `extend` statement (an ExtendType, its `target`) in
    the linked symbol tree. TaskBuildSymbolTree::visitExtendType builds
    it, named `<extend>` and synthetic, and collects the extension's
    members and imports in it. TaskApplyTypeExtensions then merges those
    members, and the imports, into the extended type's symbol scope, so
    that one type can be augmented from several places, across
    compilation units.
    
    PSS Example::
    
        extend component pss_top {   // one SymbolExtendScope
            int extra;
        }
    
    Has no fields of its own: `children` holds the extension's members
    and `target` the ExtendType (both inherited from
    SymbolChildrenScope).
    
    See Also:
        SymbolScope, ExtendType, ExtendEnum, SymbolTypeScope
    
    """
    pass
    
class SymbolFunctionScope(SymbolScope):
    """
    Symbol scope for functions with overload resolution support.
    
    Represents a function in the linked symbol tree, collecting every
    declaration of one function name: prototypes, `import` declarations,
    and the definition. There is one such scope per function name, not
    one per signature: later declarations must agree with the first,
    which the linker checks (TaskBuildSymbolTree).
    
    During linking, function prototypes from different files are collected,
    import specifications are recorded, and the body (if present) is
    linked. The plist holds the function's parameters. Built by
    TaskBuildSymbolTree (visitFunctionDefinition, visitFunctionPrototype,
    visitFunctionImportProto, visitTargetTemplateFunction).
    
    PSS Example::
    
        function int add(int a, int b);                 // a prototype
        function int add(int a, int b) { return a+b; }  // the definition
    
    Attributes:
        prototypes: Every FunctionPrototype declared for the name; a
            definition's prototype is put first
        import_specs: One FunctionImport per `import ... function`
            declaration of the function, recording its platform
            qualifier (`solve` or `target`); owned copies made by the
            linker, with an empty language
        definition: Meant to point to the FunctionDefinition. Not set
            by the linker: it is always null; the definition is
            `target`, and its body is `body`
        plist: The function's parameters: a scope named `<plist>`
            holding the FunctionParamDecl nodes of the first prototype
            seen, re-bound to a definition's own parameter names
            (`ElemKind_ArgIdx` indexes it)
        body: The ExecScope of the function's definition; null for a
            function that is only declared, imported, or a target
            template. Reached by an `ElemKind_ChildIdx` step equal to
            the number of children
    
    See Also:
        SymbolScope, FunctionPrototype, FunctionDefinition, FunctionImport
    
    """
    pass
    
    def prototypes(self) -> ListUtil[FunctionPrototype]: ...
    def getPrototypes(self) -> List[FunctionPrototype]: ...
    def getPrototype(self, i: int) -> FunctionPrototype: ...
    def addPrototype(self, i: FunctionPrototype) -> None: ...
    def numPrototypes(self) -> int: ...
    
    def import_specs(self) -> ListUtil[FunctionImport]: ...
    def getImport_specs(self) -> List[FunctionImport]: ...
    def getImport_spec(self, i: int) -> FunctionImport: ...
    def addImport_spec(self, i: FunctionImport) -> None: ...
    def numImport_specs(self) -> int: ...
    
    def getDefinition(self) -> FunctionDefinition: ...
    
    def getPlist(self) -> SymbolScope: ...
    
    def getBody(self) -> ExecScope: ...
    
class SymbolTypeScope(SymbolScope):
    """
    Symbol scope for type declarations (actions, components, structs).
    
    Represents a user-defined type in the linked symbol tree, managing its
    members, methods, and constraints. Supports template specialization by
    tracking parameter lists and specialized type instantiations. Built
    for each TypeScope by TaskBuildSymbolTree::visitTypeScope (synthetic,
    `target` the declaration); the builtin types `array`, `list`, `map`,
    `set`, `string` and `pyobj` have one too.
    
    During linking, type declarations from multiple files can be merged
    (for extend statements) and specialized instances are tracked separately.
    The plist holds template parameters, while spec_types contains any
    specialized/instantiated versions of this generic type.
    
    Attributes:
        plist: Template parameter list scope, named `<plist>`, holding the
            TemplateParamDecl nodes of a generic type (`ElemKind_ParamIdx`
            indexes it); null for a non-template type
        spec_types: The specializations of this generic type, one per
            distinct argument list used, in the order they were first
            needed (`ElemKind_TypeSpec` indexes it). Built by the linker
            (TaskGetSpecializedTemplateType); empty for a non-template
            type
    
    See Also:
        SymbolScope, Action, Component, Struct, SymbolExtendScope, SymbolExtMember
    
    """
    pass
    
    def getPlist(self) -> SymbolScope: ...
    
    def spec_types(self) -> ListUtil[SymbolTypeScope]: ...
    def getSpec_types(self) -> List[SymbolTypeScope]: ...
    def getSpec_type(self, i: int) -> SymbolTypeScope: ...
    def addSpec_type(self, i: SymbolTypeScope) -> None: ...
    def numSpec_types(self) -> int: ...
    
    def ext_members(self) -> ListUtil[SymbolExtMember]: ...
    def getExt_members(self) -> List[SymbolExtMember]: ...
    def getExt_member(self, i: int) -> SymbolExtMember: ...
    def addExt_member(self, i: SymbolExtMember) -> None: ...
    def numExt_members(self) -> int: ...
    
class TemplateElem(SymbolScope):
    """
    Base class for one element of a scanned template string.
    
    Every element records where it came from in the owning
    TemplateString's ``raw`` text.  A ``Location`` is not enough for a
    renderer that wants to splice, so byte offsets are carried as well.
    The element's location is that of its first byte in the file.
    
    Note this derives from SymbolScope rather than plain ScopeChild.
    Only the block elements actually need a symbol table, but the name
    resolution machinery requires a scope pushed onto the resolution
    stack to be an ISymbolScope -- ``AstSymbolTableIterator::
    getSymScopeBack()`` silently *erases* anything else from the stack.
    Keeping one hierarchy avoids duplicating offset/extent across two
    parallel ones.  The ``name`` inherited from SymbolChildrenScope is a
    fixed kind tag (``<template-text>``, ``<template-if>``, ...), which
    also makes the resolver's debug output readable.
    
    A closing `{%%}` directive produces no element of its own; it ends
    the `body` of the innermost open TemplateBlock.
    
    Attributes:
        offset: Byte offset of the element's first byte (its opening
            delimiter, for a special element) into the owning
            TemplateString's raw text
        extent: Length in bytes, including the delimiters.  A line
            comment's extent includes the newline that ends it.
        is_own_line: True when this element's line holds directives and
            whitespace only.  §4.7.1.2 excludes that whitespace and the
            terminating newline from the expansion; deciding it needs the
            raw text, so the scanner computes it once and records it here
            rather than making every renderer re-scan.  Computed only for
            directives and comments; always false for TemplateText and
            TemplateExpr, and a line holding a mustache expression is
            never own-line.
    
    See Also:
        TemplateString, TemplateBlock, TemplateText, TemplateExpr,
        TemplateComment
    
    """
    pass
    
class ExecScope(SymbolScope):
    """
    A brace-delimited list of procedural statements with its own local
    variables -- LRM 20.7.1, `procedural_sequence_block_stmt`.
    
    The parser builds an ExecScope for the body of a native function
    (named `<func-body>`) and for every nested `{ ... }` or
    `sequence { ... }` block inside procedural code (named
    `<sequence>`); the `sequence` keyword is not recorded. ExecBlock
    derives from it for the exec block itself. Its children are the
    statements in source order; local variables declared in it are
    entered in its symbol table by the parser.
    
    PSS Example::
    
        component pss_top {
            action my_action {
                exec post_solve {          // ExecBlock (an ExecScope)
                    int local_var = 5;
                    {                      // nested ExecScope
                        int nested_var = 10;
                    }
                }
            }
        }
    
    Attributes:
        endLocation: Source location of the closing brace
    
    See Also:
        ExecBlock, SymbolScope, FunctionDefinition, ProceduralStmtDataDeclaration
    
    """
    pass
    
class TemplateString(SymbolScope):
    """
    Parsed body of one triple-quoted string that contains special
    elements -- PSS 3.1 §4.7.1.
    
    A triple-quoted string stops being a leaf and becomes a *scope* when
    it contains mustache expressions, control-flow directives or
    embedded comments: the expressions resolve against the enclosing
    model, and the directives declare variables of their own.
    
    A triple-quoted string containing **no** special elements does not
    get a TemplateString at all -- it stays a plain ExprString.  "Has
    specials" is therefore a type test rather than a list-length test.
    A plain `"..."` string never gets one either.
    
    The parser builds it for a triple-quoted string used as an
    expression (held by ExprTemplateString), as the body or file name of
    a target-template exec block (ExecTargetTemplateBlock), and as the
    body of a target-template function (TargetTemplateFunction). Its
    `name` is the fixed tag `<template>`, and its location is that of
    the first content byte after the opening quotes.
    
    PSS Example::
    
        action a {
            int size;
            exec body C = \"\"\"
                {# a block comment, not scanned for specials #}
                {% if (size > 0) %}
                memset(buf, 0, {{size}});
                {%%}
            \"\"\";
        }
    
    Attributes:
        raw: Verbatim content with the enclosing quotes stripped.  Kept
            lossless so a formatter that cannot render a template
            structurally can still copy it byte for byte.  Every
            element's `offset` is relative to it.
        elems: The top-level elements, in source order.  Elements
            inside a block are in that block's `body`, not here.
        is_const: True when every expression in the template --
            mustache expressions and the expressions in directives --
            references only constants: constant fields, enum items,
            template value parameters, and template locals that hold
            constant values (§4.7).  A function call is never
            constant.  Set by the linker (TaskTemplateCheck, run from
            TaskResolveRefs once the template is resolved); false
            until then.
        symtab: Names of the variables declared by top-level
            `{% data_type ...; %}` directives (inherited from
            SymbolScope).  The declarations themselves are this
            node's children.
    
    See Also:
        TemplateElem, ExprTemplateString, ExecTargetTemplateBlock,
        TargetTemplateFunction
    
    """
    pass
    
    def getRaw(self) -> str: ...
    
    def setRaw(self, v : str): ...
    
    def elems(self) -> ListUtil[TemplateElem]: ...
    def getElems(self) -> List[TemplateElem]: ...
    def getElem(self, i: int) -> TemplateElem: ...
    def addElem(self, i: TemplateElem) -> None: ...
    def numElems(self) -> int: ...
    
class ActivityAtomicBlock(ActivityLabeledScope):
    """
    An atomic block: `atomic { ... }` -- LRM 11.3.7,
    `activity_atomic_block_stmt`.
    
    Preserves the scheduling structure of its sub-activity against
    interference from the rest of the scenario: all actions traversed in
    the block form one scheduling cluster, which behaves like a single
    atomic action. Dependencies of any action in the block on outside
    actions become dependencies of the whole block, and an outside action
    that depends on any action in the block depends on the whole block.
    
    PSS Example::
    
        activity {
            do bring_up;
            atomic {
                do A;
                do B;           // nothing inferred between A and B
            }
        }
    
    Attributes:
        body: The braced block, built as an ActivitySequence located at the
            braces; never null.
    
    See Also:
        ActivitySequence, ActivityParallel
    
    """
    pass
    
    def getBody(self) -> ScopeChild: ...
    
class ActivityForeach(ActivityLabeledScope):
    """
    Iterates over a collection: `foreach ( [it :] coll [ [idx] ] ) stmt`
    -- LRM 11.4.3, `activity_foreach_stmt`.
    
    Traverses its body once per element of an array, list, map or set,
    with an optional iterator variable bound to the current element and an
    optional index variable bound to its index (key, for a map). The
    builder declares the iterator and index as the loop's children
    (ProceduralStmtDataDeclaration), in that order; the iterator is typed
    from the collection's element type by the linker (TaskResolveRefs).
    
    PSS Example::
    
        action top {
            A handles[4];
            rand bit[8] vals[4];
            activity {
                foreach (h : handles) {
                    h;
                }
                foreach (v : vals[i]) {
                    do A with { addr == v + i; }
                }
                foreach (vals[j]) {
                    do A with { addr == vals[j]; }
                }
            }
        }
    
    Attributes:
        it_id: The `iterator_identifier`, or null when absent.
        idx_id: The `index_identifier`, or null when absent. Written as
            `coll[j]`, the subscript first parses as part of the collection
            expression; the builder lifts it out into this field.
        path: Reference path to the collection being iterated (named
            ``path``, as on ProceduralStmtForeach: ``target`` is the
            SymbolScope field naming the scope's AST node). Null when the
            collection expression is not a reference; the builder reports
            an error then.
        body: The statement traversed per element: an ActivitySequence for a
            braced body, the statement itself otherwise, or an empty
            ActivitySequence when the body built nothing.
    
    See Also:
        ActivityRepeatCount, ActivityRepeatWhile, ProceduralStmtForeach
    
    """
    pass
    
    def getIt_id(self) -> ExprId: ...
    
    def getIdx_id(self) -> ExprId: ...
    
    def getPath(self) -> ExprRefPathContext: ...
    
    def getBody(self) -> ScopeChild: ...
    
class ActivityIfElse(ActivityLabeledScope):
    """
    Conditional traversal: `if ( cond ) stmt [ else stmt ]` -- LRM 11.4.5,
    `activity_if_else_stmt`.
    
    Traverses the first statement when the condition is true, the `else`
    statement (if any) otherwise. Unlike `select`, the choice is
    determined by the condition. An `else if` is an ActivityIfElse as the
    `false_s` statement.
    
    PSS Example::
    
        action top {
            rand bit[8] mode;
            activity {
                if (mode > 5) {
                    do A;
                } else if (mode == 0) {
                    do B;
                } else {
                    do C;
                }
            }
        }
    
    Attributes:
        cond: The `( expression )` condition.
        true_s: The statement traversed when the condition is true: an
            ActivitySequence for a braced body, the statement itself
            otherwise. Null when the statement built nothing (`if (c) ;`).
        false_s: The `else` statement, or null when there is no `else` (or
            it built nothing).
    
    Note:
        The branches are typed ScopeChild rather than ActivityStmt because a
        braced body is built as an ActivitySequence, which descends from
        ActivityLabeledScope/SymbolScope and shares only ScopeChild with the
        ActivityStmt branch of the hierarchy. Typing these as ActivityStmt
        silently discarded every block-shaped branch (gap A1).
    
    See Also:
        ActivitySelect, ActivityMatch
    
    """
    pass
    
    def getCond(self) -> Expr: ...
    
    def getTrue_s(self) -> ScopeChild: ...
    
    def getFalse_s(self) -> ScopeChild: ...
    
class ActivityMatch(ActivityLabeledScope):
    """
    Multi-way branch on a value: `match ( expr ) { ... }` -- LRM 11.4.6,
    `activity_match_stmt`.
    
    Traverses the statement of the choice whose open range list contains
    the value of the match expression, or the `default` choice when none
    does. The grammar requires at least one choice.
    
    PSS Example::
    
        action top {
            rand bit[8] opcode;
            activity {
                match (opcode) {
                    [0x00]: do A;
                    [0x01, 0x02]: { do B; do C; }
                    [0x10..0x1F]: do D;
                    default: do E;
                }
            }
        }
    
    Attributes:
        cond: The `match_expression` whose value is matched.
        choices: The `match_choice` alternatives, in source order. Their
            bodies are this scope's bodies, addressed after its (empty)
            children.
    
    See Also:
        ActivityMatchChoice, ActivitySelect, ActivityIfElse
    
    """
    pass
    
    def getCond(self) -> Expr: ...
    
    def choices(self) -> ListUtil[ActivityMatchChoice]: ...
    def getChoices(self) -> List[ActivityMatchChoice]: ...
    def getChoice(self, i: int) -> ActivityMatchChoice: ...
    def addChoice(self, i: ActivityMatchChoice) -> None: ...
    def numChoices(self) -> int: ...
    
class ActivityParallel(ActivityLabeledScope):
    """
    A parallel block: `parallel [join_spec] { ... }` -- LRM 11.3.4,
    `activity_parallel_stmt`.
    
    Its top-level statements are started together and then run without
    further synchronization. By default the statement after the block
    waits for all of them to complete; a join specification changes that.
    The statements, and the handles and `action` fields declared in the
    block, are its `children`.
    
    PSS Example::
    
        activity {
            parallel {
                do A;
                do B;
            }
            parallel join_first(1) {
                do A;
                do B;
            }
        }
    
    Attributes:
        join_spec: The `activity_join_spec`, or null when there is none (wait
            for all).
    
    See Also:
        ActivitySequence, ActivitySchedule, ActivityJoinSpec
    
    """
    pass
    
    def getJoin_spec(self) -> ActivityJoinSpec: ...
    
class ActivityRepeatCount(ActivityLabeledScope):
    """
    A counted loop: `repeat ( [i :] count ) stmt` -- LRM 11.4.1,
    `activity_repeat_stmt`.
    
    Traverses its body `count` times, in sequence. The optional index
    variable ranges from 0 to `count` - 1. The builder also declares it
    as the loop's only child (an untyped ProceduralStmtDataDeclaration),
    so that it is in scope in the body and not after the loop; it is not
    in scope in `count`.
    
    PSS Example::
    
        activity {
            repeat (4) {
                do A;
            }
            repeat (i : 5) {
                do A with { idx == i; }
            }
        }
    
    Attributes:
        loop_var: The `index_identifier`, or null when absent.
        count: The iteration count `expression`.
        body: The repeated statement: an ActivitySequence for a braced
            body, the statement itself otherwise, or an empty
            ActivitySequence when the body built nothing. Never null after
            parsing.
    
    See Also:
        ActivityRepeatWhile, ActivityForeach, ActivityReplicate, ProceduralStmtDataDeclaration
    
    """
    pass
    
    def getLoop_var(self) -> ExprId: ...
    
    def getCount(self) -> Expr: ...
    
    def getBody(self) -> ScopeChild: ...
    
class ActivityRepeatWhile(ActivityLabeledScope):
    """
    A repeat-while loop: `repeat stmt while ( cond );` -- LRM 11.4.2,
    `activity_repeat_stmt`.
    
    Traverses its body, then evaluates the condition, and repeats while it
    is true: the condition is sampled after each iteration, so the body is
    traversed at least once. The condition is of type `bool`.
    
    PSS Example::
    
        action top {
            int count;
            activity {
                repeat {
                    do A;
                } while (count < 10);
            }
        }
    
    Attributes:
        cond: The `while ( expression )` condition, evaluated after each
            iteration.
        body: The repeated statement: an ActivitySequence for a braced
            body, the statement itself otherwise, or an empty
            ActivitySequence when the body built nothing. Never null after
            parsing.
    
    See Also:
        ActivityRepeatCount, ActivityForeach, ProceduralStmtRepeatWhile
    
    """
    pass
    
    def getCond(self) -> Expr: ...
    
    def getBody(self) -> ScopeChild: ...
    
class ActivityReplicate(ActivityLabeledScope):
    """
    In-place expansion: `replicate ( [i :] N ) [ L[] : ] stmt` -- LRM
    11.5.1, `activity_replicate_stmt`.
    
    Expands to N occurrences of its statement in the enclosing activity
    scope. It adds no layer of scheduling or control flow of its own: the
    occurrences are scheduled as the context dictates (in parallel under a
    `parallel` block, in sequence under a sequence). N is a positive
    integer known at solve time. The optional index variable ranges from 0
    to N - 1; the builder declares it as the statement's only child
    (ProceduralStmtDataDeclaration). An optional label array names each
    occurrence `L[0]` ... `L[N-1]` as a named sub-activity.
    
    PSS Example::
    
        activity {
            parallel {
                replicate (4) do A;
            }
            replicate (i : 3) RL[]: {
                do A with { idx == i; }
            }
        }
    
    Attributes:
        idx_id: The `index_identifier`, or null when absent.
        count: The `expression` giving the number of occurrences N.
        it_label: The `label_identifier` of the label array (`RL` in
            `RL[]:`), or null when absent.
        body: The replicated `labeled_activity_stmt`, or an empty
            ActivitySequence when it built nothing.
    
    See Also:
        ActivityRepeatCount, ActivityParallel, ActivityLabeledScope
    
    """
    pass
    
    def getIdx_id(self) -> ExprId: ...
    
    def getCount(self) -> Expr: ...
    
    def getIt_label(self) -> ExprId: ...
    
    def getBody(self) -> ScopeChild: ...
    
class ActivitySchedule(ActivityLabeledScope):
    """
    A schedule block: `schedule [join_spec] { ... }` -- LRM 11.3.5,
    `activity_schedule_stmt`.
    
    Its top-level statements are all traversed, in any order or
    concurrently, subject to the other scheduling constraints and the
    flow-object and resource rules: the tool chooses a legal schedule.
    Scheduling constraints (ActivitySchedulingConstraint) can impose
    relative order on the statements. The statements, and the handles and
    `action` fields declared in the block, are its `children`.
    
    PSS Example::
    
        action top {
            A a1;
            B b1;
            C c1;
            activity {
                schedule {
                    a1;
                    b1;
                    c1;
                }
                constraint sequence { a1, b1 };
            }
        }
    
    Attributes:
        join_spec: The `activity_join_spec`, or null when there is none (wait
            for all).
    
    See Also:
        ActivitySchedulingConstraint, ActivityParallel, ActivitySequence, ActivityJoinSpec
    
    """
    pass
    
    def getJoin_spec(self) -> ActivityJoinSpec: ...
    
class MonitorActivityOverlap(MonitorActivityLabeledScope):
    """
    Overlap block for concurrent sequence monitoring.
    
    The overlapping scenario (LRM 16.3.5,
    `monitor_activity_overlap_stmt`): ``overlap { a; b; }`` matches its
    body statements as ``schedule`` does -- in any order, without
    sharing action executions -- and additionally requires an instant
    at which all of them are active at once.
    
    Like ``concat``, this is an n-ary block and not a binary operator; the
    former ``lhs``/``rhs`` fields modelled an ``a overlap b`` syntax that
    PSS does not have.
    
    PSS Example::
    
        component c {
            action addr_phase { }
            action data_phase { }
    
            monitor concurrent_check {
                addr_phase ap;
                data_phase dp;
    
                activity {
                    overlap {
                        ap;
                        dp;
                    }
                }
            }
        }
    
    Attributes:
        label: Optional identifier expression for the label
            (inherited from MonitorActivityLabeledScope)
    
    See Also:
        MonitorActivityConcat, MonitorActivitySchedule
    
    """
    pass
    
class MonitorActivitySchedule(MonitorActivityLabeledScope):
    """
    Defines a scheduled monitoring block with flexible ordering.
    
    The scheduling scenario (LRM 16.3.8,
    `monitor_activity_schedule_stmt`): ``schedule { a; b; }`` matches
    its body statements in any order, with any overlaps or gaps, as long
    as no action execution is shared between them -- unlike
    ``sequence``, which fixes the order.
    
    PSS Example::
    
        component c {
            action monitor_addr { }
            action monitor_data { }
    
            monitor flexible_protocol {
                monitor_addr ma;
                monitor_data md;
    
                activity {
                    main_check: schedule {
                        ma;
                        md;
                    }
                }
            }
        }
    
    Attributes:
        label: Optional identifier expression for the schedule label
            (inherited from MonitorActivityLabeledScope)
    
    See Also:
        MonitorActivitySequence, MonitorActivityOverlap, ActivitySchedule
    
    """
    pass
    
class MonitorActivitySelect(MonitorActivityLabeledScope):
    """
    Alternative monitoring paths.
    
    The selection scenario (LRM 16.3.6, `monitor_activity_select_stmt`):
    ``select { a; b; }`` is matched by a match of any one of its
    alternatives. The grammar requires at least two.
    
    The alternatives are the scope's children. The class previously held a
    ``branches`` list of MonitorActivitySelectBranch, each with a guard
    expression -- a guarded form that exists for action ``select`` but not
    for monitor ``select``, so no branch was ever constructible. That
    class has been removed.
    
    PSS Example::
    
        component c {
            action fast_path { }
            action slow_path { }
    
            monitor protocol_variants {
                fast_path fp;
                slow_path sp;
    
                activity {
                    protocol_choice: select {
                        fp;
                        sp;
                    }
                }
            }
        }
    
    Attributes:
        label: Optional identifier expression for the select label
            (inherited from MonitorActivityLabeledScope)
    
    See Also:
        MonitorActivitySequence, ActivitySelect
    
    """
    pass
    
class MonitorActivitySequence(MonitorActivityLabeledScope):
    """
    Defines a sequential monitoring block.
    
    The sequential scenario (LRM 16.3.2,
    `monitor_activity_sequence_block_stmt`): its body statements are
    matched in order, each at or after the match point of the previous
    one, so arbitrary gaps are allowed between them. The ``sequence``
    keyword is optional -- a bare braced block inside a monitor activity
    is a sequence. An empty block is the empty scenario (LRM 16.3.7).
    
    PSS Example::
    
        component c {
            action start_phase { }
            action data_phase { }
            action end_phase { }
    
            monitor transaction_check {
                start_phase s;
                data_phase d;
                end_phase e;
    
                activity {
                    sequence {
                        s;
                        d;
                        e;
                    }
    
                    // The keyword is optional
                    {
                        s;
                        eventually e;
                    }
                }
            }
        }
    
    Attributes:
        label: Optional identifier expression for the sequence label
            (inherited from MonitorActivityLabeledScope)
    
    See Also:
        MonitorActivityConcat, MonitorActivitySchedule, ActivitySequence
    
    """
    pass
    
class MonitorActivityConcat(MonitorActivityLabeledScope):
    """
    Temporal concatenation block.
    
    The concatenation scenario (LRM 16.3.3,
    `monitor_activity_concat_stmt`): ``concat { a; b; c; }`` matches
    each body statement starting exactly at the match point of the
    previous one, with no gap -- the distinction from ``sequence``,
    which permits gaps.
    
    Note this is an n-ary block, not a binary operator: PSS has no ``##``
    concatenation operator, and the class previously modelled one with
    ``lhs``/``rhs`` fields that no source could produce.
    
    PSS Example::
    
        component c {
            action phase1 { }
            action phase2 { }
    
            monitor protocol_monitor {
                phase1 p1;
                phase2 p2;
    
                activity {
                    concat {
                        p1;
                        p2;
                    }
                }
            }
        }
    
    Attributes:
        label: Optional identifier expression for the label
            (inherited from MonitorActivityLabeledScope)
    
    See Also:
        MonitorActivityOverlap, MonitorActivitySequence
    
    """
    pass
    
class ActivitySelect(ActivityLabeledScope):
    """
    Traverses one of several branches: `select { ... }` -- LRM 11.4.4,
    `activity_select_stmt`.
    
    Each evaluation traverses exactly one enabled branch. A branch is
    enabled when it has no guard or its guard is true. When any branch has
    a weight, a branch without one weighs 1, and the probability of a
    branch is its weight over the sum of the enabled branches' weights.
    The grammar requires at least two branches.
    
    PSS Example::
    
        action top {
            rand bit[2] mode;
            activity {
                select {
                    do A;
                    do B;
                }
                select {
                    [70]: do A;
                    (mode == 0)[20]: do B;
                    (mode != 0): do C;
                }
            }
        }
    
    Attributes:
        branches: The `select_branch` alternatives, in source order. The
            branch bodies are this scope's bodies, addressed after its
            (empty) children. A bare `;` with no guard or weight, as
            after `do A with { ... };`, terminates the statement before
            it and is not a branch; an empty branch is written `{ }`.
    
    See Also:
        ActivitySelectBranch, ActivityMatch, ActivityIfElse
    
    """
    pass
    
    def branches(self) -> ListUtil[ActivitySelectBranch]: ...
    def getBranches(self) -> List[ActivitySelectBranch]: ...
    def getBranche(self, i: int) -> ActivitySelectBranch: ...
    def addBranche(self, i: ActivitySelectBranch) -> None: ...
    def numBranches(self) -> int: ...
    
class MonitorActivityEventually(MonitorActivityLabeledScope):
    """
    The eventuality scenario (LRM 16.3.4,
    `monitor_activity_eventually_stmt`).
    
    ``eventually <stmt>`` matches its operand starting at any checkpoint
    at or after the current one, rather than only at the current one --
    ``eventually r;`` matches some later ``r``, not just the next. The
    LRM makes the operand a full ``monitor_activity_stmt``, so it may be
    a traversal or a whole block.
    
    The class previously carried a ``condition`` expression as well as a
    body. There is no such expression in the grammar -- ``eventually``
    takes a statement and nothing else -- and the field was always null.
    
    PSS Example::
    
        component c {
            action request { }
            action response { }
    
            monitor liveness_check {
                request rq;
                response rs;
    
                activity {
                    sequence {
                        rq;
                        eventually rs;
                    }
    
                    eventually {
                        rq;
                        rs;
                    }
                }
            }
        }
    
    Attributes:
        body: The operand statement, built as any monitor activity
            statement is: a traversal, a constraint, or a block (a
            braced operand is a MonitorActivitySequence). Typed
            ScopeChild because a block is a scope rather than a
            MonitorActivityStmt. Null when the operand builds no
            statement node (a bare ``;``, or an annotation). Set by
            the parser.
        label: Optional label (inherited from
            MonitorActivityLabeledScope)
    
    See Also:
        MonitorActivityLabeledScope, MonitorActivitySequence,
        MonitorActivityStmt
    
    """
    pass
    
    def getBody(self) -> ScopeChild: ...
    
class ActivitySequence(ActivityLabeledScope):
    """
    A sequential block: `sequence { ... }` or a bare `{ ... }` -- LRM
    11.3.3, `activity_sequence_block_stmt`.
    
    Its statements are traversed in order, each completing before the next
    starts. The statements, and the handles and `action` fields declared in
    the block, are its `children`.
    
    The builder also makes an ActivitySequence for the braces of an
    `atomic` block (ActivityAtomicBlock's `body`), and substitutes an empty,
    unlocated one for a compound statement's body that built no statement
    (`repeat (3) ;`), so such a body is never null.
    
    PSS Example::
    
        activity {
            sequence {
                do A;
                do B;
            }
            setup: {
                do C;
                do D;
            }
        }
    
    See Also:
        ActivityParallel, ActivitySchedule, ActivityAtomicBlock, ActivityLabeledScope
    
    """
    pass
    
class ProceduralStmtForeach(ProceduralStmtSymbolBodyScope):
    """
    Foreach loop over a collection -- LRM 20.7.8,
    `foreach ( [ iterator_identifier : ] expression [ [ index_identifier ] ] ) procedural_stmt`.
    
    Runs the body once per element of an array, list, map or set. The
    iterator variable holds the current element; the index variable
    holds the array/list position or the map key (a set takes no
    index). At least one of the two must be written.
    
    The node is a symbol scope named `<foreach>`. For each variable
    written, the parser adds a child ProceduralStmtDataDeclaration with
    a null type and enters it in the symbol table: the iterator first,
    then the index. The linker (TaskResolveRefs) later gives the
    iterator's declaration the collection's element type. The body is
    held in `body`, not among the children.
    
    PSS Example::
    
        component pss_top {
            int values[10];
            int total;
            exec init_up {
                foreach (v : values) {          // iterator only
                    total += v;
                }
                foreach (values[i]) {           // index only
                    values[i] = i;
                }
                foreach (v : values[i]) {       // both
                    total += v * i;
                }
            }
        }
    
    Attributes:
        path: The collection expression. The grammar parses
            `values[i]` as a subscripted path, so the parser lifts a
            trailing single-name subscript back out as the index
            variable. Null when the collection is not an
            ExprRefPathContext (e.g. a type-qualified `pkg::arr`); the
            expression is then dropped.
        it_id: The iterator variable's name, or null when none is
            written
        idx_id: The index variable's name, or null when none is written
        body: The loop body (inherited); null if the body is an empty
            statement (`;`)
    
    See Also:
        ProceduralStmtRepeat, ProceduralStmtWhile, ExprRefPathContext, ActivityForeach
    
    """
    pass
    
    def getPath(self) -> ExprRefPath: ...
    
    def getIt_id(self) -> ExprId: ...
    
    def getIdx_id(self) -> ExprId: ...
    
class ProceduralStmtRepeat(ProceduralStmtSymbolBodyScope):
    """
    Repeat-count loop -- LRM 20.7.6,
    `repeat ( [ index_identifier : ] expression ) procedural_stmt`.
    
    Runs the body the number of times the count expression gives (not
    at all if it is 0). The optional index variable ranges from 0 to one
    less than the count.
    
    The node is a symbol scope named `<repeat>`. The parser always adds
    one child, a ProceduralStmtDataDeclaration with a null type that
    declares the index variable; when no index is written the child is
    named `_` and is not entered in the symbol table. The body is held
    in `body`, not among the children.
    
    PSS Example::
    
        component pss_top {
            action my_action {
                int total;
                exec post_solve {
                    repeat (10) {
                        total += 1;
                    }
    
                    repeat (i : 5) {        // i = 0, 1, 2, 3, 4
                        total += i;
                    }
                }
            }
        }
    
    Attributes:
        it_id: The index variable's name (the LRM's
            `index_identifier`), or null when none is written
        count: The iteration-count expression. Always set.
        body: The loop body (inherited); null if the body is an empty
            statement (`;`)
    
    See Also:
        ProceduralStmtRepeatWhile, ProceduralStmtWhile, ProceduralStmtForeach
    
    """
    pass
    
    def getIt_id(self) -> ExprId: ...
    
    def getCount(self) -> Expr: ...
    
class TemplateAssign(TemplateElem):
    """
    A template variable assignment -- §4.7.1.2, Table 5.
    
    ``{% identifier = expression ; %}``
    
    §4.7.1.2 restricts the target: it may only be a variable *previously
    declared within the same triple-quoted string*.  Assigning to an
    action attribute is illegal, and nothing about the syntax
    distinguishes the two cases -- the only way to tell them apart is to
    ask which symtab the name resolved through.  That is why template
    locals must be real symbols in a real scope rather than a side table.
    
    PSS Example::
    
        exec body C = \"\"\"
            {% int total = 0; %}
            {% total = size + 1; %}
            r = {{total}};
        \"\"\";
    
    Attributes:
        lhs: The assignment target: a bare identifier.  The linker
            (TaskResolveRefs) sets the ExprId's ``decl`` to the
            declaration it names -- even when the assignment is illegal
            -- and reports a target not declared in this template.
        rhs: The assigned expression
    
    See Also:
        TemplateVarDecl
    
    """
    pass
    
    def getLhs(self) -> ExprRefName: ...
    
    def getRhs(self) -> Expr: ...
    
class TemplateBlock(TemplateElem):
    """
    Base class for a control-flow directive that opens a block.
    
    §4.7.1.2: a foreach iterator/index, a repeat index, and a variable
    declaration are "added to the scope until the block closing
    directive, and can be referenced in mustache expressions and other
    control-flow directives within this block."  That is what makes a
    block a scope.
    
    The variables are synthesized as ProceduralStmtDataDeclaration nodes
    and registered in this node's own symtab, exactly as
    ProceduralStmtForeach does for a procedural loop -- which means
    ``{% int x; %}`` and a procedural ``int x;`` resolve through one path.
    The declarations are this node's children (``getChildren()``),
    separate from ``body``.  The block's `offset`, `extent` and location
    are those of its opening directive only.
    
    Attributes:
        body: Elements between this directive and the directive that
            ends it -- its ``{%%}``, or for an if/else-if arm the next
            ``{% else ... %}``.  Empty for an empty block.
        symtab: Names of the variables this block introduces: a foreach
            iterator and index, a repeat index, and variables declared
            directly in the body (inherited from SymbolScope)
    
    See Also:
        TemplateIfClause, TemplateIf, TemplateForeach, TemplateRepeat,
        TemplateVarDecl
    
    """
    pass
    
    def body(self) -> ListUtil[TemplateElem]: ...
    def getBodyList(self) -> List[TemplateElem]: ...
    def getBody(self, i: int) -> TemplateElem: ...
    def addBody(self, i: TemplateElem) -> None: ...
    def numBody(self) -> int: ...
    
class TemplateComment(TemplateElem):
    """
    A template comment -- ``{# ... #}`` or ``{#}`` to end of line,
    §4.7.1.3.
    
    Comment content is **not** processed for special elements: a ``{{``
    inside a comment is literal text.
    
    Comments are retained rather than discarded.  Evaluation drops them,
    but *parsing* must not, or a formatter loses the user's comments.
    Dropping is the renderer's job.
    
    PSS Example::
    
        exec body C = \"\"\"
            {# not expanded: {{size}} #}
            nop; {#} rest of the line is a comment
        \"\"\";
    
    Attributes:
        text: Comment content, excluding the delimiters (and, for the
            line form, excluding the terminating newline)
        is_line: True for the ``{#}`` line form, false for ``{# ... #}``
    
    See Also:
        TemplateElem
    
    """
    pass
    
    def getText(self) -> str: ...
    
    def setText(self, v : str): ...
    
class TemplateExpr(TemplateElem):
    """
    A mustache expression -- ``{{ expression }}``, §4.7.1.1.
    
    The expression is parsed by the ordinary PSS expression grammar and
    resolves against whatever is referenceable at that point in the
    source, including template-local variables of enclosing blocks.
    §4.7.1.1 additionally requires the type to be scalar and any
    function called to be ``pure``; the linker checks both
    (TaskResolveRefs, TaskTemplateCheck).  A mustache whose content does
    not parse as an expression is reported and produces no element.
    
    PSS Example::
    
        exec body C = \"\"\" stw {{addr}}, {{value}} \"\"\";
    
    Attributes:
        expr: The parsed expression between the braces.  Its locations
            are file positions inside the string.
    
    See Also:
        TemplateElem, TemplateString
    
    """
    pass
    
    def getExpr(self) -> Expr: ...
    
class ExecBlock(ExecScope):
    """
    A procedural exec block -- LRM 20.1, `exec_block`:
    `exec exec_kind { exec_stmt ... }`.
    
    Declared in an action, component, flow/resource object or struct,
    it holds PSS procedural statements to run at the point the kind
    names (pre_solve, body, init_up, ...). Several blocks of one kind
    in a scope act as one block, in source order (20.1.1 d). A derived
    type's block replaces the base type's block of the same kind unless
    it calls `super;` (20.1.4.1). The parser names every ExecBlock
    `<exec>`. The target-template form (`exec kind Lang = "...";`) is
    an ExecTargetTemplateBlock instead.
    
    PSS Example::
    
        component pss_top {
            action my_action {
                rand int x;
                int y;
    
                exec pre_solve {
                    y = 5;
                }
    
                exec post_solve {
                    y = x + 1;
                }
            }
        }
    
    Attributes:
        kind: Which exec block this is, from `exec_kind`. An unknown
            kind name is reported as an error and built as
            ExecKind_Body.
    
    See Also:
        ExecKind, ExecScope, ExecTargetTemplateBlock, ProceduralStmtSuper
    
    """
    pass
    
    def getKind(self) -> int: ...
    def setKind(self, v : ExecKind | int) -> None: ...
    
class TemplateIf(TemplateElem):
    """
    A template if directive with its else-if and else arms -- §4.7.1.2.
    
    The clauses are held **flat**, not as a tree of nested ifs.  The
    source is a flat directive sequence, so nesting would be an invention
    a formatter would then have to undo.  The node itself declares no
    variables; each arm is its own scope.  Its `offset`, `extent` and
    location are those of the opening ``{% if (...) %}`` directive.
    
    PSS Example::
    
        exec body C = \"\"\"
            {% if (size == 0) %} empty {% else if (size < 4) %} small {% else %} large {%%}
        \"\"\";
    
    Attributes:
        clauses: if / else-if / else arms, in source order.  The first
            is always the ``if`` arm.
    
    See Also:
        TemplateIfClause, TemplateBlock
    
    """
    pass
    
    def clauses(self) -> ListUtil[TemplateIfClause]: ...
    def getClauses(self) -> List[TemplateIfClause]: ...
    def getClause(self, i: int) -> TemplateIfClause: ...
    def addClause(self, i: TemplateIfClause) -> None: ...
    def numClauses(self) -> int: ...
    
class TemplateText(TemplateElem):
    """
    A run of literal text between special elements of a triple-quoted
    string (§4.7.1).
    
    Everything that is not a mustache expression, a control-flow
    directive or an embedded comment is literal text, including a lone
    `{` (so `{ {` spells a literal double brace).  The text is kept
    exactly as written: removing the whitespace and newline of a line
    that holds only directives (§4.7.1.2) is left to the renderer, which
    uses the neighbouring elements' `is_own_line`.
    
    PSS Example::
    
        exec body C = \"\"\" stw {{addr}}, {{value}} \"\"\";
        // TemplateText elements: " stw ", ", ", " "
    
    Attributes:
        text: The literal text, verbatim -- the bytes
            `raw[offset, offset+extent)` of the owning TemplateString
    
    See Also:
        TemplateElem, TemplateExpr, TemplateString
    
    """
    pass
    
    def getText(self) -> str: ...
    
    def setText(self, v : str): ...
    
class TemplateVarDecl(TemplateElem):
    """
    A template variable declaration -- §4.7.1.2, Table 5.
    
    ``{% data_type procedural_data_instantiation { , procedural_data_instantiation } ; %}``
    
    The declarations are ProceduralStmtDataDeclaration nodes, the same
    node a procedural ``int x;`` produces, so both resolve through one
    path.  They are registered in the enclosing TemplateBlock's (or
    TemplateString's) symtab, which makes each variable visible to the
    later elements of that block and invisible after its ``{%%}``.  A
    name already declared in the same scope is reported as a duplicate.
    
    PSS Example::
    
        exec body C = \"\"\"
            {% int total = 0, n; %}
            r = {{total}};
        \"\"\";
    
    Attributes:
        decls: The declared variables, one per
            ``procedural_data_instantiation``, in source order.  The
            entries do not own their nodes: each declaration is owned
            by the children list of the enclosing TemplateBlock or
            TemplateString.
    
    See Also:
        TemplateAssign, TemplateBlock, ProceduralStmtDataDeclaration
    
    """
    pass
    
    def decls(self) -> ListUtil[ProceduralStmtDataDeclaration]: ...
    def getDecls(self) -> List[ProceduralStmtDataDeclaration]: ...
    def getDecl(self, i: int) -> ProceduralStmtDataDeclaration: ...
    def addDecl(self, i: ProceduralStmtDataDeclaration) -> None: ...
    def numDecls(self) -> int: ...
    
class TemplateForeach(TemplateBlock):
    """
    A template foreach directive -- §4.7.1.2, Table 5.
    
    ``{% foreach ( [ iterator_identifier : ] expression [ [ index_identifier ] ] ) %}``
    
    Iterates over a collection, emitting its body once per element.  The
    iterator and index, when written, are declared as variables of this
    block: the parser synthesizes an untyped ProceduralStmtDataDeclaration
    for each and adds it to the block's children and symtab.
    
    PSS Example::
    
        exec body C = \"\"\"
            {% foreach (v : vals[i]) %}
            buf[{{i}}] = {{v}};
            {%%}
        \"\"\";
    
    Attributes:
        expr: The collection expression being iterated, without the
            trailing index.  Resolved in the enclosing scope, so it
            cannot see the loop variables.
        it: Iterator variable identifier, or null if not written
        idx: Index variable identifier, or null if not written.  A
            trailing ``[ i ]`` that the expression grammar parsed as a
            subscript is lifted out of ``expr`` into this field.
    
    See Also:
        TemplateBlock, TemplateRepeat, ProceduralStmtForeach
    
    """
    pass
    
    def getExpr(self) -> Expr: ...
    
    def getIt(self) -> ExprId: ...
    
    def getIdx(self) -> ExprId: ...
    
class TemplateRepeat(TemplateBlock):
    """
    A template repeat directive -- §4.7.1.2, Table 5.
    
    ``{% repeat ( [ index_identifier : ] expression ) %}``
    
    Emits its body the given number of times.  The index, when written,
    is declared as a variable of this block (an untyped, synthesized
    ProceduralStmtDataDeclaration in the block's children and symtab).
    
    PSS Example::
    
        exec body C = \"\"\"
            {% repeat (j : 4) %}
            nop; // iteration {{j}}
            {%%}
        \"\"\";
    
    Attributes:
        expr: The repeat-count expression.  Resolved in the enclosing
            scope.
        idx: Index variable identifier, or null if not written
    
    See Also:
        TemplateBlock, TemplateForeach, ProceduralStmtRepeat
    
    """
    pass
    
    def getExpr(self) -> Expr: ...
    
    def getIdx(self) -> ExprId: ...
    
class TemplateIfClause(TemplateBlock):
    """
    One arm of a template if/else-if/else chain (§4.7.1.2, Table 5).
    
    Built for each ``{% if (...) %}``, ``{% else if (...) %}`` and
    ``{% else %}`` directive and held in the owning TemplateIf's
    ``clauses``.  Its `offset`, `extent`, location and `is_own_line`
    are those of the directive that opens the arm; its body runs to the
    next arm's directive or to the chain's ``{%%}``.  Each arm is a
    separate scope.
    
    PSS Example::
    
        exec body C = \"\"\"
            {% if (a) %} one {% else if (b) %} two {% else %} three {%%}
        \"\"\";
    
    Attributes:
        cond: The guard expression inside the parentheses; null for the
            ``else`` arm.  Resolved in the enclosing scope, not the
            arm's own.
    
    See Also:
        TemplateIf, TemplateBlock
    
    """
    pass
    
    def getCond(self) -> Expr: ...
    
