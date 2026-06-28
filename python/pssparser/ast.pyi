from enum import IntEnum, auto
from typing import Dict, List, Tuple
class AssignOp(IntEnum):
    AssignOp_Eq = auto()
    AssignOp_PlusEq = auto()
    AssignOp_MinusEq = auto()
    AssignOp_ShlEq = auto()
    AssignOp_ShrEq = auto()
    AssignOp_OrEq = auto()
    AssignOp_AndEq = auto()
    
class ExecKind(IntEnum):
    ExecKind_Body = auto()
    ExecKind_Header = auto()
    ExecKind_Declaration = auto()
    ExecKind_RunStart = auto()
    ExecKind_RunEnd = auto()
    ExecKind_InitDown = auto()
    ExecKind_InitUp = auto()
    ExecKind_PreSolve = auto()
    ExecKind_PostSolve = auto()
    
class ExprBinOp(IntEnum):
    BinOp_LogOr = auto()
    BinOp_LogAnd = auto()
    BinOp_BitOr = auto()
    BinOp_BitXor = auto()
    BinOp_BitAnd = auto()
    BinOp_Lt = auto()
    BinOp_Le = auto()
    BinOp_Gt = auto()
    BinOp_Ge = auto()
    BinOp_Exp = auto()
    BinOp_Mul = auto()
    BinOp_Div = auto()
    BinOp_Mod = auto()
    BinOp_Add = auto()
    BinOp_Sub = auto()
    BinOp_Shl = auto()
    BinOp_Shr = auto()
    BinOp_Eq = auto()
    BinOp_Ne = auto()
    
class ExprUnaryOp(IntEnum):
    UnaryOp_Plus = auto()
    UnaryOp_Minus = auto()
    UnaryOp_LogNot = auto()
    UnaryOp_BitNeg = auto()
    UnaryOp_BitAnd = auto()
    UnaryOp_BitOr = auto()
    UnaryOp_BitXor = auto()
    
class ExtendTargetE(IntEnum):
    Action = auto()
    Annotation = auto()
    Buffer = auto()
    Component = auto()
    Enum = auto()
    Resource = auto()
    State = auto()
    Stream = auto()
    Struct = auto()
    
class FunctionParamDeclKind(IntEnum):
    ParamKind_DataType = auto()
    ParamKind_Type = auto()
    ParamKind_RefAction = auto()
    ParamKind_RefComponent = auto()
    ParamKind_RefBuffer = auto()
    ParamKind_RefResource = auto()
    ParamKind_RefState = auto()
    ParamKind_RefStream = auto()
    ParamKind_RefStruct = auto()
    ParamKind_Struct = auto()
    
class ParamDir(IntEnum):
    ParamDir_Default = auto()
    ParamDir_In = auto()
    ParamDir_Out = auto()
    ParamDir_InOut = auto()
    
class PlatQual(IntEnum):
    PlatQual_None = auto()
    PlatQual_Target = auto()
    PlatQual_Solve = auto()
    
class StringMethodId(IntEnum):
    StringMethod_None = auto()
    StringMethod_Size = auto()
    StringMethod_Find = auto()
    StringMethod_FindLast = auto()
    StringMethod_FindAll = auto()
    StringMethod_Lower = auto()
    StringMethod_Upper = auto()
    StringMethod_Split = auto()
    StringMethod_Chars = auto()
    
class StructKind(IntEnum):
    Buffer = auto()
    Struct = auto()
    Resource = auto()
    Stream = auto()
    State = auto()
    
class SymbolRefPathElemKind(IntEnum):
    ElemKind_ChildIdx = auto()
    ElemKind_ArgIdx = auto()
    ElemKind_Inline = auto()
    ElemKind_ParamIdx = auto()
    ElemKind_Super = auto()
    ElemKind_TypeSpec = auto()
    
class TypeCategory(IntEnum):
    Action = auto()
    Component = auto()
    Buffer = auto()
    Resource = auto()
    State = auto()
    Stream = auto()
    Struct = auto()
    
class Location:
    fileid: int
    lineno: int
    linepos: int
    extent: int

class SymbolRefPathElem:
    kind: int
    idx: int

class FieldAttr(IntEnum):
    Action = auto()
    Builtin = auto()
    Rand = auto()
    Const = auto()
    Static = auto()
    Instance = auto()
    Private = auto()
    Protected = auto()
    
class Factory(object):
    def mkAssocData(self) -> 'AssocData': ...
    def mkTemplateParamDeclList(self) -> 'TemplateParamDeclList': ...
    def mkExecTargetTemplateParam(self,
        expr : Expr,
        start : int,
        end : int) -> 'ExecTargetTemplateParam': ...
    def mkExpr(self) -> 'Expr': ...
    def mkTemplateParamValue(self) -> 'TemplateParamValue': ...
    def mkTemplateParamValueList(self) -> 'TemplateParamValueList': ...
    def mkMonitorActivityMatchChoice(self,
        is_default : bool,
        cond : ExprOpenRangeList,
        body : ScopeChild) -> 'MonitorActivityMatchChoice': ...
    def mkExprAggrMapElem(self,
        lhs : Expr,
        rhs : Expr) -> 'ExprAggrMapElem': ...
    def mkExprAggrStructElem(self,
        name : ExprId,
        value : Expr) -> 'ExprAggrStructElem': ...
    def mkRefExpr(self) -> 'RefExpr': ...
    def mkMonitorActivitySelectBranch(self,
        guard : Expr,
        body : ScopeChild) -> 'MonitorActivitySelectBranch': ...
    def mkActivityMatchChoice(self,
        is_default : bool,
        cond : ExprOpenRangeList,
        body : ScopeChild) -> 'ActivityMatchChoice': ...
    def mkScopeChild(self) -> 'ScopeChild': ...
    def mkActivitySelectBranch(self,
        guard : Expr,
        weight : Expr,
        body : ScopeChild) -> 'ActivitySelectBranch': ...
    def mkSymbolImportSpec(self) -> 'SymbolImportSpec': ...
    def mkSymbolRefPath(self) -> 'SymbolRefPath': ...
    def mkGenericConstraintDeclValue(self) -> 'GenericConstraintDeclValue': ...
    def mkActionFieldInitializer(self,
        path : ExprHierarchicalId,
        value : Expr) -> 'ActionFieldInitializer': ...
    def mkGenericConstraintParam(self,
        name : ExprId,
        is_const : bool,
        is_numeric : bool,
        type : DataType) -> 'GenericConstraintParam': ...
    def mkMethodParameterList(self) -> 'MethodParameterList': ...
    def mkActivityJoinSpec(self) -> 'ActivityJoinSpec': ...
    def mkMonitorActivityStmt(self) -> 'MonitorActivityStmt': ...
    def mkNamedScopeChild(self,
        name : ExprId) -> 'NamedScopeChild': ...
    def mkPackageImportStmt(self,
        wildcard : bool,
        alias : ExprId) -> 'PackageImportStmt': ...
    def mkActivitySchedulingConstraint(self,
        is_parallel : bool) -> 'ActivitySchedulingConstraint': ...
    def mkActivityStmt(self) -> 'ActivityStmt': ...
    def mkAnnotation(self,
        type : TypeIdentifier) -> 'Annotation': ...
    def mkAnnotationParam(self,
        value : Expr) -> 'AnnotationParam': ...
    def mkProceduralStmtIfClause(self,
        cond : Expr,
        body : ScopeChild) -> 'ProceduralStmtIfClause': ...
    def mkComponentBind(self,
        pool_path : str,
        is_wildcard : bool) -> 'ComponentBind': ...
    def mkConstraintStmt(self) -> 'ConstraintStmt': ...
    def mkPyImportFromStmt(self) -> 'PyImportFromStmt': ...
    def mkPyImportStmt(self) -> 'PyImportStmt': ...
    def mkRefExprScopeIndex(self,
        base : RefExpr,
        offset : int) -> 'RefExprScopeIndex': ...
    def mkRefExprTypeScopeContext(self,
        base : RefExpr,
        offset : int) -> 'RefExprTypeScopeContext': ...
    def mkCoverStmtInline(self,
        body : ScopeChild) -> 'CoverStmtInline': ...
    def mkCoverStmtReference(self,
        target : ExprRefPath) -> 'CoverStmtReference': ...
    def mkRefExprTypeScopeGlobal(self,
        fileid : int) -> 'RefExprTypeScopeGlobal': ...
    def mkScope(self) -> 'Scope': ...
    def mkScopeChildRef(self,
        target : ScopeChild) -> 'ScopeChildRef': ...
    def mkDataType(self) -> 'DataType': ...
    def mkSymbolChild(self) -> 'SymbolChild': ...
    def mkSymbolScopeRef(self,
        name : str) -> 'SymbolScopeRef': ...
    def mkExecStmt(self) -> 'ExecStmt': ...
    def mkExecTargetTemplateBlock(self,
        kind : ExecKind,
        data : str) -> 'ExecTargetTemplateBlock': ...
    def mkTemplateParamDecl(self,
        name : ExprId) -> 'TemplateParamDecl': ...
    def mkExportFunction(self,
        plat : PlatQual,
        name : ExprId) -> 'ExportFunction': ...
    def mkTemplateParamExprValue(self,
        value : Expr) -> 'TemplateParamExprValue': ...
    def mkTemplateParamTypeValue(self,
        value : DataType) -> 'TemplateParamTypeValue': ...
    def mkExprAggrLiteral(self) -> 'ExprAggrLiteral': ...
    def mkTypeIdentifier(self) -> 'TypeIdentifier': ...
    def mkTypeIdentifierElem(self,
        id : ExprId,
        params : TemplateParamValueList) -> 'TypeIdentifierElem': ...
    def mkTypedefDeclaration(self,
        name : ExprId,
        type : DataType) -> 'TypedefDeclaration': ...
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
        ref : ExprRefPathStatic) -> 'ExprCompileHas': ...
    def mkExprCond(self,
        cond_e : Expr,
        true_e : Expr,
        false_e : Expr) -> 'ExprCond': ...
    def mkExprDomainOpenRangeList(self) -> 'ExprDomainOpenRangeList': ...
    def mkExprDomainOpenRangeValue(self,
        single : bool,
        lhs : Expr,
        rhs : Expr) -> 'ExprDomainOpenRangeValue': ...
    def mkExprHierarchicalId(self) -> 'ExprHierarchicalId': ...
    def mkExprId(self,
        id : str,
        is_escaped : bool) -> 'ExprId': ...
    def mkExprIn(self,
        lhs : Expr,
        rhs : ExprOpenRangeList,
        collection : Expr) -> 'ExprIn': ...
    def mkExprListLiteral(self) -> 'ExprListLiteral': ...
    def mkExprMemberPathElem(self,
        id : ExprId,
        params : MethodParameterList) -> 'ExprMemberPathElem': ...
    def mkExprNull(self) -> 'ExprNull': ...
    def mkExprNumber(self) -> 'ExprNumber': ...
    def mkExprOpenRangeList(self) -> 'ExprOpenRangeList': ...
    def mkExprOpenRangeValue(self,
        lhs : Expr,
        rhs : Expr) -> 'ExprOpenRangeValue': ...
    def mkExprRefPath(self) -> 'ExprRefPath': ...
    def mkExprRefPathElem(self) -> 'ExprRefPathElem': ...
    def mkExprStaticRefPath(self,
        is_global : bool,
        leaf : ExprMemberPathElem) -> 'ExprStaticRefPath': ...
    def mkExprString(self,
        value : str,
        is_raw : bool) -> 'ExprString': ...
    def mkExprStructLiteral(self) -> 'ExprStructLiteral': ...
    def mkExprStructLiteralItem(self,
        id : ExprId,
        value : Expr) -> 'ExprStructLiteralItem': ...
    def mkExprSubscript(self,
        expr : Expr,
        subscript : Expr) -> 'ExprSubscript': ...
    def mkExprSubstring(self,
        expr : Expr,
        start : Expr,
        end : Expr) -> 'ExprSubstring': ...
    def mkExprUnary(self,
        op : ExprUnaryOp,
        rhs : Expr) -> 'ExprUnary': ...
    def mkExtendEnum(self,
        target : TypeIdentifier) -> 'ExtendEnum': ...
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
    def mkActionHandleField(self,
        name : ExprId,
        type : DataType) -> 'ActionHandleField': ...
    def mkActivityBindStmt(self,
        lhs : ExprHierarchicalId) -> 'ActivityBindStmt': ...
    def mkActivityConstraint(self,
        constraint : ConstraintStmt) -> 'ActivityConstraint': ...
    def mkActivityJoinSpecBranch(self) -> 'ActivityJoinSpecBranch': ...
    def mkActivityJoinSpecFirst(self,
        count : Expr) -> 'ActivityJoinSpecFirst': ...
    def mkActivityJoinSpecNone(self) -> 'ActivityJoinSpecNone': ...
    def mkActivityJoinSpecSelect(self,
        count : Expr) -> 'ActivityJoinSpecSelect': ...
    def mkActivityLabeledStmt(self) -> 'ActivityLabeledStmt': ...
    def mkConstraintScope(self) -> 'ConstraintScope': ...
    def mkConstraintStmtDefault(self,
        hid : ExprHierarchicalId,
        expr : Expr) -> 'ConstraintStmtDefault': ...
    def mkConstraintStmtDefaultDisable(self,
        hid : ExprHierarchicalId) -> 'ConstraintStmtDefaultDisable': ...
    def mkConstraintStmtExpr(self,
        expr : Expr) -> 'ConstraintStmtExpr': ...
    def mkConstraintStmtField(self,
        name : ExprId,
        type : DataType) -> 'ConstraintStmtField': ...
    def mkConstraintStmtIf(self,
        cond : Expr,
        true_c : ConstraintScope,
        false_c : ConstraintScope) -> 'ConstraintStmtIf': ...
    def mkConstraintStmtUnique(self) -> 'ConstraintStmtUnique': ...
    def mkCovergroup(self,
        name : ExprId) -> 'Covergroup': ...
    def mkCovergroupCoverpoint(self,
        name : ExprId,
        target : Expr) -> 'CovergroupCoverpoint': ...
    def mkCovergroupCross(self,
        name : ExprId) -> 'CovergroupCross': ...
    def mkDataTypeBool(self) -> 'DataTypeBool': ...
    def mkDataTypeChandle(self) -> 'DataTypeChandle': ...
    def mkDataTypeEnum(self,
        tid : DataTypeUserDefined,
        in_rangelist : ExprOpenRangeList) -> 'DataTypeEnum': ...
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
    def mkExprRefPathId(self,
        id : ExprId) -> 'ExprRefPathId': ...
    def mkExprRefPathStatic(self,
        is_global : bool) -> 'ExprRefPathStatic': ...
    def mkExprRefPathStaticRooted(self,
        root : ExprRefPathStatic,
        leaf : ExprHierarchicalId) -> 'ExprRefPathStaticRooted': ...
    def mkExprSignedNumber(self,
        image : str,
        width : int,
        value : int) -> 'ExprSignedNumber': ...
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
    def mkMonitorActivityActionTraversal(self,
        target : ExprRefPath,
        with_c : ConstraintStmt) -> 'MonitorActivityActionTraversal': ...
    def mkMonitorActivityConcat(self,
        lhs : MonitorActivityStmt,
        rhs : MonitorActivityStmt) -> 'MonitorActivityConcat': ...
    def mkMonitorActivityEventually(self,
        condition : Expr,
        body : MonitorActivityStmt) -> 'MonitorActivityEventually': ...
    def mkMonitorActivityIfElse(self,
        cond : Expr,
        true_s : MonitorActivityStmt,
        false_s : MonitorActivityStmt) -> 'MonitorActivityIfElse': ...
    def mkMonitorActivityMatch(self,
        cond : Expr) -> 'MonitorActivityMatch': ...
    def mkMonitorActivityMonitorTraversal(self,
        target : ExprRefPath,
        with_c : ConstraintStmt) -> 'MonitorActivityMonitorTraversal': ...
    def mkMonitorActivityOverlap(self,
        lhs : MonitorActivityStmt,
        rhs : MonitorActivityStmt) -> 'MonitorActivityOverlap': ...
    def mkMonitorActivityRepeatCount(self,
        loop_var : ExprId,
        count : Expr,
        body : ScopeChild) -> 'MonitorActivityRepeatCount': ...
    def mkMonitorActivityRepeatWhile(self,
        cond : Expr,
        body : ScopeChild) -> 'MonitorActivityRepeatWhile': ...
    def mkMonitorActivitySelect(self) -> 'MonitorActivitySelect': ...
    def mkMonitorConstraint(self,
        constraint : ConstraintStmt) -> 'MonitorConstraint': ...
    def mkNamedScope(self,
        name : ExprId) -> 'NamedScope': ...
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
    def mkProceduralStmtFunctionCall(self,
        prefix : ExprRefPathStaticRooted) -> 'ProceduralStmtFunctionCall': ...
    def mkProceduralStmtIfElse(self) -> 'ProceduralStmtIfElse': ...
    def mkProceduralStmtMatch(self,
        expr : Expr) -> 'ProceduralStmtMatch': ...
    def mkProceduralStmtMatchChoice(self,
        is_default : bool,
        cond : ExprOpenRangeList,
        body : ScopeChild) -> 'ProceduralStmtMatchChoice': ...
    def mkProceduralStmtRandomize(self,
        target : Expr) -> 'ProceduralStmtRandomize': ...
    def mkProceduralStmtReturn(self,
        expr : Expr) -> 'ProceduralStmtReturn': ...
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
    def mkActivityActionHandleTraversal(self,
        target : ExprRefPathContext,
        with_c : ConstraintStmt) -> 'ActivityActionHandleTraversal': ...
    def mkActivityActionTypeTraversal(self,
        target : DataTypeUserDefined,
        with_c : ConstraintStmt) -> 'ActivityActionTypeTraversal': ...
    def mkActivityAtomicBlock(self,
        body : ScopeChild) -> 'ActivityAtomicBlock': ...
    def mkActivityForeach(self,
        it_id : ExprId,
        idx_id : ExprId,
        target : ExprRefPathContext,
        body : ScopeChild) -> 'ActivityForeach': ...
    def mkActivityIfElse(self,
        cond : Expr,
        true_s : ActivityStmt,
        false_s : ActivityStmt) -> 'ActivityIfElse': ...
    def mkActivityMatch(self,
        cond : Expr) -> 'ActivityMatch': ...
    def mkActivityRepeatCount(self,
        loop_var : ExprId,
        count : Expr,
        body : ScopeChild) -> 'ActivityRepeatCount': ...
    def mkActivityRepeatWhile(self,
        cond : Expr,
        body : ScopeChild) -> 'ActivityRepeatWhile': ...
    def mkActivityReplicate(self,
        idx_id : ExprId,
        it_label : ExprId,
        body : ScopeChild) -> 'ActivityReplicate': ...
    def mkActivitySelect(self) -> 'ActivitySelect': ...
    def mkActivitySuper(self) -> 'ActivitySuper': ...
    def mkConstraintBlock(self,
        name : str,
        is_dynamic : bool) -> 'ConstraintBlock': ...
    def mkProceduralStmtRepeatWhile(self,
        body : ScopeChild,
        expr : Expr) -> 'ProceduralStmtRepeatWhile': ...
    def mkProceduralStmtWhile(self,
        body : ScopeChild,
        expr : Expr) -> 'ProceduralStmtWhile': ...
    def mkConstraintStmtForall(self,
        iterator_id : ExprId,
        type_id : DataTypeUserDefined,
        ref_path : ExprRefPath) -> 'ConstraintStmtForall': ...
    def mkConstraintStmtForeach(self,
        expr : Expr) -> 'ConstraintStmtForeach': ...
    def mkConstraintStmtImplication(self,
        cond : Expr) -> 'ConstraintStmtImplication': ...
    def mkSymbolScope(self,
        name : str) -> 'SymbolScope': ...
    def mkTypeScope(self,
        name : ExprId,
        super_t : TypeIdentifier) -> 'TypeScope': ...
    def mkExprRefPathStaticFunc(self,
        is_global : bool,
        params : MethodParameterList) -> 'ExprRefPathStaticFunc': ...
    def mkExprRefPathSuper(self,
        hier_id : ExprHierarchicalId) -> 'ExprRefPathSuper': ...
    def mkAction(self,
        name : ExprId,
        super_t : TypeIdentifier,
        is_abstract : bool) -> 'Action': ...
    def mkMonitor(self,
        name : ExprId,
        super_t : TypeIdentifier) -> 'Monitor': ...
    def mkMonitorActivityDecl(self,
        name : str) -> 'MonitorActivityDecl': ...
    def mkActivityDecl(self,
        name : str) -> 'ActivityDecl': ...
    def mkActivityLabeledScope(self,
        name : str) -> 'ActivityLabeledScope': ...
    def mkMonitorActivitySchedule(self,
        name : str) -> 'MonitorActivitySchedule': ...
    def mkMonitorActivitySequence(self,
        name : str) -> 'MonitorActivitySequence': ...
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
    def mkSymbolEnumScope(self,
        name : str) -> 'SymbolEnumScope': ...
    def mkSymbolExtendScope(self,
        name : str) -> 'SymbolExtendScope': ...
    def mkSymbolFunctionScope(self,
        name : str) -> 'SymbolFunctionScope': ...
    def mkSymbolTypeScope(self,
        name : str,
        plist : SymbolScope) -> 'SymbolTypeScope': ...
    def mkExecScope(self,
        name : str) -> 'ExecScope': ...
    def mkGenericConstraintDeclBool(self,
        name : str,
        is_dynamic : bool) -> 'GenericConstraintDeclBool': ...
    def mkProceduralStmtForeach(self,
        name : str,
        body : ScopeChild,
        path : ExprRefPath,
        it_id : ExprId,
        idx_id : ExprId) -> 'ProceduralStmtForeach': ...
    def mkExecBlock(self,
        name : str,
        kind : ExecKind) -> 'ExecBlock': ...
    def mkProceduralStmtRepeat(self,
        name : str,
        body : ScopeChild,
        it_id : ExprId,
        count : Expr) -> 'ProceduralStmtRepeat': ...
    def mkActivityParallel(self,
        name : str,
        join_spec : ActivityJoinSpec) -> 'ActivityParallel': ...
    def mkActivitySchedule(self,
        name : str,
        join_spec : ActivityJoinSpec) -> 'ActivitySchedule': ...
    def mkActivitySequence(self,
        name : str) -> 'ActivitySequence': ...
    @staticmethod
    def inst() -> 'Factory': ...
    
class AssocData(object):
    pass
    
class TemplateParamDeclList(object):
    pass
    
    def params(self) -> ListUtil...
        """Returns an iterator over the items"""
    
    def getParams(self) -> List[TemplateParamDecl]: ...
    
class ExecTargetTemplateParam(object):
    pass
    
    def getExpr(self) -> Expr: ...
    
class Expr(object):
    pass
    
class TemplateParamValue(object):
    pass
    
class TemplateParamValueList(object):
    pass
    
    def values(self) -> ListUtil...
        """Returns an iterator over the items"""
    
    def getValues(self) -> List[TemplateParamValue]: ...
    
class MonitorActivityMatchChoice(object):
    pass
    
    def getCond(self) -> ExprOpenRangeList: ...
    
    def getBody(self) -> ScopeChild: ...
    
class ExprAggrMapElem(object):
    pass
    
    def getLhs(self) -> Expr: ...
    
    def getRhs(self) -> Expr: ...
    
class ExprAggrStructElem(object):
    pass
    
    def getName(self) -> ExprId: ...
    
    def getValue(self) -> Expr: ...
    
class RefExpr(object):
    pass
    
class MonitorActivitySelectBranch(object):
    pass
    
    def getGuard(self) -> Expr: ...
    
    def getBody(self) -> ScopeChild: ...
    
class ActivityMatchChoice(object):
    pass
    
    def getCond(self) -> ExprOpenRangeList: ...
    
    def getBody(self) -> ScopeChild: ...
    
class ScopeChild(object):
    pass
    
    def getDocstring(self) -> str: ...
    
    def setDocstring(self, v : str): ...
    
    def getLocation(self) -> 'Location': ...
    
    def getParent(self) -> Scope: ...
    
    def getAssocData(self) -> AssocData: ...
    
    def annotations(self) -> ListUtil...
        """Returns an iterator over the items"""
    
    def getAnnotations(self) -> List[Annotation]: ...
    
class ActivitySelectBranch(object):
    pass
    
    def getGuard(self) -> Expr: ...
    
    def getWeight(self) -> Expr: ...
    
    def getBody(self) -> ScopeChild: ...
    
class SymbolImportSpec(object):
    pass
    
    def imports(self) -> ListUtil...
        """Returns an iterator over the items"""
    
    def getImports(self) -> List[PackageImportStmt]: ...
    
class SymbolRefPath(object):
    pass
    
    def path(self) -> ListUtil...
        """Returns an iterator over the items"""
    
    def getPath(self) -> List[SymbolRefPathElem]: ...
    
class GenericConstraintDeclValue(ScopeChild):
    """
    Value-returning generic constraint declaration.
    
    Represents a declaration of the form
    ``[static] constraint <type> name(params) expr;``.
    
    """
    pass
    
    def getReturn_type(self) -> DataType: ...
    
    def getName(self) -> ExprId: ...
    
    def parameters(self) -> ListUtil...
        """Returns an iterator over the items"""
    
    def getParameters(self) -> List[GenericConstraintParam]: ...
    
    def getExpr(self) -> Expr: ...
    
class ActionFieldInitializer(ScopeChild):
    """
    Single field assignment in a PSS 3.1 action initializer list.
    
    Represents entries such as ``.x = 1`` or ``.cfg.mode = FAST`` used in
    action-handle declarations and action traversal statements.
    
    """
    pass
    
    def getPath(self) -> ExprHierarchicalId: ...
    
    def getValue(self) -> Expr: ...
    
class GenericConstraintParam(ScopeChild):
    """
    Parameter declaration for a PSS 3.1 generic constraint.
    
    Generic constraint parameters may be typed with either a concrete
    PSS data type or the `numeric` category and may optionally be
    declared `const`.
    
    """
    pass
    
    def getName(self) -> ExprId: ...
    
    def getType(self) -> DataType: ...
    
class MethodParameterList(Expr):
    """
    Represents a method or function parameter list.
    
    Contains the list of argument expressions passed to a method or function call.
    Used within method call expressions to specify the actual parameters.
    
    PSS Example::
    
        my_function(arg1, arg2, arg3)
        obj.method(x, y)
    
    Attributes:
        parameters: List of argument expressions
    
    See Also:
        ExprMemberPathElem, ExprRefPathStaticFunc
    
    """
    pass
    
    def parameters(self) -> ListUtil...
        """Returns an iterator over the items"""
    
    def getParameters(self) -> List[Expr]: ...
    
class ActivityJoinSpec(ScopeChild):
    """
    Base class for specifying join semantics in parallel and schedule blocks.
    
    ActivityJoinSpec defines how parallel or scheduled activities synchronize
    and when the containing block completes. Different join specifications
    provide flexibility in modeling concurrent execution patterns.
    
    PSS Example::
    
        action my_action {
            activity {
                // Various join specifications
                parallel join_none { }      // No synchronization
                parallel join_first(2) { }  // Wait for first 2
                parallel join_select(1) { } // Select 1 to complete
                parallel join_branch { }    // Explicit branches
            }
        }
    
    Attributes:
        (base class - no specific attributes)
    
    See Also:
        ActivityJoinSpecNone, ActivityJoinSpecFirst, ActivityJoinSpecSelect, ActivityJoinSpecBranch
    
    """
    pass
    
class MonitorActivityStmt(ScopeChild):
    """
    Base class for all monitor activity statements.
    
    MonitorActivityStmt is the abstract base class for all statements that can
    appear within a monitor's activity block. Monitor activity statements define
    temporal sequences, property assertions, and coverage collection patterns.
    They use temporal operators like concatenation (##), eventually, and overlap
    to specify time-based relationships. Note these are PSS 3.0 features.
    
    PSS Example::
    
        monitor protocol_monitor {
            activity {
                // Various MonitorActivityStmt subclasses
                req ##1 ack;                  // Concat
                eventually grant;             // Eventually
                repeat(3) data_phase;         // Repeat
                sequence { start; end; }      // Sequence
                if (mode == 0) fast; else slow;  // IfElse
            }
        }
    
    Attributes:
        (base class - no specific attributes)
    
    See Also:
        MonitorActivityDecl, MonitorActivityConcat, MonitorActivityEventually,
        MonitorActivitySequence
    
    """
    pass
    
class NamedScopeChild(ScopeChild):
    """
    An AST node with an identifier name that is a child of a scope.
    
    Base class for named declarations that aren't scopes themselves,
    such as fields, enum items, and function parameters. The name is
    used for symbol lookup within the parent scope.
    
    PSS Example::
    
        struct my_struct {
            int field1;        // NamedScopeChild with name="field1"
            bool field2;       // NamedScopeChild with name="field2"
        }
    
    Attributes:
        name: Identifier expression containing the name
    
    See Also:
        ScopeChild, NamedScope, Field
    
    """
    pass
    
    def getName(self) -> ExprId: ...
    
class PackageImportStmt(ScopeChild):
    """
    Import statement bringing package symbols into current scope.
    
    Imports types and declarations from another package. Can import
    all symbols with wildcard or create an alias for qualified access.
    
    PSS Example::
    
        import other_pkg::*;              // Wildcard import
        import other_pkg::MyAction;       // Single import
        import other_pkg as op;           // Aliased import
    
    Attributes:
        wildcard: True if using wildcard (::*)
        alias: Optional alias name for the import
        path: Type identifier for the imported package/symbol
    
    See Also:
        PackageScope, TypeIdentifier
    
    """
    pass
    
    def getAlias(self) -> ExprId: ...
    
    def getPath(self) -> TypeIdentifier: ...
    
class ActivitySchedulingConstraint(ScopeChild):
    """
    Defines ordering constraints between scheduled activities.
    
    ActivitySchedulingConstraint specifies sequential or parallel execution
    ordering relationships between activities in a schedule block. It allows
    explicit control over the relative timing of activities.
    
    PSS Example::
    
        action my_action {
            activity {
                schedule {
                    do comp1.action_a;
                    do comp2.action_b;
                    do comp3.action_c;
                    
                    // Sequential ordering
                    action_a before action_b;
                    
                    // Parallel execution
                    parallel(action_a, action_b);
                }
            }
        }
    
    Attributes:
        is_parallel: True if this is a parallel constraint, False for sequential
        targets: List of hierarchical IDs identifying the constrained activities
    
    See Also:
        ActivitySchedule
    
    """
    pass
    
    def targets(self) -> ListUtil...
        """Returns an iterator over the items"""
    
    def getTargets(self) -> List[ExprHierarchicalId]: ...
    
class ActivityStmt(ScopeChild):
    """
    Base class for all activity statements.
    
    ActivityStmt is the abstract base class for all statements that can appear
    within an activity block. Activity statements define the execution behavior
    of actions, including action traversals, control flow, parallelism, and
    scheduling constraints.
    
    PSS Example::
    
        action my_action {
            activity {
                // Various ActivityStmt subclasses
                do comp.sub_action;        // Traversal
                sequence { }                // Sequence
                parallel { }                // Parallel
                if (condition) { }          // IfElse
            }
        }
    
    Attributes:
        (base class - no specific attributes)
    
    See Also:
        ActivityDecl, ActivitySequence, ActivityParallel, ActivityActionHandleTraversal
    
    """
    pass
    
class Annotation(ScopeChild):
    """
    Applied annotation attached to a model element.
    
    Represents an annotation use such as ``@desc("hello")`` or
    ``@meta(name="foo")``. The annotation type is referenced by name and
    the parameters preserve both positional and name-mapped arguments.
    
    See Also:
        AnnotationDecl, AnnotationParam
    
    """
    pass
    
    def getType(self) -> TypeIdentifier: ...
    
    def parameters(self) -> ListUtil...
        """Returns an iterator over the items"""
    
    def getParameters(self) -> List[AnnotationParam]: ...
    
class AnnotationParam(ScopeChild):
    """
    Parameter to an applied annotation.
    
    Positional parameters leave ``name`` unset. Name-mapped parameters set
    ``name`` to the mapped field identifier.
    
    See Also:
        Annotation
    
    """
    pass
    
    def getName(self) -> ExprId: ...
    
    def getValue(self) -> Expr: ...
    
class ProceduralStmtIfClause(ScopeChild):
    """
    Single if or else-if clause with condition and body.
    
    ProceduralStmtIfClause represents one conditional branch in an if-else-if
    chain. Each clause has a condition expression and a body that executes
    if the condition is true. Multiple clauses are chained together in
    ProceduralStmtIfElse.
    
    PSS Example::
    
        action my_action {
            exec body {
                int x = 10;
                
                if (x > 15) {          // First ProceduralStmtIfClause
                    console.log("Big");
                } else if (x > 5) {    // Second ProceduralStmtIfClause
                    console.log("Medium");
                }
            }
        }
    
    Attributes:
        cond: Condition expression to evaluate
        body: Statement(s) to execute if condition is true
    
    See Also:
        ProceduralStmtIfElse
    
    """
    pass
    
    def getCond(self) -> Expr: ...
    
    def getBody(self) -> ScopeChild: ...
    
class ComponentBind(ScopeChild):
    """
    Component-level object/pool bind directive (``bind pool targets;``).
    
    Binds a pool to a set of action object-reference fields, or to all
    compatible references via the wildcard form. Targets are captured as
    plain dotted-path strings (e.g. ``"a.x"``); the wildcard form sets
    ``is_wildcard`` and leaves ``targets`` empty. Paths are stored as
    text rather than resolved references, so this node is inert during
    link (no ref resolution, no traversal cycles).
    
    PSS Example::
    
        component pss_top {
            pool my_buffer p;
            bind p *;                  // wildcard
            bind p { producer.out };   // explicit target path
        }
    
    Attributes:
        pool_path: Hierarchical id of the bound pool (e.g. ``"p"``).
        is_wildcard: True for the ``bind p *;`` form.
        targets: Explicit dotted bind-item paths (empty when wildcard),
            e.g. ``["producer.out", "consumer.inp"]``.
    
    """
    pass
    
    def getPool_path(self) -> str: ...
    
    def setPool_path(self, v : str): ...
    
    def targets(self) -> ListUtil...
        """Returns an iterator over the items"""
    
    def getTargets(self) -> List[str]: ...
    
class ConstraintStmt(ScopeChild):
    """
    Base class for all constraint statement types.
    
    Represents any statement that can appear within a constraint block, including
    expressions, loops, conditionals, implications, and other constraint constructs.
    All specific constraint statement types derive from this base class.
    
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
        ConstraintStmtExpr, ConstraintStmtIf, ConstraintStmtForeach, ConstraintStmtForall
    
    """
    pass
    
class PyImportFromStmt(ScopeChild):
    """
    Python 'from...import' statement for selective imports.
    
    Imports specific symbols from a Python module into PSS context.
    
    PSS Example::
    
        python from os import path, environ;
        python from numpy import array, matrix;
    
    Attributes:
        path: Module path (e.g., ["os"])
        targets: List of symbols to import (e.g., ["path", "environ"])
    
    See Also:
        PyImportStmt
    
    """
    pass
    
    def path(self) -> ListUtil...
        """Returns an iterator over the items"""
    
    def getPath(self) -> List[ExprId]: ...
    
    def targets(self) -> ListUtil...
        """Returns an iterator over the items"""
    
    def getTargets(self) -> List[ExprId]: ...
    
class PyImportStmt(ScopeChild):
    """
    Python import statement for embedded Python integration.
    
    Imports Python modules into PSS context. Allows PSS code to
    access Python libraries and functions.
    
    PSS Example::
    
        python import os;
        python import numpy as np;
    
    Attributes:
        path: List of identifiers forming module path (e.g., ["os", "path"])
        alias: Optional alias for the import
    
    See Also:
        PyImportFromStmt
    
    """
    pass
    
    def path(self) -> ListUtil...
        """Returns an iterator over the items"""
    
    def getPath(self) -> List[ExprId]: ...
    
    def getAlias(self) -> ExprId: ...
    
class RefExprScopeIndex(RefExpr):
    """
    Reference to a scope using indexed access.
    
    Represents a resolved reference to a scope accessed via an index
    relative to a base reference. Used for efficient symbol lookup in
    the linked tree structure.
    
    Attributes:
        base: Base reference expression
        offset: Index offset from base to target scope
    
    See Also:
        RefExpr, SymbolScope
    
    """
    pass
    
    def getBase(self) -> RefExpr: ...
    
class RefExprTypeScopeContext(RefExpr):
    """
    Reference to a type scope relative to a context.
    
    Represents a resolved reference to a type scope relative to another
    reference expression. Used for navigating hierarchical type structures
    during linking (e.g., nested types, inner classes).
    
    Attributes:
        base: Base reference expression providing context
        offset: Offset from base to target type scope
    
    See Also:
        RefExpr, RefExprTypeScopeGlobal, SymbolTypeScope
    
    """
    pass
    
    def getBase(self) -> RefExpr: ...
    
class CoverStmtInline(ScopeChild):
    """
    Inline coverage statement within monitor or action.
    
    CoverStmtInline represents an inline form of coverage collection where the
    coverage body is specified directly within the cover statement. The body
    contains monitor activities or sequences that define coverage points to be
    tracked during execution. Note these are PSS 3.0 features.
    
    PSS Example::
    
        monitor protocol_coverage {
            activity {
                // Inline coverage of sequence
                cover {
                    req ##1 ack;
                }
                
                // Coverage of temporal pattern
                cover {
                    start ##1 data_phase ##1 end;
                }
                
                // Multiple coverage points
                cover {
                    fast_path;
                }
                
                cover {
                    slow_path;
                }
                
                // Complex patterns
                cover {
                    sequence {
                        init;
                        repeat(4) transfer;
                        done;
                    }
                }
            }
        }
    
    Attributes:
        body: Scope containing monitor activities to cover
    
    See Also:
        CoverStmtReference, MonitorActivityStmt, Monitor
    
    """
    pass
    
    def getBody(self) -> ScopeChild: ...
    
class CoverStmtReference(ScopeChild):
    """
    Reference coverage statement for monitor instance.
    
    CoverStmtReference represents a reference form of coverage collection that
    specifies coverage should be collected for a previously declared monitor
    instance. This allows reusing monitor definitions for coverage without
    duplicating the monitor activity specification. Note these are PSS 3.0
    features.
    
    PSS Example::
    
        monitor handshake_mon {
            activity {
                req ##1 ack;
            }
        }
        
        monitor data_transfer_mon {
            activity {
                valid ##0 ready ##1 data;
            }
        }
        
        action transaction {
            handshake_mon hshake;
            data_transfer_mon dtrans;
            
            activity {
                // Reference-based coverage
                cover hshake;
                cover dtrans;
                
                // Monitor execution
                monitor hshake;
                monitor dtrans;
            }
        }
        
        component top {
            handshake_mon global_monitor;
            
            activity {
                cover global_monitor;
            }
        }
    
    Attributes:
        target: Reference path to the monitor instance to cover
    
    See Also:
        CoverStmtInline, Monitor, ExprRefPath
    
    """
    pass
    
    def getTarget(self) -> ExprRefPath: ...
    
class RefExprTypeScopeGlobal(RefExpr):
    """
    Reference to a type scope at the global (file) level.
    
    Represents a resolved reference to a type defined at the global scope
    of a specific file. Used during linking to track cross-file type
    references and maintain file boundaries in the symbol tree.
    
    Attributes:
        fileid: File identifier where the type scope is defined
    
    See Also:
        RefExpr, GlobalScope, SymbolTypeScope
    
    """
    pass
    
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
        endLocation: Source location of closing brace
        children: List of child nodes in this scope
        parent: Parent scope (inherited from ScopeChild)
    
    See Also:
        ScopeChild, NamedScope, GlobalScope
    
    """
    pass
    
    def getEndLocation(self) -> 'Location': ...
    
    def children(self) -> ListUtil...
        """Returns an iterator over the items"""
    
    def getChildren(self) -> List[ScopeChild]: ...
    
class ScopeChildRef(ScopeChild):
    """
    Reference to another AST node, used for type aliases and forwards.
    
    Represents a symbolic reference that will be resolved during linking.
    Used when one AST node needs to reference another without creating
    a direct pointer.
    
    Attributes:
        target: The referenced AST node
    
    See Also:
        ScopeChild, FieldRef
    
    """
    pass
    
    def getTarget(self) -> ScopeChild: ...
    
class DataType(ScopeChild):
    """
    Base class for all PSS data types.
    
    Represents the type system in PSS. All type expressions (int, bool,
    user-defined types, etc.) derive from this base class. Used in field
    declarations, expressions, and function signatures.
    
    See Also:
        DataTypeInt, DataTypeBool, DataTypeUserDefined, Field
    
    """
    pass
    
class SymbolChild(ScopeChild):
    """
    Base class for all symbols in the fully-linked symbol tree.
    
    Represents a node in the post-linking symbol resolution tree, distinct from
    the physical AST. Extends ScopeChild with linking-specific metadata including
    a unique identifier and parent scope reference.
    
    The symbol tree is constructed during the linking phase after parsing, providing
    a logical view of declarations with resolved imports and type references.
    
    Attributes:
        id: Unique identifier for this symbol within the tree (-1 if unassigned)
        upper: Parent symbol scope in the linked tree hierarchy
    
    See Also:
        SymbolScope, SymbolChildrenScope, ScopeChild
    
    """
    pass
    
    def getUpper(self) -> SymbolScope: ...
    
class SymbolScopeRef(ScopeChild):
    """
    Lightweight reference to a symbol scope by name.
    
    Provides a named reference mechanism for symbols without duplicating
    the full scope structure. Used during linking to create references
    between scopes before full resolution is complete.
    
    Attributes:
        name: Identifier of the referenced scope
    
    See Also:
        SymbolScope, ScopeChild
    
    """
    pass
    
    def getName(self) -> str: ...
    
    def setName(self, v : str): ...
    
class ExecStmt(ScopeChild):
    """
    Base class for all procedural statements in exec blocks.
    
    ExecStmt is the abstract base class for all statements that can appear
    within exec blocks (body, pre_solve, post_solve, etc.). These statements
    define imperative/procedural execution semantics including assignments,
    function calls, control flow, and data declarations.
    
    PSS Example::
    
        action my_action {
            exec body {
                // Various ExecStmt subclasses
                int x = 10;              // ProceduralStmtDataDeclaration
                x += 5;                  // ProceduralStmtAssignment
                if (x > 10) { }          // ProceduralStmtIfElse
                my_func();               // ProceduralStmtFunctionCall
            }
        }
    
    Attributes:
        upper: Pointer to enclosing symbol scope (not visited during traversal)
    
    See Also:
        ExecScope, ExecBlock, ProceduralStmtAssignment
    
    """
    pass
    
    def getUpper(self) -> SymbolScope: ...
    
class ExecTargetTemplateBlock(ScopeChild):
    """
    Target-specific template code with parameterized substitution.
    
    ExecTargetTemplateBlock represents target-language-specific exec code
    using a template string with parameter substitutions. This allows native
    code generation for specific execution targets while maintaining PSS
    portability through parameterization.
    
    PSS Example::
    
        action my_action {
            int value;
            
            exec body {
                // Target template example (conceptual)
                target cpp '''
                    std::cout << "Value = " << {{value}} << std::endl;
                ''';
            }
        }
    
    Attributes:
        kind: Type of exec block this template belongs to
        data: Template string with {{parameter}} placeholders
        parameters: List of parameter substitutions
    
    See Also:
        ExecTargetTemplateParam, ExecBlock
    
    """
    pass
    
    def setKind(self, v : ExecKind): ...
    
    def getData(self) -> str: ...
    
    def setData(self, v : str): ...
    
    def parameters(self) -> ListUtil...
        """Returns an iterator over the items"""
    
    def getParameters(self) -> List[ExecTargetTemplateParam]: ...
    
class TemplateParamDecl(ScopeChild):
    """
    Base class for template parameter declarations.
    
    Template parameters allow types and functions to be parameterized, enabling
    generic programming in PSS. This abstract base class provides the common name
    field shared by all template parameter types (generic type, category-constrained
    type, and value parameters).
    
    PSS Example::
    
        // Generic type parameter T
        action generic<T> {
            rand T value;
        }
        
        // Value parameter N
        action sized<int N> {
            int array[N];
        }
        
        // Category-constrained parameter T
        component container<T: action> {
            T inst;
        }
    
    Attributes:
        name: Identifier for the template parameter
    
    See Also:
        TemplateGenericTypeParamDecl, TemplateCategoryTypeParamDecl,
        TemplateValueParamDecl, TemplateParamDeclList
    
    """
    pass
    
    def getName(self) -> ExprId: ...
    
class ExportFunction(ScopeChild):
    """
    Exported target function declaration.
    
    Represents a PSS 3.1 ``export target function name;`` declaration.
    
    """
    pass
    
    def setPlat(self, v : PlatQual): ...
    
    def getName(self) -> ExprId: ...
    
class TemplateParamExprValue(TemplateParamValue):
    """
    Expression value for template instantiation.
    
    Represents a compile-time constant expression provided when instantiating a
    template. This is used to fill in value parameters with concrete values. The
    expression must be evaluable at compile time and must match the type specified
    in the corresponding value parameter declaration.
    
    PSS Example::
    
        // Template with value parameters
        action sized<int N, int WIDTH> {
            bit<WIDTH> array[N];
        }
        
        // Instantiation with expression values
        sized<16, 8> inst1;  // Literal expressions
        
        // Using constants as expression values
        const int BUFFER_SIZE = 32;
        const int DATA_WIDTH = 64;
        sized<BUFFER_SIZE, DATA_WIDTH> inst2;
        
        // Expressions can be computed
        sized<8*4, 2+6> inst3;  // 32 elements, 8 bits wide
        
        // Mixed type and expression values
        action mixed<T, int COUNT> {
            T values[COUNT];
        }
        mixed<bit<32>, 10> mixed_inst;
        // First value: bit<32> (TemplateParamTypeValue)
        // Second value: 10 (TemplateParamExprValue)
    
    Attributes:
        value: The compile-time constant expression
    
    See Also:
        TemplateParamValue, TemplateParamTypeValue, Expr, TemplateValueParamDecl
    
    """
    pass
    
    def getValue(self) -> Expr: ...
    
class TemplateParamTypeValue(TemplateParamValue):
    """
    Type value for template instantiation.
    
    Represents a type argument provided when instantiating a template. This is used
    to fill in type parameters (both generic and category-constrained) with concrete
    types. The value must be a valid data type expression that satisfies any
    constraints specified in the template parameter declaration.
    
    PSS Example::
    
        // Template with type parameters
        action generic<T, U: action> {
            rand T data;
            U action_inst;
        }
        
        // Instantiation with type values
        generic<bit<16>, my_action_t> inst;
        // First parameter value: bit<16> (built-in type)
        // Second parameter value: my_action_t (user-defined action type)
        
        // Complex type as parameter value
        struct nested_struct<T> {
            T value;
        }
        generic<nested_struct<int<32>>, other_action_t> complex_inst;
    
    Attributes:
        value: The type being provided as the template argument
    
    See Also:
        TemplateParamValue, TemplateParamExprValue, DataType,
        TemplateGenericTypeParamDecl, TemplateCategoryTypeParamDecl
    
    """
    pass
    
    def getValue(self) -> DataType: ...
    
class ExprAggrLiteral(Expr):
    """
    Base class for aggregate literal expressions.
    
    Represents the common structure for all aggregate literals including arrays,
    maps, and struct initializers. Aggregate literals are used to initialize
    composite data structures with specific values.
    
    PSS Example::
    
        {1, 2, 3}              // Array literal (ExprAggrList)
        {name: value, ...}     // Struct literal (ExprAggrStruct)
        {[key]: value, ...}    // Map literal (ExprAggrMap)
    
    See Also:
        ExprAggrList, ExprAggrMap, ExprAggrStruct, ExprAggrEmpty
    
    """
    pass
    
class TypeIdentifier(Expr):
    """
    Represents a type identifier expression.
    
    Used to reference type names, possibly with template parameters. The type
    identifier can be simple or qualified with package/scope names. The target
    field is resolved during semantic analysis.
    
    PSS Example::
    
        my_type_t
        pkg::my_component
        std::addr_handle_t
        container<int>          // With template parameters
    
    Attributes:
        elems: List of identifier elements forming the type path
        target: Resolved symbol reference (null before resolution)
    
    See Also:
        TypeIdentifierElem, ExprHierarchicalId
    
    """
    pass
    
    def elems(self) -> ListUtil...
        """Returns an iterator over the items"""
    
    def getElems(self) -> List[TypeIdentifierElem]: ...
    
    def getTarget(self) -> SymbolRefPath: ...
    
class TypeIdentifierElem(Expr):
    """
    Represents a single element in a type identifier path.
    
    Building block for type identifiers. Contains an identifier and optional
    template parameters. Multiple elements are chained for qualified type names.
    
    PSS Example::
    
        my_pkg          // Simple element
        container<int>  // Element with template parameters
    
    Attributes:
        id: The identifier name
        params: Template parameter value list if present
    
    See Also:
        TypeIdentifier, ExprId, TemplateParamValueList
    
    """
    pass
    
    def getId(self) -> ExprId: ...
    
    def getParams(self) -> TemplateParamValueList: ...
    
class TypedefDeclaration(ScopeChild):
    pass
    
    def getName(self) -> ExprId: ...
    
    def getType(self) -> DataType: ...
    
class ExprBin(Expr):
    """
    Represents a binary expression with an operator.
    
    Binary expressions combine two operands (left and right) with an operator such as
    arithmetic, logical, bitwise, comparison, or shift operators. The operator determines
    how the operands are combined to produce a result value.
    
    PSS Example::
    
        a + b           // Arithmetic addition
        x && y          // Logical AND
        value << 2      // Left shift
        count == 5      // Equality comparison
    
    Attributes:
        lhs: Left-hand side operand expression
        op: Binary operator (ExprBinOp enum value)
        rhs: Right-hand side operand expression
    
    See Also:
        ExprBinOp, ExprUnary, Expr
    
    """
    pass
    
    def getLhs(self) -> Expr: ...
    
    def setOp(self, v : ExprBinOp): ...
    
    def getRhs(self) -> Expr: ...
    
class ExprBitSlice(Expr):
    """
    Represents a bit-slice or bit-range selection expression.
    
    Extracts a contiguous range of bits from an integer value. The lhs specifies
    the high bit index and rhs specifies the low bit index of the range. Both
    indices are inclusive. Single bit selection uses the same index for both.
    
    PSS Example::
    
        value[7:0]      // Extract bits 7 through 0
        data[15:8]      // Extract bits 15 through 8
        flags[3:3]      // Extract single bit 3
    
    Attributes:
        lhs: Upper bit index expression
        rhs: Lower bit index expression
    
    See Also:
        ExprSubscript, ExprRefPathId
    
    """
    pass
    
    def getLhs(self) -> Expr: ...
    
    def getRhs(self) -> Expr: ...
    
class ExprBool(Expr):
    """
    Represents a boolean literal value.
    
    Contains either the value true or false. Boolean literals are used in
    conditional expressions, constraints, and logical operations.
    
    PSS Example::
    
        bool flag = true;
        constraint c { enabled == false; }
    
    Attributes:
        value: The boolean value (true or false)
    
    See Also:
        ExprNumber, ExprString
    
    """
    pass
    
class ExprCast(Expr):
    """
    Represents an explicit type cast expression.
    
    Converts an expression from one type to another. The casting_type specifies
    the target type, and expr is the value being converted. Used for numeric
    conversions, widening/narrowing operations, and explicit type coercion.
    
    PSS Example::
    
        bit[16] x = 16'h1234;
        bit[8] y = (bit[8])x;           // Cast to narrower type
        int z = (int)some_expression;   // Cast to int
    
    Attributes:
        casting_type: Target type for the cast
        expr: Expression being cast
    
    See Also:
        DataType, Expr
    
    """
    pass
    
    def getCasting_type(self) -> DataType: ...
    
    def getExpr(self) -> Expr: ...
    
class ExprCompileHas(Expr):
    """
    Represents a compile-time existence check expression.
    
    Used in compile-time conditional compilation to test whether a symbol or
    path exists in the current scope. Returns a compile-time boolean value
    indicating whether the referenced element is available.
    
    PSS Example::
    
        if (compile.has(some_package::some_type)) {
            // Code for when type exists
        }
    
    Attributes:
        ref: Static reference path to check for existence
    
    See Also:
        ExprRefPathStatic
    
    """
    pass
    
    def getRef(self) -> ExprRefPathStatic: ...
    
class ExprCond(Expr):
    """
    Represents a ternary conditional expression (? :).
    
    Evaluates a condition expression and returns one of two values depending on
    whether the condition is true or false. This is the PSS equivalent of the
    ternary operator found in C-like languages.
    
    PSS Example::
    
        int result = (x > 10) ? x : 10;  // Use x if > 10, else 10
        bit[8] value = flag ? 8'hFF : 8'h00;
    
    Attributes:
        cond_e: Boolean condition expression
        true_e: Expression evaluated if condition is true
        false_e: Expression evaluated if condition is false
    
    See Also:
        ExprBin, ExprBool
    
    """
    pass
    
    def getCond_e(self) -> Expr: ...
    
    def getTrue_e(self) -> Expr: ...
    
    def getFalse_e(self) -> Expr: ...
    
class ExprDomainOpenRangeList(Expr):
    """
    Represents a domain constraint range list expression.
    
    Contains a list of range values that define valid domains for random variables
    in constraint blocks. Each range can be a single value or a range interval.
    
    PSS Example::
    
        rand bit[8] value;
        constraint c { value in [1..10, 20, 30..40]; }
    
    Attributes:
        values: List of range value specifications
    
    See Also:
        ExprDomainOpenRangeValue, ExprIn
    
    """
    pass
    
    def values(self) -> ListUtil...
        """Returns an iterator over the items"""
    
    def getValues(self) -> List[ExprDomainOpenRangeValue]: ...
    
class ExprDomainOpenRangeValue(Expr):
    """
    Represents a single range value in a domain constraint.
    
    Can represent either a single value or a range interval. If single is true,
    only lhs is used. For ranges, lhs is the lower bound and rhs is the upper bound.
    
    PSS Example::
    
        rand int x;
        constraint c { 
            x in [1..10];      // Range: lhs=1, rhs=10, single=false
            x in [42];         // Single: lhs=42, single=true
        }
    
    Attributes:
        single: True if single value, false if range
        lhs: Lower bound or single value
        rhs: Upper bound (only used if single is false)
    
    See Also:
        ExprDomainOpenRangeList, ExprIn
    
    """
    pass
    
    def getLhs(self) -> Expr: ...
    
    def getRhs(self) -> Expr: ...
    
class ExprHierarchicalId(Expr):
    """
    Represents a qualified identifier with scope resolution.
    
    A hierarchical identifier consists of multiple name elements separated by
    scope resolution operators (::). Used to reference types, packages, or
    members through nested scopes.
    
    PSS Example::
    
        my_pkg::my_component::my_field
        std::addr_handle_t
        parent_comp::child_comp
    
    Attributes:
        elems: List of path elements forming the hierarchical identifier
    
    See Also:
        ExprId, ExprMemberPathElem, ExprRefPath
    
    """
    pass
    
    def elems(self) -> ListUtil...
        """Returns an iterator over the items"""
    
    def getElems(self) -> List[ExprMemberPathElem]: ...
    
class ExprId(Expr):
    """
    Represents a simple identifier expression.
    
    The most basic form of identifier, representing a variable name, field name,
    type name, or other named entity. Can be escaped (prefixed with backslash)
    to allow use of keywords or special characters as identifiers.
    
    PSS Example::
    
        my_variable
        field_name
        \begin          // Escaped identifier
    
    Attributes:
        id: The identifier string
        is_escaped: True if identifier is escaped with backslash
        location: Source location of the identifier
    
    See Also:
        ExprHierarchicalId, ExprRefPath, ExprMemberPathElem
    
    """
    pass
    
    def getId(self) -> str: ...
    
    def setId(self, v : str): ...
    
    def getLocation(self) -> 'Location': ...
    
class ExprIn(Expr):
    """
    Represents a set membership test expression (in operator).
    
    Two forms exist in PSS:
      Range-list form:  x in [1..10, 20, 30..40]  -- rhs is populated
      Collection form:  x in comp.some_list        -- collection is populated
    
    Attributes:
        lhs:        Expression to test for membership
        rhs:        Range list (range-list form; empty for collection form)
        collection: Collection expression (collection form; null for range-list form)
    
    See Also:
        ExprOpenRangeList, ExprDomainOpenRangeList
    
    """
    pass
    
    def getLhs(self) -> Expr: ...
    
    def getRhs(self) -> ExprOpenRangeList: ...
    
    def getCollection(self) -> Expr: ...
    
class ExprListLiteral(Expr):
    """
    Represents a list literal expression.
    
    Similar to ExprAggrList but may have different semantic usage. Contains
    an ordered sequence of expression values.
    
    PSS Example::
    
        list<int> values = [1, 2, 3, 4, 5];
    
    Attributes:
        value: List of expression values
    
    See Also:
        ExprAggrList, Expr
    
    """
    pass
    
    def value(self) -> ListUtil...
        """Returns an iterator over the items"""
    
    def getValue(self) -> List[Expr]: ...
    
class ExprMemberPathElem(Expr):
    """
    Represents a single element in a member access path.
    
    Building block for hierarchical identifiers and reference paths. Can represent
    a field access, method call, or array subscript. Multiple elements are chained
    together to form complex access expressions.
    
    PSS Example::
    
        obj.field               // Simple member access
        comp.method(args)       // Method call with parameters
        arr[i]                  // Array subscript
        str.upper()             // String method call
    
    Attributes:
        id: The identifier name
        params: Method parameters if this is a function call
        subscript: Array subscript expressions if applicable
        target: Resolved target index (-1 if unresolved)
        super: Super class reference index
        string_method_id: Identifier for string methods
    
    See Also:
        ExprHierarchicalId, ExprId, MethodParameterList
    
    """
    pass
    
    def getId(self) -> ExprId: ...
    
    def getParams(self) -> MethodParameterList: ...
    
    def subscript(self) -> ListUtil...
        """Returns an iterator over the items"""
    
    def getSubscript(self) -> List[Expr]: ...
    
    def setString_method_id(self, v : StringMethodId): ...
    
class ExprNull(Expr):
    """
    Represents a null literal value.
    
    Used to represent the absence of a value for reference types. Null is
    commonly used with handle types to indicate an uninitialized or invalid
    reference.
    
    PSS Example::
    
        addr_handle_t h = null;
        if (handle == null) { ... }
    
    See Also:
        ExprBool, ExprNumber
    
    """
    pass
    
class ExprNumber(Expr):
    """
    Abstract base class for numeric literal expressions.
    
    Represents constant numeric values in PSS source code. Concrete subclasses
    handle signed and unsigned integers with various representations and bit widths.
    
    PSS Example::
    
        42              // Decimal number
        0x2A            // Hexadecimal
        8'hFF           // Sized hexadecimal (8 bits)
        -10             // Negative number
    
    See Also:
        ExprSignedNumber, ExprUnsignedNumber
    
    """
    pass
    
class ExprOpenRangeList(Expr):
    """
    Represents a list of value ranges for set membership tests.
    
    Contains a collection of range specifications used with the 'in' operator.
    Each range can be a single value or an interval. Used primarily in
    constraint expressions.
    
    PSS Example::
    
        rand int x;
        constraint c { x in [1..10, 20, 30..40]; }
    
    Attributes:
        values: List of range value specifications
    
    See Also:
        ExprOpenRangeValue, ExprIn, ExprDomainOpenRangeList
    
    """
    pass
    
    def values(self) -> ListUtil...
        """Returns an iterator over the items"""
    
    def getValues(self) -> List[ExprOpenRangeValue]: ...
    
class ExprOpenRangeValue(Expr):
    """
    Represents a single value or range in a range list.
    
    Specifies either a single value (when rhs is null) or a range interval
    (when both lhs and rhs are present). Used within ExprOpenRangeList for
    set membership constraints.
    
    PSS Example::
    
        x in [5];           // Single value: lhs=5, rhs=null
        x in [1..10];       // Range: lhs=1, rhs=10
    
    Attributes:
        lhs: Lower bound or single value
        rhs: Upper bound (null for single value)
    
    See Also:
        ExprOpenRangeList, ExprIn
    
    """
    pass
    
    def getLhs(self) -> Expr: ...
    
    def getRhs(self) -> Expr: ...
    
class ExprRefPath(Expr):
    """
    Base class for reference path expressions.
    
    Reference paths represent access to fields, variables, or components through
    a navigation path. The target field points to the resolved symbol path after
    semantic analysis. Concrete subclasses handle different forms of paths.
    
    PSS Example::
    
        component.field         // Reference to component field
        super.parent_field      // Reference to parent field
        ::pkg::type             // Static reference path
    
    Attributes:
        target: Resolved symbol reference path (null before resolution)
    
    See Also:
        ExprRefPathId, ExprRefPathContext, ExprRefPathStatic
    
    """
    pass
    
    def getTarget(self) -> SymbolRefPath: ...
    
class ExprRefPathElem(Expr):
    """
    Base class for elements within a reference path.
    
    Represents individual components that can be part of a reference path
    expression. Used as a building block for more complex path structures.
    
    See Also:
        ExprRefPath, ExprMemberPathElem
    
    """
    pass
    
class ExprStaticRefPath(Expr):
    """
    Deprecated static reference path expression.
    
    Legacy class for static reference paths. This class is marked for removal
    and should not be used in new code. Use ExprRefPathStatic instead.
    
    See Also:
        ExprRefPathStatic
    
    """
    pass
    
    def base(self) -> ListUtil...
        """Returns an iterator over the items"""
    
    def getBase(self) -> List[TypeIdentifierElem]: ...
    
    def getLeaf(self) -> ExprMemberPathElem: ...
    
class ExprString(Expr):
    """
    Represents a string literal expression.
    
    Contains a string constant value. Can be a regular string (with escape
    sequences processed) or a raw string (escape sequences preserved). Used
    for string data, messages, and identifiers.
    
    PSS Example::
    
        string msg = "Hello, World!";
        string path = r"C:\path\to\file";  // Raw string
    
    Attributes:
        value: The string content
        is_raw: True if this is a raw string literal
    
    See Also:
        ExprBool, ExprNumber, ExprSubstring
    
    """
    pass
    
    def getValue(self) -> str: ...
    
    def setValue(self, v : str): ...
    
class ExprStructLiteral(Expr):
    """
    Represents a struct literal expression.
    
    Similar to ExprAggrStruct but may have different semantic usage. Initializes
    struct fields with named values provided in a list of items.
    
    PSS Example::
    
        struct Config {
            int x;
            int y;
        }
        Config cfg = {x: 10, y: 20};
    
    Attributes:
        values: List of field initialization items
    
    See Also:
        ExprStructLiteralItem, ExprAggrStruct
    
    """
    pass
    
    def values(self) -> ListUtil...
        """Returns an iterator over the items"""
    
    def getValues(self) -> List[ExprStructLiteralItem]: ...
    
class ExprStructLiteralItem(Expr):
    """
    Represents a field initialization in a struct literal.
    
    Contains a field name identifier and its corresponding value expression.
    Used within ExprStructLiteral to specify individual field assignments.
    
    PSS Example::
    
        // Within struct literal: {field: value}
        {x: 10, y: 20}
    
    Attributes:
        id: Field name identifier
        value: Expression providing the field's value
    
    See Also:
        ExprStructLiteral, ExprId
    
    """
    pass
    
    def getId(self) -> ExprId: ...
    
    def getValue(self) -> Expr: ...
    
class ExprSubscript(Expr):
    """
    Represents an array subscript or indexing expression.
    
    Accesses a single element of an array, list, or map by index. The expr
    is the collection being indexed, and subscript is the index value.
    
    PSS Example::
    
        array<int, 10> arr;
        int x = arr[5];         // Access element at index 5
        int y = matrix[i];      // Dynamic index
    
    Attributes:
        expr: Array or collection expression
        subscript: Index expression
    
    See Also:
        ExprBitSlice, ExprMemberPathElem
    
    """
    pass
    
    def getExpr(self) -> Expr: ...
    
    def getSubscript(self) -> Expr: ...
    
class ExprSubstring(Expr):
    """
    Represents a substring extraction expression.
    
    Extracts a portion of a string based on start and end indices. Used with
    string expressions to select character ranges.
    
    PSS Example::
    
        string s = "Hello, World!";
        string sub = s[0:5];        // "Hello"
        string tail = s[7:12];      // "World"
    
    Attributes:
        expr: String expression to extract from
        start: Starting index expression
        end: Ending index expression
    
    See Also:
        ExprString, ExprSubscript, ExprBitSlice
    
    """
    pass
    
    def getExpr(self) -> Expr: ...
    
    def getStart(self) -> Expr: ...
    
    def getEnd(self) -> Expr: ...
    
class ExprUnary(Expr):
    """
    Represents a unary expression with an operator.
    
    Applies a unary operator to a single operand. Unary operators include
    arithmetic negation, logical NOT, bitwise negation, and reduction operators.
    
    PSS Example::
    
        -x              // Unary minus
        !flag           // Logical NOT
        ~bits           // Bitwise negation
        &vector         // Reduction AND
    
    Attributes:
        op: Unary operator (ExprUnaryOp enum value)
        rhs: Operand expression
    
    See Also:
        ExprUnaryOp, ExprBin, Expr
    
    """
    pass
    
    def setOp(self, v : ExprUnaryOp): ...
    
    def getRhs(self) -> Expr: ...
    
class ExtendEnum(ScopeChild):
    """
    Enum extension declaration for adding values to existing enums.
    
    Represents an 'extend' statement that adds new enumerator values
    to an existing enum type. Enum extensions allow adding values
    without modifying the original enum definition.
    
    PSS Example::
    
        enum status {
            OK,
            ERROR
        };
        
        extend enum status {
            WARNING,
            INFO
        };
    
    Attributes:
        target: Type identifier of the enum to extend
        items: List of new enumerator values to add
    
    See Also:
        ExtendType, EnumDecl, EnumItem
    
    """
    pass
    
    def getTarget(self) -> TypeIdentifier: ...
    
    def items(self) -> ListUtil...
        """Returns an iterator over the items"""
    
    def getItems(self) -> List[EnumItem]: ...
    
class FunctionDefinition(ScopeChild):
    """
    Complete function definition with implementation body.
    
    Represents a function declaration with a complete implementation,
    including prototype (signature) and execution body. Functions can
    be qualified for target or solve-time execution using platform
    qualifiers.
    
    PSS Example::
    
        // Simple function
        function int add(int a, int b) {
            return a + b;
        }
        
        // Target function with output parameter
        function void process(input int x, output int result) = target {
            result = x * 2;
        }
        
        // Solve-time function
        function int calculate(int value) = solve {
            return value + 100;
        }
    
    Attributes:
        endLocation: Location of function closing brace
        proto: Function prototype (signature)
        body: Execution scope containing statements
        plat: Platform qualifier (None, Target, or Solve)
    
    See Also:
        FunctionPrototype, ExecScope, PlatQual, FunctionImport
    
    """
    pass
    
    def getEndLocation(self) -> 'Location': ...
    
    def getProto(self) -> FunctionPrototype: ...
    
    def getBody(self) -> ExecScope: ...
    
    def setPlat(self, v : PlatQual): ...
    
class FunctionImport(ScopeChild):
    """
    Base class for importing external functions.
    
    Represents an import statement that brings external functions into
    PSS scope. External functions can be qualified for target or
    solve-time execution and can specify the implementation language.
    This is an abstract base; concrete imports use FunctionImportType
    or FunctionImportProto.
    
    PSS Example::
    
        // Import by type name
        import class my_pkg::util_funcs = target "cpp";
        
        // Import function prototype
        import function int extern_func(int x) = solve "python";
    
    Attributes:
        plat: Platform qualifier (None, Target, or Solve)
        lang: Implementation language identifier (e.g., "cpp", "python")
    
    See Also:
        FunctionImportType, FunctionImportProto, PlatQual
    
    """
    pass
    
    def setPlat(self, v : PlatQual): ...
    
    def getLang(self) -> str: ...
    
    def setLang(self, v : str): ...
    
class FunctionParamDecl(ScopeChild):
    """
    Function parameter declaration with type and direction.
    
    Represents a single parameter in a function signature. Parameters
    can have direction qualifiers (input, output, inout), default values,
    and various kinds (data types, type parameters, or references).
    Supports variadic parameters for variable-length argument lists.
    
    PSS Example::
    
        // Function with multiple parameter types
        function void my_func(
            input int x,              // Input parameter
            output int result,        // Output parameter
            inout int counter,        // Input/output parameter
            int default_val = 10      // Parameter with default value
        );
        
        // Type parameter
        function void generic<type T>(T value);
        
        // Reference parameters
        function void process_action(ref my_action act);
        
        // Variadic function
        function void log(string fmt, ...);
    
    Attributes:
        kind: Parameter kind (data type, type, reference, etc.)
        name: Parameter identifier
        type: Parameter data type
        dir: Parameter direction (Default, In, Out, InOut)
        dflt: Optional default value expression
        is_varargs: True if this is a variadic parameter (...)
    
    See Also:
        FunctionPrototype, FunctionParamDeclKind, ParamDir, DataType
    
    """
    pass
    
    def setKind(self, v : FunctionParamDeclKind): ...
    
    def getName(self) -> ExprId: ...
    
    def getType(self) -> DataType: ...
    
    def setDir(self, v : ParamDir): ...
    
    def getDflt(self) -> Expr: ...
    
class ActionHandleField(NamedScopeChild):
    """
    Action handle field declaration.
    
    Represents an action instance field declared in an action or monitor
    body, including optional PSS 3.1 initializer assignments and support
    for array-typed handles.
    
    """
    pass
    
    def getType(self) -> DataType: ...
    
    def initializers(self) -> ListUtil...
        """Returns an iterator over the items"""
    
    def getInitializers(self) -> List[ActionFieldInitializer]: ...
    
class ActivityBindStmt(ActivityStmt):
    """
    Binds resource references between actions.
    
    ActivityBindStmt creates a binding between resource references, allowing
    an action to use resources from another action's scope. This enables
    resource sharing and coordination between actions in a behavior tree.
    
    PSS Example::
    
        action producer {
            output mydata_s data_out;
            activity { }
        }
        
        action consumer {
            input mydata_s data_in;
            activity { }
        }
        
        action top {
            producer prod;
            consumer cons;
            
            activity {
                do prod;
                do cons;
                bind cons.data_in prod.data_out;
            }
        }
    
    Attributes:
        lhs: Left-hand side hierarchical ID (the reference being bound)
        rhs: List of right-hand side hierarchical IDs (source references)
    
    See Also:
        FieldRef, FieldCompRef
    
    """
    pass
    
    def getLhs(self) -> ExprHierarchicalId: ...
    
    def rhs(self) -> ListUtil...
        """Returns an iterator over the items"""
    
    def getRhs(self) -> List[ExprHierarchicalId]: ...
    
class ActivityConstraint(ActivityStmt):
    """
    Adds constraints within an activity block.
    
    ActivityConstraint allows constraint statements to be embedded within
    activity blocks to further constrain the behavior or data of actions
    being executed. These constraints are evaluated during scenario generation.
    
    PSS Example::
    
        action my_action {
            rand bit[16] addr;
            rand bit[8] data;
            
            activity {
                do comp.sub_action with {
                    addr == 0x1000;
                }
                
                constraint {
                    data inside [0..100];
                }
            }
        }
    
    Attributes:
        constraint: The constraint statement to be applied
    
    See Also:
        ConstraintStmt, ConstraintBlock
    
    """
    pass
    
    def getConstraint(self) -> ConstraintStmt: ...
    
class ActivityJoinSpecBranch(ActivityJoinSpec):
    """
    Join specification with explicit branch identification.
    
    ActivityJoinSpecBranch allows explicit specification of which branches
    must complete for the parallel or schedule block to complete. This provides
    fine-grained control over synchronization points.
    
    PSS Example::
    
        action my_action {
            activity {
                parallel join_branch (branch1, branch2) {
                    branch1: do comp.action1;
                    branch2: do comp.action2;
                    branch3: do comp.action3;
                    // Block completes when branch1 and branch2 complete
                    // branch3 may still be running
                }
            }
        }
    
    Attributes:
        branches: List of reference paths identifying branches that must complete
    
    See Also:
        ActivityJoinSpec, ActivityParallel, ActivitySchedule
    
    """
    pass
    
    def branches(self) -> ListUtil...
        """Returns an iterator over the items"""
    
    def getBranches(self) -> List[ExprRefPathContext]: ...
    
class ActivityJoinSpecFirst(ActivityJoinSpec):
    """
    Join specification that waits for the first N branches to complete.
    
    ActivityJoinSpecFirst causes the parallel or schedule block to complete
    when the first specified number of branches have completed. Unlike join_select,
    this waits for the actual first branches to finish rather than randomly
    selecting which ones complete.
    
    PSS Example::
    
        action my_action {
            activity {
                // Wait for first 2 to complete
                parallel join_first(2) {
                    do comp.action1;
                    do comp.action2;
                    do comp.action3;
                    do comp.action4;
                }
                // Block completes as soon as any 2 finish
                
                // Wait for first one
                parallel join_first(1) {
                    do comp.option_a;
                    do comp.option_b;
                }
            }
        }
    
    Attributes:
        count: Expression specifying how many branches to wait for
    
    See Also:
        ActivityJoinSpec, ActivityJoinSpecSelect, ActivityParallel
    
    """
    pass
    
    def getCount(self) -> Expr: ...
    
class ActivityJoinSpecNone(ActivityJoinSpec):
    """
    Join specification with no synchronization.
    
    ActivityJoinSpecNone indicates that the parallel or schedule block completes
    immediately without waiting for any branches to complete. The branches continue
    executing asynchronously in the background. This is useful for fire-and-forget
    concurrent operations.
    
    PSS Example::
    
        action my_action {
            activity {
                // No waiting for completion
                parallel join_none {
                    do comp.background_task1;
                    do comp.background_task2;
                    do comp.background_task3;
                }
                // Execution continues immediately
                do comp.foreground_task;
            }
        }
    
    Attributes:
        (no specific attributes)
    
    See Also:
        ActivityJoinSpec, ActivityJoinSpecFirst, ActivityParallel
    
    """
    pass
    
class ActivityJoinSpecSelect(ActivityJoinSpec):
    """
    Join specification that randomly selects branches to complete.
    
    ActivityJoinSpecSelect causes the parallel or schedule block to complete
    when a specified number of branches have completed. The selection of which
    branches complete is typically random and can be constrained.
    
    PSS Example::
    
        action my_action {
            activity {
                // Select 2 branches to complete
                parallel join_select(2) {
                    do comp.action1;
                    do comp.action2;
                    do comp.action3;
                    do comp.action4;
                }
                // Block completes when any 2 actions complete
                
                // Select 1 (like a race condition)
                parallel join_select(1) {
                    do comp.fast_path;
                    do comp.slow_path;
                }
            }
        }
    
    Attributes:
        count: Expression specifying how many branches must complete
    
    See Also:
        ActivityJoinSpec, ActivityJoinSpecFirst, ActivityParallel
    
    """
    pass
    
    def getCount(self) -> Expr: ...
    
class ActivityLabeledStmt(ActivityStmt):
    """
    Base class for activity statements that can have a label.
    
    ActivityLabeledStmt provides the ability to attach an optional label to
    an activity statement. Labels can be used to reference activities in
    scheduling constraints or for identification purposes.
    
    PSS Example::
    
        action my_action {
            activity {
                my_label: do comp.sub_action;
                
                another_label: sequence {
                    do comp.action1;
                    do comp.action2;
                }
            }
        }
    
    Attributes:
        label: Optional identifier expression for the label
    
    See Also:
        ActivityActionHandleTraversal, ActivitySequence, ActivityRepeatCount
    
    """
    pass
    
    def getLabel(self) -> ExprId: ...
    
class ConstraintScope(ConstraintStmt):
    """
    Container for a sequence of constraint statements.
    
    A constraint scope groups multiple constraint statements together, forming the body
    of constraint blocks, conditional constraints, loops, and implications. It maintains
    the source location information for the entire scope.
    
    PSS Example::
    
        constraint my_constraints {
            // This entire block is a ConstraintScope
            value1 > 0;
            value2 < 100;
            value1 + value2 == 50;
        }
    
    Attributes:
        endLocation: Source location of the closing brace
        constraints: Ordered list of constraint statements within this scope
    
    See Also:
        ConstraintBlock, ConstraintStmt
    
    """
    pass
    
    def getEndLocation(self) -> 'Location': ...
    
    def constraints(self) -> ListUtil...
        """Returns an iterator over the items"""
    
    def getConstraints(self) -> List[ConstraintStmt]: ...
    
class ConstraintStmtDefault(ConstraintStmt):
    """
    Default value constraint for random fields.
    
    Specifies a default value for a random field that will be used if no other constraints
    determine its value. Default constraints have lower priority than regular constraints
    and can be disabled using 'default disable' statements. This provides a fallback value
    while allowing overrides.
    
    PSS Example::
    
        action network_packet {
            rand bit[16] packet_size;
            rand bit[8] priority;
            
            constraint defaults_c {
                default packet_size == 64;      // Minimum Ethernet frame
                default priority == 0;           // Normal priority
            }
            
            constraint size_limits_c {
                packet_size <= 1500;             // This overrides default
            }
        }
    
    Attributes:
        hid: Hierarchical identifier of the field receiving the default value
        expr: The default value expression
    
    See Also:
        ConstraintStmtDefaultDisable, ConstraintStmtExpr, ExprHierarchicalId
    
    """
    pass
    
    def getHid(self) -> ExprHierarchicalId: ...
    
    def getExpr(self) -> Expr: ...
    
class ConstraintStmtDefaultDisable(ConstraintStmt):
    """
    Disables inherited default value constraints.
    
    Explicitly disables default constraints that would otherwise be inherited from a base
    type or applied from enclosing scopes. This allows derived types to override parent
    defaults or clear unwanted default values, giving full control to other constraints.
    
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
                default disable addr;    // Don't use parent's default
                addr inside [0x2000..0x2FFF];  // Use this range instead
            }
        }
    
    Attributes:
        hid: Hierarchical identifier of the field whose default is being disabled
    
    See Also:
        ConstraintStmtDefault, ExprHierarchicalId
    
    """
    pass
    
    def getHid(self) -> ExprHierarchicalId: ...
    
class ConstraintStmtExpr(ConstraintStmt):
    """
    Expression-based constraint statement.
    
    Represents a constraint expressed as a Boolean expression that must evaluate to true
    during randomization. This is the most common form of constraint, supporting arithmetic
    relations, logical operations, and complex expressions involving random variables.
    
    PSS Example::
    
        action transfer {
            rand bit[16] addr;
            rand bit[8] size;
            
            constraint valid_transfer_c {
                addr >= 0x1000;                    // Simple relational
                addr + size <= 0xFFFF;             // Arithmetic expression
                size inside [1, 2, 4, 8];          // Set membership
                (addr & 0x3) == 0;                 // Address alignment
            }
        }
    
    Attributes:
        expr: The Boolean expression that must be satisfied
    
    See Also:
        Expr, ConstraintStmt, ConstraintBlock
    
    """
    pass
    
    def getExpr(self) -> Expr: ...
    
class ConstraintStmtField(ConstraintStmt):
    """
    Iterator variable declaration within constraint loops.
    
    Represents a temporary variable introduced by foreach or forall statements. These
    variables are scoped to the constraint loop body and provide access to collection
    elements or type instances during constraint evaluation.
    
    PSS Example::
    
        constraint iteration_c {
            foreach (items[idx]) {
                // 'idx' is a ConstraintStmtField
                // 'items[idx]' references the element
                items[idx] != 0;
            }
        }
    
    Attributes:
        name: The name of the iterator variable
        type: The data type of the iterator variable
    
    See Also:
        ConstraintStmtForeach, ConstraintStmtForall, ConstraintSymbolScope
    
    """
    pass
    
    def getName(self) -> ExprId: ...
    
    def getType(self) -> DataType: ...
    
class ConstraintStmtIf(ConstraintStmt):
    """
    Conditional constraint statement with optional else clause.
    
    Applies different constraints based on the evaluation of a Boolean condition. If the
    condition is true, constraints in the true branch are active; otherwise, constraints
    in the optional else branch are active. The condition is evaluated after randomization
    of variables it depends on.
    
    PSS Example::
    
        action memory_access {
            rand bit is_read;
            rand bit[32] addr;
            rand bit[8] data;
            
            constraint access_type_c {
                if (is_read) {
                    addr inside [0x0000..0x0FFF];  // ROM region
                } else {
                    addr inside [0x1000..0x1FFF];  // RAM region
                    data != 0;                      // Write non-zero
                }
            }
        }
    
    Attributes:
        cond: The Boolean condition expression
        true_c: Constraints applied when condition is true
        false_c: Constraints applied when condition is false (may be empty)
    
    See Also:
        ConstraintScope, ConstraintStmtExpr, ConstraintStmtImplication
    
    """
    pass
    
    def getCond(self) -> Expr: ...
    
    def getTrue_c(self) -> ConstraintScope: ...
    
    def getFalse_c(self) -> ConstraintScope: ...
    
class ConstraintStmtUnique(ConstraintStmt):
    """
    Uniqueness constraint ensuring distinct values.
    
    Constrains a set of expressions to have mutually distinct values during randomization.
    All expressions in the list must evaluate to different values, preventing duplicates
    within the specified set.
    
    PSS Example::
    
        action transaction_set {
            rand bit[8] id1, id2, id3, id4;
            rand bit[16] addr[4];
            
            constraint unique_ids_c {
                unique { id1, id2, id3, id4 };
            }
            
            constraint unique_addresses_c {
                unique { addr[0], addr[1], addr[2], addr[3] };
            }
            
            constraint mixed_unique_c {
                unique { id1, id2, id3 };  // First three must differ
                // id4 is not constrained by this
            }
        }
    
    Attributes:
        list: Expressions that must have unique values
    
    See Also:
        ConstraintStmtExpr, ExprHierarchicalId
    
    """
    pass
    
    def list(self) -> ListUtil...
        """Returns an iterator over the items"""
    
    def getList(self) -> List[ExprHierarchicalId]: ...
    
class Covergroup(NamedScopeChild):
    """
    An inline covergroup instance declared in an action/struct/component.
    
    Corresponds to the PSS ``covergroup { ... } name;`` form. Carries the
    instance name (inherited) plus its coverpoints and crosses.
    
    PSS Example::
    
        action a {
            rand bit[4] x, y;
            covergroup {
                coverpoint x;
                coverpoint y;
                xy : cross x, y;
            } cg;
        }
    
    Attributes:
        name: Covergroup instance name (inherited from NamedScopeChild)
        coverpoints: The covergroup's coverpoints
        crosses: The covergroup's crosses
    
    See Also:
        CovergroupCoverpoint, CovergroupCross
    
    """
    pass
    
    def coverpoints(self) -> ListUtil...
        """Returns an iterator over the items"""
    
    def getCoverpoints(self) -> List[CovergroupCoverpoint]: ...
    
    def crosses(self) -> ListUtil...
        """Returns an iterator over the items"""
    
    def getCrosses(self) -> List[CovergroupCross]: ...
    
class CovergroupCoverpoint(NamedScopeChild):
    """
    A coverpoint within a covergroup.
    
    Samples the value of ``target`` (an expression, typically a field
    reference). The coverpoint name is the optional label, or the target
    identifier when unlabeled.
    
    PSS Example::
    
        covergroup {
            cp_x : coverpoint x;   // labeled
            coverpoint y;          // unlabeled (name 'y')
        } cg;
    
    Attributes:
        name: Coverpoint name (inherited from NamedScopeChild)
        target: Expression being sampled
    
    See Also:
        Covergroup, CovergroupCross
    
    """
    pass
    
    def getTarget(self) -> Expr: ...
    
class CovergroupCross(NamedScopeChild):
    """
    A cross of named coverpoints within a covergroup.
    
    PSS Example::
    
        covergroup {
            coverpoint a;
            coverpoint b;
            ab : cross a, b;
        } cg;
    
    Attributes:
        name: Cross name (inherited from NamedScopeChild)
        coverpoint_names: Names of the coverpoints being crossed
    
    See Also:
        Covergroup, CovergroupCoverpoint
    
    """
    pass
    
    def coverpoint_names(self) -> ListUtil...
        """Returns an iterator over the items"""
    
    def getCoverpoint_names(self) -> List[ExprId]: ...
    
class DataTypeBool(DataType):
    """
    Boolean data type.
    
    Represents the 'bool' type in PSS. Boolean values are true or false.
    
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
    Opaque handle type for referencing external objects.
    
    Represents the 'chandle' type - an opaque pointer to data managed
    outside PSS (typically C/C++ objects). Used for interfacing with
    external code and APIs.
    
    PSS Example::
    
        function void use_object(chandle obj);
    
    See Also:
        DataType, DataTypePyObj
    
    """
    pass
    
class DataTypeEnum(DataType):
    """
    Enum type reference with optional range restriction.
    
    Represents a reference to an enum type, optionally restricted to
    a subset of enum values using an 'in' range expression.
    
    PSS Example::
    
        enum my_enum { A, B, C, D };
        
        rand my_enum value in [A, B];    // Only A or B allowed
    
    Attributes:
        tid: Reference to the user-defined enum type
        in_rangelist: Optional range restriction expression
    
    See Also:
        EnumDecl, DataTypeUserDefined, ExprOpenRangeList
    
    """
    pass
    
    def getTid(self) -> DataTypeUserDefined: ...
    
    def getIn_rangelist(self) -> ExprOpenRangeList: ...
    
class DataTypeInt(DataType):
    """
    Integer data type with signedness, width, and optional range.
    
    Represents integer types in PSS. Can be signed/unsigned, have
    explicit or inferred bit-width, and include value constraints.
    
    PSS Example::
    
        int<8> byte_val;                    // 8-bit signed
        bit<16> word_val;                   // 16-bit unsigned
        rand int addr in [0x1000..0x2000];  // With range constraint
        int value;                          // Implementation-defined width
    
    Attributes:
        is_signed: True for 'int', false for 'bit'
        width: Bit-width expression (optional)
        in_range: Optional domain range constraint
    
    See Also:
        DataType, ExprDomainOpenRangeList
    
    """
    pass
    
    def getWidth(self) -> Expr: ...
    
    def getIn_range(self) -> ExprDomainOpenRangeList: ...
    
class DataTypePyObj(DataType):
    """
    Python object type for embedded Python integration.
    
    Represents Python objects accessible within PSS. Used for
    interfacing with embedded Python code and libraries.
    
    See Also:
        DataTypeChandle, PyImportStmt
    
    """
    pass
    
class DataTypeRef(DataType):
    """
    Reference type to another type instance.
    
    Represents a reference (pointer) to an instance of a user-defined
    type. Used for creating references to action or component instances.
    
    PSS Example::
    
        action A { }
        
        action B {
            ref A a_ref;    // Reference to action A instance
        }
    
    Attributes:
        type: The user-defined type being referenced
    
    See Also:
        DataTypeUserDefined, FieldRef
    
    """
    pass
    
    def getType(self) -> DataTypeUserDefined: ...
    
class DataTypeString(DataType):
    """
    String data type with optional value constraint.
    
    Represents string literals and variables in PSS. Can be constrained
    to a specific set of allowed string values.
    
    PSS Example::
    
        string message;
        rand string mode in ["read", "write", "execute"];
    
    Attributes:
        has_range: True if 'in' constraint is present
        in_range: List of allowed string values
    
    See Also:
        DataType, ExprString
    
    """
    pass
    
    def in_range(self) -> ListUtil...
        """Returns an iterator over the items"""
    
    def getIn_range(self) -> List[str]: ...
    
class DataTypeUserDefined(DataType):
    """
    Reference to a user-defined type (action, component, struct, enum).
    
    Represents a type reference using a type identifier. The identifier
    may be simple or hierarchical (package-qualified). Resolution to the
    actual type occurs during linking phase.
    
    PSS Example::
    
        my_pkg::my_action a1;        // Qualified type reference
        my_struct s1;                // Simple type reference
    
    Attributes:
        is_global: True if type reference starts with '::'
        type_id: Hierarchical type identifier
    
    See Also:
        TypeIdentifier, DataType, Action, Component, Struct
    
    """
    pass
    
    def getType_id(self) -> TypeIdentifier: ...
    
class EnumDecl(NamedScopeChild):
    """
    Enum type declaration with named values.
    
    Declares an enumerated type with a set of named constant values.
    Enums can be used as field types and in constraints.
    
    PSS Example::
    
        enum direction {
            NORTH, SOUTH, EAST, WEST
        };
        
        enum error_code {
            SUCCESS = 0,
            ERR_INVALID = 1,
            ERR_TIMEOUT = 2
        };
    
    Attributes:
        name: Enum type name (inherited from NamedScopeChild)
        items: List of enumerator values
    
    See Also:
        EnumItem, DataTypeEnum
    
    """
    pass
    
    def items(self) -> ListUtil...
        """Returns an iterator over the items"""
    
    def getItems(self) -> List[EnumItem]: ...
    
class EnumItem(NamedScopeChild):
    """
    Single enumerator value within an enum declaration.
    
    Represents one named value in an enum. Can have an explicit value
    expression or be auto-assigned sequentially.
    
    PSS Example::
    
        enum status {
            OK = 0,          // Explicit value
            ERROR,           // Auto-assigned value (1)
            PENDING = 100    // Explicit value
        };
    
    Attributes:
        name: Enumerator identifier (inherited from NamedScopeChild)
        value: Optional value expression
        upper: Back-reference to containing enum scope
    
    See Also:
        EnumDecl, NamedScopeChild
    
    """
    pass
    
    def getValue(self) -> Expr: ...
    
    def getUpper(self) -> SymbolEnumScope: ...
    
class ExprAggrEmpty(ExprAggrLiteral):
    """
    Represents an empty aggregate literal.
    
    Used to initialize arrays, maps, or structs with no elements. This is the
    literal form `{}` that creates an empty collection or default-initialized
    composite structure.
    
    PSS Example::
    
        array<int, 10> arr = {};  // Empty array literal
        map<string, int> m = {};  // Empty map literal
    
    See Also:
        ExprAggrLiteral, ExprAggrList, ExprAggrMap
    
    """
    pass
    
class ExprAggrList(ExprAggrLiteral):
    """
    Represents an array or list literal expression.
    
    Contains a comma-separated list of expressions enclosed in braces. Used to
    initialize arrays with explicit element values. Each element expression is
    evaluated and assigned to the corresponding array position.
    
    PSS Example::
    
        array<int, 5> values = {1, 2, 3, 4, 5};
        array<bit[8], 3> bytes = {8'hFF, 8'h00, 8'hAA};
    
    Attributes:
        elems: List of expression elements in the array literal
    
    See Also:
        ExprAggrLiteral, ExprAggrEmpty
    
    """
    pass
    
    def elems(self) -> ListUtil...
        """Returns an iterator over the items"""
    
    def getElems(self) -> List[Expr]: ...
    
class ExprAggrMap(ExprAggrLiteral):
    """
    Represents a map literal expression.
    
    Contains key-value pairs for initializing map data structures. Each element
    is an ExprAggrMapElem with a key in square brackets followed by a colon and value.
    
    PSS Example::
    
        map<string, int> ages = {
            ["Alice"]: 30,
            ["Bob"]: 25,
            ["Charlie"]: 35
        };
    
    Attributes:
        elems: List of key-value pair elements
    
    See Also:
        ExprAggrMapElem, ExprAggrLiteral
    
    """
    pass
    
    def elems(self) -> ListUtil...
        """Returns an iterator over the items"""
    
    def getElems(self) -> List[ExprAggrMapElem]: ...
    
class ExprAggrStruct(ExprAggrLiteral):
    """
    Represents a struct literal expression.
    
    Initializes a struct with named field values. Each element specifies a field name
    and its corresponding value expression. Fields can be initialized in any order,
    and unspecified fields receive default values.
    
    PSS Example::
    
        struct Point {
            int x;
            int y;
        }
        
        Point p = {x: 100, y: 200};
    
    Attributes:
        elems: List of field initialization elements
    
    See Also:
        ExprAggrStructElem, ExprAggrLiteral
    
    """
    pass
    
    def elems(self) -> ListUtil...
        """Returns an iterator over the items"""
    
    def getElems(self) -> List[ExprAggrStructElem]: ...
    
class ExprRefPathContext(ExprRefPath):
    """
    Represents a context-relative reference path.
    
    A reference that navigates relative to the current context, optionally
    starting with a super reference to access parent scope. The hier_id
    specifies the path to follow.
    
    PSS Example::
    
        super.parent_field      // Access parent's field
        comp.sub.field          // Navigate through context
    
    Attributes:
        is_super: True if path starts with super keyword
        hier_id: Hierarchical identifier path
        slice: Optional bit slice
    
    See Also:
        ExprRefPath, ExprHierarchicalId, ExprRefPathSuper
    
    """
    pass
    
    def getHier_id(self) -> ExprHierarchicalId: ...
    
    def getSlice(self) -> ExprBitSlice: ...
    
class ExprRefPathId(ExprRefPath):
    """
    Represents a simple identifier reference path.
    
    A reference consisting of a single identifier, optionally followed by a
    bit slice. The simplest form of reference path, used to access local
    variables, fields, or parameters.
    
    PSS Example::
    
        my_field
        value[7:0]          // With bit slice
        variable
    
    Attributes:
        id: The identifier being referenced
        slice: Optional bit slice for bit-range extraction
    
    See Also:
        ExprRefPath, ExprId, ExprBitSlice
    
    """
    pass
    
    def getId(self) -> ExprId: ...
    
    def getSlice(self) -> ExprBitSlice: ...
    
class ExprRefPathStatic(ExprRefPath):
    """
    Represents a static reference path to types or symbols.
    
    Used to reference types, packages, or compile-time constants through
    qualified names. Can be global (starting with ::) or relative. The base
    contains the type identifier path elements.
    
    PSS Example::
    
        ::my_pkg::my_type           // Global static reference
        pkg::type_name              // Package-qualified type
        std::addr_handle_t          // Standard library type
    
    Attributes:
        is_global: True if path starts with :: (global scope)
        base: List of type identifier elements forming the path
        slice: Optional bit slice
    
    See Also:
        ExprRefPath, TypeIdentifierElem, ExprRefPathStaticFunc
    
    """
    pass
    
    def base(self) -> ListUtil...
        """Returns an iterator over the items"""
    
    def getBase(self) -> List[TypeIdentifierElem]: ...
    
    def getSlice(self) -> ExprBitSlice: ...
    
class ExprRefPathStaticRooted(ExprRefPath):
    """
    Represents a reference path with static root and dynamic leaf.
    
    Combines a static reference path (root) with a hierarchical identifier
    (leaf) for mixed static/dynamic references. The root is resolved statically,
    then the leaf is navigated dynamically from that point.
    
    PSS Example::
    
        my_pkg::my_type::field.subfield
        // root: my_pkg::my_type
        // leaf: field.subfield
    
    Attributes:
        root: Static reference path to the base
        leaf: Hierarchical identifier for dynamic navigation
        slice: Optional bit slice
    
    See Also:
        ExprRefPathStatic, ExprHierarchicalId
    
    """
    pass
    
    def getRoot(self) -> ExprRefPathStatic: ...
    
    def getLeaf(self) -> ExprHierarchicalId: ...
    
    def getSlice(self) -> ExprBitSlice: ...
    
class ExprSignedNumber(ExprNumber):
    """
    Represents a signed integer literal value.
    
    Stores a signed numeric constant with its textual representation, bit width,
    and numeric value. Can represent negative numbers and is used for signed
    arithmetic expressions.
    
    PSS Example::
    
        -42
        -8'sd10         // Signed decimal with specified width
        -100
    
    Attributes:
        image: Original text representation from source
        width: Bit width of the value (0 for unsized)
        value: The signed integer value
    
    See Also:
        ExprNumber, ExprUnsignedNumber
    
    """
    pass
    
    def getImage(self) -> str: ...
    
    def setImage(self, v : str): ...
    
class ExprUnsignedNumber(ExprNumber):
    """
    Represents an unsigned integer literal value.
    
    Stores an unsigned numeric constant with its textual representation, bit width,
    and numeric value. Used for positive integers and unsigned arithmetic.
    
    PSS Example::
    
        42
        8'hFF           // Hexadecimal with specified width
        32'hDEADBEEF    // 32-bit hex value
        1000
    
    Attributes:
        image: Original text representation from source
        width: Bit width of the value (0 for unsized)
        value: The unsigned integer value
    
    See Also:
        ExprNumber, ExprSignedNumber
    
    """
    pass
    
    def getImage(self) -> str: ...
    
    def setImage(self, v : str): ...
    
class ExtendType(Scope):
    """
    Maps between local item identifier and item child index
    
    """
    pass
    
    def setKind(self, v : ExtendTargetE): ...
    
    def getTarget(self) -> TypeIdentifier: ...
    
    def getImports(self) -> SymbolImportSpec: ...
    
class Field(NamedScopeChild):
    """
    Data field declaration within actions, components, or structs.
    
    Represents variable declarations with optional type, attributes,
    and initialization. Fields can be randomized ('rand'), constant
    ('const'), static ('static'), or have visibility modifiers.
    
    PSS Example::
    
        action my_action {
            rand int<32> addr;           // Random field
            const int timeout = 100;     // Constant field
            static int counter;          // Static field
            private bool flag;           // Private field
        }
    
    Attributes:
        name: Field identifier (inherited from NamedScopeChild)
        type: Data type of the field
        attr: Attribute flags (FieldAttr)
        init: Optional initializer expression
    
    See Also:
        FieldAttr, DataType, NamedScopeChild
    
    """
    pass
    
    def getType(self) -> DataType: ...
    
    def setAttr(self, v : FieldAttr): ...
    
    def getInit(self) -> Expr: ...
    
class FieldClaim(NamedScopeChild):
    """
    Claim or lock on a resource instance.
    
    Declares exclusive access to a resource for the duration of an
    action. Claims can be locks (exclusive) or shares (non-exclusive).
    Used for resource management and synchronization.
    
    PSS Example::
    
        resource bus_t { }
        
        action my_action {
            lock bus_t my_bus;     // Exclusive lock
            share bus_t my_bus2;   // Shared access
        }
    
    Attributes:
        name: Claim identifier (inherited from NamedScopeChild)
        type: Resource type to claim
        is_lock: True for 'lock', false for 'share'
    
    See Also:
        Struct (with kind=Resource), FieldRef
    
    """
    pass
    
    def getType(self) -> DataTypeUserDefined: ...
    
class FieldCompRef(NamedScopeChild):
    """
    Component reference field for hierarchical composition.
    
    Declares a reference to a component instance. Used for building
    the structural hierarchy of components within other components.
    
    PSS Example::
    
        component sub_comp { }
        
        component top_comp {
            sub_comp sc1;    // Component reference field
            sub_comp sc2;
        }
    
    Attributes:
        name: Field name (inherited from NamedScopeChild)
        type: User-defined component type
    
    See Also:
        FieldRef, Component, DataTypeUserDefined
    
    """
    pass
    
    def getType(self) -> DataTypeUserDefined: ...
    
class FieldPool(NamedScopeChild):
    """
    Pool declaration within a component.
    
    Declares a pool of flow- or resource-objects of a given type, with an
    optional size (capacity). Actions bind their object references to pools
    via ``bind`` statements.
    
    PSS Example::
    
        component pss_top {
            pool [16] my_resource pool_a;   // sized pool
            pool my_buffer pool_b;          // unsized pool
        }
    
    Attributes:
        name: Pool identifier (inherited from NamedScopeChild)
        type: Element type held by the pool
        size: Optional capacity expression (null if unsized)
    
    See Also:
        FieldClaim, FieldRef
    
    """
    pass
    
    def getType(self) -> DataTypeUserDefined: ...
    
    def getSize(self) -> Expr: ...
    
class FieldRef(NamedScopeChild):
    """
    Reference field pointing to action/component instances.
    
    Declares a reference (pointer) to an action or component instance.
    References can be inputs (passed in) or outputs (assigned internally).
    Used for action composition and resource sharing.
    
    PSS Example::
    
        action producer { }
        
        action consumer {
            input producer p_ref;    // Input reference
            ref producer p_local;    // Local reference
        }
    
    Attributes:
        name: Reference name (inherited from NamedScopeChild)
        type: User-defined type being referenced
        is_input: True if declared as 'input'
    
    See Also:
        FieldCompRef, FieldClaim, DataTypeRef
    
    """
    pass
    
    def getType(self) -> DataTypeUserDefined: ...
    
class FunctionImportProto(FunctionImport):
    """
    Import a single external function by prototype.
    
    Imports a specific external function by declaring its complete
    prototype (signature). The function is implemented externally in
    the specified language and platform. Used for integrating individual
    foreign functions into PSS.
    
    PSS Example::
    
        // Import C++ target function
        import function void write_reg(
            int addr, 
            int data
        ) = target "cpp";
        
        // Import Python solve-time function
        import function int optimize(
            input int constraints[], 
            output int solution[]
        ) = solve "python";
        
        // Import with various parameter types
        import function string format_message(
            string fmt,
            input int value,
            ...
        ) = target;
        
        action my_action {
            exec body {
                write_reg(0x1000, 0x42);
                string msg = format_message("Value: %d", 42);
            }
        }
    
    Attributes:
        plat: Platform qualifier (inherited from FunctionImport)
        lang: Implementation language (inherited from FunctionImport)
        proto: Complete function prototype with signature
    
    See Also:
        FunctionImport, FunctionImportType, FunctionPrototype
    
    """
    pass
    
    def getProto(self) -> FunctionPrototype: ...
    
class FunctionImportType(FunctionImport):
    """
    Import all functions from an external type/class.
    
    Imports all methods from a specified external type by referencing
    its type identifier. Used when importing entire classes or packages
    of utility functions from foreign implementations.
    
    PSS Example::
    
        // Import all methods from a C++ class
        import class my_pkg::MathUtils = target "cpp";
        
        // Import Python utility package for solve-time
        import class algorithms::Optimizer = solve "python";
        
        component my_comp {
            // Can now use imported functions
            exec init {
                int result = MathUtils::square(5);
            }
        }
    
    Attributes:
        plat: Platform qualifier (inherited from FunctionImport)
        lang: Implementation language (inherited from FunctionImport)
        type: Type identifier of the class/package to import
    
    See Also:
        FunctionImport, FunctionImportProto, TypeIdentifier
    
    """
    pass
    
    def getType(self) -> TypeIdentifier: ...
    
class FunctionPrototype(NamedScopeChild):
    """
    Function signature without implementation.
    
    Represents a function's interface: return type, name, and parameter
    list. Used both in complete function definitions and standalone
    prototypes. Can be marked as pure virtual, and qualified for
    target or solve-time execution. Core functions are built-in library
    functions.
    
    PSS Example::
    
        // Pure virtual method in action
        action base_action {
            pure virtual function void execute();
        }
        
        // Function prototype with parameters
        function int multiply(int a, int b);
        
        // Target function prototype
        function void hw_write(int addr, int data) = target;
        
        // Solve-time function prototype
        function int compute_size() = solve;
    
    Attributes:
        name: Function name (inherited from NamedScopeChild)
        rtype: Return type (void if no return)
        parameters: List of parameter declarations
        is_pure: True if declared as 'pure virtual'
        is_target: True if qualified with '= target'
        is_solve: True if qualified with '= solve'
        is_core: True for built-in library functions
    
    See Also:
        FunctionDefinition, FunctionParamDecl, FunctionImportProto
    
    """
    pass
    
    def getRtype(self) -> DataType: ...
    
    def parameters(self) -> ListUtil...
        """Returns an iterator over the items"""
    
    def getParameters(self) -> List[FunctionParamDecl]: ...
    
class GlobalScope(Scope):
    """
    Root scope representing a single source file.
    
    The top-level container for all PSS declarations in one compilation
    unit. Each source file parsed creates one GlobalScope containing all
    package declarations, imports, and top-level definitions.
    
    Attributes:
        fileid: Unique identifier for this source file
        filename: Path to the source file
        children: All top-level declarations (inherited from Scope)
    
    See Also:
        Scope, PackageScope
    
    """
    pass
    
    def getFilename(self) -> str: ...
    
    def setFilename(self, v : str): ...
    
class MonitorActivityActionTraversal(MonitorActivityStmt):
    """
    Monitors the execution of a specific action instance.
    
    MonitorActivityActionTraversal allows a monitor to observe the execution
    of a specific action instance referenced by a handle. This enables monitoring
    action behavior, timing, and completion. The action reference can include
    inline constraints to refine monitoring scope. Note these are PSS 3.0 features.
    
    PSS Example::
    
        component my_comp {
            action transfer_action {
                rand bit[16] addr;
            }
        }
        
        monitor transfer_monitor {
            my_comp comp;
            
            activity {
                // Monitor specific action execution
                monitor comp.transfer_action;
                
                // Monitor with constraint
                monitor comp.transfer_action with {
                    addr < 0x1000;
                }
                
                // Combined with temporal operators
                start ##1 monitor comp.transfer_action ##1 end;
            }
        }
    
    Attributes:
        target: Reference path to the action instance to monitor
        with_c: Optional constraint statement applied to monitoring
    
    See Also:
        MonitorActivityMonitorTraversal, ActivityActionHandleTraversal,
        ExprRefPath
    
    """
    pass
    
    def getTarget(self) -> ExprRefPath: ...
    
    def getWith_c(self) -> ConstraintStmt: ...
    
class MonitorActivityConcat(MonitorActivityStmt):
    """
    Temporal concatenation operator for sequential event monitoring.
    
    MonitorActivityConcat represents the temporal concatenation operator (##)
    that specifies two monitor activities must occur in sequence, with optional
    cycle delay between them. The left-hand side must complete before the
    right-hand side is checked. This is the fundamental temporal operator for
    building time-based sequences. Note these are PSS 3.0 features.
    
    PSS Example::
    
        monitor protocol_monitor {
            activity {
                // Immediate concatenation
                req ##0 ack;              // req and ack in same cycle
                
                // Fixed delay
                start ##1 data;           // start, then 1 cycle, then data
                req ##3 grant;            // req, then 3 cycles, then grant
                
                // Chained concatenation
                phase1 ##1 phase2 ##1 phase3;
                
                // Complex expressions
                (a || b) ##2 (c && d);
            }
        }
    
    Attributes:
        lhs: Left-hand side monitor activity (occurs first)
        rhs: Right-hand side monitor activity (occurs after delay)
    
    See Also:
        MonitorActivityOverlap, MonitorActivitySequence, MonitorActivityEventually
    
    """
    pass
    
    def getLhs(self) -> MonitorActivityStmt: ...
    
    def getRhs(self) -> MonitorActivityStmt: ...
    
class MonitorActivityEventually(MonitorActivityStmt):
    """
    Eventually operator for temporal property checking.
    
    MonitorActivityEventually specifies that a condition or monitor activity
    must eventually become true at some point in the future. Unlike concatenation
    which requires fixed timing, eventually allows any amount of time to pass
    before the property holds. This is used for liveness properties and
    non-deterministic timing. Note these are PSS 3.0 features.
    
    PSS Example::
    
        monitor liveness_check {
            activity {
                // Basic eventually
                eventually grant;         // grant must occur sometime
                
                // Eventually with condition
                eventually (status == DONE);
                
                // Combined with sequences
                sequence {
                    request;
                    eventually response;
                }
                
                // Multiple eventuallys
                req ##1 eventually ack ##1 eventually done;
                
                // Eventually with complex condition
                eventually (counter > 100 && valid);
            }
        }
    
    Attributes:
        condition: Optional expression that must eventually be true
        body: Monitor activity statement that must eventually occur
    
    See Also:
        MonitorActivityConcat, MonitorConstraint, MonitorActivityIfElse
    
    """
    pass
    
    def getCondition(self) -> Expr: ...
    
    def getBody(self) -> MonitorActivityStmt: ...
    
class MonitorActivityIfElse(MonitorActivityStmt):
    """
    Conditional branching in monitor activities.
    
    MonitorActivityIfElse provides conditional execution of monitor activities
    based on a boolean expression. If the condition is true, the true branch
    is monitored; otherwise, the optional false branch is monitored. This allows
    mode-dependent or data-dependent monitoring patterns. Note these are PSS 3.0
    features.
    
    PSS Example::
    
        monitor conditional_protocol {
            rand bit[2] mode;
            rand bit fast_mode;
            
            activity {
                // Basic if-else
                if (mode == 0) {
                    basic_sequence;
                } else {
                    extended_sequence;
                }
                
                // If without else
                if (fast_mode) {
                    quick_check;
                }
                
                // Nested conditions
                if (mode == 0) {
                    protocol_a;
                } else if (mode == 1) {
                    protocol_b;
                } else {
                    protocol_default;
                }
                
                // Combined with temporal operators
                start ##1 if (error) error_handler else normal_path ##1 done;
            }
        }
    
    Attributes:
        cond: Boolean expression determining which branch to monitor
        true_s: Monitor activity for true condition
        false_s: Optional monitor activity for false condition
    
    See Also:
        MonitorActivitySelect, ActivityIfElse, MonitorActivityMatch
    
    """
    pass
    
    def getCond(self) -> Expr: ...
    
    def getTrue_s(self) -> MonitorActivityStmt: ...
    
    def getFalse_s(self) -> MonitorActivityStmt: ...
    
class MonitorActivityMatch(MonitorActivityStmt):
    """
    Multi-way pattern matching for monitor activities.
    
    MonitorActivityMatch provides multi-way branching based on matching an
    expression against multiple value ranges or patterns. Each choice specifies
    a pattern and corresponding monitor activity. A default choice can handle
    unmatched cases. Note these are PSS 3.0 features.
    
    PSS Example::
    
        monitor state_based {
            rand bit[3] state;
            
            activity {
                // Match on state value
                match (state) {
                    0: idle_protocol;
                    [1..3]: active_protocol;
                    4: suspend_protocol;
                    default: error_protocol;
                }
                
                // Complex patterns
                match (opcode) {
                    READ: read_sequence;
                    WRITE: write_sequence;
                    [BURST_READ, BURST_WRITE]: burst_sequence;
                    default: unknown_op;
                }
                
                // Combined with temporal operators
                init ##1 match (mode) {
                    0: fast_path ##1 done;
                    1: slow_path ##1 done;
                }
            }
        }
    
    Attributes:
        cond: Expression to match against choice patterns
        choices: List of match choices with patterns and bodies
    
    See Also:
        MonitorActivityMatchChoice, MonitorActivityIfElse, ActivityMatch
    
    """
    pass
    
    def getCond(self) -> Expr: ...
    
    def choices(self) -> ListUtil...
        """Returns an iterator over the items"""
    
    def getChoices(self) -> List[MonitorActivityMatchChoice]: ...
    
class MonitorActivityMonitorTraversal(MonitorActivityStmt):
    """
    Invokes a nested monitor instance.
    
    MonitorActivityMonitorTraversal allows hierarchical composition of monitors
    by invoking another monitor instance. This enables reuse of monitor
    specifications and building complex monitoring patterns from simpler ones.
    The monitor reference can include inline constraints. Note these are PSS 3.0
    features.
    
    PSS Example::
    
        monitor handshake_monitor {
            activity {
                req ##1 ack;
            }
        }
        
        monitor data_phase_monitor {
            activity {
                valid ##0 ready;
                eventually done;
            }
        }
        
        monitor protocol_monitor {
            handshake_monitor hshake;
            data_phase_monitor dphase;
            
            activity {
                // Invoke nested monitors
                monitor hshake;
                monitor dphase;
                
                // With constraints
                monitor hshake with {
                    // constraint expressions
                }
                
                // In temporal sequences
                start ##1 monitor hshake ##1 monitor dphase;
            }
        }
    
    Attributes:
        target: Reference path to the monitor instance to invoke
        with_c: Optional constraint statement applied to monitoring
    
    See Also:
        MonitorActivityActionTraversal, Monitor, ExprRefPath
    
    """
    pass
    
    def getTarget(self) -> ExprRefPath: ...
    
    def getWith_c(self) -> ConstraintStmt: ...
    
class MonitorActivityOverlap(MonitorActivityStmt):
    """
    Overlap operator for concurrent sequence monitoring.
    
    MonitorActivityOverlap specifies that two monitor activities can overlap
    in time, allowing concurrent or interleaved execution patterns to be
    monitored. Unlike concatenation which requires strict sequencing, overlap
    permits the activities to occur simultaneously or with interleaving.
    Note these are PSS 3.0 features.
    
    PSS Example::
    
        monitor concurrent_check {
            activity {
                // Overlapping sequences
                sequence { req1; data1; } overlap sequence { req2; data2; }
                
                // Concurrent protocol phases
                addr_phase overlap data_phase;
                
                // Multiple overlaps
                stream_a overlap stream_b overlap stream_c;
                
                // Complex overlap patterns
                (start ##1 process ##1 end) overlap (monitor_signal);
            }
        }
    
    Attributes:
        lhs: Left-hand side monitor activity
        rhs: Right-hand side monitor activity (can overlap with lhs)
    
    See Also:
        MonitorActivityConcat, MonitorActivitySequence, MonitorActivitySchedule
    
    """
    pass
    
    def getLhs(self) -> MonitorActivityStmt: ...
    
    def getRhs(self) -> MonitorActivityStmt: ...
    
class MonitorActivityRepeatCount(MonitorActivityStmt):
    """
    Fixed repetition of monitor activity.
    
    MonitorActivityRepeatCount specifies that a monitor activity must be observed
    a fixed number of times. The count can be a constant or expression, and an
    optional loop variable tracks the iteration index. This is used for monitoring
    repeated sequences or patterns. Note these are PSS 3.0 features.
    
    PSS Example::
    
        monitor burst_monitor {
            rand bit[4] burst_len;
            
            activity {
                // Fixed count
                repeat(4) data_beat;
                
                // Expression-based count
                repeat(burst_len) data_transfer;
                
                // With loop variable
                repeat(i: 8) {
                    beat[i] ##1 ack[i];
                }
                
                // Nested repeats
                repeat(4) {
                    start ##1 repeat(8) data ##1 end;
                }
                
                // Combined with temporal operators
                init ##1 repeat(burst_len) transfer ##1 done;
            }
        }
    
    Attributes:
        loop_var: Optional loop variable identifier for iteration index
        count: Expression specifying number of repetitions
        body: Monitor activity body to repeat
    
    See Also:
        MonitorActivityRepeatWhile, ActivityRepeatCount, MonitorActivityStmt
    
    """
    pass
    
    def getLoop_var(self) -> ExprId: ...
    
    def getCount(self) -> Expr: ...
    
    def getBody(self) -> ScopeChild: ...
    
class MonitorActivityRepeatWhile(MonitorActivityStmt):
    """
    Conditional repetition of monitor activity.
    
    MonitorActivityRepeatWhile specifies that a monitor activity should be
    repeatedly observed as long as a condition remains true. The condition is
    evaluated before each iteration. This is used for monitoring variable-length
    sequences or data-dependent patterns. Note these are PSS 3.0 features.
    
    PSS Example::
    
        monitor variable_length {
            rand bit more_data;
            rand bit[8] count;
            
            activity {
                // Simple condition
                repeat while (more_data) {
                    data_phase;
                }
                
                // Expression-based condition
                repeat while (count > 0) {
                    transfer;
                    count = count - 1;
                }
                
                // Complex temporal pattern
                init ##1 repeat while (active) {
                    req ##1 ack;
                } ##1 done;
                
                // Nested with other constructs
                repeat while (state == RUNNING) {
                    sequence {
                        cmd_valid;
                        ##[1:3] response;
                    }
                }
            }
        }
    
    Attributes:
        cond: Boolean expression evaluated before each iteration
        body: Monitor activity body to repeat while condition is true
    
    See Also:
        MonitorActivityRepeatCount, ActivityRepeatWhile, MonitorActivityStmt
    
    """
    pass
    
    def getCond(self) -> Expr: ...
    
    def getBody(self) -> ScopeChild: ...
    
class MonitorActivitySelect(MonitorActivityStmt):
    """
    Branch selection for alternative monitoring paths.
    
    MonitorActivitySelect represents a select construct that specifies multiple
    alternative monitoring paths. One branch is chosen based on guard conditions
    or non-deterministically. This allows monitoring of different protocol
    variants or alternative sequences. Note these are PSS 3.0 features.
    
    PSS Example::
    
        monitor protocol_variants {
            activity {
                // Non-deterministic choice
                select {
                    fast_path;
                    slow_path;
                }
                
                // Guarded selection
                select {
                    (mode == 0): basic_protocol;
                    (mode == 1): extended_protocol;
                    (mode == 2): burst_protocol;
                }
                
                // Labeled select
                protocol_choice: select {
                    short_transaction;
                    long_transaction;
                }
            }
        }
    
    Attributes:
        label: Optional identifier expression for the select label
        branches: List of select branches with guards and bodies
    
    See Also:
        MonitorActivitySelectBranch, ActivitySelect, MonitorActivityIfElse
    
    """
    pass
    
    def getLabel(self) -> ExprId: ...
    
    def branches(self) -> ListUtil...
        """Returns an iterator over the items"""
    
    def getBranches(self) -> List[MonitorActivitySelectBranch]: ...
    
class MonitorConstraint(MonitorActivityStmt):
    """
    Inline constraint within monitor activity.
    
    MonitorConstraint allows constraint statements to be embedded within monitor
    activity blocks to assert properties or relationships that must hold during
    monitoring. These constraints can reference monitor fields and express
    temporal invariants. Note these are PSS 3.0 features.
    
    PSS Example::
    
        monitor protocol_monitor {
            rand bit[8] priority;
            rand bit[16] addr;
            
            activity {
                // Inline constraints
                constraint {
                    priority inside [1..8];
                    addr % 4 == 0;
                }
                
                // Combined with temporal operators
                sequence {
                    start;
                    constraint { addr < 0x1000; }
                    data_transfer;
                }
                
                // Multiple constraints
                req ##1 {
                    constraint { priority > 0; }
                    ack;
                }
            }
        }
    
    Attributes:
        constraint: Constraint statement to be evaluated
    
    See Also:
        ConstraintStmt, MonitorActivityStmt, ActivityConstraint
    
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
        name: Identifier expression containing the name
    
    See Also:
        Scope, NamedScopeChild, TypeScope
    
    """
    pass
    
    def getName(self) -> ExprId: ...
    
class PackageScope(Scope):
    """
    PSS package scope for organizing and namespacing declarations.
    
    Represents a package declaration in PSS. Packages provide namespace
    management and can be split across multiple files. Multiple package
    declarations with the same name are merged together.
    
    PSS Example::
    
        package my_pkg {
            component C1 { }
            action A1 { }
        }
        
        package my_pkg {       // Same package, merged with above
            action A2 { }
        }
    
    Attributes:
        id: Hierarchical package identifier (e.g., ["my", "pkg"])
        sibling: Next package scope with the same name (for merging)
        children: Package members (inherited from Scope)
    
    See Also:
        Scope, PackageImportStmt
    
    """
    pass
    
    def id(self) -> ListUtil...
        """Returns an iterator over the items"""
    
    def getId(self) -> List[ExprId]: ...
    
    def getSibling(self) -> PackageScope: ...
    
class ProceduralStmtAssignment(ExecStmt):
    """
    Assignment statement with compound assignment operators.
    
    ProceduralStmtAssignment represents variable assignment operations in
    exec blocks. Supports simple assignment (=) and compound assignments
    (+=, -=, <<=, >>=, |=, &=) for modifying variable values.
    
    PSS Example::
    
        action my_action {
            exec body {
                int x = 10;
                int y = 20;
                
                x = y + 5;      // Simple assignment
                x += 10;        // Add and assign
                x -= 3;         // Subtract and assign
                x <<= 2;        // Shift left and assign
                x |= 0xFF;      // Bitwise OR and assign
            }
        }
    
    Attributes:
        lhs: Left-hand side expression (target variable)
        op: Assignment operator (=, +=, -=, etc.)
        rhs: Right-hand side expression (value to assign)
    
    See Also:
        AssignOp, ProceduralStmtExpr, ProceduralStmtDataDeclaration
    
    """
    pass
    
    def getLhs(self) -> Expr: ...
    
    def setOp(self, v : AssignOp): ...
    
    def getRhs(self) -> Expr: ...
    
class ProceduralStmtBody(ExecStmt):
    """
    Statement block containing a single statement or compound statement.
    
    ProceduralStmtBody wraps a statement or block of statements, providing
    a common base for control flow constructs that contain a body (while,
    repeat-while, etc.). The body can be a single statement or a scope
    containing multiple statements.
    
    PSS Example::
    
        action my_action {
            exec body {
                // Single statement body
                while (x > 0) x--;
                
                // Compound statement body
                while (y > 0) {
                    y--;
                    console.log(y);
                }
            }
        }
    
    Attributes:
        body: Statement or scope contained in this body
    
    See Also:
        ProceduralStmtWhile, ProceduralStmtRepeatWhile, ExecScope
    
    """
    pass
    
    def getBody(self) -> ScopeChild: ...
    
class ProceduralStmtBreak(ExecStmt):
    """
    Break statement to exit from innermost loop.
    
    ProceduralStmtBreak represents a break statement that immediately exits
    the innermost enclosing loop (while, repeat, repeat-while, foreach) or
    match statement. Execution continues with the statement following the loop.
    
    PSS Example::
    
        action my_action {
            exec body {
                int i = 0;
                
                while (true) {
                    console.log("i = ", i);
                    i++;
                    if (i >= 10) {
                        break;  // Exit the while loop
                    }
                }
                console.log("Loop exited");
            }
        }
    
    Attributes:
        (no attributes)
    
    See Also:
        ProceduralStmtContinue, ProceduralStmtWhile, ProceduralStmtForeach
    
    """
    pass
    
class ProceduralStmtContinue(ExecStmt):
    """
    Continue statement to skip to next loop iteration.
    
    ProceduralStmtContinue represents a continue statement that skips the
    remainder of the current iteration and jumps to the next iteration of
    the innermost enclosing loop (while, repeat, repeat-while, foreach).
    
    PSS Example::
    
        action my_action {
            exec body {
                repeat (i : 10) {
                    if (i % 2 == 0) {
                        continue;  // Skip even numbers
                    }
                    console.log("Odd: ", i);
                }
            }
        }
    
    Attributes:
        (no attributes)
    
    See Also:
        ProceduralStmtBreak, ProceduralStmtWhile, ProceduralStmtForeach
    
    """
    pass
    
class ProceduralStmtDataDeclaration(ExecStmt):
    """
    Local variable declaration with optional initialization.
    
    ProceduralStmtDataDeclaration represents the declaration of a local
    variable within an exec block. Variables are scoped to the block in
    which they are declared and can optionally be initialized with an
    expression.
    
    PSS Example::
    
        action my_action {
            exec body {
                // Declaration without initialization
                int x;
                
                // Declaration with initialization
                int y = 10;
                string msg = "Hello";
                bool flag = true;
                
                // Complex initialization
                int sum = x + y * 2;
            }
        }
    
    Attributes:
        name: Identifier for the variable being declared
        datatype: Type of the variable
        init: Optional initialization expression
    
    See Also:
        ProceduralStmtAssignment, DataType, Field
    
    """
    pass
    
    def getName(self) -> ExprId: ...
    
    def getDatatype(self) -> DataType: ...
    
    def getInit(self) -> Expr: ...
    
class ProceduralStmtExpr(ExecStmt):
    """
    Expression statement for side-effect expressions.
    
    ProceduralStmtExpr represents an expression evaluated for its side effects
    rather than its value. Commonly used for function calls, increment/decrement
    operations, and other expressions that modify state.
    
    PSS Example::
    
        action my_action {
            exec body {
                int x = 0;
                
                x++;                    // Increment expression
                x--;                    // Decrement expression
                my_func();              // Function call (see ProceduralStmtFunctionCall)
                (x > 5) ? x++ : x--;    // Conditional expression with side effects
            }
        }
    
    Attributes:
        expr: Expression to evaluate
    
    See Also:
        ProceduralStmtFunctionCall, ProceduralStmtAssignment, Expr
    
    """
    pass
    
    def getExpr(self) -> Expr: ...
    
class ProceduralStmtFunctionCall(ExecStmt):
    """
    Function or method call statement.
    
    ProceduralStmtFunctionCall represents a call to a function or method in
    an exec block. The prefix identifies the function (which may be qualified
    with package or component paths), and params provides the argument list.
    
    PSS Example::
    
        action my_action {
            exec body {
                // Simple function call
                my_function(10, 20);
                
                // Qualified function call
                my_pkg::my_function(x, y);
                
                // Method call on component
                comp.my_method(value);
                
                // Built-in function call
                console.log("Hello");
            }
        }
    
    Attributes:
        prefix: Static reference path to the function/method
        params: List of argument expressions
    
    See Also:
        ExprRefPathStaticRooted, FunctionDefinition, ProceduralStmtReturn
    
    """
    pass
    
    def getPrefix(self) -> ExprRefPathStaticRooted: ...
    
    def params(self) -> ListUtil...
        """Returns an iterator over the items"""
    
    def getParams(self) -> List[Expr]: ...
    
class ProceduralStmtIfElse(ExecStmt):
    """
    If-else-if-else conditional statement.
    
    ProceduralStmtIfElse represents a complete conditional statement with
    multiple if/else-if clauses and an optional else clause. Evaluates
    conditions in order and executes the first matching branch, or the
    else branch if no conditions match.
    
    PSS Example::
    
        action my_action {
            exec body {
                int x = 10;
                
                if (x > 20) {
                    console.log("Large");
                } else if (x > 10) {
                    console.log("Medium");
                } else if (x > 0) {
                    console.log("Small");
                } else {
                    console.log("Zero or negative");
                }
            }
        }
    
    Attributes:
        if_then: List of if/else-if clauses evaluated in order
        else_then: Optional else body executed if no clause matches
    
    See Also:
        ProceduralStmtIfClause, ProceduralStmtMatch
    
    """
    pass
    
    def if_then(self) -> ListUtil...
        """Returns an iterator over the items"""
    
    def getIf_then(self) -> List[ProceduralStmtIfClause]: ...
    
    def getElse_then(self) -> ScopeChild: ...
    
class ProceduralStmtMatch(ExecStmt):
    """
    Pattern matching statement for value-based branching.
    
    ProceduralStmtMatch represents a match statement that evaluates an
    expression and executes the body of the first matching choice. Similar
    to switch-case in other languages but supports range patterns and
    more complex matching.
    
    PSS Example::
    
        action my_action {
            exec body {
                int status = get_status();
                
                match (status) {
                    [0..9]: {
                        console.log("Single digit");
                    }
                    [10, 20, 30]: {
                        console.log("Multiple values");
                    }
                    default: {
                        console.log("Other value");
                    }
                }
            }
        }
    
    Attributes:
        expr: Expression to match against choice patterns
        choices: List of match choices with patterns and bodies
    
    See Also:
        ProceduralStmtMatchChoice, ProceduralStmtIfElse, ExprOpenRangeList
    
    """
    pass
    
    def getExpr(self) -> Expr: ...
    
    def choices(self) -> ListUtil...
        """Returns an iterator over the items"""
    
    def getChoices(self) -> List[ProceduralStmtMatchChoice]: ...
    
class ProceduralStmtMatchChoice(ExecStmt):
    """
    Single choice in a match statement with pattern and body.
    
    ProceduralStmtMatchChoice represents one branch in a match statement.
    Each choice specifies a pattern (value, range, or list) to match against,
    or serves as the default case. The body executes if the match expression
    matches this choice's pattern.
    
    PSS Example::
    
        action my_action {
            exec body {
                int x = 10;
                
                match (x) {
                    [0..9]: {              // Range pattern
                        console.log("0-9");
                    }
                    [10, 20, 30]: {        // Value list pattern
                        console.log("Special values");
                    }
                    default: {             // Default case (is_default=true)
                        console.log("Other");
                    }
                }
            }
        }
    
    Attributes:
        is_default: True if this is the default case
        cond: Pattern to match (range list), null for default
        body: Statement(s) to execute if pattern matches
    
    See Also:
        ProceduralStmtMatch, ExprOpenRangeList, ExprOpenRangeValue
    
    """
    pass
    
    def getCond(self) -> ExprOpenRangeList: ...
    
    def getBody(self) -> ScopeChild: ...
    
class ProceduralStmtRandomize(ExecStmt):
    """
    Inline randomization with optional constraints.
    
    ProceduralStmtRandomize represents an inline randomization statement
    that randomizes a variable or object with optional additional constraints.
    This allows procedural code to trigger randomization at specific points
    with customized constraint sets.
    
    PSS Example::
    
        action my_action {
            rand int x;
            rand int y;
            
            exec body {
                // Randomize with inline constraints
                randomize (x, y) with {
                    x > 0;
                    y < 100;
                    x + y < 50;
                };
                
                console.log("x=", x, " y=", y);
            }
        }
    
    Attributes:
        target: Expression identifying what to randomize
        constraints: List of inline constraint statements
    
    See Also:
        ConstraintStmt, ConstraintBlock, Field
    
    """
    pass
    
    def getTarget(self) -> Expr: ...
    
    def constraints(self) -> ListUtil...
        """Returns an iterator over the items"""
    
    def getConstraints(self) -> List[ConstraintStmt]: ...
    
class ProceduralStmtReturn(ExecStmt):
    """
    Return statement from function or method.
    
    ProceduralStmtReturn represents a return statement that exits the current
    function or method, optionally returning a value. For void functions, the
    expr field is null.
    
    PSS Example::
    
        function int add(int a, int b) {
            exec body {
                return a + b;  // Return with value
            }
        }
        
        function void log_message(string msg) {
            exec body {
                console.log(msg);
                return;  // Return without value
            }
        }
    
    Attributes:
        expr: Expression to return (null for void functions)
    
    See Also:
        ProceduralStmtFunctionCall, FunctionDefinition, FunctionPrototype
    
    """
    pass
    
    def getExpr(self) -> Expr: ...
    
class ProceduralStmtYield(ExecStmt):
    """
    Yield control back to scheduler or runtime.
    
    ProceduralStmtYield represents a yield statement that temporarily suspends
    execution and returns control to the scheduler or runtime system. This
    allows cooperative multitasking and time-slicing in execution models.
    
    PSS Example::
    
        action my_action {
            exec body {
                console.log("Starting work");
                
                // Yield control to allow other actions to run
                yield;
                
                console.log("Resuming work");
            }
        }
    
    Attributes:
        (no attributes)
    
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
        name: Identifier for this scope (package, type, function name)
        children: List of child declarations and sub-scopes
        target: Reference to the original physical AST node being wrapped
    
    See Also:
        SymbolChild, SymbolScope, ScopeChild
    
    """
    pass
    
    def getName(self) -> str: ...
    
    def setName(self, v : str): ...
    
    def children(self) -> ListUtil...
        """Returns an iterator over the items"""
    
    def getChildren(self) -> List[ScopeChild]: ...
    
    def getTarget(self) -> ScopeChild: ...
    
class TemplateCategoryTypeParamDecl(TemplateParamDecl):
    """
    Category-constrained type template parameter declaration.
    
    Declares a template type parameter constrained to a specific type category
    (action, component, buffer, resource, state, stream, or struct). This ensures
    type safety by restricting template instantiation to compatible types. An
    optional restriction can further narrow the accepted types to a specific base
    type or interface, and a default type can be provided.
    
    PSS Example::
    
        // Action category constraint
        component action_container<T: action> {
            T action_inst;
            
            activity {
                do action_inst;
            }
        }
        
        // Resource category constraint with default
        action resource_user<R: resource = my_resource_t> {
            lock R resource_lock;
        }
        
        // Component category constraint
        component comp_wrapper<C: component> {
            C wrapped_comp;
        }
        
        // Instantiation examples
        action_container<my_action_t> container;
        resource_user<custom_resource_t> user;
        resource_user<> default_user;  // Uses my_resource_t
    
    Attributes:
        name: Identifier for the type parameter (inherited)
        category: Required type category (Action, Component, etc.)
        restriction: Optional base type or interface that must be satisfied
        dflt: Optional default type if not specified during instantiation
    
    See Also:
        TemplateGenericTypeParamDecl, TypeCategory, TypeIdentifier
    
    """
    pass
    
    def setCategory(self, v : TypeCategory): ...
    
    def getRestriction(self) -> TypeIdentifier: ...
    
    def getDflt(self) -> DataType: ...
    
class TemplateGenericTypeParamDecl(TemplateParamDecl):
    """
    Generic type template parameter declaration.
    
    Declares a template type parameter without category constraints. The parameter
    can be instantiated with any data type (built-in types, user-defined types,
    etc.). An optional default type can be specified for cases where the template
    is instantiated without explicit type arguments.
    
    PSS Example::
    
        // Generic type parameter without default
        action generic_action<T> {
            rand T value;
            
            exec body {
                // T can be any type
            }
        }
        
        // Generic type parameter with default
        struct generic_struct<T = bit<32>> {
            T data;
        }
        
        // Instantiation examples
        generic_action<bit<8>> byte_action;
        generic_action<int<32>> int_action;
        generic_struct<> default_struct;  // Uses bit<32>
    
    Attributes:
        name: Identifier for the type parameter (inherited)
        dflt: Optional default type if not specified during instantiation
    
    See Also:
        TemplateCategoryTypeParamDecl, TemplateParamDecl, DataType
    
    """
    pass
    
    def getDflt(self) -> DataType: ...
    
class TemplateValueParamDecl(TemplateParamDecl):
    """
    Value template parameter declaration.
    
    Declares a template parameter that accepts a compile-time constant value rather
    than a type. Value parameters must have a specific data type (typically integer
    types) and can have optional default values. These are commonly used for array
    sizes, repetition counts, and other compile-time configuration values.
    
    PSS Example::
    
        // Value parameter for array size
        struct fixed_array<int N> {
            bit<8> data[N];
        }
        
        // Multiple value parameters with defaults
        action repeated<int COUNT = 10, int WIDTH = 32> {
            bit<WIDTH> values[COUNT];
            
            exec body {
                repeat (COUNT) {
                    // Process each value
                }
            }
        }
        
        // Mixed type and value parameters
        action generic_sized<T, int SIZE> {
            T array[SIZE];
        }
        
        // Instantiation examples
        fixed_array<16> arr16;
        repeated<5, 64> custom;
        repeated<> default_repeated;  // Uses COUNT=10, WIDTH=32
        generic_sized<bit<8>, 32> byte_array;
    
    Attributes:
        name: Identifier for the value parameter (inherited)
        type: Data type of the parameter (e.g., int, bool)
        dflt: Optional default value expression
    
    See Also:
        TemplateGenericTypeParamDecl, TemplateParamExprValue, DataType
    
    """
    pass
    
    def getType(self) -> DataType: ...
    
    def getDflt(self) -> Expr: ...
    
class ActivityActionHandleTraversal(ActivityLabeledStmt):
    """
    Traverses a specific action instance (handle).
    
    ActivityActionHandleTraversal represents the execution of a specific action
    instance referenced by a handle (component field). It can include inline
    constraints to further refine the action's random variables.
    
    PSS Example::
    
        component my_comp {
            action sub_action {
                rand bit[16] addr;
            }
        }
        
        action top_action {
            my_comp comp;
            
            activity {
                // Basic traversal
                do comp.sub_action;
                
                // Traversal with inline constraint
                do comp.sub_action with {
                    addr == 0x1000;
                }
                
                // Labeled traversal
                label1: do comp.sub_action;
            }
        }
    
    Attributes:
        target: Reference path to the action instance
        with_c: Optional constraint statement applied to the traversal
    
    See Also:
        ActivityActionTypeTraversal, ExprRefPathContext
    
    """
    pass
    
    def getTarget(self) -> ExprRefPathContext: ...
    
    def getWith_c(self) -> ConstraintStmt: ...
    
    def initializers(self) -> ListUtil...
        """Returns an iterator over the items"""
    
    def getInitializers(self) -> List[ActionFieldInitializer]: ...
    
class ActivityActionTypeTraversal(ActivityLabeledStmt):
    """
    Traverses an action by type rather than specific instance.
    
    ActivityActionTypeTraversal allows execution of any action of a given type,
    with the specific instance selected at elaboration or runtime. This provides
    flexibility in action selection and can include inline constraints.
    
    PSS Example::
    
        action base_action {
            rand bit[16] addr;
        }
        
        action derived_action : base_action {
            rand bit[8] data;
        }
        
        action top_action {
            activity {
                // Traverse by type
                do base_action;
                
                // Traverse with constraint
                do base_action with {
                    addr inside [0..255];
                }
                
                // Labeled type traversal
                my_label: do derived_action;
            }
        }
    
    Attributes:
        target: User-defined data type specifying the action type
        with_c: Optional constraint statement applied to the traversal
    
    See Also:
        ActivityActionHandleTraversal, DataTypeUserDefined
    
    """
    pass
    
    def getTarget(self) -> DataTypeUserDefined: ...
    
    def getWith_c(self) -> ConstraintStmt: ...
    
    def initializers(self) -> ListUtil...
        """Returns an iterator over the items"""
    
    def getInitializers(self) -> List[ActionFieldInitializer]: ...
    
class ActivityAtomicBlock(ActivityLabeledStmt):
    """
    Marks a block of activities as atomic for scheduling.
    
    ActivityAtomicBlock ensures that the contained activities execute as an
    indivisible unit with respect to other concurrent activities. This provides
    atomicity guarantees for critical sections of activity execution.
    
    PSS Example::
    
        action my_action {
            activity {
                parallel {
                    sequence {
                        atomic {
                            do comp.read_resource;
                            do comp.modify_resource;
                            do comp.write_resource;
                        }
                    }
                    sequence {
                        atomic {
                            do comp.read_resource;
                            do comp.modify_resource;
                            do comp.write_resource;
                        }
                    }
                }
            }
        }
    
    Attributes:
        body: Activity statement body that executes atomically
    
    See Also:
        ActivitySequence, ActivityParallel
    
    """
    pass
    
    def getBody(self) -> ScopeChild: ...
    
class ActivityForeach(ActivityLabeledStmt):
    """
    Iterates over elements in a collection.
    
    ActivityForeach executes its body once for each element in a collection,
    providing access to the current element through an iterator variable and
    optionally the current index.
    
    PSS Example::
    
        action my_action {
            rand bit[8] data[10];
            
            activity {
                // Foreach with iterator
                foreach (d : data) {
                    do comp.process with {
                        value == d;
                    }
                }
                
                // Foreach with iterator and index
                foreach (d[i] : data) {
                    do comp.process with {
                        value == d;
                        index == i;
                    }
                }
            }
        }
    
    Attributes:
        it_id: Iterator identifier for the current element
        idx_id: Optional index identifier for the current position
        target: Reference path to the collection being iterated
        body: Activity statement body executed for each element
    
    See Also:
        ActivityRepeatCount, ActivityRepeatWhile
    
    """
    pass
    
    def getIt_id(self) -> ExprId: ...
    
    def getIdx_id(self) -> ExprId: ...
    
    def getTarget(self) -> ExprRefPathContext: ...
    
    def getBody(self) -> ScopeChild: ...
    
class ActivityIfElse(ActivityLabeledStmt):
    """
    Conditional execution of activity branches.
    
    ActivityIfElse provides conditional branching in activity blocks, executing
    one of two branches based on a boolean condition. Unlike select, the choice
    is deterministic based on the condition value.
    
    PSS Example::
    
        action my_action {
            rand bit[8] mode;
            rand bit enable;
            
            activity {
                // Simple if-else
                if (enable) {
                    do comp.enabled_action;
                } else {
                    do comp.disabled_action;
                }
                
                // If without else
                if (mode > 5) {
                    do comp.high_mode_action;
                }
                
                // Nested if-else
                if (mode == 0) {
                    do comp.mode0;
                } else if (mode == 1) {
                    do comp.mode1;
                } else {
                    do comp.default_mode;
                }
            }
        }
    
    Attributes:
        cond: Boolean expression determining which branch executes
        true_s: Activity statement executed when condition is true
        false_s: Optional activity statement executed when condition is false
    
    See Also:
        ActivitySelect, ActivityMatch
    
    """
    pass
    
    def getCond(self) -> Expr: ...
    
    def getTrue_s(self) -> ActivityStmt: ...
    
    def getFalse_s(self) -> ActivityStmt: ...
    
class ActivityMatch(ActivityLabeledStmt):
    """
    Pattern matching on expression values.
    
    ActivityMatch provides multi-way branching based on pattern matching against
    an expression value. It's similar to a switch statement, allowing matching
    against specific values, ranges, or a default case.
    
    PSS Example::
    
        action my_action {
            rand bit[8] opcode;
            
            activity {
                match (opcode) {
                    // Single value
                    [0x00]: { do comp.nop_action; }
                    
                    // Multiple values
                    [0x01, 0x02, 0x03]: { do comp.arithmetic; }
                    
                    // Range
                    [0x10..0x1F]: { do comp.memory_ops; }
                    
                    // Multiple ranges
                    [0x20..0x2F, 0x40..0x4F]: { do comp.control; }
                    
                    // Default case
                    default: { do comp.illegal_opcode; }
                }
            }
        }
    
    Attributes:
        cond: Expression whose value is matched against the choices
        choices: List of match choices with patterns and bodies
    
    See Also:
        ActivityMatchChoice, ActivitySelect, ActivityIfElse
    
    """
    pass
    
    def getCond(self) -> Expr: ...
    
    def choices(self) -> ListUtil...
        """Returns an iterator over the items"""
    
    def getChoices(self) -> List[ActivityMatchChoice]: ...
    
class ActivityRepeatCount(ActivityLabeledStmt):
    """
    Repeats an activity body a fixed number of times.
    
    ActivityRepeatCount executes its body a specified number of iterations,
    with an optional loop variable that tracks the current iteration. Each
    iteration executes sequentially.
    
    PSS Example::
    
        action my_action {
            activity {
                // Basic repeat
                repeat (10) {
                    do comp.sub_action;
                }
                
                // Repeat with loop variable
                repeat (i : 5) {
                    do comp.sub_action with {
                        index == i;
                    }
                }
                
                // Repeat with expression
                repeat (num_iterations) {
                    do comp.action;
                }
            }
        }
    
    Attributes:
        loop_var: Optional loop variable identifier
        count: Expression specifying the number of iterations
        body: Activity statement body to execute each iteration
    
    See Also:
        ActivityRepeatWhile, ActivityForeach, ActivityReplicate
    
    """
    pass
    
    def getLoop_var(self) -> ExprId: ...
    
    def getCount(self) -> Expr: ...
    
    def getBody(self) -> ScopeChild: ...
    
class ActivityRepeatWhile(ActivityLabeledStmt):
    """
    Repeats an activity body while a condition is true.
    
    ActivityRepeatWhile executes its body repeatedly as long as the specified
    condition evaluates to true. The condition is checked before each iteration,
    including the first one.
    
    PSS Example::
    
        action my_action {
            rand bit[8] counter;
            
            activity {
                // Basic while loop
                repeat while (counter < 10) {
                    do comp.increment_action;
                }
                
                // Conditional processing
                repeat while (has_more_data()) {
                    do comp.process_data;
                }
                
                // Complex condition
                repeat while (status == ACTIVE && count > 0) {
                    do comp.work_action;
                }
            }
        }
    
    Attributes:
        cond: Boolean expression evaluated before each iteration
        body: Activity statement body to execute while condition is true
    
    See Also:
        ActivityRepeatCount, ActivityForeach
    
    """
    pass
    
    def getCond(self) -> Expr: ...
    
    def getBody(self) -> ScopeChild: ...
    
class ActivityReplicate(ActivityLabeledStmt):
    """
    Replicates an activity N times with concurrent execution.
    
    ActivityReplicate creates N concurrent instances of the body activity,
    potentially with different constraint values for each instance. Unlike
    repeat, which executes sequentially, replicate creates parallel instances
    that may execute concurrently.
    
    PSS Example::
    
        action my_action {
            activity {
                // Replicate 4 times
                replicate (4) {
                    do comp.worker_action;
                }
                
                // Replicate with index variable
                replicate (i : 8) {
                    do comp.indexed_action with {
                        id == i;
                    }
                }
                
                // Replicate with iterator label
                replicate (i : 3) it_label {
                    do comp.action;
                }
            }
        }
    
    Attributes:
        idx_id: Optional index variable identifier (0 to count-1)
        it_label: Optional label for the iterator instance
        body: Activity statement body replicated N times
    
    See Also:
        ActivityRepeatCount, ActivityParallel
    
    """
    pass
    
    def getIdx_id(self) -> ExprId: ...
    
    def getIt_label(self) -> ExprId: ...
    
    def getBody(self) -> ScopeChild: ...
    
class ActivitySelect(ActivityLabeledStmt):
    """
    Randomly selects and executes one branch from alternatives.
    
    ActivitySelect provides a weighted random choice between multiple branches.
    Each branch can have a guard condition and a weight expression to control
    selection probability. Only one branch is executed per select statement.
    
    PSS Example::
    
        action my_action {
            rand bit[8] mode;
            
            activity {
                // Basic select (equal probability)
                select {
                    1: { do comp.option_a; }
                    1: { do comp.option_b; }
                    1: { do comp.option_c; }
                }
                
                // Weighted select
                select {
                    70: { do comp.common_case; }
                    20: { do comp.rare_case; }
                    10: { do comp.very_rare_case; }
                }
                
                // Select with guards
                select {
                    [mode == 0] 1: { do comp.mode0_action; }
                    [mode == 1] 1: { do comp.mode1_action; }
                    [mode == 2] 1: { do comp.mode2_action; }
                }
            }
        }
    
    Attributes:
        branches: List of select branches with guards, weights, and bodies
    
    See Also:
        ActivitySelectBranch, ActivityMatch, ActivityIfElse
    
    """
    pass
    
    def branches(self) -> ListUtil...
        """Returns an iterator over the items"""
    
    def getBranches(self) -> List[ActivitySelectBranch]: ...
    
class ActivitySuper(ActivityLabeledStmt):
    """
    Invokes the super-class activity implementation.
    
    ActivitySuper allows a derived action to call the activity block defined
    in its parent action class. This enables activity inheritance and extension
    similar to method overriding in object-oriented programming.
    
    PSS Example::
    
        action base_action {
            activity {
                do comp.init;
                do comp.process;
            }
        }
        
        action derived_action : base_action {
            activity {
                do comp.setup;
                super;              // Execute base_action's activity
                do comp.cleanup;
            }
        }
        
        action extended_action : base_action {
            activity {
                super;              // Just execute parent activity
            }
        }
    
    Attributes:
        (inherits from ActivityLabeledStmt)
    
    See Also:
        ActivityDecl, Action
    
    """
    pass
    
class ConstraintBlock(ConstraintScope):
    """
    Named constraint block declaration within a type.
    
    A constraint block is a reusable, named collection of constraints that can be
    declared within a component, action, or struct type. Constraint blocks can be
    dynamically enabled or disabled during randomization, providing flexible control
    over constraint application.
    
    PSS Example::
    
        action my_action {
            rand bit[8] value;
            
            constraint valid_range_c {
                value >= 10;
                value <= 100;
            }
            
            constraint dynamic_limit_c is_dynamic {
                value < 50;
            }
        }
    
    Attributes:
        name: The name of the constraint block
        is_dynamic: Whether the constraint block can be dynamically enabled/disabled
        constraints: List of constraint statements in this block (inherited)
    
    See Also:
        ConstraintScope, ConstraintStmt
    
    """
    pass
    
    def getName(self) -> str: ...
    
    def setName(self, v : str): ...
    
class ProceduralStmtRepeatWhile(ProceduralStmtBody):
    """
    Post-test loop that executes at least once.
    
    ProceduralStmtRepeatWhile represents a repeat-while loop (do-while style)
    that executes the body at least once, then continues while the condition
    is true. The condition is evaluated after each iteration.
    
    PSS Example::
    
        action my_action {
            exec body {
                int x = 0;
                
                // Executes body first, then checks condition
                repeat {
                    x++;
                    console.log("x = ", x);
                } while (x < 5);
                // Executes at least once even if x >= 5 initially
            }
        }
    
    Attributes:
        expr: Condition evaluated after each iteration
        body: Statement(s) to execute (inherited from ProceduralStmtBody)
    
    See Also:
        ProceduralStmtWhile, ProceduralStmtRepeat, ProceduralStmtBody
    
    """
    pass
    
    def getExpr(self) -> Expr: ...
    
class ProceduralStmtWhile(ProceduralStmtBody):
    """
    Pre-test loop with condition evaluated before each iteration.
    
    ProceduralStmtWhile represents a standard while loop that evaluates the
    condition before executing the body. The body may never execute if the
    condition is initially false.
    
    PSS Example::
    
        action my_action {
            exec body {
                int x = 10;
                
                // Standard while loop
                while (x > 0) {
                    console.log("x = ", x);
                    x--;
                }
                
                // Condition checked first - may not execute
                while (false) {
                    console.log("Never executed");
                }
            }
        }
    
    Attributes:
        expr: Condition evaluated before each iteration
        body: Statement(s) to execute (inherited from ProceduralStmtBody)
    
    See Also:
        ProceduralStmtRepeatWhile, ProceduralStmtRepeat, ProceduralStmtForeach
    
    """
    pass
    
    def getExpr(self) -> Expr: ...
    
class ConstraintStmtForall(ConstraintScope):
    """
    Universal quantification constraint over typed instances.
    
    Expresses constraints that must hold for all instances of a specified type that are
    accessible through a reference path. This is similar to foreach but operates on type
    instances rather than array elements, enabling relationship constraints across object
    collections.
    
    PSS Example::
    
        component pss_top {
            pool [4] resource_p;
            
            action use_resources {
                lock resource_p r1, r2;
                
                constraint different_resources_c {
                    forall (resource_p rp : this.comp.resource_p) {
                        (rp != r1) && (rp != r2);
                    }
                }
            }
        }
    
    Attributes:
        iterator_id: Iterator variable name for the type instance
        type_id: The type being iterated over
        ref_path: Path expression to the collection of instances
        symtab: Symbol table for the iterator variable
        constraints: Constraint statements for all instances (inherited)
    
    See Also:
        ConstraintStmtForeach, ConstraintScope, ConstraintStmtField
    
    """
    pass
    
    def getIterator_id(self) -> ExprId: ...
    
    def getType_id(self) -> DataTypeUserDefined: ...
    
    def getRef_path(self) -> ExprRefPath: ...
    
    def getSymtab(self) -> ConstraintSymbolScope: ...
    
class ConstraintStmtForeach(ConstraintScope):
    """
    Iterative constraint over array or collection elements.
    
    Applies constraints to each element of an array or collection. The foreach statement
    introduces iterator variables for the element and optionally its index, making them
    available within the constraint scope for expressing element-wise constraints.
    
    PSS Example::
    
        action packet_sequence {
            rand bit[8] lengths[10];
            
            constraint valid_lengths_c {
                foreach (lengths[i]) {
                    lengths[i] > 0;
                    lengths[i] <= 255;
                }
            }
            
            constraint increasing_c {
                foreach (lengths[i]) {
                    if (i > 0) {
                        lengths[i] >= lengths[i-1];
                    }
                }
            }
        }
    
    Attributes:
        it: Iterator variable for the current element
        idx: Iterator variable for the current index (optional)
        expr: The collection expression being iterated
        symtab: Symbol table for iterator variables
        constraints: Constraint statements applied to each element (inherited)
    
    See Also:
        ConstraintStmtForall, ConstraintScope, ConstraintStmtField
    
    """
    pass
    
    def getIt(self) -> ConstraintStmtField: ...
    
    def getIdx(self) -> ConstraintStmtField: ...
    
    def getExpr(self) -> Expr: ...
    
    def getSymtab(self) -> ConstraintSymbolScope: ...
    
class ConstraintStmtImplication(ConstraintScope):
    """
    Implication constraint using the -> operator.
    
    Expresses an implication relationship where the constraints in the scope are only
    active when the condition evaluates to true. Unlike if-else, implication does not
    constrain the condition itself - if the antecedent is false, the consequent constraints
    are simply ignored. This is useful for soft constraints and conditional relationships.
    
    PSS Example::
    
        action bus_transaction {
            rand bit burst_mode;
            rand bit[4] burst_length;
            rand bit[32] addr;
            
            constraint burst_constraints_c {
                burst_mode -> {
                    burst_length inside [2, 4, 8, 16];
                    (addr & 0xF) == 0;  // 16-byte aligned
                }
            }
            
            constraint normal_mode_c {
                !burst_mode -> {
                    burst_length == 1;
                }
            }
        }
    
    Attributes:
        cond: The antecedent condition expression
        constraints: Consequent constraints active when condition is true (inherited)
    
    See Also:
        ConstraintStmtIf, ConstraintScope, ConstraintStmtExpr
    
    """
    pass
    
    def getCond(self) -> Expr: ...
    
class SymbolScope(SymbolChildrenScope):
    """
    Maps between local item identifier and item child index
    
    """
    pass
    
    def getImports(self) -> SymbolImportSpec: ...
    
class TypeScope(NamedScope):
    """
    Base class for named type declarations (actions, components, structs).
    
    Represents PSS types that can be parameterized with templates,
    extended through inheritance, and used in type references. Provides
    common infrastructure for type system features.
    
    PSS Example::
    
        component my_comp : base_comp {     // TypeScope with super_t
            // ...
        }
        
        action my_action<T> {               // TypeScope with params
            // ...
        }
    
    Attributes:
        name: Type name (inherited from NamedScope)
        super_t: Optional base type for inheritance
        params: Template parameter declarations
        opaque: True if type body is hidden (forward declaration)
    
    See Also:
        Action, Component, Struct, NamedScope
    
    """
    pass
    
    def getSuper_t(self) -> TypeIdentifier: ...
    
    def getParams(self) -> TemplateParamDeclList: ...
    
class ExprRefPathStaticFunc(ExprRefPathStatic):
    """
    Represents a static function call expression.
    
    Extends ExprRefPathStatic to include method parameters for calling static
    functions or compile-time functions. Used for function calls on static
    types or within package scope.
    
    PSS Example::
    
        my_pkg::my_function(arg1, arg2)
        compile.has(some_type)
    
    Attributes:
        params: Method parameter list for the function call
    
    See Also:
        ExprRefPathStatic, MethodParameterList
    
    """
    pass
    
    def getParams(self) -> MethodParameterList: ...
    
class ExprRefPathSuper(ExprRefPathContext):
    """
    Represents a super reference to parent scope.
    
    Specialization of ExprRefPathContext specifically for super references.
    Used to access fields, methods, or constraints defined in a parent
    component or action.
    
    PSS Example::
    
        super.parent_field
        super.parent_method()
    
    See Also:
        ExprRefPathContext, ExprRefPath
    
    """
    pass
    
class Action(TypeScope):
    """
    Action declaration defining reusable behavior blocks.
    
    Actions are the fundamental unit of behavior in PSS. They encapsulate
    data (fields), constraints, and activities (control flow). Actions can
    be composed hierarchically and randomized according to constraints.
    
    PSS Example::
    
        action my_action {
            rand int addr;
            
            constraint {
                addr >= 0x1000;
                addr < 0x2000;
            }
            
            activity {
                do_read(addr);
            }
        }
    
    Attributes:
        is_abstract: True if declared as 'abstract action'
        name: Action name (inherited from NamedScope)
        super_t: Optional base action type (inherited from TypeScope)
        children: Fields, constraints, activities (inherited from Scope)
    
    See Also:
        Component, TypeScope, ActivityStmt
    
    """
    pass
    
class Monitor(TypeScope):
    """
    Declares a PSS 3.0 monitor type for temporal property verification.
    
    Monitor represents a PSS 3.0 monitor type declaration that defines temporal
    properties and sequences to be verified during execution. Monitors contain
    activity blocks that specify sequences of events, temporal operators, and
    coverage collection. Unlike actions, monitors observe behavior without
    affecting execution flow. Note these are PSS 3.0 features.
    
    PSS Example::
    
        monitor protocol_check {
            activity {
                req ##1 ack;              // Request followed by ack
                eventually gnt;           // Grant must occur
            }
        }
        
        monitor bus_monitor {
            activity {
                sequence {
                    addr_phase;
                    data_phase;
                }
            }
        }
        
        abstract monitor base_monitor {
            // Can be extended
        }
    
    Attributes:
        is_abstract: True if this is an abstract monitor declaration
    
    See Also:
        MonitorActivityDecl, MonitorActivityStmt, Action
    
    """
    pass
    
class MonitorActivityDecl(SymbolScope):
    """
    Declares an activity block within a monitor.
    
    MonitorActivityDecl represents the declaration of an activity block that
    defines the temporal behavior to be monitored. It serves as a symbol scope
    containing monitor activity statements that specify temporal sequences,
    properties, and coverage. Unlike action activities, monitor activities
    observe execution patterns. Note these are PSS 3.0 features.
    
    PSS Example::
    
        monitor handshake_check {
            activity {
                // Temporal sequence monitoring
                req ##1 ack;
                eventually done;
                
                // Coverage collection
                cover { req ##1 ack; }
            }
        }
        
        monitor bus_protocol {
            activity {
                sequence {
                    addr_valid;
                    ##[1:3] data_valid;
                }
            }
        }
    
    Attributes:
        (inherits symbol scope capabilities)
    
    See Also:
        MonitorActivityStmt, Monitor, ActivityDecl
    
    """
    pass
    
class ActivityDecl(SymbolScope):
    """
    Declares an activity block within an action.
    
    ActivityDecl represents the declaration of an activity block that defines
    the behavioral execution flow of an action. It serves as a symbol scope
    containing activity statements that specify sequences, parallelism, 
    scheduling, and control flow.
    
    PSS Example::
    
        action my_action {
            activity {
                do comp1.child_action;
                do comp2.child_action;
            }
        }
    
    Attributes:
        (inherits symbol scope capabilities)
    
    See Also:
        ActivityStmt, Action, SymbolScope
    
    """
    pass
    
class ActivityLabeledScope(SymbolScope):
    """
    Base class for labeled activity scopes.
    
    ActivityLabeledScope represents activity constructs that introduce a new
    scope and can be labeled. This includes sequences, parallel blocks, and
    schedule blocks. The label can be used for referencing in scheduling
    constraints.
    
    PSS Example::
    
        action my_action {
            activity {
                my_seq: sequence {
                    do comp.action1;
                    do comp.action2;
                }
                
                my_par: parallel {
                    do comp.action3;
                    do comp.action4;
                }
            }
        }
    
    Attributes:
        label: Optional identifier expression for the label
    
    See Also:
        ActivitySequence, ActivityParallel, ActivitySchedule
    
    """
    pass
    
    def getLabel(self) -> ExprId: ...
    
class MonitorActivitySchedule(SymbolScope):
    """
    Defines a scheduled monitoring block with flexible ordering.
    
    MonitorActivitySchedule represents a schedule block within monitor activities
    that allows monitor activities to be observed in a flexible order, subject
    to explicit ordering constraints. Unlike sequences which enforce strict
    ordering, schedules permit concurrent or reordered observation unless
    constrained otherwise. Note these are PSS 3.0 features.
    
    PSS Example::
    
        monitor flexible_protocol {
            activity {
                schedule {
                    phase_a;
                    phase_b;
                    phase_c;
                    
                    // Ordering constraints
                    phase_a before phase_c;
                }
                
                // Labeled schedule
                main_check: schedule {
                    monitor_addr;
                    monitor_data;
                    monitor_response;
                    
                    // Can occur in any order
                }
            }
        }
    
    Attributes:
        label: Optional identifier expression for the schedule label
    
    See Also:
        MonitorActivitySequence, ActivitySchedule, MonitorActivityStmt
    
    """
    pass
    
    def getLabel(self) -> ExprId: ...
    
class MonitorActivitySequence(SymbolScope):
    """
    Defines a sequential monitoring block.
    
    MonitorActivitySequence specifies that its contained monitor activities
    execute in strict sequential order. Each monitored event or property must
    be observed before the next is checked. This is used to group temporal
    patterns that must occur in sequence. Note these are PSS 3.0 features.
    
    PSS Example::
    
        monitor transaction_check {
            activity {
                // Explicit sequence
                sequence {
                    start_phase;
                    data_phase;
                    end_phase;
                }
                
                // Labeled sequence for reference
                setup: sequence {
                    config_valid;
                    ##1 config_ack;
                }
                
                // Nested sequences
                sequence {
                    init;
                    sequence {
                        req ##1 ack;
                        eventually done;
                    }
                }
            }
        }
    
    Attributes:
        label: Optional identifier expression for the sequence label
    
    See Also:
        MonitorActivityStmt, MonitorActivitySchedule, ActivitySequence
    
    """
    pass
    
    def getLabel(self) -> ExprId: ...
    
class AnnotationDecl(TypeScope):
    """
    Annotation type declaration.
    
    Represents a PSS 3.1 ``annotation`` declaration, including optional
    template parameters, inheritance, and body fields.
    
    See Also:
        Annotation, ExtendType
    
    """
    pass
    
class Component(TypeScope):
    """
    Component declaration defining test environment structure.
    
    Components represent the static structure of the test environment.
    They contain actions, pools of resources, constraints, and other
    components. Components form the containment hierarchy for actions.
    
    PSS Example::
    
        component pss_top {
            action my_action { }
            pool [16] my_action actions;
            
            bind actions *;
        }
    
    Attributes:
        name: Component name (inherited from NamedScope)
        super_t: Optional base component type (inherited from TypeScope)
        children: Actions, resources, pools, etc (inherited from Scope)
    
    See Also:
        Action, TypeScope, Field
    
    """
    pass
    
class ProceduralStmtSymbolBodyScope(SymbolScope):
    """
    Symbol scope with statement body for loop constructs.
    
    ProceduralStmtSymbolBodyScope combines symbol scope capabilities with
    a statement body, providing a base class for loop constructs that need
    to declare iterator variables (repeat, foreach). The symbol scope holds
    the iterator variable declarations.
    
    PSS Example::
    
        action my_action {
            exec body {
                // 'i' is declared in the symbol scope
                repeat (i : 10) {
                    console.log("i = ", i);
                    // 'i' is accessible here
                }
                // 'i' is not accessible here
                
                // Similar for foreach
                int arr[5];
                foreach (elem [idx] : arr) {
                    // 'elem' and 'idx' in symbol scope
                }
            }
        }
    
    Attributes:
        body: Statement(s) contained in this scope
    
    See Also:
        ProceduralStmtRepeat, ProceduralStmtForeach, SymbolScope
    
    """
    pass
    
    def getBody(self) -> ScopeChild: ...
    
class ConstraintSymbolScope(SymbolScope):
    """
    Symbol table scope for constraint expressions.
    
    Provides a symbol resolution context for identifiers used within constraint statements.
    This scope manages the visibility of iterator variables (from foreach/forall) and field
    references within the constraint context.
    
    PSS Example::
    
        constraint loop_constraint {
            foreach (items[i]) {
                // 'i' and 'items[i]' are resolved through ConstraintSymbolScope
                items[i] > 0;
            }
        }
    
    Attributes:
        constraint: The constraint statement this scope is associated with
    
    See Also:
        SymbolScope, ConstraintStmtForeach, ConstraintStmtForall
    
    """
    pass
    
    def getConstraint(self) -> ConstraintStmt: ...
    
class RootSymbolScope(SymbolScope):
    """
    List of inbound refs to each unit
    
    """
    pass
    
    def units(self) -> ListUtil...
        """Returns an iterator over the items"""
    
    def getUnits(self) -> List[GlobalScope]: ...
    
    def fileOutRef(self) -> ListUtil...
        """Returns an iterator over the items"""
    
    def getFileOutRef(self) -> List[List[int]]: ...
    
    def fileInRef(self) -> ListUtil...
        """Returns an iterator over the items"""
    
    def getFileInRef(self) -> List[List[int]]: ...
    
class Struct(TypeScope):
    """
    Structured data type declaration (struct/buffer/stream/state/resource).
    
    Represents various structured data containers in PSS. The 'kind' field
    determines the specific semantics: plain data struct, memory buffer,
    data stream, state object, or shared resource.
    
    PSS Example::
    
        struct packet_s {
            int<8> header;
            int<32> payload;
        }
        
        buffer dma_buf_t {
            int<8> data[1024];
        }
        
        resource bus_t {
            int bandwidth;
        }
        
        stream data_stream_t {
            int<16> samples;
        }
        
        state session_state_t {
            bool connected;
        }
    
    Attributes:
        name: Type name (inherited from NamedScope via TypeScope)
        kind: Structure kind (StructKind enum)
        super_t: Optional base type (inherited from TypeScope)
        children: Field declarations (inherited from Scope)
    
    See Also:
        StructKind, TypeScope, Field
    
    """
    pass
    
    def setKind(self, v : StructKind): ...
    
class SymbolEnumScope(SymbolScope):
    """
    Symbol scope for enumeration type declarations.
    
    Represents an enum definition in the linked symbol tree, managing the
    namespace for enum items and their associated values. Provides symbol
    resolution for enum member access during type checking.
    
    The scope contains the enum's items as children, enabling qualified
    name lookup (e.g., MyEnum::ItemName) during compilation.
    
    See Also:
        SymbolScope, EnumDecl, EnumItem
    
    """
    pass
    
class SymbolExtendScope(SymbolScope):
    """
    Symbol scope for PSS extend statements.
    
    Represents an extend declaration in the linked symbol tree, which adds
    new members to an existing type. Manages the namespace for extension
    members and links them back to the base type being extended.
    
    During linking, multiple extend declarations targeting the same type
    are merged into the type's symbol scope, allowing type augmentation
    across compilation units.
    
    Attributes:
        (inherits from SymbolScope - children contain extension members)
    
    See Also:
        SymbolScope, ExtendType, ExtendEnum
    
    """
    pass
    
class SymbolFunctionScope(SymbolScope):
    """
    Symbol scope for functions with overload resolution support.
    
    Represents a function in the linked symbol tree, managing multiple
    declarations (prototypes, imports, definition) for the same function name.
    Supports function overloading by tracking all signatures and selecting
    the appropriate one during call resolution.
    
    During linking, function prototypes from different files are collected,
    import specifications are resolved, and the definition (if present) is
    linked. The plist handles template parameters for generic functions.
    
    Attributes:
        prototypes: All declared function signatures (forward declarations)
        import_specs: Imported function specifications (DPI/foreign functions)
        definition: The function implementation (null if only prototype/import)
        plist: Template parameter list scope (if this is a generic function)
        body: Function body scope containing local variables and statements
    
    See Also:
        SymbolScope, FunctionPrototype, FunctionDefinition, FunctionImport
    
    """
    pass
    
    def prototypes(self) -> ListUtil...
        """Returns an iterator over the items"""
    
    def getPrototypes(self) -> List[FunctionPrototype]: ...
    
    def import_specs(self) -> ListUtil...
        """Returns an iterator over the items"""
    
    def getImport_specs(self) -> List[FunctionImport]: ...
    
    def getDefinition(self) -> FunctionDefinition: ...
    
    def getPlist(self) -> SymbolScope: ...
    
    def getBody(self) -> ExecScope: ...
    
class SymbolTypeScope(SymbolScope):
    """
    Symbol scope for type declarations (actions, components, structs).
    
    Represents a user-defined type in the linked symbol tree, managing its
    members, methods, and constraints. Supports template specialization by
    tracking parameter lists and specialized type instantiations.
    
    During linking, type declarations from multiple files can be merged
    (for extend statements) and specialized instances are tracked separately.
    The plist holds template parameters, while spec_types contains any
    specialized/instantiated versions of this generic type.
    
    Attributes:
        plist: Template parameter list scope (if this is a generic type)
        spec_types: List of specialized/instantiated versions of this type
    
    See Also:
        SymbolScope, Action, Component, Struct, SymbolExtendScope
    
    """
    pass
    
    def getPlist(self) -> SymbolScope: ...
    
    def spec_types(self) -> ListUtil...
        """Returns an iterator over the items"""
    
    def getSpec_types(self) -> List[SymbolTypeScope]: ...
    
class ExecScope(SymbolScope):
    """
    Scope containing procedural statements with symbol table capabilities.
    
    ExecScope represents a scope that can contain procedural statements and
    maintains a symbol table for local variables. It provides the scoping
    infrastructure for exec blocks and statement bodies.
    
    PSS Example::
    
        action my_action {
            exec body {
                // This exec body is an ExecScope
                int local_var = 5;  // Symbol in this scope
                {
                    // Nested scope (also ExecScope)
                    int nested_var = 10;
                }
            }
        }
    
    Attributes:
        endLocation: Source location of the closing brace
    
    See Also:
        ExecBlock, SymbolScope, ProceduralStmtBody
    
    """
    pass
    
    def getEndLocation(self) -> 'Location': ...
    
class GenericConstraintDeclBool(ConstraintBlock):
    """
    Boolean generic constraint declaration.
    
    Represents a declaration of the form
    ``[static] constraint name(params) constraint_set``.
    
    """
    pass
    
    def parameters(self) -> ListUtil...
        """Returns an iterator over the items"""
    
    def getParameters(self) -> List[GenericConstraintParam]: ...
    
class ProceduralStmtForeach(ProceduralStmtSymbolBodyScope):
    """
    Iteration over elements of a collection.
    
    ProceduralStmtForeach represents a foreach loop that iterates over elements
    of an array, list, or other collection. Provides both the element iterator
    and an optional index iterator for tracking position.
    
    PSS Example::
    
        action my_action {
            int values[10];
            
            exec body {
                // Iterate over array elements
                foreach (v : values) {
                    console.log("Value: ", v);
                }
                
                // Iterate with index
                foreach (v [i] : values) {
                    console.log("values[", i, "] = ", v);
                }
            }
        }
    
    Attributes:
        path: Reference path to the collection to iterate
        it_id: Iterator variable for current element
        idx_id: Optional index variable for current position
        body: Statement(s) to execute each iteration (inherited)
    
    See Also:
        ProceduralStmtRepeat, ProceduralStmtWhile, ExprRefPath
    
    """
    pass
    
    def getPath(self) -> ExprRefPath: ...
    
    def getIt_id(self) -> ExprId: ...
    
    def getIdx_id(self) -> ExprId: ...
    
class ExecBlock(ExecScope):
    """
    Complete exec block with specific execution phase.
    
    ExecBlock represents a complete exec block declaration within an action or
    component. The kind field specifies when this code executes (body, pre_solve,
    post_solve, etc.). Each exec block is a symbol scope containing procedural
    statements.
    
    PSS Example::
    
        action my_action {
            rand int x;
            
            exec pre_solve {
                // Executes before randomization
                console.log("About to solve");
            }
            
            exec body {
                // Main execution body
                console.log("x = ", x);
            }
            
            exec post_solve {
                // Executes after randomization
                console.log("Solved x = ", x);
            }
        }
    
    Attributes:
        kind: Type of exec block (Body, PreSolve, PostSolve, etc.)
    
    See Also:
        ExecKind, ExecScope, Action
    
    """
    pass
    
    def setKind(self, v : ExecKind): ...
    
class ProceduralStmtRepeat(ProceduralStmtSymbolBodyScope):
    """
    Fixed-count repeat loop with optional iterator variable.
    
    ProceduralStmtRepeat represents a loop that executes a fixed number of
    times, specified by the count expression. An optional iterator variable
    tracks the current iteration index (0-based).
    
    PSS Example::
    
        action my_action {
            exec body {
                // Repeat 10 times without iterator
                repeat (10) {
                    console.log("Iteration");
                }
                
                // Repeat with iterator variable
                repeat (i : 5) {
                    console.log("Iteration ", i);  // i = 0, 1, 2, 3, 4
                }
            }
        }
    
    Attributes:
        it_id: Optional iterator variable identifier
        count: Expression specifying number of iterations
        body: Statement(s) to execute each iteration (inherited)
    
    See Also:
        ProceduralStmtRepeatWhile, ProceduralStmtWhile, ProceduralStmtForeach
    
    """
    pass
    
    def getIt_id(self) -> ExprId: ...
    
    def getCount(self) -> Expr: ...
    
class ActivityParallel(ActivityLabeledScope):
    """
    Defines a parallel execution block with join semantics.
    
    ActivityParallel specifies that its contained activities may execute
    concurrently. The join specification determines when the parallel block
    completes relative to its branches. By default, all branches must complete.
    
    PSS Example::
    
        action my_action {
            activity {
                // Default parallel (wait for all)
                parallel {
                    do comp.action1;
                    do comp.action2;
                    do comp.action3;
                }
                
                // Parallel with join_first
                parallel join_first(2) {
                    do comp.fast_action;
                    do comp.medium_action;
                    do comp.slow_action;
                }
                
                // Parallel with join_none (fire and forget)
                parallel join_none {
                    do comp.background1;
                    do comp.background2;
                }
            }
        }
    
    Attributes:
        join_spec: Specification of join behavior for the parallel block
    
    See Also:
        ActivitySequence, ActivitySchedule, ActivityJoinSpec
    
    """
    pass
    
    def getJoin_spec(self) -> ActivityJoinSpec: ...
    
class ActivitySchedule(ActivityLabeledScope):
    """
    Defines a scheduled execution block with explicit ordering constraints.
    
    ActivitySchedule allows activities to execute with explicit scheduling
    constraints that define relative ordering. Unlike parallel blocks where
    all actions start together, schedule blocks allow fine-grained control
    over when each activity begins and ends relative to others.
    
    PSS Example::
    
        action my_action {
            activity {
                schedule {
                    a: do comp.action_a;
                    b: do comp.action_b;
                    c: do comp.action_c;
                    d: do comp.action_d;
                    
                    // Scheduling constraints
                    a before b;           // Sequential
                    a before c;           // Sequential
                    parallel(b, c);       // Parallel
                    b before d;
                    c before d;
                }
            }
        }
    
    Attributes:
        join_spec: Specification of join behavior for the schedule block
    
    See Also:
        ActivitySchedulingConstraint, ActivityParallel, ActivitySequence
    
    """
    pass
    
    def getJoin_spec(self) -> ActivityJoinSpec: ...
    
class ActivitySequence(ActivityLabeledScope):
    """
    Defines a sequential execution block.
    
    ActivitySequence specifies that its contained activities execute in strict
    sequential order, one after another. Each activity completes before the next
    begins. This is the default execution model and can be explicitly specified
    with the 'sequence' keyword.
    
    PSS Example::
    
        action my_action {
            activity {
                // Explicit sequence
                sequence {
                    do comp.init_action;
                    do comp.process_action;
                    do comp.cleanup_action;
                }
                
                // Labeled sequence
                setup_phase: sequence {
                    do comp.config;
                    do comp.verify;
                }
                
                // Nested sequences
                sequence {
                    sequence {
                        do comp.step1;
                        do comp.step2;
                    }
                    do comp.step3;
                }
            }
        }
    
    Attributes:
        (inherits from ActivityLabeledScope)
    
    See Also:
        ActivityParallel, ActivitySchedule, ActivityLabeledScope
    
    """
    pass
    
