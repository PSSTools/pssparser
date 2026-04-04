# cython: language_level=3
import ctypes
import os
import sys
from typing import List, Iterable
from libc.stdint cimport intptr_t
from cython.operator cimport dereference
from pssparser cimport ast_decl
from enum import IntEnum

if sys.platform == 'darwin':
    _libname = "libast.dylib"
elif sys.platform == 'win32':
    _libname = "ast.dll"
else:
    _libname = "libast.so"


class ListIterator(object):
    def __init__(self, n_children, get_child):
        self.n_children = n_children
        self.get_child = get_child
        self.index = 0
    
    def __next__(self):
        if (self.index >= self.n_children):
            raise StopIteration()
        else:
            ret = self.get_child(self.index)
            self.index += 1
            return ret
        

class ListUtil(object):
    def __init__(self, n_children, get_child):
        self.n_children = n_children
        self.get_child = get_child
    
    def __iter__(self):
        return ListIterator(self.n_children(), self.get_child)

class AssignOp(IntEnum):
    AssignOp_Eq = ast_decl.AssignOp.AssignOp_AssignOp_Eq
    AssignOp_PlusEq = ast_decl.AssignOp.AssignOp_AssignOp_PlusEq
    AssignOp_MinusEq = ast_decl.AssignOp.AssignOp_AssignOp_MinusEq
    AssignOp_ShlEq = ast_decl.AssignOp.AssignOp_AssignOp_ShlEq
    AssignOp_ShrEq = ast_decl.AssignOp.AssignOp_AssignOp_ShrEq
    AssignOp_OrEq = ast_decl.AssignOp.AssignOp_AssignOp_OrEq
    AssignOp_AndEq = ast_decl.AssignOp.AssignOp_AssignOp_AndEq
class ExecKind(IntEnum):
    ExecKind_Body = ast_decl.ExecKind.ExecKind_ExecKind_Body
    ExecKind_Header = ast_decl.ExecKind.ExecKind_ExecKind_Header
    ExecKind_Declaration = ast_decl.ExecKind.ExecKind_ExecKind_Declaration
    ExecKind_RunStart = ast_decl.ExecKind.ExecKind_ExecKind_RunStart
    ExecKind_RunEnd = ast_decl.ExecKind.ExecKind_ExecKind_RunEnd
    ExecKind_InitDown = ast_decl.ExecKind.ExecKind_ExecKind_InitDown
    ExecKind_InitUp = ast_decl.ExecKind.ExecKind_ExecKind_InitUp
    ExecKind_PreSolve = ast_decl.ExecKind.ExecKind_ExecKind_PreSolve
    ExecKind_PostSolve = ast_decl.ExecKind.ExecKind_ExecKind_PostSolve
class ExprBinOp(IntEnum):
    BinOp_LogOr = ast_decl.ExprBinOp.ExprBinOp_BinOp_LogOr
    BinOp_LogAnd = ast_decl.ExprBinOp.ExprBinOp_BinOp_LogAnd
    BinOp_BitOr = ast_decl.ExprBinOp.ExprBinOp_BinOp_BitOr
    BinOp_BitXor = ast_decl.ExprBinOp.ExprBinOp_BinOp_BitXor
    BinOp_BitAnd = ast_decl.ExprBinOp.ExprBinOp_BinOp_BitAnd
    BinOp_Lt = ast_decl.ExprBinOp.ExprBinOp_BinOp_Lt
    BinOp_Le = ast_decl.ExprBinOp.ExprBinOp_BinOp_Le
    BinOp_Gt = ast_decl.ExprBinOp.ExprBinOp_BinOp_Gt
    BinOp_Ge = ast_decl.ExprBinOp.ExprBinOp_BinOp_Ge
    BinOp_Exp = ast_decl.ExprBinOp.ExprBinOp_BinOp_Exp
    BinOp_Mul = ast_decl.ExprBinOp.ExprBinOp_BinOp_Mul
    BinOp_Div = ast_decl.ExprBinOp.ExprBinOp_BinOp_Div
    BinOp_Mod = ast_decl.ExprBinOp.ExprBinOp_BinOp_Mod
    BinOp_Add = ast_decl.ExprBinOp.ExprBinOp_BinOp_Add
    BinOp_Sub = ast_decl.ExprBinOp.ExprBinOp_BinOp_Sub
    BinOp_Shl = ast_decl.ExprBinOp.ExprBinOp_BinOp_Shl
    BinOp_Shr = ast_decl.ExprBinOp.ExprBinOp_BinOp_Shr
    BinOp_Eq = ast_decl.ExprBinOp.ExprBinOp_BinOp_Eq
    BinOp_Ne = ast_decl.ExprBinOp.ExprBinOp_BinOp_Ne
class ExprUnaryOp(IntEnum):
    UnaryOp_Plus = ast_decl.ExprUnaryOp.ExprUnaryOp_UnaryOp_Plus
    UnaryOp_Minus = ast_decl.ExprUnaryOp.ExprUnaryOp_UnaryOp_Minus
    UnaryOp_LogNot = ast_decl.ExprUnaryOp.ExprUnaryOp_UnaryOp_LogNot
    UnaryOp_BitNeg = ast_decl.ExprUnaryOp.ExprUnaryOp_UnaryOp_BitNeg
    UnaryOp_BitAnd = ast_decl.ExprUnaryOp.ExprUnaryOp_UnaryOp_BitAnd
    UnaryOp_BitOr = ast_decl.ExprUnaryOp.ExprUnaryOp_UnaryOp_BitOr
    UnaryOp_BitXor = ast_decl.ExprUnaryOp.ExprUnaryOp_UnaryOp_BitXor
class ExtendTargetE(IntEnum):
    Action = ast_decl.ExtendTargetE.ExtendTargetE_Action
    Annotation = ast_decl.ExtendTargetE.ExtendTargetE_Annotation
    Buffer = ast_decl.ExtendTargetE.ExtendTargetE_Buffer
    Component = ast_decl.ExtendTargetE.ExtendTargetE_Component
    Enum = ast_decl.ExtendTargetE.ExtendTargetE_Enum
    Resource = ast_decl.ExtendTargetE.ExtendTargetE_Resource
    State = ast_decl.ExtendTargetE.ExtendTargetE_State
    Stream = ast_decl.ExtendTargetE.ExtendTargetE_Stream
    Struct = ast_decl.ExtendTargetE.ExtendTargetE_Struct
class FunctionParamDeclKind(IntEnum):
    ParamKind_DataType = ast_decl.FunctionParamDeclKind.FunctionParamDeclKind_ParamKind_DataType
    ParamKind_Type = ast_decl.FunctionParamDeclKind.FunctionParamDeclKind_ParamKind_Type
    ParamKind_RefAction = ast_decl.FunctionParamDeclKind.FunctionParamDeclKind_ParamKind_RefAction
    ParamKind_RefComponent = ast_decl.FunctionParamDeclKind.FunctionParamDeclKind_ParamKind_RefComponent
    ParamKind_RefBuffer = ast_decl.FunctionParamDeclKind.FunctionParamDeclKind_ParamKind_RefBuffer
    ParamKind_RefResource = ast_decl.FunctionParamDeclKind.FunctionParamDeclKind_ParamKind_RefResource
    ParamKind_RefState = ast_decl.FunctionParamDeclKind.FunctionParamDeclKind_ParamKind_RefState
    ParamKind_RefStream = ast_decl.FunctionParamDeclKind.FunctionParamDeclKind_ParamKind_RefStream
    ParamKind_RefStruct = ast_decl.FunctionParamDeclKind.FunctionParamDeclKind_ParamKind_RefStruct
    ParamKind_Struct = ast_decl.FunctionParamDeclKind.FunctionParamDeclKind_ParamKind_Struct
class ParamDir(IntEnum):
    ParamDir_Default = ast_decl.ParamDir.ParamDir_ParamDir_Default
    ParamDir_In = ast_decl.ParamDir.ParamDir_ParamDir_In
    ParamDir_Out = ast_decl.ParamDir.ParamDir_ParamDir_Out
    ParamDir_InOut = ast_decl.ParamDir.ParamDir_ParamDir_InOut
class PlatQual(IntEnum):
    PlatQual_None = ast_decl.PlatQual.PlatQual_PlatQual_None
    PlatQual_Target = ast_decl.PlatQual.PlatQual_PlatQual_Target
    PlatQual_Solve = ast_decl.PlatQual.PlatQual_PlatQual_Solve
class StringMethodId(IntEnum):
    StringMethod_None = ast_decl.StringMethodId.StringMethodId_StringMethod_None
    StringMethod_Size = ast_decl.StringMethodId.StringMethodId_StringMethod_Size
    StringMethod_Find = ast_decl.StringMethodId.StringMethodId_StringMethod_Find
    StringMethod_FindLast = ast_decl.StringMethodId.StringMethodId_StringMethod_FindLast
    StringMethod_FindAll = ast_decl.StringMethodId.StringMethodId_StringMethod_FindAll
    StringMethod_Lower = ast_decl.StringMethodId.StringMethodId_StringMethod_Lower
    StringMethod_Upper = ast_decl.StringMethodId.StringMethodId_StringMethod_Upper
    StringMethod_Split = ast_decl.StringMethodId.StringMethodId_StringMethod_Split
    StringMethod_Chars = ast_decl.StringMethodId.StringMethodId_StringMethod_Chars
class StructKind(IntEnum):
    Buffer = ast_decl.StructKind.StructKind_Buffer
    Struct = ast_decl.StructKind.StructKind_Struct
    Resource = ast_decl.StructKind.StructKind_Resource
    Stream = ast_decl.StructKind.StructKind_Stream
    State = ast_decl.StructKind.StructKind_State
class SymbolRefPathElemKind(IntEnum):
    ElemKind_ChildIdx = ast_decl.SymbolRefPathElemKind.SymbolRefPathElemKind_ElemKind_ChildIdx
    ElemKind_ArgIdx = ast_decl.SymbolRefPathElemKind.SymbolRefPathElemKind_ElemKind_ArgIdx
    ElemKind_Inline = ast_decl.SymbolRefPathElemKind.SymbolRefPathElemKind_ElemKind_Inline
    ElemKind_ParamIdx = ast_decl.SymbolRefPathElemKind.SymbolRefPathElemKind_ElemKind_ParamIdx
    ElemKind_Super = ast_decl.SymbolRefPathElemKind.SymbolRefPathElemKind_ElemKind_Super
    ElemKind_TypeSpec = ast_decl.SymbolRefPathElemKind.SymbolRefPathElemKind_ElemKind_TypeSpec
class TypeCategory(IntEnum):
    Action = ast_decl.TypeCategory.TypeCategory_Action
    Component = ast_decl.TypeCategory.TypeCategory_Component
    Buffer = ast_decl.TypeCategory.TypeCategory_Buffer
    Resource = ast_decl.TypeCategory.TypeCategory_Resource
    State = ast_decl.TypeCategory.TypeCategory_State
    Stream = ast_decl.TypeCategory.TypeCategory_Stream
    Struct = ast_decl.TypeCategory.TypeCategory_Struct
cdef class Location:
    @property
    def fileid(self):
        return self._val.fileid
    @property
    def lineno(self):
        return self._val.lineno
    @property
    def linepos(self):
        return self._val.linepos
    @property
    def extent(self):
        return self._val.extent
    @staticmethod
    cdef Location wrap(const ast_decl.Location &v):
        ret = Location()
        ret._val = v
        return ret

cdef class SymbolRefPathElem:
    @property
    def kind(self):
        return self._val.kind
    @property
    def idx(self):
        return self._val.idx
    @staticmethod
    cdef SymbolRefPathElem wrap(const ast_decl.SymbolRefPathElem &v):
        ret = SymbolRefPathElem()
        ret._val = v
        return ret

class FieldAttr(IntEnum):
    Action = ast_decl.FieldAttr.FieldAttr_Action
    Builtin = ast_decl.FieldAttr.FieldAttr_Builtin
    Rand = ast_decl.FieldAttr.FieldAttr_Rand
    Const = ast_decl.FieldAttr.FieldAttr_Const
    Static = ast_decl.FieldAttr.FieldAttr_Static
    Instance = ast_decl.FieldAttr.FieldAttr_Instance
    Private = ast_decl.FieldAttr.FieldAttr_Private
    Protected = ast_decl.FieldAttr.FieldAttr_Protected
cdef Factory _inst = None
cdef class Factory(object):
    cpdef TemplateParamDeclList mkTemplateParamDeclList(self):
        return TemplateParamDeclList.mk(self._hndl.mkTemplateParamDeclList(
), True)
    cpdef AssocData mkAssocData(self):
        return AssocData.mk(self._hndl.mkAssocData(
), True)
    cpdef ExecTargetTemplateParam mkExecTargetTemplateParam(self,
            Expr expr,
            int32_t start,
            int32_t end):
        return ExecTargetTemplateParam.mk(self._hndl.mkExecTargetTemplateParam(
                expr.asExpr(),
                start,
                end), True)
    cpdef Expr mkExpr(self):
        return Expr.mk(self._hndl.mkExpr(
), True)
    cpdef TemplateParamValue mkTemplateParamValue(self):
        return TemplateParamValue.mk(self._hndl.mkTemplateParamValue(
), True)
    cpdef MonitorActivityMatchChoice mkMonitorActivityMatchChoice(self,
            bool is_default,
            ExprOpenRangeList cond,
            ScopeChild body):
        return MonitorActivityMatchChoice.mk(self._hndl.mkMonitorActivityMatchChoice(
                is_default,
                cond.asExprOpenRangeList(),
                body.asScopeChild()), True)
    cpdef TemplateParamValueList mkTemplateParamValueList(self):
        return TemplateParamValueList.mk(self._hndl.mkTemplateParamValueList(
), True)
    cpdef ExprAggrMapElem mkExprAggrMapElem(self,
            Expr lhs,
            Expr rhs):
        return ExprAggrMapElem.mk(self._hndl.mkExprAggrMapElem(
                lhs.asExpr(),
                rhs.asExpr()), True)
    cpdef RefExpr mkRefExpr(self):
        return RefExpr.mk(self._hndl.mkRefExpr(
), True)
    cpdef ExprAggrStructElem mkExprAggrStructElem(self,
            ExprId name,
            Expr value):
        return ExprAggrStructElem.mk(self._hndl.mkExprAggrStructElem(
                name.asExprId(),
                value.asExpr()), True)
    cpdef MonitorActivitySelectBranch mkMonitorActivitySelectBranch(self,
            Expr guard,
            ScopeChild body):
        return MonitorActivitySelectBranch.mk(self._hndl.mkMonitorActivitySelectBranch(
                guard.asExpr(),
                body.asScopeChild()), True)
    cpdef ScopeChild mkScopeChild(self):
        return ScopeChild.mk(self._hndl.mkScopeChild(
), True)
    cpdef ActivityMatchChoice mkActivityMatchChoice(self,
            bool is_default,
            ExprOpenRangeList cond,
            ScopeChild body):
        return ActivityMatchChoice.mk(self._hndl.mkActivityMatchChoice(
                is_default,
                cond.asExprOpenRangeList(),
                body.asScopeChild()), True)
    cpdef SymbolImportSpec mkSymbolImportSpec(self):
        return SymbolImportSpec.mk(self._hndl.mkSymbolImportSpec(
), True)
    cpdef SymbolRefPath mkSymbolRefPath(self):
        return SymbolRefPath.mk(self._hndl.mkSymbolRefPath(
), True)
    cpdef ActivitySelectBranch mkActivitySelectBranch(self,
            Expr guard,
            Expr weight,
            ScopeChild body):
        return ActivitySelectBranch.mk(self._hndl.mkActivitySelectBranch(
                guard.asExpr(),
                weight.asExpr(),
                body.asScopeChild()), True)
    cpdef ActionFieldInitializer mkActionFieldInitializer(self,
            ExprHierarchicalId path,
            Expr value):
        return ActionFieldInitializer.mk(self._hndl.mkActionFieldInitializer(
                path.asExprHierarchicalId(),
                value.asExpr()), True)
    cpdef ActivityJoinSpec mkActivityJoinSpec(self):
        return ActivityJoinSpec.mk(self._hndl.mkActivityJoinSpec(
), True)
    cpdef MonitorActivityStmt mkMonitorActivityStmt(self):
        return MonitorActivityStmt.mk(self._hndl.mkMonitorActivityStmt(
), True)
    cpdef NamedScopeChild mkNamedScopeChild(self,
            ExprId name):
        return NamedScopeChild.mk(self._hndl.mkNamedScopeChild(
                name.asExprId()), True)
    cpdef PackageImportStmt mkPackageImportStmt(self,
            bool wildcard,
            ExprId alias):
        return PackageImportStmt.mk(self._hndl.mkPackageImportStmt(
                wildcard,
                alias.asExprId()), True)
    cpdef ActivitySchedulingConstraint mkActivitySchedulingConstraint(self,
            bool is_parallel):
        return ActivitySchedulingConstraint.mk(self._hndl.mkActivitySchedulingConstraint(
                is_parallel), True)
    cpdef ActivityStmt mkActivityStmt(self):
        return ActivityStmt.mk(self._hndl.mkActivityStmt(
), True)
    cpdef ProceduralStmtIfClause mkProceduralStmtIfClause(self,
            Expr cond,
            ScopeChild body):
        return ProceduralStmtIfClause.mk(self._hndl.mkProceduralStmtIfClause(
                cond.asExpr(),
                body.asScopeChild()), True)
    cpdef Annotation mkAnnotation(self,
            TypeIdentifier type):
        return Annotation.mk(self._hndl.mkAnnotation(
                type.asTypeIdentifier()), True)
    cpdef AnnotationParam mkAnnotationParam(self,
            Expr value):
        return AnnotationParam.mk(self._hndl.mkAnnotationParam(
                value.asExpr()), True)
    cpdef ConstraintStmt mkConstraintStmt(self):
        return ConstraintStmt.mk(self._hndl.mkConstraintStmt(
), True)
    cpdef PyImportFromStmt mkPyImportFromStmt(self):
        return PyImportFromStmt.mk(self._hndl.mkPyImportFromStmt(
), True)
    cpdef PyImportStmt mkPyImportStmt(self):
        return PyImportStmt.mk(self._hndl.mkPyImportStmt(
), True)
    cpdef RefExprScopeIndex mkRefExprScopeIndex(self,
            RefExpr base,
            int32_t offset):
        return RefExprScopeIndex.mk(self._hndl.mkRefExprScopeIndex(
                base.asRefExpr(),
                offset), True)
    cpdef RefExprTypeScopeContext mkRefExprTypeScopeContext(self,
            RefExpr base,
            int32_t offset):
        return RefExprTypeScopeContext.mk(self._hndl.mkRefExprTypeScopeContext(
                base.asRefExpr(),
                offset), True)
    cpdef RefExprTypeScopeGlobal mkRefExprTypeScopeGlobal(self,
            int32_t fileid):
        return RefExprTypeScopeGlobal.mk(self._hndl.mkRefExprTypeScopeGlobal(
                fileid), True)
    cpdef Scope mkScope(self):
        return Scope.mk(self._hndl.mkScope(
), True)
    cpdef CoverStmtInline mkCoverStmtInline(self,
            ScopeChild body):
        return CoverStmtInline.mk(self._hndl.mkCoverStmtInline(
                body.asScopeChild()), True)
    cpdef CoverStmtReference mkCoverStmtReference(self,
            ExprRefPath target):
        return CoverStmtReference.mk(self._hndl.mkCoverStmtReference(
                target.asExprRefPath()), True)
    cpdef DataType mkDataType(self):
        return DataType.mk(self._hndl.mkDataType(
), True)
    cpdef ScopeChildRef mkScopeChildRef(self,
            ScopeChild target):
        return ScopeChildRef.mk(self._hndl.mkScopeChildRef(
                target.asScopeChild()), True)
    cpdef SymbolChild mkSymbolChild(self):
        return SymbolChild.mk(self._hndl.mkSymbolChild(
), True)
    cpdef SymbolScopeRef mkSymbolScopeRef(self,
            str name):
        return SymbolScopeRef.mk(self._hndl.mkSymbolScopeRef(
                name), True)
    cpdef TemplateParamDecl mkTemplateParamDecl(self,
            ExprId name):
        return TemplateParamDecl.mk(self._hndl.mkTemplateParamDecl(
                name.asExprId()), True)
    cpdef ExecStmt mkExecStmt(self):
        return ExecStmt.mk(self._hndl.mkExecStmt(
), True)
    cpdef ExecTargetTemplateBlock mkExecTargetTemplateBlock(self,
             kind,
            str data):
        cdef int kind_i = int(kind)
        return ExecTargetTemplateBlock.mk(self._hndl.mkExecTargetTemplateBlock(
                <ast_decl.ExecKind>(kind_i),
                data), True)
    cpdef TemplateParamExprValue mkTemplateParamExprValue(self,
            Expr value):
        return TemplateParamExprValue.mk(self._hndl.mkTemplateParamExprValue(
                value.asExpr()), True)
    cpdef ExportFunction mkExportFunction(self,
             plat,
            ExprId name):
        cdef int plat_i = int(plat)
        return ExportFunction.mk(self._hndl.mkExportFunction(
                <ast_decl.PlatQual>(plat_i),
                name.asExprId()), True)
    cpdef TemplateParamTypeValue mkTemplateParamTypeValue(self,
            DataType value):
        return TemplateParamTypeValue.mk(self._hndl.mkTemplateParamTypeValue(
                value.asDataType()), True)
    cpdef TypeIdentifier mkTypeIdentifier(self):
        return TypeIdentifier.mk(self._hndl.mkTypeIdentifier(
), True)
    cpdef ExprAggrLiteral mkExprAggrLiteral(self):
        return ExprAggrLiteral.mk(self._hndl.mkExprAggrLiteral(
), True)
    cpdef TypeIdentifierElem mkTypeIdentifierElem(self,
            ExprId id,
            TemplateParamValueList params):
        return TypeIdentifierElem.mk(self._hndl.mkTypeIdentifierElem(
                id.asExprId(),
                params.asTemplateParamValueList()), True)
    cpdef TypedefDeclaration mkTypedefDeclaration(self,
            ExprId name,
            DataType type):
        return TypedefDeclaration.mk(self._hndl.mkTypedefDeclaration(
                name.asExprId(),
                type.asDataType()), True)
    cpdef ExprBin mkExprBin(self,
            Expr lhs,
             op,
            Expr rhs):
        cdef int op_i = int(op)
        return ExprBin.mk(self._hndl.mkExprBin(
                lhs.asExpr(),
                <ast_decl.ExprBinOp>(op_i),
                rhs.asExpr()), True)
    cpdef ExprBitSlice mkExprBitSlice(self,
            Expr lhs,
            Expr rhs):
        return ExprBitSlice.mk(self._hndl.mkExprBitSlice(
                lhs.asExpr(),
                rhs.asExpr()), True)
    cpdef ExprBool mkExprBool(self,
            bool value):
        return ExprBool.mk(self._hndl.mkExprBool(
                value), True)
    cpdef ExprCast mkExprCast(self,
            DataType casting_type,
            Expr expr):
        return ExprCast.mk(self._hndl.mkExprCast(
                casting_type.asDataType(),
                expr.asExpr()), True)
    cpdef ExprCompileHas mkExprCompileHas(self,
            ExprRefPathStatic ref):
        return ExprCompileHas.mk(self._hndl.mkExprCompileHas(
                ref.asExprRefPathStatic()), True)
    cpdef ExprCond mkExprCond(self,
            Expr cond_e,
            Expr true_e,
            Expr false_e):
        return ExprCond.mk(self._hndl.mkExprCond(
                cond_e.asExpr(),
                true_e.asExpr(),
                false_e.asExpr()), True)
    cpdef ExprDomainOpenRangeList mkExprDomainOpenRangeList(self):
        return ExprDomainOpenRangeList.mk(self._hndl.mkExprDomainOpenRangeList(
), True)
    cpdef ExprDomainOpenRangeValue mkExprDomainOpenRangeValue(self,
            bool single,
            Expr lhs,
            Expr rhs):
        return ExprDomainOpenRangeValue.mk(self._hndl.mkExprDomainOpenRangeValue(
                single,
                lhs.asExpr(),
                rhs.asExpr()), True)
    cpdef ExprHierarchicalId mkExprHierarchicalId(self):
        return ExprHierarchicalId.mk(self._hndl.mkExprHierarchicalId(
), True)
    cpdef ExprId mkExprId(self,
            str id,
            bool is_escaped):
        return ExprId.mk(self._hndl.mkExprId(
                id,
                is_escaped), True)
    cpdef ExprIn mkExprIn(self,
            Expr lhs,
            ExprOpenRangeList rhs):
        return ExprIn.mk(self._hndl.mkExprIn(
                lhs.asExpr(),
                rhs.asExprOpenRangeList()), True)
    cpdef ExprListLiteral mkExprListLiteral(self):
        return ExprListLiteral.mk(self._hndl.mkExprListLiteral(
), True)
    cpdef ExprMemberPathElem mkExprMemberPathElem(self,
            ExprId id,
            MethodParameterList params):
        return ExprMemberPathElem.mk(self._hndl.mkExprMemberPathElem(
                id.asExprId(),
                params.asMethodParameterList()), True)
    cpdef ExprNull mkExprNull(self):
        return ExprNull.mk(self._hndl.mkExprNull(
), True)
    cpdef ExprNumber mkExprNumber(self):
        return ExprNumber.mk(self._hndl.mkExprNumber(
), True)
    cpdef ExprOpenRangeList mkExprOpenRangeList(self):
        return ExprOpenRangeList.mk(self._hndl.mkExprOpenRangeList(
), True)
    cpdef ExprOpenRangeValue mkExprOpenRangeValue(self,
            Expr lhs,
            Expr rhs):
        return ExprOpenRangeValue.mk(self._hndl.mkExprOpenRangeValue(
                lhs.asExpr(),
                rhs.asExpr()), True)
    cpdef ExprRefPath mkExprRefPath(self):
        return ExprRefPath.mk(self._hndl.mkExprRefPath(
), True)
    cpdef ExprRefPathElem mkExprRefPathElem(self):
        return ExprRefPathElem.mk(self._hndl.mkExprRefPathElem(
), True)
    cpdef ExprStaticRefPath mkExprStaticRefPath(self,
            bool is_global,
            ExprMemberPathElem leaf):
        return ExprStaticRefPath.mk(self._hndl.mkExprStaticRefPath(
                is_global,
                leaf.asExprMemberPathElem()), True)
    cpdef ExprString mkExprString(self,
            str value,
            bool is_raw):
        return ExprString.mk(self._hndl.mkExprString(
                value,
                is_raw), True)
    cpdef ExprStructLiteral mkExprStructLiteral(self):
        return ExprStructLiteral.mk(self._hndl.mkExprStructLiteral(
), True)
    cpdef ExprStructLiteralItem mkExprStructLiteralItem(self,
            ExprId id,
            Expr value):
        return ExprStructLiteralItem.mk(self._hndl.mkExprStructLiteralItem(
                id.asExprId(),
                value.asExpr()), True)
    cpdef ExprSubscript mkExprSubscript(self,
            Expr expr,
            Expr subscript):
        return ExprSubscript.mk(self._hndl.mkExprSubscript(
                expr.asExpr(),
                subscript.asExpr()), True)
    cpdef ExprSubstring mkExprSubstring(self,
            Expr expr,
            Expr start,
            Expr end):
        return ExprSubstring.mk(self._hndl.mkExprSubstring(
                expr.asExpr(),
                start.asExpr(),
                end.asExpr()), True)
    cpdef ExprUnary mkExprUnary(self,
             op,
            Expr rhs):
        cdef int op_i = int(op)
        return ExprUnary.mk(self._hndl.mkExprUnary(
                <ast_decl.ExprUnaryOp>(op_i),
                rhs.asExpr()), True)
    cpdef ExtendEnum mkExtendEnum(self,
            TypeIdentifier target):
        return ExtendEnum.mk(self._hndl.mkExtendEnum(
                target.asTypeIdentifier()), True)
    cpdef FunctionDefinition mkFunctionDefinition(self,
            FunctionPrototype proto,
            ExecScope body,
             plat):
        cdef int plat_i = int(plat)
        return FunctionDefinition.mk(self._hndl.mkFunctionDefinition(
                proto.asFunctionPrototype(),
                body.asExecScope(),
                <ast_decl.PlatQual>(plat_i)), True)
    cpdef FunctionImport mkFunctionImport(self,
             plat,
            str lang):
        cdef int plat_i = int(plat)
        return FunctionImport.mk(self._hndl.mkFunctionImport(
                <ast_decl.PlatQual>(plat_i),
                lang), True)
    cpdef FunctionParamDecl mkFunctionParamDecl(self,
             kind,
            ExprId name,
            DataType type,
             dir,
            Expr dflt):
        cdef int kind_i = int(kind)
        cdef int dir_i = int(dir)
        return FunctionParamDecl.mk(self._hndl.mkFunctionParamDecl(
                <ast_decl.FunctionParamDeclKind>(kind_i),
                name.asExprId(),
                type.asDataType(),
                <ast_decl.ParamDir>(dir_i),
                dflt.asExpr()), True)
    cpdef GenericConstraintDeclValue mkGenericConstraintDeclValue(self):
        return GenericConstraintDeclValue.mk(self._hndl.mkGenericConstraintDeclValue(
), True)
    cpdef GenericConstraintParam mkGenericConstraintParam(self,
            ExprId name,
            bool is_const,
            bool is_numeric,
            DataType type):
        return GenericConstraintParam.mk(self._hndl.mkGenericConstraintParam(
                name.asExprId(),
                is_const,
                is_numeric,
                type.asDataType()), True)
    cpdef MethodParameterList mkMethodParameterList(self):
        return MethodParameterList.mk(self._hndl.mkMethodParameterList(
), True)
    cpdef MonitorActivityActionTraversal mkMonitorActivityActionTraversal(self,
            ExprRefPath target,
            ConstraintStmt with_c):
        return MonitorActivityActionTraversal.mk(self._hndl.mkMonitorActivityActionTraversal(
                target.asExprRefPath(),
                with_c.asConstraintStmt()), True)
    cpdef MonitorActivityConcat mkMonitorActivityConcat(self,
            MonitorActivityStmt lhs,
            MonitorActivityStmt rhs):
        return MonitorActivityConcat.mk(self._hndl.mkMonitorActivityConcat(
                lhs.asMonitorActivityStmt(),
                rhs.asMonitorActivityStmt()), True)
    cpdef ActionHandleField mkActionHandleField(self,
            ExprId name,
            DataType type):
        return ActionHandleField.mk(self._hndl.mkActionHandleField(
                name.asExprId(),
                type.asDataType()), True)
    cpdef MonitorActivityEventually mkMonitorActivityEventually(self,
            Expr condition,
            MonitorActivityStmt body):
        return MonitorActivityEventually.mk(self._hndl.mkMonitorActivityEventually(
                condition.asExpr(),
                body.asMonitorActivityStmt()), True)
    cpdef MonitorActivityIfElse mkMonitorActivityIfElse(self,
            Expr cond,
            MonitorActivityStmt true_s,
            MonitorActivityStmt false_s):
        return MonitorActivityIfElse.mk(self._hndl.mkMonitorActivityIfElse(
                cond.asExpr(),
                true_s.asMonitorActivityStmt(),
                false_s.asMonitorActivityStmt()), True)
    cpdef MonitorActivityMatch mkMonitorActivityMatch(self,
            Expr cond):
        return MonitorActivityMatch.mk(self._hndl.mkMonitorActivityMatch(
                cond.asExpr()), True)
    cpdef ActivityBindStmt mkActivityBindStmt(self,
            ExprHierarchicalId lhs):
        return ActivityBindStmt.mk(self._hndl.mkActivityBindStmt(
                lhs.asExprHierarchicalId()), True)
    cpdef ActivityConstraint mkActivityConstraint(self,
            ConstraintStmt constraint):
        return ActivityConstraint.mk(self._hndl.mkActivityConstraint(
                constraint.asConstraintStmt()), True)
    cpdef MonitorActivityMonitorTraversal mkMonitorActivityMonitorTraversal(self,
            ExprRefPath target,
            ConstraintStmt with_c):
        return MonitorActivityMonitorTraversal.mk(self._hndl.mkMonitorActivityMonitorTraversal(
                target.asExprRefPath(),
                with_c.asConstraintStmt()), True)
    cpdef MonitorActivityOverlap mkMonitorActivityOverlap(self,
            MonitorActivityStmt lhs,
            MonitorActivityStmt rhs):
        return MonitorActivityOverlap.mk(self._hndl.mkMonitorActivityOverlap(
                lhs.asMonitorActivityStmt(),
                rhs.asMonitorActivityStmt()), True)
    cpdef MonitorActivityRepeatCount mkMonitorActivityRepeatCount(self,
            ExprId loop_var,
            Expr count,
            ScopeChild body):
        return MonitorActivityRepeatCount.mk(self._hndl.mkMonitorActivityRepeatCount(
                loop_var.asExprId(),
                count.asExpr(),
                body.asScopeChild()), True)
    cpdef MonitorActivityRepeatWhile mkMonitorActivityRepeatWhile(self,
            Expr cond,
            ScopeChild body):
        return MonitorActivityRepeatWhile.mk(self._hndl.mkMonitorActivityRepeatWhile(
                cond.asExpr(),
                body.asScopeChild()), True)
    cpdef ActivityJoinSpecBranch mkActivityJoinSpecBranch(self):
        return ActivityJoinSpecBranch.mk(self._hndl.mkActivityJoinSpecBranch(
), True)
    cpdef ActivityJoinSpecFirst mkActivityJoinSpecFirst(self,
            Expr count):
        return ActivityJoinSpecFirst.mk(self._hndl.mkActivityJoinSpecFirst(
                count.asExpr()), True)
    cpdef ActivityJoinSpecNone mkActivityJoinSpecNone(self):
        return ActivityJoinSpecNone.mk(self._hndl.mkActivityJoinSpecNone(
), True)
    cpdef ActivityJoinSpecSelect mkActivityJoinSpecSelect(self,
            Expr count):
        return ActivityJoinSpecSelect.mk(self._hndl.mkActivityJoinSpecSelect(
                count.asExpr()), True)
    cpdef MonitorActivitySelect mkMonitorActivitySelect(self):
        return MonitorActivitySelect.mk(self._hndl.mkMonitorActivitySelect(
), True)
    cpdef ActivityLabeledStmt mkActivityLabeledStmt(self):
        return ActivityLabeledStmt.mk(self._hndl.mkActivityLabeledStmt(
), True)
    cpdef MonitorConstraint mkMonitorConstraint(self,
            ConstraintStmt constraint):
        return MonitorConstraint.mk(self._hndl.mkMonitorConstraint(
                constraint.asConstraintStmt()), True)
    cpdef NamedScope mkNamedScope(self,
            ExprId name):
        return NamedScope.mk(self._hndl.mkNamedScope(
                name.asExprId()), True)
    cpdef PackageScope mkPackageScope(self):
        return PackageScope.mk(self._hndl.mkPackageScope(
), True)
    cpdef ProceduralStmtAssignment mkProceduralStmtAssignment(self,
            Expr lhs,
             op,
            Expr rhs):
        cdef int op_i = int(op)
        return ProceduralStmtAssignment.mk(self._hndl.mkProceduralStmtAssignment(
                lhs.asExpr(),
                <ast_decl.AssignOp>(op_i),
                rhs.asExpr()), True)
    cpdef ProceduralStmtBody mkProceduralStmtBody(self,
            ScopeChild body):
        return ProceduralStmtBody.mk(self._hndl.mkProceduralStmtBody(
                body.asScopeChild()), True)
    cpdef ProceduralStmtBreak mkProceduralStmtBreak(self):
        return ProceduralStmtBreak.mk(self._hndl.mkProceduralStmtBreak(
), True)
    cpdef ProceduralStmtContinue mkProceduralStmtContinue(self):
        return ProceduralStmtContinue.mk(self._hndl.mkProceduralStmtContinue(
), True)
    cpdef ProceduralStmtDataDeclaration mkProceduralStmtDataDeclaration(self,
            ExprId name,
            DataType datatype,
            Expr init):
        return ProceduralStmtDataDeclaration.mk(self._hndl.mkProceduralStmtDataDeclaration(
                name.asExprId(),
                datatype.asDataType(),
                init.asExpr()), True)
    cpdef ProceduralStmtExpr mkProceduralStmtExpr(self,
            Expr expr):
        return ProceduralStmtExpr.mk(self._hndl.mkProceduralStmtExpr(
                expr.asExpr()), True)
    cpdef ProceduralStmtFunctionCall mkProceduralStmtFunctionCall(self,
            ExprRefPathStaticRooted prefix):
        return ProceduralStmtFunctionCall.mk(self._hndl.mkProceduralStmtFunctionCall(
                prefix.asExprRefPathStaticRooted()), True)
    cpdef ProceduralStmtIfElse mkProceduralStmtIfElse(self):
        return ProceduralStmtIfElse.mk(self._hndl.mkProceduralStmtIfElse(
), True)
    cpdef ProceduralStmtMatch mkProceduralStmtMatch(self,
            Expr expr):
        return ProceduralStmtMatch.mk(self._hndl.mkProceduralStmtMatch(
                expr.asExpr()), True)
    cpdef ProceduralStmtMatchChoice mkProceduralStmtMatchChoice(self,
            bool is_default,
            ExprOpenRangeList cond,
            ScopeChild body):
        return ProceduralStmtMatchChoice.mk(self._hndl.mkProceduralStmtMatchChoice(
                is_default,
                cond.asExprOpenRangeList(),
                body.asScopeChild()), True)
    cpdef ProceduralStmtRandomize mkProceduralStmtRandomize(self,
            Expr target):
        return ProceduralStmtRandomize.mk(self._hndl.mkProceduralStmtRandomize(
                target.asExpr()), True)
    cpdef ProceduralStmtReturn mkProceduralStmtReturn(self,
            Expr expr):
        return ProceduralStmtReturn.mk(self._hndl.mkProceduralStmtReturn(
                expr.asExpr()), True)
    cpdef ConstraintScope mkConstraintScope(self):
        return ConstraintScope.mk(self._hndl.mkConstraintScope(
), True)
    cpdef ConstraintStmtDefault mkConstraintStmtDefault(self,
            ExprHierarchicalId hid,
            Expr expr):
        return ConstraintStmtDefault.mk(self._hndl.mkConstraintStmtDefault(
                hid.asExprHierarchicalId(),
                expr.asExpr()), True)
    cpdef ConstraintStmtDefaultDisable mkConstraintStmtDefaultDisable(self,
            ExprHierarchicalId hid):
        return ConstraintStmtDefaultDisable.mk(self._hndl.mkConstraintStmtDefaultDisable(
                hid.asExprHierarchicalId()), True)
    cpdef ConstraintStmtExpr mkConstraintStmtExpr(self,
            Expr expr):
        return ConstraintStmtExpr.mk(self._hndl.mkConstraintStmtExpr(
                expr.asExpr()), True)
    cpdef ConstraintStmtField mkConstraintStmtField(self,
            ExprId name,
            DataType type):
        return ConstraintStmtField.mk(self._hndl.mkConstraintStmtField(
                name.asExprId(),
                type.asDataType()), True)
    cpdef ProceduralStmtYield mkProceduralStmtYield(self):
        return ProceduralStmtYield.mk(self._hndl.mkProceduralStmtYield(
), True)
    cpdef ConstraintStmtIf mkConstraintStmtIf(self,
            Expr cond,
            ConstraintScope true_c,
            ConstraintScope false_c):
        return ConstraintStmtIf.mk(self._hndl.mkConstraintStmtIf(
                cond.asExpr(),
                true_c.asConstraintScope(),
                false_c.asConstraintScope()), True)
    cpdef ConstraintStmtUnique mkConstraintStmtUnique(self):
        return ConstraintStmtUnique.mk(self._hndl.mkConstraintStmtUnique(
), True)
    cpdef SymbolChildrenScope mkSymbolChildrenScope(self,
            str name):
        return SymbolChildrenScope.mk(self._hndl.mkSymbolChildrenScope(
                name), True)
    cpdef DataTypeBool mkDataTypeBool(self):
        return DataTypeBool.mk(self._hndl.mkDataTypeBool(
), True)
    cpdef DataTypeChandle mkDataTypeChandle(self):
        return DataTypeChandle.mk(self._hndl.mkDataTypeChandle(
), True)
    cpdef DataTypeEnum mkDataTypeEnum(self,
            DataTypeUserDefined tid,
            ExprOpenRangeList in_rangelist):
        return DataTypeEnum.mk(self._hndl.mkDataTypeEnum(
                tid.asDataTypeUserDefined(),
                in_rangelist.asExprOpenRangeList()), True)
    cpdef DataTypeInt mkDataTypeInt(self,
            bool is_signed,
            Expr width,
            ExprDomainOpenRangeList in_range):
        return DataTypeInt.mk(self._hndl.mkDataTypeInt(
                is_signed,
                width.asExpr(),
                in_range.asExprDomainOpenRangeList()), True)
    cpdef DataTypePyObj mkDataTypePyObj(self):
        return DataTypePyObj.mk(self._hndl.mkDataTypePyObj(
), True)
    cpdef DataTypeRef mkDataTypeRef(self,
            DataTypeUserDefined type):
        return DataTypeRef.mk(self._hndl.mkDataTypeRef(
                type.asDataTypeUserDefined()), True)
    cpdef DataTypeString mkDataTypeString(self,
            bool has_range):
        return DataTypeString.mk(self._hndl.mkDataTypeString(
                has_range), True)
    cpdef DataTypeUserDefined mkDataTypeUserDefined(self,
            bool is_global,
            TypeIdentifier type_id):
        return DataTypeUserDefined.mk(self._hndl.mkDataTypeUserDefined(
                is_global,
                type_id.asTypeIdentifier()), True)
    cpdef EnumDecl mkEnumDecl(self,
            ExprId name):
        return EnumDecl.mk(self._hndl.mkEnumDecl(
                name.asExprId()), True)
    cpdef EnumItem mkEnumItem(self,
            ExprId name,
            Expr value):
        return EnumItem.mk(self._hndl.mkEnumItem(
                name.asExprId(),
                value.asExpr()), True)
    cpdef TemplateCategoryTypeParamDecl mkTemplateCategoryTypeParamDecl(self,
            ExprId name,
             category,
            TypeIdentifier restriction,
            DataType dflt):
        cdef int category_i = int(category)
        return TemplateCategoryTypeParamDecl.mk(self._hndl.mkTemplateCategoryTypeParamDecl(
                name.asExprId(),
                <ast_decl.TypeCategory>(category_i),
                restriction.asTypeIdentifier(),
                dflt.asDataType()), True)
    cpdef TemplateGenericTypeParamDecl mkTemplateGenericTypeParamDecl(self,
            ExprId name,
            DataType dflt):
        return TemplateGenericTypeParamDecl.mk(self._hndl.mkTemplateGenericTypeParamDecl(
                name.asExprId(),
                dflt.asDataType()), True)
    cpdef ExprAggrEmpty mkExprAggrEmpty(self):
        return ExprAggrEmpty.mk(self._hndl.mkExprAggrEmpty(
), True)
    cpdef ExprAggrList mkExprAggrList(self):
        return ExprAggrList.mk(self._hndl.mkExprAggrList(
), True)
    cpdef TemplateValueParamDecl mkTemplateValueParamDecl(self,
            ExprId name,
            DataType type,
            Expr dflt):
        return TemplateValueParamDecl.mk(self._hndl.mkTemplateValueParamDecl(
                name.asExprId(),
                type.asDataType(),
                dflt.asExpr()), True)
    cpdef ExprAggrMap mkExprAggrMap(self):
        return ExprAggrMap.mk(self._hndl.mkExprAggrMap(
), True)
    cpdef ExprAggrStruct mkExprAggrStruct(self):
        return ExprAggrStruct.mk(self._hndl.mkExprAggrStruct(
), True)
    cpdef ExprRefPathContext mkExprRefPathContext(self,
            ExprHierarchicalId hier_id):
        return ExprRefPathContext.mk(self._hndl.mkExprRefPathContext(
                hier_id.asExprHierarchicalId()), True)
    cpdef ExprRefPathId mkExprRefPathId(self,
            ExprId id):
        return ExprRefPathId.mk(self._hndl.mkExprRefPathId(
                id.asExprId()), True)
    cpdef ExprRefPathStatic mkExprRefPathStatic(self,
            bool is_global):
        return ExprRefPathStatic.mk(self._hndl.mkExprRefPathStatic(
                is_global), True)
    cpdef ExprRefPathStaticRooted mkExprRefPathStaticRooted(self,
            ExprRefPathStatic root,
            ExprHierarchicalId leaf):
        return ExprRefPathStaticRooted.mk(self._hndl.mkExprRefPathStaticRooted(
                root.asExprRefPathStatic(),
                leaf.asExprHierarchicalId()), True)
    cpdef ExprSignedNumber mkExprSignedNumber(self,
            str image,
            int32_t width,
            int64_t value):
        return ExprSignedNumber.mk(self._hndl.mkExprSignedNumber(
                image,
                width,
                value), True)
    cpdef ExprUnsignedNumber mkExprUnsignedNumber(self,
            str image,
            int32_t width,
            uint64_t value):
        return ExprUnsignedNumber.mk(self._hndl.mkExprUnsignedNumber(
                image,
                width,
                value), True)
    cpdef ExtendType mkExtendType(self,
             kind,
            TypeIdentifier target):
        cdef int kind_i = int(kind)
        return ExtendType.mk(self._hndl.mkExtendType(
                <ast_decl.ExtendTargetE>(kind_i),
                target.asTypeIdentifier()), True)
    cpdef Field mkField(self,
            ExprId name,
            DataType type,
             attr,
            Expr init):
        cdef int attr_i = int(attr)
        return Field.mk(self._hndl.mkField(
                name.asExprId(),
                type.asDataType(),
                <ast_decl.FieldAttr>(attr_i),
                init.asExpr()), True)
    cpdef FieldClaim mkFieldClaim(self,
            ExprId name,
            DataTypeUserDefined type,
            bool is_lock):
        return FieldClaim.mk(self._hndl.mkFieldClaim(
                name.asExprId(),
                type.asDataTypeUserDefined(),
                is_lock), True)
    cpdef FieldCompRef mkFieldCompRef(self,
            ExprId name,
            DataTypeUserDefined type):
        return FieldCompRef.mk(self._hndl.mkFieldCompRef(
                name.asExprId(),
                type.asDataTypeUserDefined()), True)
    cpdef FieldRef mkFieldRef(self,
            ExprId name,
            DataTypeUserDefined type,
            bool is_input):
        return FieldRef.mk(self._hndl.mkFieldRef(
                name.asExprId(),
                type.asDataTypeUserDefined(),
                is_input), True)
    cpdef FunctionImportProto mkFunctionImportProto(self,
             plat,
            str lang,
            FunctionPrototype proto):
        cdef int plat_i = int(plat)
        return FunctionImportProto.mk(self._hndl.mkFunctionImportProto(
                <ast_decl.PlatQual>(plat_i),
                lang,
                proto.asFunctionPrototype()), True)
    cpdef FunctionImportType mkFunctionImportType(self,
             plat,
            str lang,
            TypeIdentifier type):
        cdef int plat_i = int(plat)
        return FunctionImportType.mk(self._hndl.mkFunctionImportType(
                <ast_decl.PlatQual>(plat_i),
                lang,
                type.asTypeIdentifier()), True)
    cpdef FunctionPrototype mkFunctionPrototype(self,
            ExprId name,
            DataType rtype,
            bool is_target,
            bool is_solve):
        return FunctionPrototype.mk(self._hndl.mkFunctionPrototype(
                name.asExprId(),
                rtype.asDataType(),
                is_target,
                is_solve), True)
    cpdef GlobalScope mkGlobalScope(self,
            int32_t fileid):
        return GlobalScope.mk(self._hndl.mkGlobalScope(
                fileid), True)
    cpdef ActivityActionHandleTraversal mkActivityActionHandleTraversal(self,
            ExprRefPathContext target,
            ConstraintStmt with_c):
        return ActivityActionHandleTraversal.mk(self._hndl.mkActivityActionHandleTraversal(
                target.asExprRefPathContext(),
                with_c.asConstraintStmt()), True)
    cpdef ActivityActionTypeTraversal mkActivityActionTypeTraversal(self,
            DataTypeUserDefined target,
            ConstraintStmt with_c):
        return ActivityActionTypeTraversal.mk(self._hndl.mkActivityActionTypeTraversal(
                target.asDataTypeUserDefined(),
                with_c.asConstraintStmt()), True)
    cpdef ActivityAtomicBlock mkActivityAtomicBlock(self,
            ScopeChild body):
        return ActivityAtomicBlock.mk(self._hndl.mkActivityAtomicBlock(
                body.asScopeChild()), True)
    cpdef ActivityForeach mkActivityForeach(self,
            ExprId it_id,
            ExprId idx_id,
            ExprRefPathContext target,
            ScopeChild body):
        return ActivityForeach.mk(self._hndl.mkActivityForeach(
                it_id.asExprId(),
                idx_id.asExprId(),
                target.asExprRefPathContext(),
                body.asScopeChild()), True)
    cpdef ActivityIfElse mkActivityIfElse(self,
            Expr cond,
            ActivityStmt true_s,
            ActivityStmt false_s):
        return ActivityIfElse.mk(self._hndl.mkActivityIfElse(
                cond.asExpr(),
                true_s.asActivityStmt(),
                false_s.asActivityStmt()), True)
    cpdef ActivityMatch mkActivityMatch(self,
            Expr cond):
        return ActivityMatch.mk(self._hndl.mkActivityMatch(
                cond.asExpr()), True)
    cpdef ActivityRepeatCount mkActivityRepeatCount(self,
            ExprId loop_var,
            Expr count,
            ScopeChild body):
        return ActivityRepeatCount.mk(self._hndl.mkActivityRepeatCount(
                loop_var.asExprId(),
                count.asExpr(),
                body.asScopeChild()), True)
    cpdef ActivityRepeatWhile mkActivityRepeatWhile(self,
            Expr cond,
            ScopeChild body):
        return ActivityRepeatWhile.mk(self._hndl.mkActivityRepeatWhile(
                cond.asExpr(),
                body.asScopeChild()), True)
    cpdef ActivityReplicate mkActivityReplicate(self,
            ExprId idx_id,
            ExprId it_label,
            ScopeChild body):
        return ActivityReplicate.mk(self._hndl.mkActivityReplicate(
                idx_id.asExprId(),
                it_label.asExprId(),
                body.asScopeChild()), True)
    cpdef ActivitySelect mkActivitySelect(self):
        return ActivitySelect.mk(self._hndl.mkActivitySelect(
), True)
    cpdef ActivitySuper mkActivitySuper(self):
        return ActivitySuper.mk(self._hndl.mkActivitySuper(
), True)
    cpdef ProceduralStmtRepeatWhile mkProceduralStmtRepeatWhile(self,
            ScopeChild body,
            Expr expr):
        return ProceduralStmtRepeatWhile.mk(self._hndl.mkProceduralStmtRepeatWhile(
                body.asScopeChild(),
                expr.asExpr()), True)
    cpdef ConstraintBlock mkConstraintBlock(self,
            str name,
            bool is_dynamic):
        return ConstraintBlock.mk(self._hndl.mkConstraintBlock(
                name,
                is_dynamic), True)
    cpdef ProceduralStmtWhile mkProceduralStmtWhile(self,
            ScopeChild body,
            Expr expr):
        return ProceduralStmtWhile.mk(self._hndl.mkProceduralStmtWhile(
                body.asScopeChild(),
                expr.asExpr()), True)
    cpdef ConstraintStmtForall mkConstraintStmtForall(self,
            ExprId iterator_id,
            DataTypeUserDefined type_id,
            ExprRefPath ref_path):
        return ConstraintStmtForall.mk(self._hndl.mkConstraintStmtForall(
                iterator_id.asExprId(),
                type_id.asDataTypeUserDefined(),
                ref_path.asExprRefPath()), True)
    cpdef ConstraintStmtForeach mkConstraintStmtForeach(self,
            Expr expr):
        return ConstraintStmtForeach.mk(self._hndl.mkConstraintStmtForeach(
                expr.asExpr()), True)
    cpdef ConstraintStmtImplication mkConstraintStmtImplication(self,
            Expr cond):
        return ConstraintStmtImplication.mk(self._hndl.mkConstraintStmtImplication(
                cond.asExpr()), True)
    cpdef SymbolScope mkSymbolScope(self,
            str name):
        return SymbolScope.mk(self._hndl.mkSymbolScope(
                name), True)
    cpdef TypeScope mkTypeScope(self,
            ExprId name,
            TypeIdentifier super_t):
        return TypeScope.mk(self._hndl.mkTypeScope(
                name.asExprId(),
                super_t.asTypeIdentifier()), True)
    cpdef ExprRefPathStaticFunc mkExprRefPathStaticFunc(self,
            bool is_global,
            MethodParameterList params):
        return ExprRefPathStaticFunc.mk(self._hndl.mkExprRefPathStaticFunc(
                is_global,
                params.asMethodParameterList()), True)
    cpdef ExprRefPathSuper mkExprRefPathSuper(self,
            ExprHierarchicalId hier_id):
        return ExprRefPathSuper.mk(self._hndl.mkExprRefPathSuper(
                hier_id.asExprHierarchicalId()), True)
    cpdef Action mkAction(self,
            ExprId name,
            TypeIdentifier super_t,
            bool is_abstract):
        return Action.mk(self._hndl.mkAction(
                name.asExprId(),
                super_t.asTypeIdentifier(),
                is_abstract), True)
    cpdef MonitorActivityDecl mkMonitorActivityDecl(self,
            str name):
        return MonitorActivityDecl.mk(self._hndl.mkMonitorActivityDecl(
                name), True)
    cpdef ActivityDecl mkActivityDecl(self,
            str name):
        return ActivityDecl.mk(self._hndl.mkActivityDecl(
                name), True)
    cpdef MonitorActivitySchedule mkMonitorActivitySchedule(self,
            str name):
        return MonitorActivitySchedule.mk(self._hndl.mkMonitorActivitySchedule(
                name), True)
    cpdef MonitorActivitySequence mkMonitorActivitySequence(self,
            str name):
        return MonitorActivitySequence.mk(self._hndl.mkMonitorActivitySequence(
                name), True)
    cpdef ActivityLabeledScope mkActivityLabeledScope(self,
            str name):
        return ActivityLabeledScope.mk(self._hndl.mkActivityLabeledScope(
                name), True)
    cpdef AnnotationDecl mkAnnotationDecl(self,
            ExprId name,
            TypeIdentifier super_t):
        return AnnotationDecl.mk(self._hndl.mkAnnotationDecl(
                name.asExprId(),
                super_t.asTypeIdentifier()), True)
    cpdef Component mkComponent(self,
            ExprId name,
            TypeIdentifier super_t):
        return Component.mk(self._hndl.mkComponent(
                name.asExprId(),
                super_t.asTypeIdentifier()), True)
    cpdef ProceduralStmtSymbolBodyScope mkProceduralStmtSymbolBodyScope(self,
            str name,
            ScopeChild body):
        return ProceduralStmtSymbolBodyScope.mk(self._hndl.mkProceduralStmtSymbolBodyScope(
                name,
                body.asScopeChild()), True)
    cpdef RootSymbolScope mkRootSymbolScope(self,
            str name):
        return RootSymbolScope.mk(self._hndl.mkRootSymbolScope(
                name), True)
    cpdef ConstraintSymbolScope mkConstraintSymbolScope(self,
            str name):
        return ConstraintSymbolScope.mk(self._hndl.mkConstraintSymbolScope(
                name), True)
    cpdef Struct mkStruct(self,
            ExprId name,
            TypeIdentifier super_t,
             kind):
        cdef int kind_i = int(kind)
        return Struct.mk(self._hndl.mkStruct(
                name.asExprId(),
                super_t.asTypeIdentifier(),
                <ast_decl.StructKind>(kind_i)), True)
    cpdef SymbolEnumScope mkSymbolEnumScope(self,
            str name):
        return SymbolEnumScope.mk(self._hndl.mkSymbolEnumScope(
                name), True)
    cpdef SymbolExtendScope mkSymbolExtendScope(self,
            str name):
        return SymbolExtendScope.mk(self._hndl.mkSymbolExtendScope(
                name), True)
    cpdef SymbolFunctionScope mkSymbolFunctionScope(self,
            str name):
        return SymbolFunctionScope.mk(self._hndl.mkSymbolFunctionScope(
                name), True)
    cpdef SymbolTypeScope mkSymbolTypeScope(self,
            str name,
            SymbolScope plist):
        return SymbolTypeScope.mk(self._hndl.mkSymbolTypeScope(
                name,
                plist.asSymbolScope()), True)
    cpdef ExecScope mkExecScope(self,
            str name):
        return ExecScope.mk(self._hndl.mkExecScope(
                name), True)
    cpdef GenericConstraintDeclBool mkGenericConstraintDeclBool(self,
            str name,
            bool is_dynamic):
        return GenericConstraintDeclBool.mk(self._hndl.mkGenericConstraintDeclBool(
                name,
                is_dynamic), True)
    cpdef Monitor mkMonitor(self,
            ExprId name,
            TypeIdentifier super_t):
        return Monitor.mk(self._hndl.mkMonitor(
                name.asExprId(),
                super_t.asTypeIdentifier()), True)
    cpdef ProceduralStmtRepeat mkProceduralStmtRepeat(self,
            str name,
            ScopeChild body,
            ExprId it_id,
            Expr count):
        return ProceduralStmtRepeat.mk(self._hndl.mkProceduralStmtRepeat(
                name,
                body.asScopeChild(),
                it_id.asExprId(),
                count.asExpr()), True)
    cpdef ActivityParallel mkActivityParallel(self,
            str name,
            ActivityJoinSpec join_spec):
        return ActivityParallel.mk(self._hndl.mkActivityParallel(
                name,
                join_spec.asActivityJoinSpec()), True)
    cpdef ActivitySchedule mkActivitySchedule(self,
            str name,
            ActivityJoinSpec join_spec):
        return ActivitySchedule.mk(self._hndl.mkActivitySchedule(
                name,
                join_spec.asActivityJoinSpec()), True)
    cpdef ProceduralStmtForeach mkProceduralStmtForeach(self,
            str name,
            ScopeChild body,
            ExprRefPath path,
            ExprId it_id,
            ExprId idx_id):
        return ProceduralStmtForeach.mk(self._hndl.mkProceduralStmtForeach(
                name,
                body.asScopeChild(),
                path.asExprRefPath(),
                it_id.asExprId(),
                idx_id.asExprId()), True)
    cpdef ActivitySequence mkActivitySequence(self,
            str name):
        return ActivitySequence.mk(self._hndl.mkActivitySequence(
                name), True)
    cpdef ExecBlock mkExecBlock(self,
            str name,
             kind):
        cdef int kind_i = int(kind)
        return ExecBlock.mk(self._hndl.mkExecBlock(
                name,
                <ast_decl.ExecKind>(kind_i)), True)
    @staticmethod
    cdef mk(ast_decl.IFactory *hndl):
        ret = Factory()
        ret._hndl = hndl
        return ret
    @staticmethod
    def inst():
        cdef Factory factory
        global _inst
        if _inst is None:
            ext_dir = os.path.dirname(os.path.abspath(__file__))
            build_dir = os.path.abspath(os.path.join(ext_dir, "../../build"))
            libname = _libname
            core_lib = None
            for libdir in ("lib", "lib64", "bin"):
                if os.path.isfile(os.path.join(build_dir, libdir, libname)):
                    core_lib = os.path.join(build_dir, libdir, libname)
                    break
            if core_lib is None:
                core_lib = os.path.join(ext_dir, libname)
            if not os.path.isfile(core_lib):
                raise Exception("Extension library core \"%s\" doesn't exist" % core_lib)
            if _libname == "libast.dylib":
                import glob as _glob
                for _al in _glob.glob(os.path.join(os.path.dirname(core_lib), 'libantlr4-runtime*.dylib')):
                    ctypes.cdll.LoadLibrary(_al)
            so = ctypes.cdll.LoadLibrary(core_lib)
            func = so.ast_getFactory
            func.restype = ctypes.c_void_p
            
            hndl = <ast_decl.IFactoryP>(<intptr_t>(func()))
            factory = Factory()
            factory._hndl = hndl
            _inst = factory
        return _inst
cdef class TemplateParamDeclList(object):
    
    def __dealloc__(self):
        if self._owned and self._hndl != NULL:
            del self._hndl
            self._hndl = NULL
    
    cpdef void accept(self, VisitorBase v):
        self._hndl.accept(v._hndl)
    
    cpdef int id(self):
        return reinterpret_cast[intptr_t](self._hndl)
    def __hash__(self):
        return reinterpret_cast[intptr_t](self._hndl)
    
    def __eq__(self, o):
        oh = <TemplateParamDeclList>(o)
        return self._hndl == oh._hndl
    
    cdef ast_decl.ITemplateParamDeclList *asTemplateParamDeclList(self):
        return dynamic_cast[ast_decl.ITemplateParamDeclListP](self._hndl)
    @staticmethod
    cdef TemplateParamDeclList mk(ast_decl.ITemplateParamDeclList *hndl, bool owned):
        '''Creates a Python wrapper around native class'''
        ret = TemplateParamDeclList()
        ret._hndl = hndl
        ret._owned = owned
        return ret
    
    def params(self) -> ListUtil:
        return ListUtil(self.numParams, self.getParam)
    
    cpdef getParams(self):
        cdef const std_vector[ast_decl.ITemplateParamDeclUP] *__lp = &self.asTemplateParamDeclList().getParams()
        cdef ast_decl.ITemplateParamDecl *__ep;
        ret = []
        of = ObjFactory()
        for __i in range(__lp.size()):
            __ep = __lp.at(__i).get()
            ret.append(__ep.accept(of._hndl))
        return ret
    cpdef getParam(self, i):
        cdef ast_decl.ITemplateParamDecl *__ep = self.asTemplateParamDeclList().getParams().at(i).get();
        of = ObjFactory()
        __ep.accept(of._hndl)
        return of._obj
    cpdef void addParam(self, TemplateParamDecl i):
        i._owned = False
        self.asTemplateParamDeclList().getParams().push_back(ast_decl.ITemplateParamDeclUP(i.asTemplateParamDecl(), True))
    cpdef numParams(self):
        return self.asTemplateParamDeclList().getParams().size()
    cpdef bool getSpecialized(self):
        return dynamic_cast[ast_decl.ITemplateParamDeclListP](self._hndl).getSpecialized()

cdef class AssocData(object):
    
    def __dealloc__(self):
        if self._owned and self._hndl != NULL:
            del self._hndl
            self._hndl = NULL
    
    cpdef void accept(self, VisitorBase v):
        self._hndl.accept(v._hndl)
    
    cpdef int id(self):
        return reinterpret_cast[intptr_t](self._hndl)
    def __hash__(self):
        return reinterpret_cast[intptr_t](self._hndl)
    
    def __eq__(self, o):
        oh = <AssocData>(o)
        return self._hndl == oh._hndl
    
    cdef ast_decl.IAssocData *asAssocData(self):
        return dynamic_cast[ast_decl.IAssocDataP](self._hndl)
    @staticmethod
    cdef AssocData mk(ast_decl.IAssocData *hndl, bool owned):
        '''Creates a Python wrapper around native class'''
        ret = AssocData()
        ret._hndl = hndl
        ret._owned = owned
        return ret
    

cdef class ExecTargetTemplateParam(object):
    
    def __dealloc__(self):
        if self._owned and self._hndl != NULL:
            del self._hndl
            self._hndl = NULL
    
    cpdef void accept(self, VisitorBase v):
        self._hndl.accept(v._hndl)
    
    cpdef int id(self):
        return reinterpret_cast[intptr_t](self._hndl)
    def __hash__(self):
        return reinterpret_cast[intptr_t](self._hndl)
    
    def __eq__(self, o):
        oh = <ExecTargetTemplateParam>(o)
        return self._hndl == oh._hndl
    
    cdef ast_decl.IExecTargetTemplateParam *asExecTargetTemplateParam(self):
        return dynamic_cast[ast_decl.IExecTargetTemplateParamP](self._hndl)
    @staticmethod
    cdef ExecTargetTemplateParam mk(ast_decl.IExecTargetTemplateParam *hndl, bool owned):
        '''Creates a Python wrapper around native class'''
        ret = ExecTargetTemplateParam()
        ret._hndl = hndl
        ret._owned = owned
        return ret
    
    cpdef Expr getExpr(self):
        if self.asExecTargetTemplateParam().getExpr() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asExecTargetTemplateParam().getExpr().accept(of._hndl)
            return <Expr>(of._obj)
    cpdef int32_t getStart(self):
        return dynamic_cast[ast_decl.IExecTargetTemplateParamP](self._hndl).getStart()
    cpdef int32_t getEnd(self):
        return dynamic_cast[ast_decl.IExecTargetTemplateParamP](self._hndl).getEnd()

cdef class Expr(object):
    
    def __dealloc__(self):
        if self._owned and self._hndl != NULL:
            del self._hndl
            self._hndl = NULL
    
    cpdef void accept(self, VisitorBase v):
        self._hndl.accept(v._hndl)
    
    cpdef int id(self):
        return reinterpret_cast[intptr_t](self._hndl)
    def __hash__(self):
        return reinterpret_cast[intptr_t](self._hndl)
    
    def __eq__(self, o):
        oh = <Expr>(o)
        return self._hndl == oh._hndl
    
    cdef ast_decl.IExpr *asExpr(self):
        return dynamic_cast[ast_decl.IExprP](self._hndl)
    @staticmethod
    cdef Expr mk(ast_decl.IExpr *hndl, bool owned):
        '''Creates a Python wrapper around native class'''
        ret = Expr()
        ret._hndl = hndl
        ret._owned = owned
        return ret
    

cdef class TemplateParamValue(object):
    
    def __dealloc__(self):
        if self._owned and self._hndl != NULL:
            del self._hndl
            self._hndl = NULL
    
    cpdef void accept(self, VisitorBase v):
        self._hndl.accept(v._hndl)
    
    cpdef int id(self):
        return reinterpret_cast[intptr_t](self._hndl)
    def __hash__(self):
        return reinterpret_cast[intptr_t](self._hndl)
    
    def __eq__(self, o):
        oh = <TemplateParamValue>(o)
        return self._hndl == oh._hndl
    
    cdef ast_decl.ITemplateParamValue *asTemplateParamValue(self):
        return dynamic_cast[ast_decl.ITemplateParamValueP](self._hndl)
    @staticmethod
    cdef TemplateParamValue mk(ast_decl.ITemplateParamValue *hndl, bool owned):
        '''Creates a Python wrapper around native class'''
        ret = TemplateParamValue()
        ret._hndl = hndl
        ret._owned = owned
        return ret
    

cdef class MonitorActivityMatchChoice(object):
    
    def __dealloc__(self):
        if self._owned and self._hndl != NULL:
            del self._hndl
            self._hndl = NULL
    
    cpdef void accept(self, VisitorBase v):
        self._hndl.accept(v._hndl)
    
    cpdef int id(self):
        return reinterpret_cast[intptr_t](self._hndl)
    def __hash__(self):
        return reinterpret_cast[intptr_t](self._hndl)
    
    def __eq__(self, o):
        oh = <MonitorActivityMatchChoice>(o)
        return self._hndl == oh._hndl
    
    cdef ast_decl.IMonitorActivityMatchChoice *asMonitorActivityMatchChoice(self):
        return dynamic_cast[ast_decl.IMonitorActivityMatchChoiceP](self._hndl)
    @staticmethod
    cdef MonitorActivityMatchChoice mk(ast_decl.IMonitorActivityMatchChoice *hndl, bool owned):
        '''Creates a Python wrapper around native class'''
        ret = MonitorActivityMatchChoice()
        ret._hndl = hndl
        ret._owned = owned
        return ret
    
    cpdef bool getIs_default(self):
        return dynamic_cast[ast_decl.IMonitorActivityMatchChoiceP](self._hndl).getIs_default()
    cpdef ExprOpenRangeList getCond(self):
        if self.asMonitorActivityMatchChoice().getCond() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asMonitorActivityMatchChoice().getCond().accept(of._hndl)
            return <ExprOpenRangeList>(of._obj)
    cpdef ScopeChild getBody(self):
        if self.asMonitorActivityMatchChoice().getBody() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asMonitorActivityMatchChoice().getBody().accept(of._hndl)
            return <ScopeChild>(of._obj)

cdef class TemplateParamValueList(object):
    
    def __dealloc__(self):
        if self._owned and self._hndl != NULL:
            del self._hndl
            self._hndl = NULL
    
    cpdef void accept(self, VisitorBase v):
        self._hndl.accept(v._hndl)
    
    cpdef int id(self):
        return reinterpret_cast[intptr_t](self._hndl)
    def __hash__(self):
        return reinterpret_cast[intptr_t](self._hndl)
    
    def __eq__(self, o):
        oh = <TemplateParamValueList>(o)
        return self._hndl == oh._hndl
    
    cdef ast_decl.ITemplateParamValueList *asTemplateParamValueList(self):
        return dynamic_cast[ast_decl.ITemplateParamValueListP](self._hndl)
    @staticmethod
    cdef TemplateParamValueList mk(ast_decl.ITemplateParamValueList *hndl, bool owned):
        '''Creates a Python wrapper around native class'''
        ret = TemplateParamValueList()
        ret._hndl = hndl
        ret._owned = owned
        return ret
    
    def values(self) -> ListUtil:
        return ListUtil(self.numValues, self.getValue)
    
    cpdef getValues(self):
        cdef const std_vector[ast_decl.ITemplateParamValueUP] *__lp = &self.asTemplateParamValueList().getValues()
        cdef ast_decl.ITemplateParamValue *__ep;
        ret = []
        of = ObjFactory()
        for __i in range(__lp.size()):
            __ep = __lp.at(__i).get()
            ret.append(__ep.accept(of._hndl))
        return ret
    cpdef getValue(self, i):
        cdef ast_decl.ITemplateParamValue *__ep = self.asTemplateParamValueList().getValues().at(i).get();
        of = ObjFactory()
        __ep.accept(of._hndl)
        return of._obj
    cpdef void addValue(self, TemplateParamValue i):
        i._owned = False
        self.asTemplateParamValueList().getValues().push_back(ast_decl.ITemplateParamValueUP(i.asTemplateParamValue(), True))
    cpdef numValues(self):
        return self.asTemplateParamValueList().getValues().size()

cdef class ExprAggrMapElem(object):
    
    def __dealloc__(self):
        if self._owned and self._hndl != NULL:
            del self._hndl
            self._hndl = NULL
    
    cpdef void accept(self, VisitorBase v):
        self._hndl.accept(v._hndl)
    
    cpdef int id(self):
        return reinterpret_cast[intptr_t](self._hndl)
    def __hash__(self):
        return reinterpret_cast[intptr_t](self._hndl)
    
    def __eq__(self, o):
        oh = <ExprAggrMapElem>(o)
        return self._hndl == oh._hndl
    
    cdef ast_decl.IExprAggrMapElem *asExprAggrMapElem(self):
        return dynamic_cast[ast_decl.IExprAggrMapElemP](self._hndl)
    @staticmethod
    cdef ExprAggrMapElem mk(ast_decl.IExprAggrMapElem *hndl, bool owned):
        '''Creates a Python wrapper around native class'''
        ret = ExprAggrMapElem()
        ret._hndl = hndl
        ret._owned = owned
        return ret
    
    cpdef Expr getLhs(self):
        if self.asExprAggrMapElem().getLhs() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asExprAggrMapElem().getLhs().accept(of._hndl)
            return <Expr>(of._obj)
    cpdef Expr getRhs(self):
        if self.asExprAggrMapElem().getRhs() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asExprAggrMapElem().getRhs().accept(of._hndl)
            return <Expr>(of._obj)

cdef class RefExpr(object):
    
    def __dealloc__(self):
        if self._owned and self._hndl != NULL:
            del self._hndl
            self._hndl = NULL
    
    cpdef void accept(self, VisitorBase v):
        self._hndl.accept(v._hndl)
    
    cpdef int id(self):
        return reinterpret_cast[intptr_t](self._hndl)
    def __hash__(self):
        return reinterpret_cast[intptr_t](self._hndl)
    
    def __eq__(self, o):
        oh = <RefExpr>(o)
        return self._hndl == oh._hndl
    
    cdef ast_decl.IRefExpr *asRefExpr(self):
        return dynamic_cast[ast_decl.IRefExprP](self._hndl)
    @staticmethod
    cdef RefExpr mk(ast_decl.IRefExpr *hndl, bool owned):
        '''Creates a Python wrapper around native class'''
        ret = RefExpr()
        ret._hndl = hndl
        ret._owned = owned
        return ret
    

cdef class ExprAggrStructElem(object):
    
    def __dealloc__(self):
        if self._owned and self._hndl != NULL:
            del self._hndl
            self._hndl = NULL
    
    cpdef void accept(self, VisitorBase v):
        self._hndl.accept(v._hndl)
    
    cpdef int id(self):
        return reinterpret_cast[intptr_t](self._hndl)
    def __hash__(self):
        return reinterpret_cast[intptr_t](self._hndl)
    
    def __eq__(self, o):
        oh = <ExprAggrStructElem>(o)
        return self._hndl == oh._hndl
    
    cdef ast_decl.IExprAggrStructElem *asExprAggrStructElem(self):
        return dynamic_cast[ast_decl.IExprAggrStructElemP](self._hndl)
    @staticmethod
    cdef ExprAggrStructElem mk(ast_decl.IExprAggrStructElem *hndl, bool owned):
        '''Creates a Python wrapper around native class'''
        ret = ExprAggrStructElem()
        ret._hndl = hndl
        ret._owned = owned
        return ret
    
    cpdef ExprId getName(self):
        if self.asExprAggrStructElem().getName() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asExprAggrStructElem().getName().accept(of._hndl)
            return <ExprId>(of._obj)
    cpdef int32_t getTarget(self):
        return dynamic_cast[ast_decl.IExprAggrStructElemP](self._hndl).getTarget()
    cpdef Expr getValue(self):
        if self.asExprAggrStructElem().getValue() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asExprAggrStructElem().getValue().accept(of._hndl)
            return <Expr>(of._obj)

cdef class MonitorActivitySelectBranch(object):
    
    def __dealloc__(self):
        if self._owned and self._hndl != NULL:
            del self._hndl
            self._hndl = NULL
    
    cpdef void accept(self, VisitorBase v):
        self._hndl.accept(v._hndl)
    
    cpdef int id(self):
        return reinterpret_cast[intptr_t](self._hndl)
    def __hash__(self):
        return reinterpret_cast[intptr_t](self._hndl)
    
    def __eq__(self, o):
        oh = <MonitorActivitySelectBranch>(o)
        return self._hndl == oh._hndl
    
    cdef ast_decl.IMonitorActivitySelectBranch *asMonitorActivitySelectBranch(self):
        return dynamic_cast[ast_decl.IMonitorActivitySelectBranchP](self._hndl)
    @staticmethod
    cdef MonitorActivitySelectBranch mk(ast_decl.IMonitorActivitySelectBranch *hndl, bool owned):
        '''Creates a Python wrapper around native class'''
        ret = MonitorActivitySelectBranch()
        ret._hndl = hndl
        ret._owned = owned
        return ret
    
    cpdef Expr getGuard(self):
        if self.asMonitorActivitySelectBranch().getGuard() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asMonitorActivitySelectBranch().getGuard().accept(of._hndl)
            return <Expr>(of._obj)
    cpdef ScopeChild getBody(self):
        if self.asMonitorActivitySelectBranch().getBody() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asMonitorActivitySelectBranch().getBody().accept(of._hndl)
            return <ScopeChild>(of._obj)

cdef class ScopeChild(object):
    
    def __dealloc__(self):
        if self._owned and self._hndl != NULL:
            del self._hndl
            self._hndl = NULL
    
    cpdef void accept(self, VisitorBase v):
        self._hndl.accept(v._hndl)
    
    cpdef int id(self):
        return reinterpret_cast[intptr_t](self._hndl)
    def __hash__(self):
        return reinterpret_cast[intptr_t](self._hndl)
    
    def __eq__(self, o):
        oh = <ScopeChild>(o)
        return self._hndl == oh._hndl
    
    cdef ast_decl.IScopeChild *asScopeChild(self):
        return dynamic_cast[ast_decl.IScopeChildP](self._hndl)
    @staticmethod
    cdef ScopeChild mk(ast_decl.IScopeChild *hndl, bool owned):
        '''Creates a Python wrapper around native class'''
        ret = ScopeChild()
        ret._hndl = hndl
        ret._owned = owned
        return ret
    
    cpdef str getDocstring(self):
        return dynamic_cast[ast_decl.IScopeChildP](self._hndl).getDocstring().decode()
    cpdef void setDocstring(self, str v):
        dynamic_cast[ast_decl.IScopeChildP](self._hndl).setDocstring(v.encode())
    cpdef Location getLocation(self):
        return Location.wrap(dynamic_cast[ast_decl.IScopeChildP](self._hndl).getLocation())
    cpdef Scope getParent(self):
        if self.asScopeChild().getParent() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asScopeChild().getParent().accept(of._hndl)
            return <Scope>(of._obj)
    cpdef int32_t getIndex(self):
        return dynamic_cast[ast_decl.IScopeChildP](self._hndl).getIndex()
    cpdef AssocData getAssocData(self):
        if self.asScopeChild().getAssocData() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asScopeChild().getAssocData().accept(of._hndl)
            return <AssocData>(of._obj)
    def annotations(self) -> ListUtil:
        return ListUtil(self.numAnnotations, self.getAnnotation)
    
    cpdef getAnnotations(self):
        cdef const std_vector[ast_decl.IAnnotationUP] *__lp = &self.asScopeChild().getAnnotations()
        cdef ast_decl.IAnnotation *__ep;
        ret = []
        of = ObjFactory()
        for __i in range(__lp.size()):
            __ep = __lp.at(__i).get()
            ret.append(__ep.accept(of._hndl))
        return ret
    cpdef getAnnotation(self, i):
        cdef ast_decl.IAnnotation *__ep = self.asScopeChild().getAnnotations().at(i).get();
        of = ObjFactory()
        __ep.accept(of._hndl)
        return of._obj
    cpdef void addAnnotation(self, Annotation i):
        i._owned = False
        self.asScopeChild().getAnnotations().push_back(ast_decl.IAnnotationUP(i.asAnnotation(), True))
    cpdef numAnnotations(self):
        return self.asScopeChild().getAnnotations().size()

cdef class ActivityMatchChoice(object):
    
    def __dealloc__(self):
        if self._owned and self._hndl != NULL:
            del self._hndl
            self._hndl = NULL
    
    cpdef void accept(self, VisitorBase v):
        self._hndl.accept(v._hndl)
    
    cpdef int id(self):
        return reinterpret_cast[intptr_t](self._hndl)
    def __hash__(self):
        return reinterpret_cast[intptr_t](self._hndl)
    
    def __eq__(self, o):
        oh = <ActivityMatchChoice>(o)
        return self._hndl == oh._hndl
    
    cdef ast_decl.IActivityMatchChoice *asActivityMatchChoice(self):
        return dynamic_cast[ast_decl.IActivityMatchChoiceP](self._hndl)
    @staticmethod
    cdef ActivityMatchChoice mk(ast_decl.IActivityMatchChoice *hndl, bool owned):
        '''Creates a Python wrapper around native class'''
        ret = ActivityMatchChoice()
        ret._hndl = hndl
        ret._owned = owned
        return ret
    
    cpdef bool getIs_default(self):
        return dynamic_cast[ast_decl.IActivityMatchChoiceP](self._hndl).getIs_default()
    cpdef ExprOpenRangeList getCond(self):
        if self.asActivityMatchChoice().getCond() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asActivityMatchChoice().getCond().accept(of._hndl)
            return <ExprOpenRangeList>(of._obj)
    cpdef ScopeChild getBody(self):
        if self.asActivityMatchChoice().getBody() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asActivityMatchChoice().getBody().accept(of._hndl)
            return <ScopeChild>(of._obj)

cdef class SymbolImportSpec(object):
    
    def __dealloc__(self):
        if self._owned and self._hndl != NULL:
            del self._hndl
            self._hndl = NULL
    
    cpdef void accept(self, VisitorBase v):
        self._hndl.accept(v._hndl)
    
    cpdef int id(self):
        return reinterpret_cast[intptr_t](self._hndl)
    def __hash__(self):
        return reinterpret_cast[intptr_t](self._hndl)
    
    def __eq__(self, o):
        oh = <SymbolImportSpec>(o)
        return self._hndl == oh._hndl
    
    cdef ast_decl.ISymbolImportSpec *asSymbolImportSpec(self):
        return dynamic_cast[ast_decl.ISymbolImportSpecP](self._hndl)
    @staticmethod
    cdef SymbolImportSpec mk(ast_decl.ISymbolImportSpec *hndl, bool owned):
        '''Creates a Python wrapper around native class'''
        ret = SymbolImportSpec()
        ret._hndl = hndl
        ret._owned = owned
        return ret
    
    def imports(self) -> ListUtil:
        return ListUtil(self.numImports, self.getImport)
    
    cpdef getImports(self):
        cdef const std_vector[ast_decl.IPackageImportStmtP] *__lp = &self.asSymbolImportSpec().getImports()
        cdef ast_decl.IPackageImportStmt *__ep;
        ret = []
        of = ObjFactory()
        for __i in range(__lp.size()):
            __ep = __lp.at(__i)
            ret.append(__ep.accept(of._hndl))
        return ret
    cpdef getImport(self, i):
        cdef ast_decl.IPackageImportStmt *__ep = self.asSymbolImportSpec().getImports().at(i);
        of = ObjFactory()
        __ep.accept(of._hndl)
        return of._obj
    cpdef void addImport(self, PackageImportStmt i):
        self.asSymbolImportSpec().getImports().push_back(i.asPackageImportStmt())
    cpdef numImports(self):
        return self.asSymbolImportSpec().getImports().size()
    cpdef bool symtabHas(self, str i):
        cdef std_unordered_map[std_string,ast_decl.UP[ast_decl.ISymbolRefPath]].const_iterator it = self.asSymbolImportSpec().getSymtab().find(i.encode())
        return (it != self.asSymbolImportSpec().getSymtab().end())
    cpdef SymbolRefPath symtabAt(self, str i):
        cdef std_unordered_map[std_string,ast_decl.UP[ast_decl.ISymbolRefPath]].const_iterator it = self.asSymbolImportSpec().getSymtab().find(i.encode())
        _obj_f = ObjFactory()
        dereference(it).second.get().accept(_obj_f._hndl)
        return _obj_f._obj

cdef class SymbolRefPath(object):
    
    def __dealloc__(self):
        if self._owned and self._hndl != NULL:
            del self._hndl
            self._hndl = NULL
    
    cpdef void accept(self, VisitorBase v):
        self._hndl.accept(v._hndl)
    
    cpdef int id(self):
        return reinterpret_cast[intptr_t](self._hndl)
    def __hash__(self):
        return reinterpret_cast[intptr_t](self._hndl)
    
    def __eq__(self, o):
        oh = <SymbolRefPath>(o)
        return self._hndl == oh._hndl
    
    cdef ast_decl.ISymbolRefPath *asSymbolRefPath(self):
        return dynamic_cast[ast_decl.ISymbolRefPathP](self._hndl)
    @staticmethod
    cdef SymbolRefPath mk(ast_decl.ISymbolRefPath *hndl, bool owned):
        '''Creates a Python wrapper around native class'''
        ret = SymbolRefPath()
        ret._hndl = hndl
        ret._owned = owned
        return ret
    
    def path(self) -> ListUtil:
        return ListUtil(self.numPath, self.getPath)
    
    cpdef int32_t getPyref_idx(self):
        return dynamic_cast[ast_decl.ISymbolRefPathP](self._hndl).getPyref_idx()

cdef class ActivitySelectBranch(object):
    
    def __dealloc__(self):
        if self._owned and self._hndl != NULL:
            del self._hndl
            self._hndl = NULL
    
    cpdef void accept(self, VisitorBase v):
        self._hndl.accept(v._hndl)
    
    cpdef int id(self):
        return reinterpret_cast[intptr_t](self._hndl)
    def __hash__(self):
        return reinterpret_cast[intptr_t](self._hndl)
    
    def __eq__(self, o):
        oh = <ActivitySelectBranch>(o)
        return self._hndl == oh._hndl
    
    cdef ast_decl.IActivitySelectBranch *asActivitySelectBranch(self):
        return dynamic_cast[ast_decl.IActivitySelectBranchP](self._hndl)
    @staticmethod
    cdef ActivitySelectBranch mk(ast_decl.IActivitySelectBranch *hndl, bool owned):
        '''Creates a Python wrapper around native class'''
        ret = ActivitySelectBranch()
        ret._hndl = hndl
        ret._owned = owned
        return ret
    
    cpdef Expr getGuard(self):
        if self.asActivitySelectBranch().getGuard() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asActivitySelectBranch().getGuard().accept(of._hndl)
            return <Expr>(of._obj)
    cpdef Expr getWeight(self):
        if self.asActivitySelectBranch().getWeight() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asActivitySelectBranch().getWeight().accept(of._hndl)
            return <Expr>(of._obj)
    cpdef ScopeChild getBody(self):
        if self.asActivitySelectBranch().getBody() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asActivitySelectBranch().getBody().accept(of._hndl)
            return <ScopeChild>(of._obj)

cdef class ActionFieldInitializer(ScopeChild):
    
    cdef ast_decl.IActionFieldInitializer *asActionFieldInitializer(self):
        return dynamic_cast[ast_decl.IActionFieldInitializerP](self._hndl)
    @staticmethod
    cdef ActionFieldInitializer mk(ast_decl.IActionFieldInitializer *hndl, bool owned):
        '''Creates a Python wrapper around native class'''
        ret = ActionFieldInitializer()
        ret._hndl = hndl
        ret._owned = owned
        return ret
    
    cpdef ExprHierarchicalId getPath(self):
        if self.asActionFieldInitializer().getPath() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asActionFieldInitializer().getPath().accept(of._hndl)
            return <ExprHierarchicalId>(of._obj)
    cpdef Expr getValue(self):
        if self.asActionFieldInitializer().getValue() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asActionFieldInitializer().getValue().accept(of._hndl)
            return <Expr>(of._obj)

cdef class ActivityJoinSpec(ScopeChild):
    
    cdef ast_decl.IActivityJoinSpec *asActivityJoinSpec(self):
        return dynamic_cast[ast_decl.IActivityJoinSpecP](self._hndl)
    @staticmethod
    cdef ActivityJoinSpec mk(ast_decl.IActivityJoinSpec *hndl, bool owned):
        '''Creates a Python wrapper around native class'''
        ret = ActivityJoinSpec()
        ret._hndl = hndl
        ret._owned = owned
        return ret
    

cdef class MonitorActivityStmt(ScopeChild):
    
    cdef ast_decl.IMonitorActivityStmt *asMonitorActivityStmt(self):
        return dynamic_cast[ast_decl.IMonitorActivityStmtP](self._hndl)
    @staticmethod
    cdef MonitorActivityStmt mk(ast_decl.IMonitorActivityStmt *hndl, bool owned):
        '''Creates a Python wrapper around native class'''
        ret = MonitorActivityStmt()
        ret._hndl = hndl
        ret._owned = owned
        return ret
    

cdef class NamedScopeChild(ScopeChild):
    
    cdef ast_decl.INamedScopeChild *asNamedScopeChild(self):
        return dynamic_cast[ast_decl.INamedScopeChildP](self._hndl)
    @staticmethod
    cdef NamedScopeChild mk(ast_decl.INamedScopeChild *hndl, bool owned):
        '''Creates a Python wrapper around native class'''
        ret = NamedScopeChild()
        ret._hndl = hndl
        ret._owned = owned
        return ret
    
    cpdef ExprId getName(self):
        if self.asNamedScopeChild().getName() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asNamedScopeChild().getName().accept(of._hndl)
            return <ExprId>(of._obj)

cdef class PackageImportStmt(ScopeChild):
    
    cdef ast_decl.IPackageImportStmt *asPackageImportStmt(self):
        return dynamic_cast[ast_decl.IPackageImportStmtP](self._hndl)
    @staticmethod
    cdef PackageImportStmt mk(ast_decl.IPackageImportStmt *hndl, bool owned):
        '''Creates a Python wrapper around native class'''
        ret = PackageImportStmt()
        ret._hndl = hndl
        ret._owned = owned
        return ret
    
    cpdef bool getWildcard(self):
        return dynamic_cast[ast_decl.IPackageImportStmtP](self._hndl).getWildcard()
    cpdef ExprId getAlias(self):
        if self.asPackageImportStmt().getAlias() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asPackageImportStmt().getAlias().accept(of._hndl)
            return <ExprId>(of._obj)
    cpdef TypeIdentifier getPath(self):
        if self.asPackageImportStmt().getPath() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asPackageImportStmt().getPath().accept(of._hndl)
            return <TypeIdentifier>(of._obj)

cdef class ActivitySchedulingConstraint(ScopeChild):
    
    cdef ast_decl.IActivitySchedulingConstraint *asActivitySchedulingConstraint(self):
        return dynamic_cast[ast_decl.IActivitySchedulingConstraintP](self._hndl)
    @staticmethod
    cdef ActivitySchedulingConstraint mk(ast_decl.IActivitySchedulingConstraint *hndl, bool owned):
        '''Creates a Python wrapper around native class'''
        ret = ActivitySchedulingConstraint()
        ret._hndl = hndl
        ret._owned = owned
        return ret
    
    cpdef bool getIs_parallel(self):
        return dynamic_cast[ast_decl.IActivitySchedulingConstraintP](self._hndl).getIs_parallel()
    def targets(self) -> ListUtil:
        return ListUtil(self.numTargets, self.getTarget)
    
    cpdef getTargets(self):
        cdef const std_vector[ast_decl.IExprHierarchicalIdUP] *__lp = &self.asActivitySchedulingConstraint().getTargets()
        cdef ast_decl.IExprHierarchicalId *__ep;
        ret = []
        of = ObjFactory()
        for __i in range(__lp.size()):
            __ep = __lp.at(__i).get()
            ret.append(__ep.accept(of._hndl))
        return ret
    cpdef getTarget(self, i):
        cdef ast_decl.IExprHierarchicalId *__ep = self.asActivitySchedulingConstraint().getTargets().at(i).get();
        of = ObjFactory()
        __ep.accept(of._hndl)
        return of._obj
    cpdef void addTarget(self, ExprHierarchicalId i):
        i._owned = False
        self.asActivitySchedulingConstraint().getTargets().push_back(ast_decl.IExprHierarchicalIdUP(i.asExprHierarchicalId(), True))
    cpdef numTargets(self):
        return self.asActivitySchedulingConstraint().getTargets().size()

cdef class ActivityStmt(ScopeChild):
    
    cdef ast_decl.IActivityStmt *asActivityStmt(self):
        return dynamic_cast[ast_decl.IActivityStmtP](self._hndl)
    @staticmethod
    cdef ActivityStmt mk(ast_decl.IActivityStmt *hndl, bool owned):
        '''Creates a Python wrapper around native class'''
        ret = ActivityStmt()
        ret._hndl = hndl
        ret._owned = owned
        return ret
    

cdef class ProceduralStmtIfClause(ScopeChild):
    
    cdef ast_decl.IProceduralStmtIfClause *asProceduralStmtIfClause(self):
        return dynamic_cast[ast_decl.IProceduralStmtIfClauseP](self._hndl)
    @staticmethod
    cdef ProceduralStmtIfClause mk(ast_decl.IProceduralStmtIfClause *hndl, bool owned):
        '''Creates a Python wrapper around native class'''
        ret = ProceduralStmtIfClause()
        ret._hndl = hndl
        ret._owned = owned
        return ret
    
    cpdef Expr getCond(self):
        if self.asProceduralStmtIfClause().getCond() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asProceduralStmtIfClause().getCond().accept(of._hndl)
            return <Expr>(of._obj)
    cpdef ScopeChild getBody(self):
        if self.asProceduralStmtIfClause().getBody() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asProceduralStmtIfClause().getBody().accept(of._hndl)
            return <ScopeChild>(of._obj)

cdef class Annotation(ScopeChild):
    
    cdef ast_decl.IAnnotation *asAnnotation(self):
        return dynamic_cast[ast_decl.IAnnotationP](self._hndl)
    @staticmethod
    cdef Annotation mk(ast_decl.IAnnotation *hndl, bool owned):
        '''Creates a Python wrapper around native class'''
        ret = Annotation()
        ret._hndl = hndl
        ret._owned = owned
        return ret
    
    cpdef TypeIdentifier getType(self):
        if self.asAnnotation().getType() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asAnnotation().getType().accept(of._hndl)
            return <TypeIdentifier>(of._obj)
    def parameters(self) -> ListUtil:
        return ListUtil(self.numParameters, self.getParameter)
    
    cpdef getParameters(self):
        cdef const std_vector[ast_decl.IAnnotationParamUP] *__lp = &self.asAnnotation().getParameters()
        cdef ast_decl.IAnnotationParam *__ep;
        ret = []
        of = ObjFactory()
        for __i in range(__lp.size()):
            __ep = __lp.at(__i).get()
            ret.append(__ep.accept(of._hndl))
        return ret
    cpdef getParameter(self, i):
        cdef ast_decl.IAnnotationParam *__ep = self.asAnnotation().getParameters().at(i).get();
        of = ObjFactory()
        __ep.accept(of._hndl)
        return of._obj
    cpdef void addParameter(self, AnnotationParam i):
        i._owned = False
        self.asAnnotation().getParameters().push_back(ast_decl.IAnnotationParamUP(i.asAnnotationParam(), True))
    cpdef numParameters(self):
        return self.asAnnotation().getParameters().size()

cdef class AnnotationParam(ScopeChild):
    
    cdef ast_decl.IAnnotationParam *asAnnotationParam(self):
        return dynamic_cast[ast_decl.IAnnotationParamP](self._hndl)
    @staticmethod
    cdef AnnotationParam mk(ast_decl.IAnnotationParam *hndl, bool owned):
        '''Creates a Python wrapper around native class'''
        ret = AnnotationParam()
        ret._hndl = hndl
        ret._owned = owned
        return ret
    
    cpdef ExprId getName(self):
        if self.asAnnotationParam().getName() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asAnnotationParam().getName().accept(of._hndl)
            return <ExprId>(of._obj)
    cpdef Expr getValue(self):
        if self.asAnnotationParam().getValue() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asAnnotationParam().getValue().accept(of._hndl)
            return <Expr>(of._obj)

cdef class ConstraintStmt(ScopeChild):
    
    cdef ast_decl.IConstraintStmt *asConstraintStmt(self):
        return dynamic_cast[ast_decl.IConstraintStmtP](self._hndl)
    @staticmethod
    cdef ConstraintStmt mk(ast_decl.IConstraintStmt *hndl, bool owned):
        '''Creates a Python wrapper around native class'''
        ret = ConstraintStmt()
        ret._hndl = hndl
        ret._owned = owned
        return ret
    

cdef class PyImportFromStmt(ScopeChild):
    
    cdef ast_decl.IPyImportFromStmt *asPyImportFromStmt(self):
        return dynamic_cast[ast_decl.IPyImportFromStmtP](self._hndl)
    @staticmethod
    cdef PyImportFromStmt mk(ast_decl.IPyImportFromStmt *hndl, bool owned):
        '''Creates a Python wrapper around native class'''
        ret = PyImportFromStmt()
        ret._hndl = hndl
        ret._owned = owned
        return ret
    
    def path(self) -> ListUtil:
        return ListUtil(self.numPath, self.getPath)
    
    cpdef getPathList(self):
        cdef const std_vector[ast_decl.IExprIdUP] *__lp = &self.asPyImportFromStmt().getPath()
        cdef ast_decl.IExprId *__ep;
        ret = []
        of = ObjFactory()
        for __i in range(__lp.size()):
            __ep = __lp.at(__i).get()
            ret.append(__ep.accept(of._hndl))
        return ret
    cpdef getPath(self, i):
        cdef ast_decl.IExprId *__ep = self.asPyImportFromStmt().getPath().at(i).get();
        of = ObjFactory()
        __ep.accept(of._hndl)
        return of._obj
    cpdef void addPath(self, ExprId i):
        i._owned = False
        self.asPyImportFromStmt().getPath().push_back(ast_decl.IExprIdUP(i.asExprId(), True))
    cpdef numPath(self):
        return self.asPyImportFromStmt().getPath().size()
    def targets(self) -> ListUtil:
        return ListUtil(self.numTargets, self.getTarget)
    
    cpdef getTargets(self):
        cdef const std_vector[ast_decl.IExprIdUP] *__lp = &self.asPyImportFromStmt().getTargets()
        cdef ast_decl.IExprId *__ep;
        ret = []
        of = ObjFactory()
        for __i in range(__lp.size()):
            __ep = __lp.at(__i).get()
            ret.append(__ep.accept(of._hndl))
        return ret
    cpdef getTarget(self, i):
        cdef ast_decl.IExprId *__ep = self.asPyImportFromStmt().getTargets().at(i).get();
        of = ObjFactory()
        __ep.accept(of._hndl)
        return of._obj
    cpdef void addTarget(self, ExprId i):
        i._owned = False
        self.asPyImportFromStmt().getTargets().push_back(ast_decl.IExprIdUP(i.asExprId(), True))
    cpdef numTargets(self):
        return self.asPyImportFromStmt().getTargets().size()

cdef class PyImportStmt(ScopeChild):
    
    cdef ast_decl.IPyImportStmt *asPyImportStmt(self):
        return dynamic_cast[ast_decl.IPyImportStmtP](self._hndl)
    @staticmethod
    cdef PyImportStmt mk(ast_decl.IPyImportStmt *hndl, bool owned):
        '''Creates a Python wrapper around native class'''
        ret = PyImportStmt()
        ret._hndl = hndl
        ret._owned = owned
        return ret
    
    def path(self) -> ListUtil:
        return ListUtil(self.numPath, self.getPath)
    
    cpdef getPathList(self):
        cdef const std_vector[ast_decl.IExprIdUP] *__lp = &self.asPyImportStmt().getPath()
        cdef ast_decl.IExprId *__ep;
        ret = []
        of = ObjFactory()
        for __i in range(__lp.size()):
            __ep = __lp.at(__i).get()
            ret.append(__ep.accept(of._hndl))
        return ret
    cpdef getPath(self, i):
        cdef ast_decl.IExprId *__ep = self.asPyImportStmt().getPath().at(i).get();
        of = ObjFactory()
        __ep.accept(of._hndl)
        return of._obj
    cpdef void addPath(self, ExprId i):
        i._owned = False
        self.asPyImportStmt().getPath().push_back(ast_decl.IExprIdUP(i.asExprId(), True))
    cpdef numPath(self):
        return self.asPyImportStmt().getPath().size()
    cpdef ExprId getAlias(self):
        if self.asPyImportStmt().getAlias() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asPyImportStmt().getAlias().accept(of._hndl)
            return <ExprId>(of._obj)

cdef class RefExprScopeIndex(RefExpr):
    
    cdef ast_decl.IRefExprScopeIndex *asRefExprScopeIndex(self):
        return dynamic_cast[ast_decl.IRefExprScopeIndexP](self._hndl)
    @staticmethod
    cdef RefExprScopeIndex mk(ast_decl.IRefExprScopeIndex *hndl, bool owned):
        '''Creates a Python wrapper around native class'''
        ret = RefExprScopeIndex()
        ret._hndl = hndl
        ret._owned = owned
        return ret
    
    cpdef RefExpr getBase(self):
        if self.asRefExprScopeIndex().getBase() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asRefExprScopeIndex().getBase().accept(of._hndl)
            return <RefExpr>(of._obj)
    cpdef int32_t getOffset(self):
        return dynamic_cast[ast_decl.IRefExprScopeIndexP](self._hndl).getOffset()

cdef class RefExprTypeScopeContext(RefExpr):
    
    cdef ast_decl.IRefExprTypeScopeContext *asRefExprTypeScopeContext(self):
        return dynamic_cast[ast_decl.IRefExprTypeScopeContextP](self._hndl)
    @staticmethod
    cdef RefExprTypeScopeContext mk(ast_decl.IRefExprTypeScopeContext *hndl, bool owned):
        '''Creates a Python wrapper around native class'''
        ret = RefExprTypeScopeContext()
        ret._hndl = hndl
        ret._owned = owned
        return ret
    
    cpdef RefExpr getBase(self):
        if self.asRefExprTypeScopeContext().getBase() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asRefExprTypeScopeContext().getBase().accept(of._hndl)
            return <RefExpr>(of._obj)
    cpdef int32_t getOffset(self):
        return dynamic_cast[ast_decl.IRefExprTypeScopeContextP](self._hndl).getOffset()

cdef class RefExprTypeScopeGlobal(RefExpr):
    
    cdef ast_decl.IRefExprTypeScopeGlobal *asRefExprTypeScopeGlobal(self):
        return dynamic_cast[ast_decl.IRefExprTypeScopeGlobalP](self._hndl)
    @staticmethod
    cdef RefExprTypeScopeGlobal mk(ast_decl.IRefExprTypeScopeGlobal *hndl, bool owned):
        '''Creates a Python wrapper around native class'''
        ret = RefExprTypeScopeGlobal()
        ret._hndl = hndl
        ret._owned = owned
        return ret
    
    cpdef int32_t getFileid(self):
        return dynamic_cast[ast_decl.IRefExprTypeScopeGlobalP](self._hndl).getFileid()

cdef class Scope(ScopeChild):
    
    cdef ast_decl.IScope *asScope(self):
        return dynamic_cast[ast_decl.IScopeP](self._hndl)
    @staticmethod
    cdef Scope mk(ast_decl.IScope *hndl, bool owned):
        '''Creates a Python wrapper around native class'''
        ret = Scope()
        ret._hndl = hndl
        ret._owned = owned
        return ret
    
    cpdef Location getEndLocation(self):
        return Location.wrap(dynamic_cast[ast_decl.IScopeP](self._hndl).getEndLocation())
    def children(self) -> ListUtil:
        return ListUtil(self.numChildren, self.getChild)
    
    cpdef getChildren(self):
        cdef const std_vector[ast_decl.IScopeChildUP] *__lp = &self.asScope().getChildren()
        cdef ast_decl.IScopeChild *__ep;
        ret = []
        of = ObjFactory()
        for __i in range(__lp.size()):
            __ep = __lp.at(__i).get()
            ret.append(__ep.accept(of._hndl))
        return ret
    cpdef getChild(self, i):
        cdef ast_decl.IScopeChild *__ep = self.asScope().getChildren().at(i).get();
        of = ObjFactory()
        __ep.accept(of._hndl)
        return of._obj
    cpdef void addChild(self, ScopeChild i):
        i._owned = False
        self.asScope().getChildren().push_back(ast_decl.IScopeChildUP(i.asScopeChild(), True))
    cpdef numChildren(self):
        return self.asScope().getChildren().size()

cdef class CoverStmtInline(ScopeChild):
    
    cdef ast_decl.ICoverStmtInline *asCoverStmtInline(self):
        return dynamic_cast[ast_decl.ICoverStmtInlineP](self._hndl)
    @staticmethod
    cdef CoverStmtInline mk(ast_decl.ICoverStmtInline *hndl, bool owned):
        '''Creates a Python wrapper around native class'''
        ret = CoverStmtInline()
        ret._hndl = hndl
        ret._owned = owned
        return ret
    
    cpdef ScopeChild getBody(self):
        if self.asCoverStmtInline().getBody() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asCoverStmtInline().getBody().accept(of._hndl)
            return <ScopeChild>(of._obj)

cdef class CoverStmtReference(ScopeChild):
    
    cdef ast_decl.ICoverStmtReference *asCoverStmtReference(self):
        return dynamic_cast[ast_decl.ICoverStmtReferenceP](self._hndl)
    @staticmethod
    cdef CoverStmtReference mk(ast_decl.ICoverStmtReference *hndl, bool owned):
        '''Creates a Python wrapper around native class'''
        ret = CoverStmtReference()
        ret._hndl = hndl
        ret._owned = owned
        return ret
    
    cpdef ExprRefPath getTarget(self):
        if self.asCoverStmtReference().getTarget() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asCoverStmtReference().getTarget().accept(of._hndl)
            return <ExprRefPath>(of._obj)

cdef class DataType(ScopeChild):
    
    cdef ast_decl.IDataType *asDataType(self):
        return dynamic_cast[ast_decl.IDataTypeP](self._hndl)
    @staticmethod
    cdef DataType mk(ast_decl.IDataType *hndl, bool owned):
        '''Creates a Python wrapper around native class'''
        ret = DataType()
        ret._hndl = hndl
        ret._owned = owned
        return ret
    

cdef class ScopeChildRef(ScopeChild):
    
    cdef ast_decl.IScopeChildRef *asScopeChildRef(self):
        return dynamic_cast[ast_decl.IScopeChildRefP](self._hndl)
    @staticmethod
    cdef ScopeChildRef mk(ast_decl.IScopeChildRef *hndl, bool owned):
        '''Creates a Python wrapper around native class'''
        ret = ScopeChildRef()
        ret._hndl = hndl
        ret._owned = owned
        return ret
    
    cpdef ScopeChild getTarget(self):
        if self.asScopeChildRef().getTarget() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asScopeChildRef().getTarget().accept(of._hndl)
            return <ScopeChild>(of._obj)

cdef class SymbolChild(ScopeChild):
    
    cdef ast_decl.ISymbolChild *asSymbolChild(self):
        return dynamic_cast[ast_decl.ISymbolChildP](self._hndl)
    @staticmethod
    cdef SymbolChild mk(ast_decl.ISymbolChild *hndl, bool owned):
        '''Creates a Python wrapper around native class'''
        ret = SymbolChild()
        ret._hndl = hndl
        ret._owned = owned
        return ret
    
    cpdef int32_t getId(self):
        return dynamic_cast[ast_decl.ISymbolChildP](self._hndl).getId()
    cpdef SymbolScope getUpper(self):
        if self.asSymbolChild().getUpper() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asSymbolChild().getUpper().accept(of._hndl)
            return <SymbolScope>(of._obj)

cdef class SymbolScopeRef(ScopeChild):
    
    cdef ast_decl.ISymbolScopeRef *asSymbolScopeRef(self):
        return dynamic_cast[ast_decl.ISymbolScopeRefP](self._hndl)
    @staticmethod
    cdef SymbolScopeRef mk(ast_decl.ISymbolScopeRef *hndl, bool owned):
        '''Creates a Python wrapper around native class'''
        ret = SymbolScopeRef()
        ret._hndl = hndl
        ret._owned = owned
        return ret
    
    cpdef str getName(self):
        return dynamic_cast[ast_decl.ISymbolScopeRefP](self._hndl).getName().decode()
    cpdef void setName(self, str v):
        dynamic_cast[ast_decl.ISymbolScopeRefP](self._hndl).setName(v.encode())

cdef class TemplateParamDecl(ScopeChild):
    
    cdef ast_decl.ITemplateParamDecl *asTemplateParamDecl(self):
        return dynamic_cast[ast_decl.ITemplateParamDeclP](self._hndl)
    @staticmethod
    cdef TemplateParamDecl mk(ast_decl.ITemplateParamDecl *hndl, bool owned):
        '''Creates a Python wrapper around native class'''
        ret = TemplateParamDecl()
        ret._hndl = hndl
        ret._owned = owned
        return ret
    
    cpdef ExprId getName(self):
        if self.asTemplateParamDecl().getName() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asTemplateParamDecl().getName().accept(of._hndl)
            return <ExprId>(of._obj)

cdef class ExecStmt(ScopeChild):
    
    cdef ast_decl.IExecStmt *asExecStmt(self):
        return dynamic_cast[ast_decl.IExecStmtP](self._hndl)
    @staticmethod
    cdef ExecStmt mk(ast_decl.IExecStmt *hndl, bool owned):
        '''Creates a Python wrapper around native class'''
        ret = ExecStmt()
        ret._hndl = hndl
        ret._owned = owned
        return ret
    
    cpdef SymbolScope getUpper(self):
        if self.asExecStmt().getUpper() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asExecStmt().getUpper().accept(of._hndl)
            return <SymbolScope>(of._obj)

cdef class ExecTargetTemplateBlock(ScopeChild):
    
    cdef ast_decl.IExecTargetTemplateBlock *asExecTargetTemplateBlock(self):
        return dynamic_cast[ast_decl.IExecTargetTemplateBlockP](self._hndl)
    @staticmethod
    cdef ExecTargetTemplateBlock mk(ast_decl.IExecTargetTemplateBlock *hndl, bool owned):
        '''Creates a Python wrapper around native class'''
        ret = ExecTargetTemplateBlock()
        ret._hndl = hndl
        ret._owned = owned
        return ret
    
    cpdef  getKind(self):
        return dynamic_cast[ast_decl.IExecTargetTemplateBlockP](self._hndl).getKind()
    cpdef str getData(self):
        return dynamic_cast[ast_decl.IExecTargetTemplateBlockP](self._hndl).getData().decode()
    cpdef void setData(self, str v):
        dynamic_cast[ast_decl.IExecTargetTemplateBlockP](self._hndl).setData(v.encode())
    def parameters(self) -> ListUtil:
        return ListUtil(self.numParameters, self.getParameter)
    
    cpdef getParameters(self):
        cdef const std_vector[ast_decl.IExecTargetTemplateParamUP] *__lp = &self.asExecTargetTemplateBlock().getParameters()
        cdef ast_decl.IExecTargetTemplateParam *__ep;
        ret = []
        of = ObjFactory()
        for __i in range(__lp.size()):
            __ep = __lp.at(__i).get()
            ret.append(__ep.accept(of._hndl))
        return ret
    cpdef getParameter(self, i):
        cdef ast_decl.IExecTargetTemplateParam *__ep = self.asExecTargetTemplateBlock().getParameters().at(i).get();
        of = ObjFactory()
        __ep.accept(of._hndl)
        return of._obj
    cpdef void addParameter(self, ExecTargetTemplateParam i):
        i._owned = False
        self.asExecTargetTemplateBlock().getParameters().push_back(ast_decl.IExecTargetTemplateParamUP(i.asExecTargetTemplateParam(), True))
    cpdef numParameters(self):
        return self.asExecTargetTemplateBlock().getParameters().size()

cdef class TemplateParamExprValue(TemplateParamValue):
    
    cdef ast_decl.ITemplateParamExprValue *asTemplateParamExprValue(self):
        return dynamic_cast[ast_decl.ITemplateParamExprValueP](self._hndl)
    @staticmethod
    cdef TemplateParamExprValue mk(ast_decl.ITemplateParamExprValue *hndl, bool owned):
        '''Creates a Python wrapper around native class'''
        ret = TemplateParamExprValue()
        ret._hndl = hndl
        ret._owned = owned
        return ret
    
    cpdef Expr getValue(self):
        if self.asTemplateParamExprValue().getValue() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asTemplateParamExprValue().getValue().accept(of._hndl)
            return <Expr>(of._obj)

cdef class ExportFunction(ScopeChild):
    
    cdef ast_decl.IExportFunction *asExportFunction(self):
        return dynamic_cast[ast_decl.IExportFunctionP](self._hndl)
    @staticmethod
    cdef ExportFunction mk(ast_decl.IExportFunction *hndl, bool owned):
        '''Creates a Python wrapper around native class'''
        ret = ExportFunction()
        ret._hndl = hndl
        ret._owned = owned
        return ret
    
    cpdef  getPlat(self):
        return dynamic_cast[ast_decl.IExportFunctionP](self._hndl).getPlat()
    cpdef ExprId getName(self):
        if self.asExportFunction().getName() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asExportFunction().getName().accept(of._hndl)
            return <ExprId>(of._obj)

cdef class TemplateParamTypeValue(TemplateParamValue):
    
    cdef ast_decl.ITemplateParamTypeValue *asTemplateParamTypeValue(self):
        return dynamic_cast[ast_decl.ITemplateParamTypeValueP](self._hndl)
    @staticmethod
    cdef TemplateParamTypeValue mk(ast_decl.ITemplateParamTypeValue *hndl, bool owned):
        '''Creates a Python wrapper around native class'''
        ret = TemplateParamTypeValue()
        ret._hndl = hndl
        ret._owned = owned
        return ret
    
    cpdef DataType getValue(self):
        if self.asTemplateParamTypeValue().getValue() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asTemplateParamTypeValue().getValue().accept(of._hndl)
            return <DataType>(of._obj)

cdef class TypeIdentifier(Expr):
    
    cdef ast_decl.ITypeIdentifier *asTypeIdentifier(self):
        return dynamic_cast[ast_decl.ITypeIdentifierP](self._hndl)
    @staticmethod
    cdef TypeIdentifier mk(ast_decl.ITypeIdentifier *hndl, bool owned):
        '''Creates a Python wrapper around native class'''
        ret = TypeIdentifier()
        ret._hndl = hndl
        ret._owned = owned
        return ret
    
    def elems(self) -> ListUtil:
        return ListUtil(self.numElems, self.getElem)
    
    cpdef getElems(self):
        cdef const std_vector[ast_decl.ITypeIdentifierElemUP] *__lp = &self.asTypeIdentifier().getElems()
        cdef ast_decl.ITypeIdentifierElem *__ep;
        ret = []
        of = ObjFactory()
        for __i in range(__lp.size()):
            __ep = __lp.at(__i).get()
            ret.append(__ep.accept(of._hndl))
        return ret
    cpdef getElem(self, i):
        cdef ast_decl.ITypeIdentifierElem *__ep = self.asTypeIdentifier().getElems().at(i).get();
        of = ObjFactory()
        __ep.accept(of._hndl)
        return of._obj
    cpdef void addElem(self, TypeIdentifierElem i):
        i._owned = False
        self.asTypeIdentifier().getElems().push_back(ast_decl.ITypeIdentifierElemUP(i.asTypeIdentifierElem(), True))
    cpdef numElems(self):
        return self.asTypeIdentifier().getElems().size()
    cpdef SymbolRefPath getTarget(self):
        if self.asTypeIdentifier().getTarget() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asTypeIdentifier().getTarget().accept(of._hndl)
            return <SymbolRefPath>(of._obj)

cdef class ExprAggrLiteral(Expr):
    
    cdef ast_decl.IExprAggrLiteral *asExprAggrLiteral(self):
        return dynamic_cast[ast_decl.IExprAggrLiteralP](self._hndl)
    @staticmethod
    cdef ExprAggrLiteral mk(ast_decl.IExprAggrLiteral *hndl, bool owned):
        '''Creates a Python wrapper around native class'''
        ret = ExprAggrLiteral()
        ret._hndl = hndl
        ret._owned = owned
        return ret
    

cdef class TypeIdentifierElem(Expr):
    
    cdef ast_decl.ITypeIdentifierElem *asTypeIdentifierElem(self):
        return dynamic_cast[ast_decl.ITypeIdentifierElemP](self._hndl)
    @staticmethod
    cdef TypeIdentifierElem mk(ast_decl.ITypeIdentifierElem *hndl, bool owned):
        '''Creates a Python wrapper around native class'''
        ret = TypeIdentifierElem()
        ret._hndl = hndl
        ret._owned = owned
        return ret
    
    cpdef ExprId getId(self):
        if self.asTypeIdentifierElem().getId() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asTypeIdentifierElem().getId().accept(of._hndl)
            return <ExprId>(of._obj)
    cpdef TemplateParamValueList getParams(self):
        if self.asTypeIdentifierElem().getParams() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asTypeIdentifierElem().getParams().accept(of._hndl)
            return <TemplateParamValueList>(of._obj)

cdef class TypedefDeclaration(ScopeChild):
    
    cdef ast_decl.ITypedefDeclaration *asTypedefDeclaration(self):
        return dynamic_cast[ast_decl.ITypedefDeclarationP](self._hndl)
    @staticmethod
    cdef TypedefDeclaration mk(ast_decl.ITypedefDeclaration *hndl, bool owned):
        '''Creates a Python wrapper around native class'''
        ret = TypedefDeclaration()
        ret._hndl = hndl
        ret._owned = owned
        return ret
    
    cpdef ExprId getName(self):
        if self.asTypedefDeclaration().getName() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asTypedefDeclaration().getName().accept(of._hndl)
            return <ExprId>(of._obj)
    cpdef DataType getType(self):
        if self.asTypedefDeclaration().getType() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asTypedefDeclaration().getType().accept(of._hndl)
            return <DataType>(of._obj)

cdef class ExprBin(Expr):
    
    cdef ast_decl.IExprBin *asExprBin(self):
        return dynamic_cast[ast_decl.IExprBinP](self._hndl)
    @staticmethod
    cdef ExprBin mk(ast_decl.IExprBin *hndl, bool owned):
        '''Creates a Python wrapper around native class'''
        ret = ExprBin()
        ret._hndl = hndl
        ret._owned = owned
        return ret
    
    cpdef Expr getLhs(self):
        if self.asExprBin().getLhs() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asExprBin().getLhs().accept(of._hndl)
            return <Expr>(of._obj)
    cpdef  getOp(self):
        return dynamic_cast[ast_decl.IExprBinP](self._hndl).getOp()
    cpdef Expr getRhs(self):
        if self.asExprBin().getRhs() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asExprBin().getRhs().accept(of._hndl)
            return <Expr>(of._obj)

cdef class ExprBitSlice(Expr):
    
    cdef ast_decl.IExprBitSlice *asExprBitSlice(self):
        return dynamic_cast[ast_decl.IExprBitSliceP](self._hndl)
    @staticmethod
    cdef ExprBitSlice mk(ast_decl.IExprBitSlice *hndl, bool owned):
        '''Creates a Python wrapper around native class'''
        ret = ExprBitSlice()
        ret._hndl = hndl
        ret._owned = owned
        return ret
    
    cpdef Expr getLhs(self):
        if self.asExprBitSlice().getLhs() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asExprBitSlice().getLhs().accept(of._hndl)
            return <Expr>(of._obj)
    cpdef Expr getRhs(self):
        if self.asExprBitSlice().getRhs() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asExprBitSlice().getRhs().accept(of._hndl)
            return <Expr>(of._obj)

cdef class ExprBool(Expr):
    
    cdef ast_decl.IExprBool *asExprBool(self):
        return dynamic_cast[ast_decl.IExprBoolP](self._hndl)
    @staticmethod
    cdef ExprBool mk(ast_decl.IExprBool *hndl, bool owned):
        '''Creates a Python wrapper around native class'''
        ret = ExprBool()
        ret._hndl = hndl
        ret._owned = owned
        return ret
    
    cpdef bool getValue(self):
        return dynamic_cast[ast_decl.IExprBoolP](self._hndl).getValue()

cdef class ExprCast(Expr):
    
    cdef ast_decl.IExprCast *asExprCast(self):
        return dynamic_cast[ast_decl.IExprCastP](self._hndl)
    @staticmethod
    cdef ExprCast mk(ast_decl.IExprCast *hndl, bool owned):
        '''Creates a Python wrapper around native class'''
        ret = ExprCast()
        ret._hndl = hndl
        ret._owned = owned
        return ret
    
    cpdef DataType getCasting_type(self):
        if self.asExprCast().getCasting_type() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asExprCast().getCasting_type().accept(of._hndl)
            return <DataType>(of._obj)
    cpdef Expr getExpr(self):
        if self.asExprCast().getExpr() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asExprCast().getExpr().accept(of._hndl)
            return <Expr>(of._obj)

cdef class ExprCompileHas(Expr):
    
    cdef ast_decl.IExprCompileHas *asExprCompileHas(self):
        return dynamic_cast[ast_decl.IExprCompileHasP](self._hndl)
    @staticmethod
    cdef ExprCompileHas mk(ast_decl.IExprCompileHas *hndl, bool owned):
        '''Creates a Python wrapper around native class'''
        ret = ExprCompileHas()
        ret._hndl = hndl
        ret._owned = owned
        return ret
    
    cpdef ExprRefPathStatic getRef(self):
        if self.asExprCompileHas().getRef() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asExprCompileHas().getRef().accept(of._hndl)
            return <ExprRefPathStatic>(of._obj)

cdef class ExprCond(Expr):
    
    cdef ast_decl.IExprCond *asExprCond(self):
        return dynamic_cast[ast_decl.IExprCondP](self._hndl)
    @staticmethod
    cdef ExprCond mk(ast_decl.IExprCond *hndl, bool owned):
        '''Creates a Python wrapper around native class'''
        ret = ExprCond()
        ret._hndl = hndl
        ret._owned = owned
        return ret
    
    cpdef Expr getCond_e(self):
        if self.asExprCond().getCond_e() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asExprCond().getCond_e().accept(of._hndl)
            return <Expr>(of._obj)
    cpdef Expr getTrue_e(self):
        if self.asExprCond().getTrue_e() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asExprCond().getTrue_e().accept(of._hndl)
            return <Expr>(of._obj)
    cpdef Expr getFalse_e(self):
        if self.asExprCond().getFalse_e() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asExprCond().getFalse_e().accept(of._hndl)
            return <Expr>(of._obj)

cdef class ExprDomainOpenRangeList(Expr):
    
    cdef ast_decl.IExprDomainOpenRangeList *asExprDomainOpenRangeList(self):
        return dynamic_cast[ast_decl.IExprDomainOpenRangeListP](self._hndl)
    @staticmethod
    cdef ExprDomainOpenRangeList mk(ast_decl.IExprDomainOpenRangeList *hndl, bool owned):
        '''Creates a Python wrapper around native class'''
        ret = ExprDomainOpenRangeList()
        ret._hndl = hndl
        ret._owned = owned
        return ret
    
    def values(self) -> ListUtil:
        return ListUtil(self.numValues, self.getValue)
    
    cpdef getValues(self):
        cdef const std_vector[ast_decl.IExprDomainOpenRangeValueUP] *__lp = &self.asExprDomainOpenRangeList().getValues()
        cdef ast_decl.IExprDomainOpenRangeValue *__ep;
        ret = []
        of = ObjFactory()
        for __i in range(__lp.size()):
            __ep = __lp.at(__i).get()
            ret.append(__ep.accept(of._hndl))
        return ret
    cpdef getValue(self, i):
        cdef ast_decl.IExprDomainOpenRangeValue *__ep = self.asExprDomainOpenRangeList().getValues().at(i).get();
        of = ObjFactory()
        __ep.accept(of._hndl)
        return of._obj
    cpdef void addValue(self, ExprDomainOpenRangeValue i):
        i._owned = False
        self.asExprDomainOpenRangeList().getValues().push_back(ast_decl.IExprDomainOpenRangeValueUP(i.asExprDomainOpenRangeValue(), True))
    cpdef numValues(self):
        return self.asExprDomainOpenRangeList().getValues().size()

cdef class ExprDomainOpenRangeValue(Expr):
    
    cdef ast_decl.IExprDomainOpenRangeValue *asExprDomainOpenRangeValue(self):
        return dynamic_cast[ast_decl.IExprDomainOpenRangeValueP](self._hndl)
    @staticmethod
    cdef ExprDomainOpenRangeValue mk(ast_decl.IExprDomainOpenRangeValue *hndl, bool owned):
        '''Creates a Python wrapper around native class'''
        ret = ExprDomainOpenRangeValue()
        ret._hndl = hndl
        ret._owned = owned
        return ret
    
    cpdef bool getSingle(self):
        return dynamic_cast[ast_decl.IExprDomainOpenRangeValueP](self._hndl).getSingle()
    cpdef Expr getLhs(self):
        if self.asExprDomainOpenRangeValue().getLhs() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asExprDomainOpenRangeValue().getLhs().accept(of._hndl)
            return <Expr>(of._obj)
    cpdef Expr getRhs(self):
        if self.asExprDomainOpenRangeValue().getRhs() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asExprDomainOpenRangeValue().getRhs().accept(of._hndl)
            return <Expr>(of._obj)

cdef class ExprHierarchicalId(Expr):
    
    cdef ast_decl.IExprHierarchicalId *asExprHierarchicalId(self):
        return dynamic_cast[ast_decl.IExprHierarchicalIdP](self._hndl)
    @staticmethod
    cdef ExprHierarchicalId mk(ast_decl.IExprHierarchicalId *hndl, bool owned):
        '''Creates a Python wrapper around native class'''
        ret = ExprHierarchicalId()
        ret._hndl = hndl
        ret._owned = owned
        return ret
    
    def elems(self) -> ListUtil:
        return ListUtil(self.numElems, self.getElem)
    
    cpdef getElems(self):
        cdef const std_vector[ast_decl.IExprMemberPathElemUP] *__lp = &self.asExprHierarchicalId().getElems()
        cdef ast_decl.IExprMemberPathElem *__ep;
        ret = []
        of = ObjFactory()
        for __i in range(__lp.size()):
            __ep = __lp.at(__i).get()
            ret.append(__ep.accept(of._hndl))
        return ret
    cpdef getElem(self, i):
        cdef ast_decl.IExprMemberPathElem *__ep = self.asExprHierarchicalId().getElems().at(i).get();
        of = ObjFactory()
        __ep.accept(of._hndl)
        return of._obj
    cpdef void addElem(self, ExprMemberPathElem i):
        i._owned = False
        self.asExprHierarchicalId().getElems().push_back(ast_decl.IExprMemberPathElemUP(i.asExprMemberPathElem(), True))
    cpdef numElems(self):
        return self.asExprHierarchicalId().getElems().size()

cdef class ExprId(Expr):
    
    cdef ast_decl.IExprId *asExprId(self):
        return dynamic_cast[ast_decl.IExprIdP](self._hndl)
    @staticmethod
    cdef ExprId mk(ast_decl.IExprId *hndl, bool owned):
        '''Creates a Python wrapper around native class'''
        ret = ExprId()
        ret._hndl = hndl
        ret._owned = owned
        return ret
    
    cpdef str getId(self):
        return dynamic_cast[ast_decl.IExprIdP](self._hndl).getId().decode()
    cpdef void setId(self, str v):
        dynamic_cast[ast_decl.IExprIdP](self._hndl).setId(v.encode())
    cpdef bool getIs_escaped(self):
        return dynamic_cast[ast_decl.IExprIdP](self._hndl).getIs_escaped()
    cpdef Location getLocation(self):
        return Location.wrap(dynamic_cast[ast_decl.IExprIdP](self._hndl).getLocation())

cdef class ExprIn(Expr):
    
    cdef ast_decl.IExprIn *asExprIn(self):
        return dynamic_cast[ast_decl.IExprInP](self._hndl)
    @staticmethod
    cdef ExprIn mk(ast_decl.IExprIn *hndl, bool owned):
        '''Creates a Python wrapper around native class'''
        ret = ExprIn()
        ret._hndl = hndl
        ret._owned = owned
        return ret
    
    cpdef Expr getLhs(self):
        if self.asExprIn().getLhs() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asExprIn().getLhs().accept(of._hndl)
            return <Expr>(of._obj)
    cpdef ExprOpenRangeList getRhs(self):
        if self.asExprIn().getRhs() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asExprIn().getRhs().accept(of._hndl)
            return <ExprOpenRangeList>(of._obj)

cdef class ExprListLiteral(Expr):
    
    cdef ast_decl.IExprListLiteral *asExprListLiteral(self):
        return dynamic_cast[ast_decl.IExprListLiteralP](self._hndl)
    @staticmethod
    cdef ExprListLiteral mk(ast_decl.IExprListLiteral *hndl, bool owned):
        '''Creates a Python wrapper around native class'''
        ret = ExprListLiteral()
        ret._hndl = hndl
        ret._owned = owned
        return ret
    
    def value(self) -> ListUtil:
        return ListUtil(self.numValue, self.getValue)
    
    cpdef getValueList(self):
        cdef const std_vector[ast_decl.IExprUP] *__lp = &self.asExprListLiteral().getValue()
        cdef ast_decl.IExpr *__ep;
        ret = []
        of = ObjFactory()
        for __i in range(__lp.size()):
            __ep = __lp.at(__i).get()
            ret.append(__ep.accept(of._hndl))
        return ret
    cpdef getValue(self, i):
        cdef ast_decl.IExpr *__ep = self.asExprListLiteral().getValue().at(i).get();
        of = ObjFactory()
        __ep.accept(of._hndl)
        return of._obj
    cpdef void addValue(self, Expr i):
        i._owned = False
        self.asExprListLiteral().getValue().push_back(ast_decl.IExprUP(i.asExpr(), True))
    cpdef numValue(self):
        return self.asExprListLiteral().getValue().size()

cdef class ExprMemberPathElem(Expr):
    
    cdef ast_decl.IExprMemberPathElem *asExprMemberPathElem(self):
        return dynamic_cast[ast_decl.IExprMemberPathElemP](self._hndl)
    @staticmethod
    cdef ExprMemberPathElem mk(ast_decl.IExprMemberPathElem *hndl, bool owned):
        '''Creates a Python wrapper around native class'''
        ret = ExprMemberPathElem()
        ret._hndl = hndl
        ret._owned = owned
        return ret
    
    cpdef ExprId getId(self):
        if self.asExprMemberPathElem().getId() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asExprMemberPathElem().getId().accept(of._hndl)
            return <ExprId>(of._obj)
    cpdef MethodParameterList getParams(self):
        if self.asExprMemberPathElem().getParams() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asExprMemberPathElem().getParams().accept(of._hndl)
            return <MethodParameterList>(of._obj)
    def subscript(self) -> ListUtil:
        return ListUtil(self.numSubscript, self.getSubscript)
    
    cpdef getSubscriptList(self):
        cdef const std_vector[ast_decl.IExprUP] *__lp = &self.asExprMemberPathElem().getSubscript()
        cdef ast_decl.IExpr *__ep;
        ret = []
        of = ObjFactory()
        for __i in range(__lp.size()):
            __ep = __lp.at(__i).get()
            ret.append(__ep.accept(of._hndl))
        return ret
    cpdef getSubscript(self, i):
        cdef ast_decl.IExpr *__ep = self.asExprMemberPathElem().getSubscript().at(i).get();
        of = ObjFactory()
        __ep.accept(of._hndl)
        return of._obj
    cpdef void addSubscript(self, Expr i):
        i._owned = False
        self.asExprMemberPathElem().getSubscript().push_back(ast_decl.IExprUP(i.asExpr(), True))
    cpdef numSubscript(self):
        return self.asExprMemberPathElem().getSubscript().size()
    cpdef int32_t getTarget(self):
        return dynamic_cast[ast_decl.IExprMemberPathElemP](self._hndl).getTarget()
    cpdef int32_t getSuper(self):
        return dynamic_cast[ast_decl.IExprMemberPathElemP](self._hndl).getSuper()
    cpdef  getString_method_id(self):
        return dynamic_cast[ast_decl.IExprMemberPathElemP](self._hndl).getString_method_id()

cdef class ExprNull(Expr):
    
    cdef ast_decl.IExprNull *asExprNull(self):
        return dynamic_cast[ast_decl.IExprNullP](self._hndl)
    @staticmethod
    cdef ExprNull mk(ast_decl.IExprNull *hndl, bool owned):
        '''Creates a Python wrapper around native class'''
        ret = ExprNull()
        ret._hndl = hndl
        ret._owned = owned
        return ret
    

cdef class ExprNumber(Expr):
    
    cdef ast_decl.IExprNumber *asExprNumber(self):
        return dynamic_cast[ast_decl.IExprNumberP](self._hndl)
    @staticmethod
    cdef ExprNumber mk(ast_decl.IExprNumber *hndl, bool owned):
        '''Creates a Python wrapper around native class'''
        ret = ExprNumber()
        ret._hndl = hndl
        ret._owned = owned
        return ret
    

cdef class ExprOpenRangeList(Expr):
    
    cdef ast_decl.IExprOpenRangeList *asExprOpenRangeList(self):
        return dynamic_cast[ast_decl.IExprOpenRangeListP](self._hndl)
    @staticmethod
    cdef ExprOpenRangeList mk(ast_decl.IExprOpenRangeList *hndl, bool owned):
        '''Creates a Python wrapper around native class'''
        ret = ExprOpenRangeList()
        ret._hndl = hndl
        ret._owned = owned
        return ret
    
    def values(self) -> ListUtil:
        return ListUtil(self.numValues, self.getValue)
    
    cpdef getValues(self):
        cdef const std_vector[ast_decl.IExprOpenRangeValueUP] *__lp = &self.asExprOpenRangeList().getValues()
        cdef ast_decl.IExprOpenRangeValue *__ep;
        ret = []
        of = ObjFactory()
        for __i in range(__lp.size()):
            __ep = __lp.at(__i).get()
            ret.append(__ep.accept(of._hndl))
        return ret
    cpdef getValue(self, i):
        cdef ast_decl.IExprOpenRangeValue *__ep = self.asExprOpenRangeList().getValues().at(i).get();
        of = ObjFactory()
        __ep.accept(of._hndl)
        return of._obj
    cpdef void addValue(self, ExprOpenRangeValue i):
        i._owned = False
        self.asExprOpenRangeList().getValues().push_back(ast_decl.IExprOpenRangeValueUP(i.asExprOpenRangeValue(), True))
    cpdef numValues(self):
        return self.asExprOpenRangeList().getValues().size()

cdef class ExprOpenRangeValue(Expr):
    
    cdef ast_decl.IExprOpenRangeValue *asExprOpenRangeValue(self):
        return dynamic_cast[ast_decl.IExprOpenRangeValueP](self._hndl)
    @staticmethod
    cdef ExprOpenRangeValue mk(ast_decl.IExprOpenRangeValue *hndl, bool owned):
        '''Creates a Python wrapper around native class'''
        ret = ExprOpenRangeValue()
        ret._hndl = hndl
        ret._owned = owned
        return ret
    
    cpdef Expr getLhs(self):
        if self.asExprOpenRangeValue().getLhs() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asExprOpenRangeValue().getLhs().accept(of._hndl)
            return <Expr>(of._obj)
    cpdef Expr getRhs(self):
        if self.asExprOpenRangeValue().getRhs() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asExprOpenRangeValue().getRhs().accept(of._hndl)
            return <Expr>(of._obj)

cdef class ExprRefPath(Expr):
    
    cdef ast_decl.IExprRefPath *asExprRefPath(self):
        return dynamic_cast[ast_decl.IExprRefPathP](self._hndl)
    @staticmethod
    cdef ExprRefPath mk(ast_decl.IExprRefPath *hndl, bool owned):
        '''Creates a Python wrapper around native class'''
        ret = ExprRefPath()
        ret._hndl = hndl
        ret._owned = owned
        return ret
    
    cpdef SymbolRefPath getTarget(self):
        if self.asExprRefPath().getTarget() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asExprRefPath().getTarget().accept(of._hndl)
            return <SymbolRefPath>(of._obj)

cdef class ExprRefPathElem(Expr):
    
    cdef ast_decl.IExprRefPathElem *asExprRefPathElem(self):
        return dynamic_cast[ast_decl.IExprRefPathElemP](self._hndl)
    @staticmethod
    cdef ExprRefPathElem mk(ast_decl.IExprRefPathElem *hndl, bool owned):
        '''Creates a Python wrapper around native class'''
        ret = ExprRefPathElem()
        ret._hndl = hndl
        ret._owned = owned
        return ret
    

cdef class ExprStaticRefPath(Expr):
    
    cdef ast_decl.IExprStaticRefPath *asExprStaticRefPath(self):
        return dynamic_cast[ast_decl.IExprStaticRefPathP](self._hndl)
    @staticmethod
    cdef ExprStaticRefPath mk(ast_decl.IExprStaticRefPath *hndl, bool owned):
        '''Creates a Python wrapper around native class'''
        ret = ExprStaticRefPath()
        ret._hndl = hndl
        ret._owned = owned
        return ret
    
    cpdef bool getIs_global(self):
        return dynamic_cast[ast_decl.IExprStaticRefPathP](self._hndl).getIs_global()
    def base(self) -> ListUtil:
        return ListUtil(self.numBase, self.getBase)
    
    cpdef getBaseList(self):
        cdef const std_vector[ast_decl.ITypeIdentifierElemUP] *__lp = &self.asExprStaticRefPath().getBase()
        cdef ast_decl.ITypeIdentifierElem *__ep;
        ret = []
        of = ObjFactory()
        for __i in range(__lp.size()):
            __ep = __lp.at(__i).get()
            ret.append(__ep.accept(of._hndl))
        return ret
    cpdef getBase(self, i):
        cdef ast_decl.ITypeIdentifierElem *__ep = self.asExprStaticRefPath().getBase().at(i).get();
        of = ObjFactory()
        __ep.accept(of._hndl)
        return of._obj
    cpdef void addBase(self, TypeIdentifierElem i):
        i._owned = False
        self.asExprStaticRefPath().getBase().push_back(ast_decl.ITypeIdentifierElemUP(i.asTypeIdentifierElem(), True))
    cpdef numBase(self):
        return self.asExprStaticRefPath().getBase().size()
    cpdef ExprMemberPathElem getLeaf(self):
        if self.asExprStaticRefPath().getLeaf() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asExprStaticRefPath().getLeaf().accept(of._hndl)
            return <ExprMemberPathElem>(of._obj)

cdef class ExprString(Expr):
    
    cdef ast_decl.IExprString *asExprString(self):
        return dynamic_cast[ast_decl.IExprStringP](self._hndl)
    @staticmethod
    cdef ExprString mk(ast_decl.IExprString *hndl, bool owned):
        '''Creates a Python wrapper around native class'''
        ret = ExprString()
        ret._hndl = hndl
        ret._owned = owned
        return ret
    
    cpdef str getValue(self):
        return dynamic_cast[ast_decl.IExprStringP](self._hndl).getValue().decode()
    cpdef void setValue(self, str v):
        dynamic_cast[ast_decl.IExprStringP](self._hndl).setValue(v.encode())
    cpdef bool getIs_raw(self):
        return dynamic_cast[ast_decl.IExprStringP](self._hndl).getIs_raw()

cdef class ExprStructLiteral(Expr):
    
    cdef ast_decl.IExprStructLiteral *asExprStructLiteral(self):
        return dynamic_cast[ast_decl.IExprStructLiteralP](self._hndl)
    @staticmethod
    cdef ExprStructLiteral mk(ast_decl.IExprStructLiteral *hndl, bool owned):
        '''Creates a Python wrapper around native class'''
        ret = ExprStructLiteral()
        ret._hndl = hndl
        ret._owned = owned
        return ret
    
    def values(self) -> ListUtil:
        return ListUtil(self.numValues, self.getValue)
    
    cpdef getValues(self):
        cdef const std_vector[ast_decl.IExprStructLiteralItemUP] *__lp = &self.asExprStructLiteral().getValues()
        cdef ast_decl.IExprStructLiteralItem *__ep;
        ret = []
        of = ObjFactory()
        for __i in range(__lp.size()):
            __ep = __lp.at(__i).get()
            ret.append(__ep.accept(of._hndl))
        return ret
    cpdef getValue(self, i):
        cdef ast_decl.IExprStructLiteralItem *__ep = self.asExprStructLiteral().getValues().at(i).get();
        of = ObjFactory()
        __ep.accept(of._hndl)
        return of._obj
    cpdef void addValue(self, ExprStructLiteralItem i):
        i._owned = False
        self.asExprStructLiteral().getValues().push_back(ast_decl.IExprStructLiteralItemUP(i.asExprStructLiteralItem(), True))
    cpdef numValues(self):
        return self.asExprStructLiteral().getValues().size()

cdef class ExprStructLiteralItem(Expr):
    
    cdef ast_decl.IExprStructLiteralItem *asExprStructLiteralItem(self):
        return dynamic_cast[ast_decl.IExprStructLiteralItemP](self._hndl)
    @staticmethod
    cdef ExprStructLiteralItem mk(ast_decl.IExprStructLiteralItem *hndl, bool owned):
        '''Creates a Python wrapper around native class'''
        ret = ExprStructLiteralItem()
        ret._hndl = hndl
        ret._owned = owned
        return ret
    
    cpdef ExprId getId(self):
        if self.asExprStructLiteralItem().getId() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asExprStructLiteralItem().getId().accept(of._hndl)
            return <ExprId>(of._obj)
    cpdef Expr getValue(self):
        if self.asExprStructLiteralItem().getValue() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asExprStructLiteralItem().getValue().accept(of._hndl)
            return <Expr>(of._obj)

cdef class ExprSubscript(Expr):
    
    cdef ast_decl.IExprSubscript *asExprSubscript(self):
        return dynamic_cast[ast_decl.IExprSubscriptP](self._hndl)
    @staticmethod
    cdef ExprSubscript mk(ast_decl.IExprSubscript *hndl, bool owned):
        '''Creates a Python wrapper around native class'''
        ret = ExprSubscript()
        ret._hndl = hndl
        ret._owned = owned
        return ret
    
    cpdef Expr getExpr(self):
        if self.asExprSubscript().getExpr() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asExprSubscript().getExpr().accept(of._hndl)
            return <Expr>(of._obj)
    cpdef Expr getSubscript(self):
        if self.asExprSubscript().getSubscript() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asExprSubscript().getSubscript().accept(of._hndl)
            return <Expr>(of._obj)

cdef class ExprSubstring(Expr):
    
    cdef ast_decl.IExprSubstring *asExprSubstring(self):
        return dynamic_cast[ast_decl.IExprSubstringP](self._hndl)
    @staticmethod
    cdef ExprSubstring mk(ast_decl.IExprSubstring *hndl, bool owned):
        '''Creates a Python wrapper around native class'''
        ret = ExprSubstring()
        ret._hndl = hndl
        ret._owned = owned
        return ret
    
    cpdef Expr getExpr(self):
        if self.asExprSubstring().getExpr() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asExprSubstring().getExpr().accept(of._hndl)
            return <Expr>(of._obj)
    cpdef Expr getStart(self):
        if self.asExprSubstring().getStart() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asExprSubstring().getStart().accept(of._hndl)
            return <Expr>(of._obj)
    cpdef Expr getEnd(self):
        if self.asExprSubstring().getEnd() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asExprSubstring().getEnd().accept(of._hndl)
            return <Expr>(of._obj)

cdef class ExprUnary(Expr):
    
    cdef ast_decl.IExprUnary *asExprUnary(self):
        return dynamic_cast[ast_decl.IExprUnaryP](self._hndl)
    @staticmethod
    cdef ExprUnary mk(ast_decl.IExprUnary *hndl, bool owned):
        '''Creates a Python wrapper around native class'''
        ret = ExprUnary()
        ret._hndl = hndl
        ret._owned = owned
        return ret
    
    cpdef  getOp(self):
        return dynamic_cast[ast_decl.IExprUnaryP](self._hndl).getOp()
    cpdef Expr getRhs(self):
        if self.asExprUnary().getRhs() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asExprUnary().getRhs().accept(of._hndl)
            return <Expr>(of._obj)

cdef class ExtendEnum(ScopeChild):
    
    cdef ast_decl.IExtendEnum *asExtendEnum(self):
        return dynamic_cast[ast_decl.IExtendEnumP](self._hndl)
    @staticmethod
    cdef ExtendEnum mk(ast_decl.IExtendEnum *hndl, bool owned):
        '''Creates a Python wrapper around native class'''
        ret = ExtendEnum()
        ret._hndl = hndl
        ret._owned = owned
        return ret
    
    cpdef TypeIdentifier getTarget(self):
        if self.asExtendEnum().getTarget() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asExtendEnum().getTarget().accept(of._hndl)
            return <TypeIdentifier>(of._obj)
    def items(self) -> ListUtil:
        return ListUtil(self.numItems, self.getItem)
    
    cpdef getItems(self):
        cdef const std_vector[ast_decl.IEnumItemUP] *__lp = &self.asExtendEnum().getItems()
        cdef ast_decl.IEnumItem *__ep;
        ret = []
        of = ObjFactory()
        for __i in range(__lp.size()):
            __ep = __lp.at(__i).get()
            ret.append(__ep.accept(of._hndl))
        return ret
    cpdef getItem(self, i):
        cdef ast_decl.IEnumItem *__ep = self.asExtendEnum().getItems().at(i).get();
        of = ObjFactory()
        __ep.accept(of._hndl)
        return of._obj
    cpdef void addItem(self, EnumItem i):
        i._owned = False
        self.asExtendEnum().getItems().push_back(ast_decl.IEnumItemUP(i.asEnumItem(), True))
    cpdef numItems(self):
        return self.asExtendEnum().getItems().size()

cdef class FunctionDefinition(ScopeChild):
    
    cdef ast_decl.IFunctionDefinition *asFunctionDefinition(self):
        return dynamic_cast[ast_decl.IFunctionDefinitionP](self._hndl)
    @staticmethod
    cdef FunctionDefinition mk(ast_decl.IFunctionDefinition *hndl, bool owned):
        '''Creates a Python wrapper around native class'''
        ret = FunctionDefinition()
        ret._hndl = hndl
        ret._owned = owned
        return ret
    
    cpdef Location getEndLocation(self):
        return Location.wrap(dynamic_cast[ast_decl.IFunctionDefinitionP](self._hndl).getEndLocation())
    cpdef FunctionPrototype getProto(self):
        if self.asFunctionDefinition().getProto() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asFunctionDefinition().getProto().accept(of._hndl)
            return <FunctionPrototype>(of._obj)
    cpdef ExecScope getBody(self):
        if self.asFunctionDefinition().getBody() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asFunctionDefinition().getBody().accept(of._hndl)
            return <ExecScope>(of._obj)
    cpdef  getPlat(self):
        return dynamic_cast[ast_decl.IFunctionDefinitionP](self._hndl).getPlat()

cdef class FunctionImport(ScopeChild):
    
    cdef ast_decl.IFunctionImport *asFunctionImport(self):
        return dynamic_cast[ast_decl.IFunctionImportP](self._hndl)
    @staticmethod
    cdef FunctionImport mk(ast_decl.IFunctionImport *hndl, bool owned):
        '''Creates a Python wrapper around native class'''
        ret = FunctionImport()
        ret._hndl = hndl
        ret._owned = owned
        return ret
    
    cpdef  getPlat(self):
        return dynamic_cast[ast_decl.IFunctionImportP](self._hndl).getPlat()
    cpdef str getLang(self):
        return dynamic_cast[ast_decl.IFunctionImportP](self._hndl).getLang().decode()
    cpdef void setLang(self, str v):
        dynamic_cast[ast_decl.IFunctionImportP](self._hndl).setLang(v.encode())

cdef class FunctionParamDecl(ScopeChild):
    
    cdef ast_decl.IFunctionParamDecl *asFunctionParamDecl(self):
        return dynamic_cast[ast_decl.IFunctionParamDeclP](self._hndl)
    @staticmethod
    cdef FunctionParamDecl mk(ast_decl.IFunctionParamDecl *hndl, bool owned):
        '''Creates a Python wrapper around native class'''
        ret = FunctionParamDecl()
        ret._hndl = hndl
        ret._owned = owned
        return ret
    
    cpdef  getKind(self):
        return dynamic_cast[ast_decl.IFunctionParamDeclP](self._hndl).getKind()
    cpdef ExprId getName(self):
        if self.asFunctionParamDecl().getName() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asFunctionParamDecl().getName().accept(of._hndl)
            return <ExprId>(of._obj)
    cpdef DataType getType(self):
        if self.asFunctionParamDecl().getType() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asFunctionParamDecl().getType().accept(of._hndl)
            return <DataType>(of._obj)
    cpdef  getDir(self):
        return dynamic_cast[ast_decl.IFunctionParamDeclP](self._hndl).getDir()
    cpdef Expr getDflt(self):
        if self.asFunctionParamDecl().getDflt() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asFunctionParamDecl().getDflt().accept(of._hndl)
            return <Expr>(of._obj)
    cpdef bool getIs_varargs(self):
        return dynamic_cast[ast_decl.IFunctionParamDeclP](self._hndl).getIs_varargs()

cdef class GenericConstraintDeclValue(ScopeChild):
    
    cdef ast_decl.IGenericConstraintDeclValue *asGenericConstraintDeclValue(self):
        return dynamic_cast[ast_decl.IGenericConstraintDeclValueP](self._hndl)
    @staticmethod
    cdef GenericConstraintDeclValue mk(ast_decl.IGenericConstraintDeclValue *hndl, bool owned):
        '''Creates a Python wrapper around native class'''
        ret = GenericConstraintDeclValue()
        ret._hndl = hndl
        ret._owned = owned
        return ret
    
    cpdef bool getIs_static(self):
        return dynamic_cast[ast_decl.IGenericConstraintDeclValueP](self._hndl).getIs_static()
    cpdef bool getIs_return_numeric(self):
        return dynamic_cast[ast_decl.IGenericConstraintDeclValueP](self._hndl).getIs_return_numeric()
    cpdef DataType getReturn_type(self):
        if self.asGenericConstraintDeclValue().getReturn_type() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asGenericConstraintDeclValue().getReturn_type().accept(of._hndl)
            return <DataType>(of._obj)
    cpdef ExprId getName(self):
        if self.asGenericConstraintDeclValue().getName() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asGenericConstraintDeclValue().getName().accept(of._hndl)
            return <ExprId>(of._obj)
    def parameters(self) -> ListUtil:
        return ListUtil(self.numParameters, self.getParameter)
    
    cpdef getParameters(self):
        cdef const std_vector[ast_decl.IGenericConstraintParamUP] *__lp = &self.asGenericConstraintDeclValue().getParameters()
        cdef ast_decl.IGenericConstraintParam *__ep;
        ret = []
        of = ObjFactory()
        for __i in range(__lp.size()):
            __ep = __lp.at(__i).get()
            ret.append(__ep.accept(of._hndl))
        return ret
    cpdef getParameter(self, i):
        cdef ast_decl.IGenericConstraintParam *__ep = self.asGenericConstraintDeclValue().getParameters().at(i).get();
        of = ObjFactory()
        __ep.accept(of._hndl)
        return of._obj
    cpdef void addParameter(self, GenericConstraintParam i):
        i._owned = False
        self.asGenericConstraintDeclValue().getParameters().push_back(ast_decl.IGenericConstraintParamUP(i.asGenericConstraintParam(), True))
    cpdef numParameters(self):
        return self.asGenericConstraintDeclValue().getParameters().size()
    cpdef Expr getExpr(self):
        if self.asGenericConstraintDeclValue().getExpr() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asGenericConstraintDeclValue().getExpr().accept(of._hndl)
            return <Expr>(of._obj)

cdef class GenericConstraintParam(ScopeChild):
    
    cdef ast_decl.IGenericConstraintParam *asGenericConstraintParam(self):
        return dynamic_cast[ast_decl.IGenericConstraintParamP](self._hndl)
    @staticmethod
    cdef GenericConstraintParam mk(ast_decl.IGenericConstraintParam *hndl, bool owned):
        '''Creates a Python wrapper around native class'''
        ret = GenericConstraintParam()
        ret._hndl = hndl
        ret._owned = owned
        return ret
    
    cpdef ExprId getName(self):
        if self.asGenericConstraintParam().getName() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asGenericConstraintParam().getName().accept(of._hndl)
            return <ExprId>(of._obj)
    cpdef bool getIs_const(self):
        return dynamic_cast[ast_decl.IGenericConstraintParamP](self._hndl).getIs_const()
    cpdef bool getIs_numeric(self):
        return dynamic_cast[ast_decl.IGenericConstraintParamP](self._hndl).getIs_numeric()
    cpdef DataType getType(self):
        if self.asGenericConstraintParam().getType() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asGenericConstraintParam().getType().accept(of._hndl)
            return <DataType>(of._obj)

cdef class MethodParameterList(Expr):
    
    cdef ast_decl.IMethodParameterList *asMethodParameterList(self):
        return dynamic_cast[ast_decl.IMethodParameterListP](self._hndl)
    @staticmethod
    cdef MethodParameterList mk(ast_decl.IMethodParameterList *hndl, bool owned):
        '''Creates a Python wrapper around native class'''
        ret = MethodParameterList()
        ret._hndl = hndl
        ret._owned = owned
        return ret
    
    def parameters(self) -> ListUtil:
        return ListUtil(self.numParameters, self.getParameter)
    
    cpdef getParameters(self):
        cdef const std_vector[ast_decl.IExprUP] *__lp = &self.asMethodParameterList().getParameters()
        cdef ast_decl.IExpr *__ep;
        ret = []
        of = ObjFactory()
        for __i in range(__lp.size()):
            __ep = __lp.at(__i).get()
            ret.append(__ep.accept(of._hndl))
        return ret
    cpdef getParameter(self, i):
        cdef ast_decl.IExpr *__ep = self.asMethodParameterList().getParameters().at(i).get();
        of = ObjFactory()
        __ep.accept(of._hndl)
        return of._obj
    cpdef void addParameter(self, Expr i):
        i._owned = False
        self.asMethodParameterList().getParameters().push_back(ast_decl.IExprUP(i.asExpr(), True))
    cpdef numParameters(self):
        return self.asMethodParameterList().getParameters().size()

cdef class MonitorActivityActionTraversal(MonitorActivityStmt):
    
    cdef ast_decl.IMonitorActivityActionTraversal *asMonitorActivityActionTraversal(self):
        return dynamic_cast[ast_decl.IMonitorActivityActionTraversalP](self._hndl)
    @staticmethod
    cdef MonitorActivityActionTraversal mk(ast_decl.IMonitorActivityActionTraversal *hndl, bool owned):
        '''Creates a Python wrapper around native class'''
        ret = MonitorActivityActionTraversal()
        ret._hndl = hndl
        ret._owned = owned
        return ret
    
    cpdef ExprRefPath getTarget(self):
        if self.asMonitorActivityActionTraversal().getTarget() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asMonitorActivityActionTraversal().getTarget().accept(of._hndl)
            return <ExprRefPath>(of._obj)
    cpdef ConstraintStmt getWith_c(self):
        if self.asMonitorActivityActionTraversal().getWith_c() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asMonitorActivityActionTraversal().getWith_c().accept(of._hndl)
            return <ConstraintStmt>(of._obj)

cdef class MonitorActivityConcat(MonitorActivityStmt):
    
    cdef ast_decl.IMonitorActivityConcat *asMonitorActivityConcat(self):
        return dynamic_cast[ast_decl.IMonitorActivityConcatP](self._hndl)
    @staticmethod
    cdef MonitorActivityConcat mk(ast_decl.IMonitorActivityConcat *hndl, bool owned):
        '''Creates a Python wrapper around native class'''
        ret = MonitorActivityConcat()
        ret._hndl = hndl
        ret._owned = owned
        return ret
    
    cpdef MonitorActivityStmt getLhs(self):
        if self.asMonitorActivityConcat().getLhs() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asMonitorActivityConcat().getLhs().accept(of._hndl)
            return <MonitorActivityStmt>(of._obj)
    cpdef MonitorActivityStmt getRhs(self):
        if self.asMonitorActivityConcat().getRhs() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asMonitorActivityConcat().getRhs().accept(of._hndl)
            return <MonitorActivityStmt>(of._obj)

cdef class ActionHandleField(NamedScopeChild):
    
    cdef ast_decl.IActionHandleField *asActionHandleField(self):
        return dynamic_cast[ast_decl.IActionHandleFieldP](self._hndl)
    @staticmethod
    cdef ActionHandleField mk(ast_decl.IActionHandleField *hndl, bool owned):
        '''Creates a Python wrapper around native class'''
        ret = ActionHandleField()
        ret._hndl = hndl
        ret._owned = owned
        return ret
    
    cpdef DataType getType(self):
        if self.asActionHandleField().getType() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asActionHandleField().getType().accept(of._hndl)
            return <DataType>(of._obj)
    def initializers(self) -> ListUtil:
        return ListUtil(self.numInitializers, self.getInitializer)
    
    cpdef getInitializers(self):
        cdef const std_vector[ast_decl.IActionFieldInitializerUP] *__lp = &self.asActionHandleField().getInitializers()
        cdef ast_decl.IActionFieldInitializer *__ep;
        ret = []
        of = ObjFactory()
        for __i in range(__lp.size()):
            __ep = __lp.at(__i).get()
            ret.append(__ep.accept(of._hndl))
        return ret
    cpdef getInitializer(self, i):
        cdef ast_decl.IActionFieldInitializer *__ep = self.asActionHandleField().getInitializers().at(i).get();
        of = ObjFactory()
        __ep.accept(of._hndl)
        return of._obj
    cpdef void addInitializer(self, ActionFieldInitializer i):
        i._owned = False
        self.asActionHandleField().getInitializers().push_back(ast_decl.IActionFieldInitializerUP(i.asActionFieldInitializer(), True))
    cpdef numInitializers(self):
        return self.asActionHandleField().getInitializers().size()

cdef class MonitorActivityEventually(MonitorActivityStmt):
    
    cdef ast_decl.IMonitorActivityEventually *asMonitorActivityEventually(self):
        return dynamic_cast[ast_decl.IMonitorActivityEventuallyP](self._hndl)
    @staticmethod
    cdef MonitorActivityEventually mk(ast_decl.IMonitorActivityEventually *hndl, bool owned):
        '''Creates a Python wrapper around native class'''
        ret = MonitorActivityEventually()
        ret._hndl = hndl
        ret._owned = owned
        return ret
    
    cpdef Expr getCondition(self):
        if self.asMonitorActivityEventually().getCondition() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asMonitorActivityEventually().getCondition().accept(of._hndl)
            return <Expr>(of._obj)
    cpdef MonitorActivityStmt getBody(self):
        if self.asMonitorActivityEventually().getBody() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asMonitorActivityEventually().getBody().accept(of._hndl)
            return <MonitorActivityStmt>(of._obj)

cdef class MonitorActivityIfElse(MonitorActivityStmt):
    
    cdef ast_decl.IMonitorActivityIfElse *asMonitorActivityIfElse(self):
        return dynamic_cast[ast_decl.IMonitorActivityIfElseP](self._hndl)
    @staticmethod
    cdef MonitorActivityIfElse mk(ast_decl.IMonitorActivityIfElse *hndl, bool owned):
        '''Creates a Python wrapper around native class'''
        ret = MonitorActivityIfElse()
        ret._hndl = hndl
        ret._owned = owned
        return ret
    
    cpdef Expr getCond(self):
        if self.asMonitorActivityIfElse().getCond() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asMonitorActivityIfElse().getCond().accept(of._hndl)
            return <Expr>(of._obj)
    cpdef MonitorActivityStmt getTrue_s(self):
        if self.asMonitorActivityIfElse().getTrue_s() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asMonitorActivityIfElse().getTrue_s().accept(of._hndl)
            return <MonitorActivityStmt>(of._obj)
    cpdef MonitorActivityStmt getFalse_s(self):
        if self.asMonitorActivityIfElse().getFalse_s() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asMonitorActivityIfElse().getFalse_s().accept(of._hndl)
            return <MonitorActivityStmt>(of._obj)

cdef class MonitorActivityMatch(MonitorActivityStmt):
    
    cdef ast_decl.IMonitorActivityMatch *asMonitorActivityMatch(self):
        return dynamic_cast[ast_decl.IMonitorActivityMatchP](self._hndl)
    @staticmethod
    cdef MonitorActivityMatch mk(ast_decl.IMonitorActivityMatch *hndl, bool owned):
        '''Creates a Python wrapper around native class'''
        ret = MonitorActivityMatch()
        ret._hndl = hndl
        ret._owned = owned
        return ret
    
    cpdef Expr getCond(self):
        if self.asMonitorActivityMatch().getCond() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asMonitorActivityMatch().getCond().accept(of._hndl)
            return <Expr>(of._obj)
    def choices(self) -> ListUtil:
        return ListUtil(self.numChoices, self.getChoice)
    
    cpdef getChoices(self):
        cdef const std_vector[ast_decl.IMonitorActivityMatchChoiceUP] *__lp = &self.asMonitorActivityMatch().getChoices()
        cdef ast_decl.IMonitorActivityMatchChoice *__ep;
        ret = []
        of = ObjFactory()
        for __i in range(__lp.size()):
            __ep = __lp.at(__i).get()
            ret.append(__ep.accept(of._hndl))
        return ret
    cpdef getChoice(self, i):
        cdef ast_decl.IMonitorActivityMatchChoice *__ep = self.asMonitorActivityMatch().getChoices().at(i).get();
        of = ObjFactory()
        __ep.accept(of._hndl)
        return of._obj
    cpdef void addChoice(self, MonitorActivityMatchChoice i):
        i._owned = False
        self.asMonitorActivityMatch().getChoices().push_back(ast_decl.IMonitorActivityMatchChoiceUP(i.asMonitorActivityMatchChoice(), True))
    cpdef numChoices(self):
        return self.asMonitorActivityMatch().getChoices().size()

cdef class ActivityBindStmt(ActivityStmt):
    
    cdef ast_decl.IActivityBindStmt *asActivityBindStmt(self):
        return dynamic_cast[ast_decl.IActivityBindStmtP](self._hndl)
    @staticmethod
    cdef ActivityBindStmt mk(ast_decl.IActivityBindStmt *hndl, bool owned):
        '''Creates a Python wrapper around native class'''
        ret = ActivityBindStmt()
        ret._hndl = hndl
        ret._owned = owned
        return ret
    
    cpdef ExprHierarchicalId getLhs(self):
        if self.asActivityBindStmt().getLhs() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asActivityBindStmt().getLhs().accept(of._hndl)
            return <ExprHierarchicalId>(of._obj)
    def rhs(self) -> ListUtil:
        return ListUtil(self.numRhs, self.getRh)
    
    cpdef getRhs(self):
        cdef const std_vector[ast_decl.IExprHierarchicalIdUP] *__lp = &self.asActivityBindStmt().getRhs()
        cdef ast_decl.IExprHierarchicalId *__ep;
        ret = []
        of = ObjFactory()
        for __i in range(__lp.size()):
            __ep = __lp.at(__i).get()
            ret.append(__ep.accept(of._hndl))
        return ret
    cpdef getRh(self, i):
        cdef ast_decl.IExprHierarchicalId *__ep = self.asActivityBindStmt().getRhs().at(i).get();
        of = ObjFactory()
        __ep.accept(of._hndl)
        return of._obj
    cpdef void addRh(self, ExprHierarchicalId i):
        i._owned = False
        self.asActivityBindStmt().getRhs().push_back(ast_decl.IExprHierarchicalIdUP(i.asExprHierarchicalId(), True))
    cpdef numRhs(self):
        return self.asActivityBindStmt().getRhs().size()

cdef class ActivityConstraint(ActivityStmt):
    
    cdef ast_decl.IActivityConstraint *asActivityConstraint(self):
        return dynamic_cast[ast_decl.IActivityConstraintP](self._hndl)
    @staticmethod
    cdef ActivityConstraint mk(ast_decl.IActivityConstraint *hndl, bool owned):
        '''Creates a Python wrapper around native class'''
        ret = ActivityConstraint()
        ret._hndl = hndl
        ret._owned = owned
        return ret
    
    cpdef ConstraintStmt getConstraint(self):
        if self.asActivityConstraint().getConstraint() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asActivityConstraint().getConstraint().accept(of._hndl)
            return <ConstraintStmt>(of._obj)

cdef class MonitorActivityMonitorTraversal(MonitorActivityStmt):
    
    cdef ast_decl.IMonitorActivityMonitorTraversal *asMonitorActivityMonitorTraversal(self):
        return dynamic_cast[ast_decl.IMonitorActivityMonitorTraversalP](self._hndl)
    @staticmethod
    cdef MonitorActivityMonitorTraversal mk(ast_decl.IMonitorActivityMonitorTraversal *hndl, bool owned):
        '''Creates a Python wrapper around native class'''
        ret = MonitorActivityMonitorTraversal()
        ret._hndl = hndl
        ret._owned = owned
        return ret
    
    cpdef ExprRefPath getTarget(self):
        if self.asMonitorActivityMonitorTraversal().getTarget() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asMonitorActivityMonitorTraversal().getTarget().accept(of._hndl)
            return <ExprRefPath>(of._obj)
    cpdef ConstraintStmt getWith_c(self):
        if self.asMonitorActivityMonitorTraversal().getWith_c() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asMonitorActivityMonitorTraversal().getWith_c().accept(of._hndl)
            return <ConstraintStmt>(of._obj)

cdef class MonitorActivityOverlap(MonitorActivityStmt):
    
    cdef ast_decl.IMonitorActivityOverlap *asMonitorActivityOverlap(self):
        return dynamic_cast[ast_decl.IMonitorActivityOverlapP](self._hndl)
    @staticmethod
    cdef MonitorActivityOverlap mk(ast_decl.IMonitorActivityOverlap *hndl, bool owned):
        '''Creates a Python wrapper around native class'''
        ret = MonitorActivityOverlap()
        ret._hndl = hndl
        ret._owned = owned
        return ret
    
    cpdef MonitorActivityStmt getLhs(self):
        if self.asMonitorActivityOverlap().getLhs() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asMonitorActivityOverlap().getLhs().accept(of._hndl)
            return <MonitorActivityStmt>(of._obj)
    cpdef MonitorActivityStmt getRhs(self):
        if self.asMonitorActivityOverlap().getRhs() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asMonitorActivityOverlap().getRhs().accept(of._hndl)
            return <MonitorActivityStmt>(of._obj)

cdef class MonitorActivityRepeatCount(MonitorActivityStmt):
    
    cdef ast_decl.IMonitorActivityRepeatCount *asMonitorActivityRepeatCount(self):
        return dynamic_cast[ast_decl.IMonitorActivityRepeatCountP](self._hndl)
    @staticmethod
    cdef MonitorActivityRepeatCount mk(ast_decl.IMonitorActivityRepeatCount *hndl, bool owned):
        '''Creates a Python wrapper around native class'''
        ret = MonitorActivityRepeatCount()
        ret._hndl = hndl
        ret._owned = owned
        return ret
    
    cpdef ExprId getLoop_var(self):
        if self.asMonitorActivityRepeatCount().getLoop_var() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asMonitorActivityRepeatCount().getLoop_var().accept(of._hndl)
            return <ExprId>(of._obj)
    cpdef Expr getCount(self):
        if self.asMonitorActivityRepeatCount().getCount() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asMonitorActivityRepeatCount().getCount().accept(of._hndl)
            return <Expr>(of._obj)
    cpdef ScopeChild getBody(self):
        if self.asMonitorActivityRepeatCount().getBody() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asMonitorActivityRepeatCount().getBody().accept(of._hndl)
            return <ScopeChild>(of._obj)

cdef class MonitorActivityRepeatWhile(MonitorActivityStmt):
    
    cdef ast_decl.IMonitorActivityRepeatWhile *asMonitorActivityRepeatWhile(self):
        return dynamic_cast[ast_decl.IMonitorActivityRepeatWhileP](self._hndl)
    @staticmethod
    cdef MonitorActivityRepeatWhile mk(ast_decl.IMonitorActivityRepeatWhile *hndl, bool owned):
        '''Creates a Python wrapper around native class'''
        ret = MonitorActivityRepeatWhile()
        ret._hndl = hndl
        ret._owned = owned
        return ret
    
    cpdef Expr getCond(self):
        if self.asMonitorActivityRepeatWhile().getCond() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asMonitorActivityRepeatWhile().getCond().accept(of._hndl)
            return <Expr>(of._obj)
    cpdef ScopeChild getBody(self):
        if self.asMonitorActivityRepeatWhile().getBody() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asMonitorActivityRepeatWhile().getBody().accept(of._hndl)
            return <ScopeChild>(of._obj)

cdef class ActivityJoinSpecBranch(ActivityJoinSpec):
    
    cdef ast_decl.IActivityJoinSpecBranch *asActivityJoinSpecBranch(self):
        return dynamic_cast[ast_decl.IActivityJoinSpecBranchP](self._hndl)
    @staticmethod
    cdef ActivityJoinSpecBranch mk(ast_decl.IActivityJoinSpecBranch *hndl, bool owned):
        '''Creates a Python wrapper around native class'''
        ret = ActivityJoinSpecBranch()
        ret._hndl = hndl
        ret._owned = owned
        return ret
    
    def branches(self) -> ListUtil:
        return ListUtil(self.numBranches, self.getBranche)
    
    cpdef getBranches(self):
        cdef const std_vector[ast_decl.IExprRefPathContextUP] *__lp = &self.asActivityJoinSpecBranch().getBranches()
        cdef ast_decl.IExprRefPathContext *__ep;
        ret = []
        of = ObjFactory()
        for __i in range(__lp.size()):
            __ep = __lp.at(__i).get()
            ret.append(__ep.accept(of._hndl))
        return ret
    cpdef getBranche(self, i):
        cdef ast_decl.IExprRefPathContext *__ep = self.asActivityJoinSpecBranch().getBranches().at(i).get();
        of = ObjFactory()
        __ep.accept(of._hndl)
        return of._obj
    cpdef void addBranche(self, ExprRefPathContext i):
        i._owned = False
        self.asActivityJoinSpecBranch().getBranches().push_back(ast_decl.IExprRefPathContextUP(i.asExprRefPathContext(), True))
    cpdef numBranches(self):
        return self.asActivityJoinSpecBranch().getBranches().size()

cdef class ActivityJoinSpecFirst(ActivityJoinSpec):
    
    cdef ast_decl.IActivityJoinSpecFirst *asActivityJoinSpecFirst(self):
        return dynamic_cast[ast_decl.IActivityJoinSpecFirstP](self._hndl)
    @staticmethod
    cdef ActivityJoinSpecFirst mk(ast_decl.IActivityJoinSpecFirst *hndl, bool owned):
        '''Creates a Python wrapper around native class'''
        ret = ActivityJoinSpecFirst()
        ret._hndl = hndl
        ret._owned = owned
        return ret
    
    cpdef Expr getCount(self):
        if self.asActivityJoinSpecFirst().getCount() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asActivityJoinSpecFirst().getCount().accept(of._hndl)
            return <Expr>(of._obj)

cdef class ActivityJoinSpecNone(ActivityJoinSpec):
    
    cdef ast_decl.IActivityJoinSpecNone *asActivityJoinSpecNone(self):
        return dynamic_cast[ast_decl.IActivityJoinSpecNoneP](self._hndl)
    @staticmethod
    cdef ActivityJoinSpecNone mk(ast_decl.IActivityJoinSpecNone *hndl, bool owned):
        '''Creates a Python wrapper around native class'''
        ret = ActivityJoinSpecNone()
        ret._hndl = hndl
        ret._owned = owned
        return ret
    

cdef class ActivityJoinSpecSelect(ActivityJoinSpec):
    
    cdef ast_decl.IActivityJoinSpecSelect *asActivityJoinSpecSelect(self):
        return dynamic_cast[ast_decl.IActivityJoinSpecSelectP](self._hndl)
    @staticmethod
    cdef ActivityJoinSpecSelect mk(ast_decl.IActivityJoinSpecSelect *hndl, bool owned):
        '''Creates a Python wrapper around native class'''
        ret = ActivityJoinSpecSelect()
        ret._hndl = hndl
        ret._owned = owned
        return ret
    
    cpdef Expr getCount(self):
        if self.asActivityJoinSpecSelect().getCount() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asActivityJoinSpecSelect().getCount().accept(of._hndl)
            return <Expr>(of._obj)

cdef class MonitorActivitySelect(MonitorActivityStmt):
    
    cdef ast_decl.IMonitorActivitySelect *asMonitorActivitySelect(self):
        return dynamic_cast[ast_decl.IMonitorActivitySelectP](self._hndl)
    @staticmethod
    cdef MonitorActivitySelect mk(ast_decl.IMonitorActivitySelect *hndl, bool owned):
        '''Creates a Python wrapper around native class'''
        ret = MonitorActivitySelect()
        ret._hndl = hndl
        ret._owned = owned
        return ret
    
    cpdef ExprId getLabel(self):
        if self.asMonitorActivitySelect().getLabel() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asMonitorActivitySelect().getLabel().accept(of._hndl)
            return <ExprId>(of._obj)
    def branches(self) -> ListUtil:
        return ListUtil(self.numBranches, self.getBranche)
    
    cpdef getBranches(self):
        cdef const std_vector[ast_decl.IMonitorActivitySelectBranchUP] *__lp = &self.asMonitorActivitySelect().getBranches()
        cdef ast_decl.IMonitorActivitySelectBranch *__ep;
        ret = []
        of = ObjFactory()
        for __i in range(__lp.size()):
            __ep = __lp.at(__i).get()
            ret.append(__ep.accept(of._hndl))
        return ret
    cpdef getBranche(self, i):
        cdef ast_decl.IMonitorActivitySelectBranch *__ep = self.asMonitorActivitySelect().getBranches().at(i).get();
        of = ObjFactory()
        __ep.accept(of._hndl)
        return of._obj
    cpdef void addBranche(self, MonitorActivitySelectBranch i):
        i._owned = False
        self.asMonitorActivitySelect().getBranches().push_back(ast_decl.IMonitorActivitySelectBranchUP(i.asMonitorActivitySelectBranch(), True))
    cpdef numBranches(self):
        return self.asMonitorActivitySelect().getBranches().size()

cdef class ActivityLabeledStmt(ActivityStmt):
    
    cdef ast_decl.IActivityLabeledStmt *asActivityLabeledStmt(self):
        return dynamic_cast[ast_decl.IActivityLabeledStmtP](self._hndl)
    @staticmethod
    cdef ActivityLabeledStmt mk(ast_decl.IActivityLabeledStmt *hndl, bool owned):
        '''Creates a Python wrapper around native class'''
        ret = ActivityLabeledStmt()
        ret._hndl = hndl
        ret._owned = owned
        return ret
    
    cpdef ExprId getLabel(self):
        if self.asActivityLabeledStmt().getLabel() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asActivityLabeledStmt().getLabel().accept(of._hndl)
            return <ExprId>(of._obj)

cdef class MonitorConstraint(MonitorActivityStmt):
    
    cdef ast_decl.IMonitorConstraint *asMonitorConstraint(self):
        return dynamic_cast[ast_decl.IMonitorConstraintP](self._hndl)
    @staticmethod
    cdef MonitorConstraint mk(ast_decl.IMonitorConstraint *hndl, bool owned):
        '''Creates a Python wrapper around native class'''
        ret = MonitorConstraint()
        ret._hndl = hndl
        ret._owned = owned
        return ret
    
    cpdef ConstraintStmt getConstraint(self):
        if self.asMonitorConstraint().getConstraint() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asMonitorConstraint().getConstraint().accept(of._hndl)
            return <ConstraintStmt>(of._obj)

cdef class NamedScope(Scope):
    
    cdef ast_decl.INamedScope *asNamedScope(self):
        return dynamic_cast[ast_decl.INamedScopeP](self._hndl)
    @staticmethod
    cdef NamedScope mk(ast_decl.INamedScope *hndl, bool owned):
        '''Creates a Python wrapper around native class'''
        ret = NamedScope()
        ret._hndl = hndl
        ret._owned = owned
        return ret
    
    cpdef ExprId getName(self):
        if self.asNamedScope().getName() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asNamedScope().getName().accept(of._hndl)
            return <ExprId>(of._obj)

cdef class PackageScope(Scope):
    
    cdef ast_decl.IPackageScope *asPackageScope(self):
        return dynamic_cast[ast_decl.IPackageScopeP](self._hndl)
    @staticmethod
    cdef PackageScope mk(ast_decl.IPackageScope *hndl, bool owned):
        '''Creates a Python wrapper around native class'''
        ret = PackageScope()
        ret._hndl = hndl
        ret._owned = owned
        return ret
    
    def id(self) -> ListUtil:
        return ListUtil(self.numId, self.getId)
    
    cpdef getIdList(self):
        cdef const std_vector[ast_decl.IExprIdUP] *__lp = &self.asPackageScope().getId()
        cdef ast_decl.IExprId *__ep;
        ret = []
        of = ObjFactory()
        for __i in range(__lp.size()):
            __ep = __lp.at(__i).get()
            ret.append(__ep.accept(of._hndl))
        return ret
    cpdef getId(self, i):
        cdef ast_decl.IExprId *__ep = self.asPackageScope().getId().at(i).get();
        of = ObjFactory()
        __ep.accept(of._hndl)
        return of._obj
    cpdef void addId(self, ExprId i):
        i._owned = False
        self.asPackageScope().getId().push_back(ast_decl.IExprIdUP(i.asExprId(), True))
    cpdef numId(self):
        return self.asPackageScope().getId().size()
    cpdef PackageScope getSibling(self):
        if self.asPackageScope().getSibling() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asPackageScope().getSibling().accept(of._hndl)
            return <PackageScope>(of._obj)

cdef class ProceduralStmtAssignment(ExecStmt):
    
    cdef ast_decl.IProceduralStmtAssignment *asProceduralStmtAssignment(self):
        return dynamic_cast[ast_decl.IProceduralStmtAssignmentP](self._hndl)
    @staticmethod
    cdef ProceduralStmtAssignment mk(ast_decl.IProceduralStmtAssignment *hndl, bool owned):
        '''Creates a Python wrapper around native class'''
        ret = ProceduralStmtAssignment()
        ret._hndl = hndl
        ret._owned = owned
        return ret
    
    cpdef Expr getLhs(self):
        if self.asProceduralStmtAssignment().getLhs() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asProceduralStmtAssignment().getLhs().accept(of._hndl)
            return <Expr>(of._obj)
    cpdef  getOp(self):
        return dynamic_cast[ast_decl.IProceduralStmtAssignmentP](self._hndl).getOp()
    cpdef Expr getRhs(self):
        if self.asProceduralStmtAssignment().getRhs() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asProceduralStmtAssignment().getRhs().accept(of._hndl)
            return <Expr>(of._obj)

cdef class ProceduralStmtBody(ExecStmt):
    
    cdef ast_decl.IProceduralStmtBody *asProceduralStmtBody(self):
        return dynamic_cast[ast_decl.IProceduralStmtBodyP](self._hndl)
    @staticmethod
    cdef ProceduralStmtBody mk(ast_decl.IProceduralStmtBody *hndl, bool owned):
        '''Creates a Python wrapper around native class'''
        ret = ProceduralStmtBody()
        ret._hndl = hndl
        ret._owned = owned
        return ret
    
    cpdef ScopeChild getBody(self):
        if self.asProceduralStmtBody().getBody() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asProceduralStmtBody().getBody().accept(of._hndl)
            return <ScopeChild>(of._obj)

cdef class ProceduralStmtBreak(ExecStmt):
    
    cdef ast_decl.IProceduralStmtBreak *asProceduralStmtBreak(self):
        return dynamic_cast[ast_decl.IProceduralStmtBreakP](self._hndl)
    @staticmethod
    cdef ProceduralStmtBreak mk(ast_decl.IProceduralStmtBreak *hndl, bool owned):
        '''Creates a Python wrapper around native class'''
        ret = ProceduralStmtBreak()
        ret._hndl = hndl
        ret._owned = owned
        return ret
    

cdef class ProceduralStmtContinue(ExecStmt):
    
    cdef ast_decl.IProceduralStmtContinue *asProceduralStmtContinue(self):
        return dynamic_cast[ast_decl.IProceduralStmtContinueP](self._hndl)
    @staticmethod
    cdef ProceduralStmtContinue mk(ast_decl.IProceduralStmtContinue *hndl, bool owned):
        '''Creates a Python wrapper around native class'''
        ret = ProceduralStmtContinue()
        ret._hndl = hndl
        ret._owned = owned
        return ret
    

cdef class ProceduralStmtDataDeclaration(ExecStmt):
    
    cdef ast_decl.IProceduralStmtDataDeclaration *asProceduralStmtDataDeclaration(self):
        return dynamic_cast[ast_decl.IProceduralStmtDataDeclarationP](self._hndl)
    @staticmethod
    cdef ProceduralStmtDataDeclaration mk(ast_decl.IProceduralStmtDataDeclaration *hndl, bool owned):
        '''Creates a Python wrapper around native class'''
        ret = ProceduralStmtDataDeclaration()
        ret._hndl = hndl
        ret._owned = owned
        return ret
    
    cpdef ExprId getName(self):
        if self.asProceduralStmtDataDeclaration().getName() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asProceduralStmtDataDeclaration().getName().accept(of._hndl)
            return <ExprId>(of._obj)
    cpdef DataType getDatatype(self):
        if self.asProceduralStmtDataDeclaration().getDatatype() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asProceduralStmtDataDeclaration().getDatatype().accept(of._hndl)
            return <DataType>(of._obj)
    cpdef Expr getInit(self):
        if self.asProceduralStmtDataDeclaration().getInit() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asProceduralStmtDataDeclaration().getInit().accept(of._hndl)
            return <Expr>(of._obj)

cdef class ProceduralStmtExpr(ExecStmt):
    
    cdef ast_decl.IProceduralStmtExpr *asProceduralStmtExpr(self):
        return dynamic_cast[ast_decl.IProceduralStmtExprP](self._hndl)
    @staticmethod
    cdef ProceduralStmtExpr mk(ast_decl.IProceduralStmtExpr *hndl, bool owned):
        '''Creates a Python wrapper around native class'''
        ret = ProceduralStmtExpr()
        ret._hndl = hndl
        ret._owned = owned
        return ret
    
    cpdef Expr getExpr(self):
        if self.asProceduralStmtExpr().getExpr() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asProceduralStmtExpr().getExpr().accept(of._hndl)
            return <Expr>(of._obj)

cdef class ProceduralStmtFunctionCall(ExecStmt):
    
    cdef ast_decl.IProceduralStmtFunctionCall *asProceduralStmtFunctionCall(self):
        return dynamic_cast[ast_decl.IProceduralStmtFunctionCallP](self._hndl)
    @staticmethod
    cdef ProceduralStmtFunctionCall mk(ast_decl.IProceduralStmtFunctionCall *hndl, bool owned):
        '''Creates a Python wrapper around native class'''
        ret = ProceduralStmtFunctionCall()
        ret._hndl = hndl
        ret._owned = owned
        return ret
    
    cpdef ExprRefPathStaticRooted getPrefix(self):
        if self.asProceduralStmtFunctionCall().getPrefix() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asProceduralStmtFunctionCall().getPrefix().accept(of._hndl)
            return <ExprRefPathStaticRooted>(of._obj)
    def params(self) -> ListUtil:
        return ListUtil(self.numParams, self.getParam)
    
    cpdef getParams(self):
        cdef const std_vector[ast_decl.IExprUP] *__lp = &self.asProceduralStmtFunctionCall().getParams()
        cdef ast_decl.IExpr *__ep;
        ret = []
        of = ObjFactory()
        for __i in range(__lp.size()):
            __ep = __lp.at(__i).get()
            ret.append(__ep.accept(of._hndl))
        return ret
    cpdef getParam(self, i):
        cdef ast_decl.IExpr *__ep = self.asProceduralStmtFunctionCall().getParams().at(i).get();
        of = ObjFactory()
        __ep.accept(of._hndl)
        return of._obj
    cpdef void addParam(self, Expr i):
        i._owned = False
        self.asProceduralStmtFunctionCall().getParams().push_back(ast_decl.IExprUP(i.asExpr(), True))
    cpdef numParams(self):
        return self.asProceduralStmtFunctionCall().getParams().size()

cdef class ProceduralStmtIfElse(ExecStmt):
    
    cdef ast_decl.IProceduralStmtIfElse *asProceduralStmtIfElse(self):
        return dynamic_cast[ast_decl.IProceduralStmtIfElseP](self._hndl)
    @staticmethod
    cdef ProceduralStmtIfElse mk(ast_decl.IProceduralStmtIfElse *hndl, bool owned):
        '''Creates a Python wrapper around native class'''
        ret = ProceduralStmtIfElse()
        ret._hndl = hndl
        ret._owned = owned
        return ret
    
    def if_then(self) -> ListUtil:
        return ListUtil(self.numIf_then, self.getIf_then)
    
    cpdef getIf_thenList(self):
        cdef const std_vector[ast_decl.IProceduralStmtIfClauseUP] *__lp = &self.asProceduralStmtIfElse().getIf_then()
        cdef ast_decl.IProceduralStmtIfClause *__ep;
        ret = []
        of = ObjFactory()
        for __i in range(__lp.size()):
            __ep = __lp.at(__i).get()
            ret.append(__ep.accept(of._hndl))
        return ret
    cpdef getIf_then(self, i):
        cdef ast_decl.IProceduralStmtIfClause *__ep = self.asProceduralStmtIfElse().getIf_then().at(i).get();
        of = ObjFactory()
        __ep.accept(of._hndl)
        return of._obj
    cpdef void addIf_then(self, ProceduralStmtIfClause i):
        i._owned = False
        self.asProceduralStmtIfElse().getIf_then().push_back(ast_decl.IProceduralStmtIfClauseUP(i.asProceduralStmtIfClause(), True))
    cpdef numIf_then(self):
        return self.asProceduralStmtIfElse().getIf_then().size()
    cpdef ScopeChild getElse_then(self):
        if self.asProceduralStmtIfElse().getElse_then() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asProceduralStmtIfElse().getElse_then().accept(of._hndl)
            return <ScopeChild>(of._obj)

cdef class ProceduralStmtMatch(ExecStmt):
    
    cdef ast_decl.IProceduralStmtMatch *asProceduralStmtMatch(self):
        return dynamic_cast[ast_decl.IProceduralStmtMatchP](self._hndl)
    @staticmethod
    cdef ProceduralStmtMatch mk(ast_decl.IProceduralStmtMatch *hndl, bool owned):
        '''Creates a Python wrapper around native class'''
        ret = ProceduralStmtMatch()
        ret._hndl = hndl
        ret._owned = owned
        return ret
    
    cpdef Expr getExpr(self):
        if self.asProceduralStmtMatch().getExpr() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asProceduralStmtMatch().getExpr().accept(of._hndl)
            return <Expr>(of._obj)
    def choices(self) -> ListUtil:
        return ListUtil(self.numChoices, self.getChoice)
    
    cpdef getChoices(self):
        cdef const std_vector[ast_decl.IProceduralStmtMatchChoiceUP] *__lp = &self.asProceduralStmtMatch().getChoices()
        cdef ast_decl.IProceduralStmtMatchChoice *__ep;
        ret = []
        of = ObjFactory()
        for __i in range(__lp.size()):
            __ep = __lp.at(__i).get()
            ret.append(__ep.accept(of._hndl))
        return ret
    cpdef getChoice(self, i):
        cdef ast_decl.IProceduralStmtMatchChoice *__ep = self.asProceduralStmtMatch().getChoices().at(i).get();
        of = ObjFactory()
        __ep.accept(of._hndl)
        return of._obj
    cpdef void addChoice(self, ProceduralStmtMatchChoice i):
        i._owned = False
        self.asProceduralStmtMatch().getChoices().push_back(ast_decl.IProceduralStmtMatchChoiceUP(i.asProceduralStmtMatchChoice(), True))
    cpdef numChoices(self):
        return self.asProceduralStmtMatch().getChoices().size()

cdef class ProceduralStmtMatchChoice(ExecStmt):
    
    cdef ast_decl.IProceduralStmtMatchChoice *asProceduralStmtMatchChoice(self):
        return dynamic_cast[ast_decl.IProceduralStmtMatchChoiceP](self._hndl)
    @staticmethod
    cdef ProceduralStmtMatchChoice mk(ast_decl.IProceduralStmtMatchChoice *hndl, bool owned):
        '''Creates a Python wrapper around native class'''
        ret = ProceduralStmtMatchChoice()
        ret._hndl = hndl
        ret._owned = owned
        return ret
    
    cpdef bool getIs_default(self):
        return dynamic_cast[ast_decl.IProceduralStmtMatchChoiceP](self._hndl).getIs_default()
    cpdef ExprOpenRangeList getCond(self):
        if self.asProceduralStmtMatchChoice().getCond() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asProceduralStmtMatchChoice().getCond().accept(of._hndl)
            return <ExprOpenRangeList>(of._obj)
    cpdef ScopeChild getBody(self):
        if self.asProceduralStmtMatchChoice().getBody() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asProceduralStmtMatchChoice().getBody().accept(of._hndl)
            return <ScopeChild>(of._obj)

cdef class ProceduralStmtRandomize(ExecStmt):
    
    cdef ast_decl.IProceduralStmtRandomize *asProceduralStmtRandomize(self):
        return dynamic_cast[ast_decl.IProceduralStmtRandomizeP](self._hndl)
    @staticmethod
    cdef ProceduralStmtRandomize mk(ast_decl.IProceduralStmtRandomize *hndl, bool owned):
        '''Creates a Python wrapper around native class'''
        ret = ProceduralStmtRandomize()
        ret._hndl = hndl
        ret._owned = owned
        return ret
    
    cpdef Expr getTarget(self):
        if self.asProceduralStmtRandomize().getTarget() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asProceduralStmtRandomize().getTarget().accept(of._hndl)
            return <Expr>(of._obj)
    def constraints(self) -> ListUtil:
        return ListUtil(self.numConstraints, self.getConstraint)
    
    cpdef getConstraints(self):
        cdef const std_vector[ast_decl.IConstraintStmtUP] *__lp = &self.asProceduralStmtRandomize().getConstraints()
        cdef ast_decl.IConstraintStmt *__ep;
        ret = []
        of = ObjFactory()
        for __i in range(__lp.size()):
            __ep = __lp.at(__i).get()
            ret.append(__ep.accept(of._hndl))
        return ret
    cpdef getConstraint(self, i):
        cdef ast_decl.IConstraintStmt *__ep = self.asProceduralStmtRandomize().getConstraints().at(i).get();
        of = ObjFactory()
        __ep.accept(of._hndl)
        return of._obj
    cpdef void addConstraint(self, ConstraintStmt i):
        i._owned = False
        self.asProceduralStmtRandomize().getConstraints().push_back(ast_decl.IConstraintStmtUP(i.asConstraintStmt(), True))
    cpdef numConstraints(self):
        return self.asProceduralStmtRandomize().getConstraints().size()

cdef class ProceduralStmtReturn(ExecStmt):
    
    cdef ast_decl.IProceduralStmtReturn *asProceduralStmtReturn(self):
        return dynamic_cast[ast_decl.IProceduralStmtReturnP](self._hndl)
    @staticmethod
    cdef ProceduralStmtReturn mk(ast_decl.IProceduralStmtReturn *hndl, bool owned):
        '''Creates a Python wrapper around native class'''
        ret = ProceduralStmtReturn()
        ret._hndl = hndl
        ret._owned = owned
        return ret
    
    cpdef Expr getExpr(self):
        if self.asProceduralStmtReturn().getExpr() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asProceduralStmtReturn().getExpr().accept(of._hndl)
            return <Expr>(of._obj)

cdef class ConstraintScope(ConstraintStmt):
    
    cdef ast_decl.IConstraintScope *asConstraintScope(self):
        return dynamic_cast[ast_decl.IConstraintScopeP](self._hndl)
    @staticmethod
    cdef ConstraintScope mk(ast_decl.IConstraintScope *hndl, bool owned):
        '''Creates a Python wrapper around native class'''
        ret = ConstraintScope()
        ret._hndl = hndl
        ret._owned = owned
        return ret
    
    cpdef Location getEndLocation(self):
        return Location.wrap(dynamic_cast[ast_decl.IConstraintScopeP](self._hndl).getEndLocation())
    def constraints(self) -> ListUtil:
        return ListUtil(self.numConstraints, self.getConstraint)
    
    cpdef getConstraints(self):
        cdef const std_vector[ast_decl.IConstraintStmtUP] *__lp = &self.asConstraintScope().getConstraints()
        cdef ast_decl.IConstraintStmt *__ep;
        ret = []
        of = ObjFactory()
        for __i in range(__lp.size()):
            __ep = __lp.at(__i).get()
            ret.append(__ep.accept(of._hndl))
        return ret
    cpdef getConstraint(self, i):
        cdef ast_decl.IConstraintStmt *__ep = self.asConstraintScope().getConstraints().at(i).get();
        of = ObjFactory()
        __ep.accept(of._hndl)
        return of._obj
    cpdef void addConstraint(self, ConstraintStmt i):
        i._owned = False
        self.asConstraintScope().getConstraints().push_back(ast_decl.IConstraintStmtUP(i.asConstraintStmt(), True))
    cpdef numConstraints(self):
        return self.asConstraintScope().getConstraints().size()

cdef class ConstraintStmtDefault(ConstraintStmt):
    
    cdef ast_decl.IConstraintStmtDefault *asConstraintStmtDefault(self):
        return dynamic_cast[ast_decl.IConstraintStmtDefaultP](self._hndl)
    @staticmethod
    cdef ConstraintStmtDefault mk(ast_decl.IConstraintStmtDefault *hndl, bool owned):
        '''Creates a Python wrapper around native class'''
        ret = ConstraintStmtDefault()
        ret._hndl = hndl
        ret._owned = owned
        return ret
    
    cpdef ExprHierarchicalId getHid(self):
        if self.asConstraintStmtDefault().getHid() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asConstraintStmtDefault().getHid().accept(of._hndl)
            return <ExprHierarchicalId>(of._obj)
    cpdef Expr getExpr(self):
        if self.asConstraintStmtDefault().getExpr() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asConstraintStmtDefault().getExpr().accept(of._hndl)
            return <Expr>(of._obj)

cdef class ConstraintStmtDefaultDisable(ConstraintStmt):
    
    cdef ast_decl.IConstraintStmtDefaultDisable *asConstraintStmtDefaultDisable(self):
        return dynamic_cast[ast_decl.IConstraintStmtDefaultDisableP](self._hndl)
    @staticmethod
    cdef ConstraintStmtDefaultDisable mk(ast_decl.IConstraintStmtDefaultDisable *hndl, bool owned):
        '''Creates a Python wrapper around native class'''
        ret = ConstraintStmtDefaultDisable()
        ret._hndl = hndl
        ret._owned = owned
        return ret
    
    cpdef ExprHierarchicalId getHid(self):
        if self.asConstraintStmtDefaultDisable().getHid() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asConstraintStmtDefaultDisable().getHid().accept(of._hndl)
            return <ExprHierarchicalId>(of._obj)

cdef class ConstraintStmtExpr(ConstraintStmt):
    
    cdef ast_decl.IConstraintStmtExpr *asConstraintStmtExpr(self):
        return dynamic_cast[ast_decl.IConstraintStmtExprP](self._hndl)
    @staticmethod
    cdef ConstraintStmtExpr mk(ast_decl.IConstraintStmtExpr *hndl, bool owned):
        '''Creates a Python wrapper around native class'''
        ret = ConstraintStmtExpr()
        ret._hndl = hndl
        ret._owned = owned
        return ret
    
    cpdef Expr getExpr(self):
        if self.asConstraintStmtExpr().getExpr() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asConstraintStmtExpr().getExpr().accept(of._hndl)
            return <Expr>(of._obj)

cdef class ConstraintStmtField(ConstraintStmt):
    
    cdef ast_decl.IConstraintStmtField *asConstraintStmtField(self):
        return dynamic_cast[ast_decl.IConstraintStmtFieldP](self._hndl)
    @staticmethod
    cdef ConstraintStmtField mk(ast_decl.IConstraintStmtField *hndl, bool owned):
        '''Creates a Python wrapper around native class'''
        ret = ConstraintStmtField()
        ret._hndl = hndl
        ret._owned = owned
        return ret
    
    cpdef ExprId getName(self):
        if self.asConstraintStmtField().getName() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asConstraintStmtField().getName().accept(of._hndl)
            return <ExprId>(of._obj)
    cpdef DataType getType(self):
        if self.asConstraintStmtField().getType() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asConstraintStmtField().getType().accept(of._hndl)
            return <DataType>(of._obj)

cdef class ProceduralStmtYield(ExecStmt):
    
    cdef ast_decl.IProceduralStmtYield *asProceduralStmtYield(self):
        return dynamic_cast[ast_decl.IProceduralStmtYieldP](self._hndl)
    @staticmethod
    cdef ProceduralStmtYield mk(ast_decl.IProceduralStmtYield *hndl, bool owned):
        '''Creates a Python wrapper around native class'''
        ret = ProceduralStmtYield()
        ret._hndl = hndl
        ret._owned = owned
        return ret
    

cdef class ConstraintStmtIf(ConstraintStmt):
    
    cdef ast_decl.IConstraintStmtIf *asConstraintStmtIf(self):
        return dynamic_cast[ast_decl.IConstraintStmtIfP](self._hndl)
    @staticmethod
    cdef ConstraintStmtIf mk(ast_decl.IConstraintStmtIf *hndl, bool owned):
        '''Creates a Python wrapper around native class'''
        ret = ConstraintStmtIf()
        ret._hndl = hndl
        ret._owned = owned
        return ret
    
    cpdef Expr getCond(self):
        if self.asConstraintStmtIf().getCond() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asConstraintStmtIf().getCond().accept(of._hndl)
            return <Expr>(of._obj)
    cpdef ConstraintScope getTrue_c(self):
        if self.asConstraintStmtIf().getTrue_c() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asConstraintStmtIf().getTrue_c().accept(of._hndl)
            return <ConstraintScope>(of._obj)
    cpdef ConstraintScope getFalse_c(self):
        if self.asConstraintStmtIf().getFalse_c() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asConstraintStmtIf().getFalse_c().accept(of._hndl)
            return <ConstraintScope>(of._obj)

cdef class ConstraintStmtUnique(ConstraintStmt):
    
    cdef ast_decl.IConstraintStmtUnique *asConstraintStmtUnique(self):
        return dynamic_cast[ast_decl.IConstraintStmtUniqueP](self._hndl)
    @staticmethod
    cdef ConstraintStmtUnique mk(ast_decl.IConstraintStmtUnique *hndl, bool owned):
        '''Creates a Python wrapper around native class'''
        ret = ConstraintStmtUnique()
        ret._hndl = hndl
        ret._owned = owned
        return ret
    
    def list(self) -> ListUtil:
        return ListUtil(self.numList, self.getList)
    
    cpdef getListList(self):
        cdef const std_vector[ast_decl.IExprHierarchicalIdUP] *__lp = &self.asConstraintStmtUnique().getList()
        cdef ast_decl.IExprHierarchicalId *__ep;
        ret = []
        of = ObjFactory()
        for __i in range(__lp.size()):
            __ep = __lp.at(__i).get()
            ret.append(__ep.accept(of._hndl))
        return ret
    cpdef getList(self, i):
        cdef ast_decl.IExprHierarchicalId *__ep = self.asConstraintStmtUnique().getList().at(i).get();
        of = ObjFactory()
        __ep.accept(of._hndl)
        return of._obj
    cpdef void addList(self, ExprHierarchicalId i):
        i._owned = False
        self.asConstraintStmtUnique().getList().push_back(ast_decl.IExprHierarchicalIdUP(i.asExprHierarchicalId(), True))
    cpdef numList(self):
        return self.asConstraintStmtUnique().getList().size()

cdef class SymbolChildrenScope(SymbolChild):
    
    cdef ast_decl.ISymbolChildrenScope *asSymbolChildrenScope(self):
        return dynamic_cast[ast_decl.ISymbolChildrenScopeP](self._hndl)
    @staticmethod
    cdef SymbolChildrenScope mk(ast_decl.ISymbolChildrenScope *hndl, bool owned):
        '''Creates a Python wrapper around native class'''
        ret = SymbolChildrenScope()
        ret._hndl = hndl
        ret._owned = owned
        return ret
    
    cpdef str getName(self):
        return dynamic_cast[ast_decl.ISymbolChildrenScopeP](self._hndl).getName().decode()
    cpdef void setName(self, str v):
        dynamic_cast[ast_decl.ISymbolChildrenScopeP](self._hndl).setName(v.encode())
    def children(self) -> ListUtil:
        return ListUtil(self.numChildren, self.getChild)
    
    cpdef getChildren(self):
        cdef const std_vector[ast_decl.IScopeChildUP] *__lp = &self.asSymbolChildrenScope().getChildren()
        cdef ast_decl.IScopeChild *__ep;
        ret = []
        of = ObjFactory()
        for __i in range(__lp.size()):
            __ep = __lp.at(__i).get()
            ret.append(__ep.accept(of._hndl))
        return ret
    cpdef getChild(self, i):
        cdef ast_decl.IScopeChild *__ep = self.asSymbolChildrenScope().getChildren().at(i).get();
        of = ObjFactory()
        __ep.accept(of._hndl)
        return of._obj
    cpdef void addChild(self, ScopeChild i):
        i._owned = False
        self.asSymbolChildrenScope().getChildren().push_back(ast_decl.IScopeChildUP(i.asScopeChild(), True))
    cpdef numChildren(self):
        return self.asSymbolChildrenScope().getChildren().size()
    cpdef ScopeChild getTarget(self):
        if self.asSymbolChildrenScope().getTarget() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asSymbolChildrenScope().getTarget().accept(of._hndl)
            return <ScopeChild>(of._obj)

cdef class DataTypeBool(DataType):
    
    cdef ast_decl.IDataTypeBool *asDataTypeBool(self):
        return dynamic_cast[ast_decl.IDataTypeBoolP](self._hndl)
    @staticmethod
    cdef DataTypeBool mk(ast_decl.IDataTypeBool *hndl, bool owned):
        '''Creates a Python wrapper around native class'''
        ret = DataTypeBool()
        ret._hndl = hndl
        ret._owned = owned
        return ret
    

cdef class DataTypeChandle(DataType):
    
    cdef ast_decl.IDataTypeChandle *asDataTypeChandle(self):
        return dynamic_cast[ast_decl.IDataTypeChandleP](self._hndl)
    @staticmethod
    cdef DataTypeChandle mk(ast_decl.IDataTypeChandle *hndl, bool owned):
        '''Creates a Python wrapper around native class'''
        ret = DataTypeChandle()
        ret._hndl = hndl
        ret._owned = owned
        return ret
    

cdef class DataTypeEnum(DataType):
    
    cdef ast_decl.IDataTypeEnum *asDataTypeEnum(self):
        return dynamic_cast[ast_decl.IDataTypeEnumP](self._hndl)
    @staticmethod
    cdef DataTypeEnum mk(ast_decl.IDataTypeEnum *hndl, bool owned):
        '''Creates a Python wrapper around native class'''
        ret = DataTypeEnum()
        ret._hndl = hndl
        ret._owned = owned
        return ret
    
    cpdef DataTypeUserDefined getTid(self):
        if self.asDataTypeEnum().getTid() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asDataTypeEnum().getTid().accept(of._hndl)
            return <DataTypeUserDefined>(of._obj)
    cpdef ExprOpenRangeList getIn_rangelist(self):
        if self.asDataTypeEnum().getIn_rangelist() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asDataTypeEnum().getIn_rangelist().accept(of._hndl)
            return <ExprOpenRangeList>(of._obj)

cdef class DataTypeInt(DataType):
    
    cdef ast_decl.IDataTypeInt *asDataTypeInt(self):
        return dynamic_cast[ast_decl.IDataTypeIntP](self._hndl)
    @staticmethod
    cdef DataTypeInt mk(ast_decl.IDataTypeInt *hndl, bool owned):
        '''Creates a Python wrapper around native class'''
        ret = DataTypeInt()
        ret._hndl = hndl
        ret._owned = owned
        return ret
    
    cpdef bool getIs_signed(self):
        return dynamic_cast[ast_decl.IDataTypeIntP](self._hndl).getIs_signed()
    cpdef Expr getWidth(self):
        if self.asDataTypeInt().getWidth() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asDataTypeInt().getWidth().accept(of._hndl)
            return <Expr>(of._obj)
    cpdef ExprDomainOpenRangeList getIn_range(self):
        if self.asDataTypeInt().getIn_range() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asDataTypeInt().getIn_range().accept(of._hndl)
            return <ExprDomainOpenRangeList>(of._obj)

cdef class DataTypePyObj(DataType):
    
    cdef ast_decl.IDataTypePyObj *asDataTypePyObj(self):
        return dynamic_cast[ast_decl.IDataTypePyObjP](self._hndl)
    @staticmethod
    cdef DataTypePyObj mk(ast_decl.IDataTypePyObj *hndl, bool owned):
        '''Creates a Python wrapper around native class'''
        ret = DataTypePyObj()
        ret._hndl = hndl
        ret._owned = owned
        return ret
    

cdef class DataTypeRef(DataType):
    
    cdef ast_decl.IDataTypeRef *asDataTypeRef(self):
        return dynamic_cast[ast_decl.IDataTypeRefP](self._hndl)
    @staticmethod
    cdef DataTypeRef mk(ast_decl.IDataTypeRef *hndl, bool owned):
        '''Creates a Python wrapper around native class'''
        ret = DataTypeRef()
        ret._hndl = hndl
        ret._owned = owned
        return ret
    
    cpdef DataTypeUserDefined getType(self):
        if self.asDataTypeRef().getType() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asDataTypeRef().getType().accept(of._hndl)
            return <DataTypeUserDefined>(of._obj)

cdef class DataTypeString(DataType):
    
    cdef ast_decl.IDataTypeString *asDataTypeString(self):
        return dynamic_cast[ast_decl.IDataTypeStringP](self._hndl)
    @staticmethod
    cdef DataTypeString mk(ast_decl.IDataTypeString *hndl, bool owned):
        '''Creates a Python wrapper around native class'''
        ret = DataTypeString()
        ret._hndl = hndl
        ret._owned = owned
        return ret
    
    cpdef bool getHas_range(self):
        return dynamic_cast[ast_decl.IDataTypeStringP](self._hndl).getHas_range()
    def in_range(self) -> ListUtil:
        return ListUtil(self.numIn_range, self.getIn_range)
    

cdef class DataTypeUserDefined(DataType):
    
    cdef ast_decl.IDataTypeUserDefined *asDataTypeUserDefined(self):
        return dynamic_cast[ast_decl.IDataTypeUserDefinedP](self._hndl)
    @staticmethod
    cdef DataTypeUserDefined mk(ast_decl.IDataTypeUserDefined *hndl, bool owned):
        '''Creates a Python wrapper around native class'''
        ret = DataTypeUserDefined()
        ret._hndl = hndl
        ret._owned = owned
        return ret
    
    cpdef bool getIs_global(self):
        return dynamic_cast[ast_decl.IDataTypeUserDefinedP](self._hndl).getIs_global()
    cpdef TypeIdentifier getType_id(self):
        if self.asDataTypeUserDefined().getType_id() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asDataTypeUserDefined().getType_id().accept(of._hndl)
            return <TypeIdentifier>(of._obj)

cdef class EnumDecl(NamedScopeChild):
    
    cdef ast_decl.IEnumDecl *asEnumDecl(self):
        return dynamic_cast[ast_decl.IEnumDeclP](self._hndl)
    @staticmethod
    cdef EnumDecl mk(ast_decl.IEnumDecl *hndl, bool owned):
        '''Creates a Python wrapper around native class'''
        ret = EnumDecl()
        ret._hndl = hndl
        ret._owned = owned
        return ret
    
    def items(self) -> ListUtil:
        return ListUtil(self.numItems, self.getItem)
    
    cpdef getItems(self):
        cdef const std_vector[ast_decl.IEnumItemUP] *__lp = &self.asEnumDecl().getItems()
        cdef ast_decl.IEnumItem *__ep;
        ret = []
        of = ObjFactory()
        for __i in range(__lp.size()):
            __ep = __lp.at(__i).get()
            ret.append(__ep.accept(of._hndl))
        return ret
    cpdef getItem(self, i):
        cdef ast_decl.IEnumItem *__ep = self.asEnumDecl().getItems().at(i).get();
        of = ObjFactory()
        __ep.accept(of._hndl)
        return of._obj
    cpdef void addItem(self, EnumItem i):
        i._owned = False
        self.asEnumDecl().getItems().push_back(ast_decl.IEnumItemUP(i.asEnumItem(), True))
    cpdef numItems(self):
        return self.asEnumDecl().getItems().size()

cdef class EnumItem(NamedScopeChild):
    
    cdef ast_decl.IEnumItem *asEnumItem(self):
        return dynamic_cast[ast_decl.IEnumItemP](self._hndl)
    @staticmethod
    cdef EnumItem mk(ast_decl.IEnumItem *hndl, bool owned):
        '''Creates a Python wrapper around native class'''
        ret = EnumItem()
        ret._hndl = hndl
        ret._owned = owned
        return ret
    
    cpdef Expr getValue(self):
        if self.asEnumItem().getValue() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asEnumItem().getValue().accept(of._hndl)
            return <Expr>(of._obj)
    cpdef SymbolEnumScope getUpper(self):
        if self.asEnumItem().getUpper() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asEnumItem().getUpper().accept(of._hndl)
            return <SymbolEnumScope>(of._obj)

cdef class TemplateCategoryTypeParamDecl(TemplateParamDecl):
    
    cdef ast_decl.ITemplateCategoryTypeParamDecl *asTemplateCategoryTypeParamDecl(self):
        return dynamic_cast[ast_decl.ITemplateCategoryTypeParamDeclP](self._hndl)
    @staticmethod
    cdef TemplateCategoryTypeParamDecl mk(ast_decl.ITemplateCategoryTypeParamDecl *hndl, bool owned):
        '''Creates a Python wrapper around native class'''
        ret = TemplateCategoryTypeParamDecl()
        ret._hndl = hndl
        ret._owned = owned
        return ret
    
    cpdef  getCategory(self):
        return dynamic_cast[ast_decl.ITemplateCategoryTypeParamDeclP](self._hndl).getCategory()
    cpdef TypeIdentifier getRestriction(self):
        if self.asTemplateCategoryTypeParamDecl().getRestriction() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asTemplateCategoryTypeParamDecl().getRestriction().accept(of._hndl)
            return <TypeIdentifier>(of._obj)
    cpdef DataType getDflt(self):
        if self.asTemplateCategoryTypeParamDecl().getDflt() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asTemplateCategoryTypeParamDecl().getDflt().accept(of._hndl)
            return <DataType>(of._obj)

cdef class TemplateGenericTypeParamDecl(TemplateParamDecl):
    
    cdef ast_decl.ITemplateGenericTypeParamDecl *asTemplateGenericTypeParamDecl(self):
        return dynamic_cast[ast_decl.ITemplateGenericTypeParamDeclP](self._hndl)
    @staticmethod
    cdef TemplateGenericTypeParamDecl mk(ast_decl.ITemplateGenericTypeParamDecl *hndl, bool owned):
        '''Creates a Python wrapper around native class'''
        ret = TemplateGenericTypeParamDecl()
        ret._hndl = hndl
        ret._owned = owned
        return ret
    
    cpdef DataType getDflt(self):
        if self.asTemplateGenericTypeParamDecl().getDflt() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asTemplateGenericTypeParamDecl().getDflt().accept(of._hndl)
            return <DataType>(of._obj)

cdef class ExprAggrEmpty(ExprAggrLiteral):
    
    cdef ast_decl.IExprAggrEmpty *asExprAggrEmpty(self):
        return dynamic_cast[ast_decl.IExprAggrEmptyP](self._hndl)
    @staticmethod
    cdef ExprAggrEmpty mk(ast_decl.IExprAggrEmpty *hndl, bool owned):
        '''Creates a Python wrapper around native class'''
        ret = ExprAggrEmpty()
        ret._hndl = hndl
        ret._owned = owned
        return ret
    

cdef class ExprAggrList(ExprAggrLiteral):
    
    cdef ast_decl.IExprAggrList *asExprAggrList(self):
        return dynamic_cast[ast_decl.IExprAggrListP](self._hndl)
    @staticmethod
    cdef ExprAggrList mk(ast_decl.IExprAggrList *hndl, bool owned):
        '''Creates a Python wrapper around native class'''
        ret = ExprAggrList()
        ret._hndl = hndl
        ret._owned = owned
        return ret
    
    def elems(self) -> ListUtil:
        return ListUtil(self.numElems, self.getElem)
    
    cpdef getElems(self):
        cdef const std_vector[ast_decl.IExprUP] *__lp = &self.asExprAggrList().getElems()
        cdef ast_decl.IExpr *__ep;
        ret = []
        of = ObjFactory()
        for __i in range(__lp.size()):
            __ep = __lp.at(__i).get()
            ret.append(__ep.accept(of._hndl))
        return ret
    cpdef getElem(self, i):
        cdef ast_decl.IExpr *__ep = self.asExprAggrList().getElems().at(i).get();
        of = ObjFactory()
        __ep.accept(of._hndl)
        return of._obj
    cpdef void addElem(self, Expr i):
        i._owned = False
        self.asExprAggrList().getElems().push_back(ast_decl.IExprUP(i.asExpr(), True))
    cpdef numElems(self):
        return self.asExprAggrList().getElems().size()

cdef class TemplateValueParamDecl(TemplateParamDecl):
    
    cdef ast_decl.ITemplateValueParamDecl *asTemplateValueParamDecl(self):
        return dynamic_cast[ast_decl.ITemplateValueParamDeclP](self._hndl)
    @staticmethod
    cdef TemplateValueParamDecl mk(ast_decl.ITemplateValueParamDecl *hndl, bool owned):
        '''Creates a Python wrapper around native class'''
        ret = TemplateValueParamDecl()
        ret._hndl = hndl
        ret._owned = owned
        return ret
    
    cpdef DataType getType(self):
        if self.asTemplateValueParamDecl().getType() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asTemplateValueParamDecl().getType().accept(of._hndl)
            return <DataType>(of._obj)
    cpdef Expr getDflt(self):
        if self.asTemplateValueParamDecl().getDflt() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asTemplateValueParamDecl().getDflt().accept(of._hndl)
            return <Expr>(of._obj)

cdef class ExprAggrMap(ExprAggrLiteral):
    
    cdef ast_decl.IExprAggrMap *asExprAggrMap(self):
        return dynamic_cast[ast_decl.IExprAggrMapP](self._hndl)
    @staticmethod
    cdef ExprAggrMap mk(ast_decl.IExprAggrMap *hndl, bool owned):
        '''Creates a Python wrapper around native class'''
        ret = ExprAggrMap()
        ret._hndl = hndl
        ret._owned = owned
        return ret
    
    def elems(self) -> ListUtil:
        return ListUtil(self.numElems, self.getElem)
    
    cpdef getElems(self):
        cdef const std_vector[ast_decl.IExprAggrMapElemUP] *__lp = &self.asExprAggrMap().getElems()
        cdef ast_decl.IExprAggrMapElem *__ep;
        ret = []
        of = ObjFactory()
        for __i in range(__lp.size()):
            __ep = __lp.at(__i).get()
            ret.append(__ep.accept(of._hndl))
        return ret
    cpdef getElem(self, i):
        cdef ast_decl.IExprAggrMapElem *__ep = self.asExprAggrMap().getElems().at(i).get();
        of = ObjFactory()
        __ep.accept(of._hndl)
        return of._obj
    cpdef void addElem(self, ExprAggrMapElem i):
        i._owned = False
        self.asExprAggrMap().getElems().push_back(ast_decl.IExprAggrMapElemUP(i.asExprAggrMapElem(), True))
    cpdef numElems(self):
        return self.asExprAggrMap().getElems().size()

cdef class ExprAggrStruct(ExprAggrLiteral):
    
    cdef ast_decl.IExprAggrStruct *asExprAggrStruct(self):
        return dynamic_cast[ast_decl.IExprAggrStructP](self._hndl)
    @staticmethod
    cdef ExprAggrStruct mk(ast_decl.IExprAggrStruct *hndl, bool owned):
        '''Creates a Python wrapper around native class'''
        ret = ExprAggrStruct()
        ret._hndl = hndl
        ret._owned = owned
        return ret
    
    def elems(self) -> ListUtil:
        return ListUtil(self.numElems, self.getElem)
    
    cpdef getElems(self):
        cdef const std_vector[ast_decl.IExprAggrStructElemUP] *__lp = &self.asExprAggrStruct().getElems()
        cdef ast_decl.IExprAggrStructElem *__ep;
        ret = []
        of = ObjFactory()
        for __i in range(__lp.size()):
            __ep = __lp.at(__i).get()
            ret.append(__ep.accept(of._hndl))
        return ret
    cpdef getElem(self, i):
        cdef ast_decl.IExprAggrStructElem *__ep = self.asExprAggrStruct().getElems().at(i).get();
        of = ObjFactory()
        __ep.accept(of._hndl)
        return of._obj
    cpdef void addElem(self, ExprAggrStructElem i):
        i._owned = False
        self.asExprAggrStruct().getElems().push_back(ast_decl.IExprAggrStructElemUP(i.asExprAggrStructElem(), True))
    cpdef numElems(self):
        return self.asExprAggrStruct().getElems().size()

cdef class ExprRefPathContext(ExprRefPath):
    
    cdef ast_decl.IExprRefPathContext *asExprRefPathContext(self):
        return dynamic_cast[ast_decl.IExprRefPathContextP](self._hndl)
    @staticmethod
    cdef ExprRefPathContext mk(ast_decl.IExprRefPathContext *hndl, bool owned):
        '''Creates a Python wrapper around native class'''
        ret = ExprRefPathContext()
        ret._hndl = hndl
        ret._owned = owned
        return ret
    
    cpdef bool getIs_super(self):
        return dynamic_cast[ast_decl.IExprRefPathContextP](self._hndl).getIs_super()
    cpdef ExprHierarchicalId getHier_id(self):
        if self.asExprRefPathContext().getHier_id() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asExprRefPathContext().getHier_id().accept(of._hndl)
            return <ExprHierarchicalId>(of._obj)
    cpdef ExprBitSlice getSlice(self):
        if self.asExprRefPathContext().getSlice() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asExprRefPathContext().getSlice().accept(of._hndl)
            return <ExprBitSlice>(of._obj)

cdef class ExprRefPathId(ExprRefPath):
    
    cdef ast_decl.IExprRefPathId *asExprRefPathId(self):
        return dynamic_cast[ast_decl.IExprRefPathIdP](self._hndl)
    @staticmethod
    cdef ExprRefPathId mk(ast_decl.IExprRefPathId *hndl, bool owned):
        '''Creates a Python wrapper around native class'''
        ret = ExprRefPathId()
        ret._hndl = hndl
        ret._owned = owned
        return ret
    
    cpdef ExprId getId(self):
        if self.asExprRefPathId().getId() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asExprRefPathId().getId().accept(of._hndl)
            return <ExprId>(of._obj)
    cpdef ExprBitSlice getSlice(self):
        if self.asExprRefPathId().getSlice() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asExprRefPathId().getSlice().accept(of._hndl)
            return <ExprBitSlice>(of._obj)

cdef class ExprRefPathStatic(ExprRefPath):
    
    cdef ast_decl.IExprRefPathStatic *asExprRefPathStatic(self):
        return dynamic_cast[ast_decl.IExprRefPathStaticP](self._hndl)
    @staticmethod
    cdef ExprRefPathStatic mk(ast_decl.IExprRefPathStatic *hndl, bool owned):
        '''Creates a Python wrapper around native class'''
        ret = ExprRefPathStatic()
        ret._hndl = hndl
        ret._owned = owned
        return ret
    
    cpdef bool getIs_global(self):
        return dynamic_cast[ast_decl.IExprRefPathStaticP](self._hndl).getIs_global()
    def base(self) -> ListUtil:
        return ListUtil(self.numBase, self.getBase)
    
    cpdef getBaseList(self):
        cdef const std_vector[ast_decl.ITypeIdentifierElemUP] *__lp = &self.asExprRefPathStatic().getBase()
        cdef ast_decl.ITypeIdentifierElem *__ep;
        ret = []
        of = ObjFactory()
        for __i in range(__lp.size()):
            __ep = __lp.at(__i).get()
            ret.append(__ep.accept(of._hndl))
        return ret
    cpdef getBase(self, i):
        cdef ast_decl.ITypeIdentifierElem *__ep = self.asExprRefPathStatic().getBase().at(i).get();
        of = ObjFactory()
        __ep.accept(of._hndl)
        return of._obj
    cpdef void addBase(self, TypeIdentifierElem i):
        i._owned = False
        self.asExprRefPathStatic().getBase().push_back(ast_decl.ITypeIdentifierElemUP(i.asTypeIdentifierElem(), True))
    cpdef numBase(self):
        return self.asExprRefPathStatic().getBase().size()
    cpdef ExprBitSlice getSlice(self):
        if self.asExprRefPathStatic().getSlice() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asExprRefPathStatic().getSlice().accept(of._hndl)
            return <ExprBitSlice>(of._obj)

cdef class ExprRefPathStaticRooted(ExprRefPath):
    
    cdef ast_decl.IExprRefPathStaticRooted *asExprRefPathStaticRooted(self):
        return dynamic_cast[ast_decl.IExprRefPathStaticRootedP](self._hndl)
    @staticmethod
    cdef ExprRefPathStaticRooted mk(ast_decl.IExprRefPathStaticRooted *hndl, bool owned):
        '''Creates a Python wrapper around native class'''
        ret = ExprRefPathStaticRooted()
        ret._hndl = hndl
        ret._owned = owned
        return ret
    
    cpdef ExprRefPathStatic getRoot(self):
        if self.asExprRefPathStaticRooted().getRoot() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asExprRefPathStaticRooted().getRoot().accept(of._hndl)
            return <ExprRefPathStatic>(of._obj)
    cpdef ExprHierarchicalId getLeaf(self):
        if self.asExprRefPathStaticRooted().getLeaf() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asExprRefPathStaticRooted().getLeaf().accept(of._hndl)
            return <ExprHierarchicalId>(of._obj)
    cpdef ExprBitSlice getSlice(self):
        if self.asExprRefPathStaticRooted().getSlice() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asExprRefPathStaticRooted().getSlice().accept(of._hndl)
            return <ExprBitSlice>(of._obj)

cdef class ExprSignedNumber(ExprNumber):
    
    cdef ast_decl.IExprSignedNumber *asExprSignedNumber(self):
        return dynamic_cast[ast_decl.IExprSignedNumberP](self._hndl)
    @staticmethod
    cdef ExprSignedNumber mk(ast_decl.IExprSignedNumber *hndl, bool owned):
        '''Creates a Python wrapper around native class'''
        ret = ExprSignedNumber()
        ret._hndl = hndl
        ret._owned = owned
        return ret
    
    cpdef str getImage(self):
        return dynamic_cast[ast_decl.IExprSignedNumberP](self._hndl).getImage().decode()
    cpdef void setImage(self, str v):
        dynamic_cast[ast_decl.IExprSignedNumberP](self._hndl).setImage(v.encode())
    cpdef int32_t getWidth(self):
        return dynamic_cast[ast_decl.IExprSignedNumberP](self._hndl).getWidth()
    cpdef int64_t getValue(self):
        return dynamic_cast[ast_decl.IExprSignedNumberP](self._hndl).getValue()

cdef class ExprUnsignedNumber(ExprNumber):
    
    cdef ast_decl.IExprUnsignedNumber *asExprUnsignedNumber(self):
        return dynamic_cast[ast_decl.IExprUnsignedNumberP](self._hndl)
    @staticmethod
    cdef ExprUnsignedNumber mk(ast_decl.IExprUnsignedNumber *hndl, bool owned):
        '''Creates a Python wrapper around native class'''
        ret = ExprUnsignedNumber()
        ret._hndl = hndl
        ret._owned = owned
        return ret
    
    cpdef str getImage(self):
        return dynamic_cast[ast_decl.IExprUnsignedNumberP](self._hndl).getImage().decode()
    cpdef void setImage(self, str v):
        dynamic_cast[ast_decl.IExprUnsignedNumberP](self._hndl).setImage(v.encode())
    cpdef int32_t getWidth(self):
        return dynamic_cast[ast_decl.IExprUnsignedNumberP](self._hndl).getWidth()
    cpdef uint64_t getValue(self):
        return dynamic_cast[ast_decl.IExprUnsignedNumberP](self._hndl).getValue()

cdef class ExtendType(Scope):
    
    cdef ast_decl.IExtendType *asExtendType(self):
        return dynamic_cast[ast_decl.IExtendTypeP](self._hndl)
    @staticmethod
    cdef ExtendType mk(ast_decl.IExtendType *hndl, bool owned):
        '''Creates a Python wrapper around native class'''
        ret = ExtendType()
        ret._hndl = hndl
        ret._owned = owned
        return ret
    
    cpdef  getKind(self):
        return dynamic_cast[ast_decl.IExtendTypeP](self._hndl).getKind()
    cpdef TypeIdentifier getTarget(self):
        if self.asExtendType().getTarget() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asExtendType().getTarget().accept(of._hndl)
            return <TypeIdentifier>(of._obj)
    cpdef bool symtabHas(self, str i):
        cdef std_unordered_map[std_string,int32_t].const_iterator it = self.asExtendType().getSymtab().find(i.encode())
        return (it != self.asExtendType().getSymtab().end())
    cpdef int32_t symtabAt(self, str i):
        cdef std_unordered_map[std_string,int32_t].const_iterator it = self.asExtendType().getSymtab().find(i.encode())
        return dereference(it).second
    cpdef SymbolImportSpec getImports(self):
        if self.asExtendType().getImports() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asExtendType().getImports().accept(of._hndl)
            return <SymbolImportSpec>(of._obj)

cdef class Field(NamedScopeChild):
    
    cdef ast_decl.IField *asField(self):
        return dynamic_cast[ast_decl.IFieldP](self._hndl)
    @staticmethod
    cdef Field mk(ast_decl.IField *hndl, bool owned):
        '''Creates a Python wrapper around native class'''
        ret = Field()
        ret._hndl = hndl
        ret._owned = owned
        return ret
    
    cpdef DataType getType(self):
        if self.asField().getType() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asField().getType().accept(of._hndl)
            return <DataType>(of._obj)
    cpdef  getAttr(self):
        return dynamic_cast[ast_decl.IFieldP](self._hndl).getAttr()
    cpdef Expr getInit(self):
        if self.asField().getInit() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asField().getInit().accept(of._hndl)
            return <Expr>(of._obj)

cdef class FieldClaim(NamedScopeChild):
    
    cdef ast_decl.IFieldClaim *asFieldClaim(self):
        return dynamic_cast[ast_decl.IFieldClaimP](self._hndl)
    @staticmethod
    cdef FieldClaim mk(ast_decl.IFieldClaim *hndl, bool owned):
        '''Creates a Python wrapper around native class'''
        ret = FieldClaim()
        ret._hndl = hndl
        ret._owned = owned
        return ret
    
    cpdef DataTypeUserDefined getType(self):
        if self.asFieldClaim().getType() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asFieldClaim().getType().accept(of._hndl)
            return <DataTypeUserDefined>(of._obj)
    cpdef bool getIs_lock(self):
        return dynamic_cast[ast_decl.IFieldClaimP](self._hndl).getIs_lock()

cdef class FieldCompRef(NamedScopeChild):
    
    cdef ast_decl.IFieldCompRef *asFieldCompRef(self):
        return dynamic_cast[ast_decl.IFieldCompRefP](self._hndl)
    @staticmethod
    cdef FieldCompRef mk(ast_decl.IFieldCompRef *hndl, bool owned):
        '''Creates a Python wrapper around native class'''
        ret = FieldCompRef()
        ret._hndl = hndl
        ret._owned = owned
        return ret
    
    cpdef DataTypeUserDefined getType(self):
        if self.asFieldCompRef().getType() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asFieldCompRef().getType().accept(of._hndl)
            return <DataTypeUserDefined>(of._obj)

cdef class FieldRef(NamedScopeChild):
    
    cdef ast_decl.IFieldRef *asFieldRef(self):
        return dynamic_cast[ast_decl.IFieldRefP](self._hndl)
    @staticmethod
    cdef FieldRef mk(ast_decl.IFieldRef *hndl, bool owned):
        '''Creates a Python wrapper around native class'''
        ret = FieldRef()
        ret._hndl = hndl
        ret._owned = owned
        return ret
    
    cpdef DataTypeUserDefined getType(self):
        if self.asFieldRef().getType() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asFieldRef().getType().accept(of._hndl)
            return <DataTypeUserDefined>(of._obj)
    cpdef bool getIs_input(self):
        return dynamic_cast[ast_decl.IFieldRefP](self._hndl).getIs_input()

cdef class FunctionImportProto(FunctionImport):
    
    cdef ast_decl.IFunctionImportProto *asFunctionImportProto(self):
        return dynamic_cast[ast_decl.IFunctionImportProtoP](self._hndl)
    @staticmethod
    cdef FunctionImportProto mk(ast_decl.IFunctionImportProto *hndl, bool owned):
        '''Creates a Python wrapper around native class'''
        ret = FunctionImportProto()
        ret._hndl = hndl
        ret._owned = owned
        return ret
    
    cpdef FunctionPrototype getProto(self):
        if self.asFunctionImportProto().getProto() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asFunctionImportProto().getProto().accept(of._hndl)
            return <FunctionPrototype>(of._obj)

cdef class FunctionImportType(FunctionImport):
    
    cdef ast_decl.IFunctionImportType *asFunctionImportType(self):
        return dynamic_cast[ast_decl.IFunctionImportTypeP](self._hndl)
    @staticmethod
    cdef FunctionImportType mk(ast_decl.IFunctionImportType *hndl, bool owned):
        '''Creates a Python wrapper around native class'''
        ret = FunctionImportType()
        ret._hndl = hndl
        ret._owned = owned
        return ret
    
    cpdef TypeIdentifier getType(self):
        if self.asFunctionImportType().getType() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asFunctionImportType().getType().accept(of._hndl)
            return <TypeIdentifier>(of._obj)

cdef class FunctionPrototype(NamedScopeChild):
    
    cdef ast_decl.IFunctionPrototype *asFunctionPrototype(self):
        return dynamic_cast[ast_decl.IFunctionPrototypeP](self._hndl)
    @staticmethod
    cdef FunctionPrototype mk(ast_decl.IFunctionPrototype *hndl, bool owned):
        '''Creates a Python wrapper around native class'''
        ret = FunctionPrototype()
        ret._hndl = hndl
        ret._owned = owned
        return ret
    
    cpdef DataType getRtype(self):
        if self.asFunctionPrototype().getRtype() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asFunctionPrototype().getRtype().accept(of._hndl)
            return <DataType>(of._obj)
    def parameters(self) -> ListUtil:
        return ListUtil(self.numParameters, self.getParameter)
    
    cpdef getParameters(self):
        cdef const std_vector[ast_decl.IFunctionParamDeclUP] *__lp = &self.asFunctionPrototype().getParameters()
        cdef ast_decl.IFunctionParamDecl *__ep;
        ret = []
        of = ObjFactory()
        for __i in range(__lp.size()):
            __ep = __lp.at(__i).get()
            ret.append(__ep.accept(of._hndl))
        return ret
    cpdef getParameter(self, i):
        cdef ast_decl.IFunctionParamDecl *__ep = self.asFunctionPrototype().getParameters().at(i).get();
        of = ObjFactory()
        __ep.accept(of._hndl)
        return of._obj
    cpdef void addParameter(self, FunctionParamDecl i):
        i._owned = False
        self.asFunctionPrototype().getParameters().push_back(ast_decl.IFunctionParamDeclUP(i.asFunctionParamDecl(), True))
    cpdef numParameters(self):
        return self.asFunctionPrototype().getParameters().size()
    cpdef bool getIs_pure(self):
        return dynamic_cast[ast_decl.IFunctionPrototypeP](self._hndl).getIs_pure()
    cpdef bool getIs_target(self):
        return dynamic_cast[ast_decl.IFunctionPrototypeP](self._hndl).getIs_target()
    cpdef bool getIs_solve(self):
        return dynamic_cast[ast_decl.IFunctionPrototypeP](self._hndl).getIs_solve()
    cpdef bool getIs_core(self):
        return dynamic_cast[ast_decl.IFunctionPrototypeP](self._hndl).getIs_core()

cdef class GlobalScope(Scope):
    
    cdef ast_decl.IGlobalScope *asGlobalScope(self):
        return dynamic_cast[ast_decl.IGlobalScopeP](self._hndl)
    @staticmethod
    cdef GlobalScope mk(ast_decl.IGlobalScope *hndl, bool owned):
        '''Creates a Python wrapper around native class'''
        ret = GlobalScope()
        ret._hndl = hndl
        ret._owned = owned
        return ret
    
    cpdef int32_t getFileid(self):
        return dynamic_cast[ast_decl.IGlobalScopeP](self._hndl).getFileid()
    cpdef str getFilename(self):
        return dynamic_cast[ast_decl.IGlobalScopeP](self._hndl).getFilename().decode()
    cpdef void setFilename(self, str v):
        dynamic_cast[ast_decl.IGlobalScopeP](self._hndl).setFilename(v.encode())

cdef class ActivityActionHandleTraversal(ActivityLabeledStmt):
    
    cdef ast_decl.IActivityActionHandleTraversal *asActivityActionHandleTraversal(self):
        return dynamic_cast[ast_decl.IActivityActionHandleTraversalP](self._hndl)
    @staticmethod
    cdef ActivityActionHandleTraversal mk(ast_decl.IActivityActionHandleTraversal *hndl, bool owned):
        '''Creates a Python wrapper around native class'''
        ret = ActivityActionHandleTraversal()
        ret._hndl = hndl
        ret._owned = owned
        return ret
    
    cpdef ExprRefPathContext getTarget(self):
        if self.asActivityActionHandleTraversal().getTarget() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asActivityActionHandleTraversal().getTarget().accept(of._hndl)
            return <ExprRefPathContext>(of._obj)
    cpdef ConstraintStmt getWith_c(self):
        if self.asActivityActionHandleTraversal().getWith_c() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asActivityActionHandleTraversal().getWith_c().accept(of._hndl)
            return <ConstraintStmt>(of._obj)
    def initializers(self) -> ListUtil:
        return ListUtil(self.numInitializers, self.getInitializer)
    
    cpdef getInitializers(self):
        cdef const std_vector[ast_decl.IActionFieldInitializerUP] *__lp = &self.asActivityActionHandleTraversal().getInitializers()
        cdef ast_decl.IActionFieldInitializer *__ep;
        ret = []
        of = ObjFactory()
        for __i in range(__lp.size()):
            __ep = __lp.at(__i).get()
            ret.append(__ep.accept(of._hndl))
        return ret
    cpdef getInitializer(self, i):
        cdef ast_decl.IActionFieldInitializer *__ep = self.asActivityActionHandleTraversal().getInitializers().at(i).get();
        of = ObjFactory()
        __ep.accept(of._hndl)
        return of._obj
    cpdef void addInitializer(self, ActionFieldInitializer i):
        i._owned = False
        self.asActivityActionHandleTraversal().getInitializers().push_back(ast_decl.IActionFieldInitializerUP(i.asActionFieldInitializer(), True))
    cpdef numInitializers(self):
        return self.asActivityActionHandleTraversal().getInitializers().size()

cdef class ActivityActionTypeTraversal(ActivityLabeledStmt):
    
    cdef ast_decl.IActivityActionTypeTraversal *asActivityActionTypeTraversal(self):
        return dynamic_cast[ast_decl.IActivityActionTypeTraversalP](self._hndl)
    @staticmethod
    cdef ActivityActionTypeTraversal mk(ast_decl.IActivityActionTypeTraversal *hndl, bool owned):
        '''Creates a Python wrapper around native class'''
        ret = ActivityActionTypeTraversal()
        ret._hndl = hndl
        ret._owned = owned
        return ret
    
    cpdef DataTypeUserDefined getTarget(self):
        if self.asActivityActionTypeTraversal().getTarget() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asActivityActionTypeTraversal().getTarget().accept(of._hndl)
            return <DataTypeUserDefined>(of._obj)
    cpdef ConstraintStmt getWith_c(self):
        if self.asActivityActionTypeTraversal().getWith_c() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asActivityActionTypeTraversal().getWith_c().accept(of._hndl)
            return <ConstraintStmt>(of._obj)
    def initializers(self) -> ListUtil:
        return ListUtil(self.numInitializers, self.getInitializer)
    
    cpdef getInitializers(self):
        cdef const std_vector[ast_decl.IActionFieldInitializerUP] *__lp = &self.asActivityActionTypeTraversal().getInitializers()
        cdef ast_decl.IActionFieldInitializer *__ep;
        ret = []
        of = ObjFactory()
        for __i in range(__lp.size()):
            __ep = __lp.at(__i).get()
            ret.append(__ep.accept(of._hndl))
        return ret
    cpdef getInitializer(self, i):
        cdef ast_decl.IActionFieldInitializer *__ep = self.asActivityActionTypeTraversal().getInitializers().at(i).get();
        of = ObjFactory()
        __ep.accept(of._hndl)
        return of._obj
    cpdef void addInitializer(self, ActionFieldInitializer i):
        i._owned = False
        self.asActivityActionTypeTraversal().getInitializers().push_back(ast_decl.IActionFieldInitializerUP(i.asActionFieldInitializer(), True))
    cpdef numInitializers(self):
        return self.asActivityActionTypeTraversal().getInitializers().size()

cdef class ActivityAtomicBlock(ActivityLabeledStmt):
    
    cdef ast_decl.IActivityAtomicBlock *asActivityAtomicBlock(self):
        return dynamic_cast[ast_decl.IActivityAtomicBlockP](self._hndl)
    @staticmethod
    cdef ActivityAtomicBlock mk(ast_decl.IActivityAtomicBlock *hndl, bool owned):
        '''Creates a Python wrapper around native class'''
        ret = ActivityAtomicBlock()
        ret._hndl = hndl
        ret._owned = owned
        return ret
    
    cpdef ScopeChild getBody(self):
        if self.asActivityAtomicBlock().getBody() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asActivityAtomicBlock().getBody().accept(of._hndl)
            return <ScopeChild>(of._obj)

cdef class ActivityForeach(ActivityLabeledStmt):
    
    cdef ast_decl.IActivityForeach *asActivityForeach(self):
        return dynamic_cast[ast_decl.IActivityForeachP](self._hndl)
    @staticmethod
    cdef ActivityForeach mk(ast_decl.IActivityForeach *hndl, bool owned):
        '''Creates a Python wrapper around native class'''
        ret = ActivityForeach()
        ret._hndl = hndl
        ret._owned = owned
        return ret
    
    cpdef ExprId getIt_id(self):
        if self.asActivityForeach().getIt_id() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asActivityForeach().getIt_id().accept(of._hndl)
            return <ExprId>(of._obj)
    cpdef ExprId getIdx_id(self):
        if self.asActivityForeach().getIdx_id() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asActivityForeach().getIdx_id().accept(of._hndl)
            return <ExprId>(of._obj)
    cpdef ExprRefPathContext getTarget(self):
        if self.asActivityForeach().getTarget() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asActivityForeach().getTarget().accept(of._hndl)
            return <ExprRefPathContext>(of._obj)
    cpdef ScopeChild getBody(self):
        if self.asActivityForeach().getBody() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asActivityForeach().getBody().accept(of._hndl)
            return <ScopeChild>(of._obj)

cdef class ActivityIfElse(ActivityLabeledStmt):
    
    cdef ast_decl.IActivityIfElse *asActivityIfElse(self):
        return dynamic_cast[ast_decl.IActivityIfElseP](self._hndl)
    @staticmethod
    cdef ActivityIfElse mk(ast_decl.IActivityIfElse *hndl, bool owned):
        '''Creates a Python wrapper around native class'''
        ret = ActivityIfElse()
        ret._hndl = hndl
        ret._owned = owned
        return ret
    
    cpdef Expr getCond(self):
        if self.asActivityIfElse().getCond() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asActivityIfElse().getCond().accept(of._hndl)
            return <Expr>(of._obj)
    cpdef ActivityStmt getTrue_s(self):
        if self.asActivityIfElse().getTrue_s() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asActivityIfElse().getTrue_s().accept(of._hndl)
            return <ActivityStmt>(of._obj)
    cpdef ActivityStmt getFalse_s(self):
        if self.asActivityIfElse().getFalse_s() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asActivityIfElse().getFalse_s().accept(of._hndl)
            return <ActivityStmt>(of._obj)

cdef class ActivityMatch(ActivityLabeledStmt):
    
    cdef ast_decl.IActivityMatch *asActivityMatch(self):
        return dynamic_cast[ast_decl.IActivityMatchP](self._hndl)
    @staticmethod
    cdef ActivityMatch mk(ast_decl.IActivityMatch *hndl, bool owned):
        '''Creates a Python wrapper around native class'''
        ret = ActivityMatch()
        ret._hndl = hndl
        ret._owned = owned
        return ret
    
    cpdef Expr getCond(self):
        if self.asActivityMatch().getCond() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asActivityMatch().getCond().accept(of._hndl)
            return <Expr>(of._obj)
    def choices(self) -> ListUtil:
        return ListUtil(self.numChoices, self.getChoice)
    
    cpdef getChoices(self):
        cdef const std_vector[ast_decl.IActivityMatchChoiceUP] *__lp = &self.asActivityMatch().getChoices()
        cdef ast_decl.IActivityMatchChoice *__ep;
        ret = []
        of = ObjFactory()
        for __i in range(__lp.size()):
            __ep = __lp.at(__i).get()
            ret.append(__ep.accept(of._hndl))
        return ret
    cpdef getChoice(self, i):
        cdef ast_decl.IActivityMatchChoice *__ep = self.asActivityMatch().getChoices().at(i).get();
        of = ObjFactory()
        __ep.accept(of._hndl)
        return of._obj
    cpdef void addChoice(self, ActivityMatchChoice i):
        i._owned = False
        self.asActivityMatch().getChoices().push_back(ast_decl.IActivityMatchChoiceUP(i.asActivityMatchChoice(), True))
    cpdef numChoices(self):
        return self.asActivityMatch().getChoices().size()

cdef class ActivityRepeatCount(ActivityLabeledStmt):
    
    cdef ast_decl.IActivityRepeatCount *asActivityRepeatCount(self):
        return dynamic_cast[ast_decl.IActivityRepeatCountP](self._hndl)
    @staticmethod
    cdef ActivityRepeatCount mk(ast_decl.IActivityRepeatCount *hndl, bool owned):
        '''Creates a Python wrapper around native class'''
        ret = ActivityRepeatCount()
        ret._hndl = hndl
        ret._owned = owned
        return ret
    
    cpdef ExprId getLoop_var(self):
        if self.asActivityRepeatCount().getLoop_var() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asActivityRepeatCount().getLoop_var().accept(of._hndl)
            return <ExprId>(of._obj)
    cpdef Expr getCount(self):
        if self.asActivityRepeatCount().getCount() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asActivityRepeatCount().getCount().accept(of._hndl)
            return <Expr>(of._obj)
    cpdef ScopeChild getBody(self):
        if self.asActivityRepeatCount().getBody() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asActivityRepeatCount().getBody().accept(of._hndl)
            return <ScopeChild>(of._obj)

cdef class ActivityRepeatWhile(ActivityLabeledStmt):
    
    cdef ast_decl.IActivityRepeatWhile *asActivityRepeatWhile(self):
        return dynamic_cast[ast_decl.IActivityRepeatWhileP](self._hndl)
    @staticmethod
    cdef ActivityRepeatWhile mk(ast_decl.IActivityRepeatWhile *hndl, bool owned):
        '''Creates a Python wrapper around native class'''
        ret = ActivityRepeatWhile()
        ret._hndl = hndl
        ret._owned = owned
        return ret
    
    cpdef Expr getCond(self):
        if self.asActivityRepeatWhile().getCond() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asActivityRepeatWhile().getCond().accept(of._hndl)
            return <Expr>(of._obj)
    cpdef ScopeChild getBody(self):
        if self.asActivityRepeatWhile().getBody() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asActivityRepeatWhile().getBody().accept(of._hndl)
            return <ScopeChild>(of._obj)

cdef class ActivityReplicate(ActivityLabeledStmt):
    
    cdef ast_decl.IActivityReplicate *asActivityReplicate(self):
        return dynamic_cast[ast_decl.IActivityReplicateP](self._hndl)
    @staticmethod
    cdef ActivityReplicate mk(ast_decl.IActivityReplicate *hndl, bool owned):
        '''Creates a Python wrapper around native class'''
        ret = ActivityReplicate()
        ret._hndl = hndl
        ret._owned = owned
        return ret
    
    cpdef ExprId getIdx_id(self):
        if self.asActivityReplicate().getIdx_id() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asActivityReplicate().getIdx_id().accept(of._hndl)
            return <ExprId>(of._obj)
    cpdef ExprId getIt_label(self):
        if self.asActivityReplicate().getIt_label() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asActivityReplicate().getIt_label().accept(of._hndl)
            return <ExprId>(of._obj)
    cpdef ScopeChild getBody(self):
        if self.asActivityReplicate().getBody() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asActivityReplicate().getBody().accept(of._hndl)
            return <ScopeChild>(of._obj)

cdef class ActivitySelect(ActivityLabeledStmt):
    
    cdef ast_decl.IActivitySelect *asActivitySelect(self):
        return dynamic_cast[ast_decl.IActivitySelectP](self._hndl)
    @staticmethod
    cdef ActivitySelect mk(ast_decl.IActivitySelect *hndl, bool owned):
        '''Creates a Python wrapper around native class'''
        ret = ActivitySelect()
        ret._hndl = hndl
        ret._owned = owned
        return ret
    
    def branches(self) -> ListUtil:
        return ListUtil(self.numBranches, self.getBranche)
    
    cpdef getBranches(self):
        cdef const std_vector[ast_decl.IActivitySelectBranchUP] *__lp = &self.asActivitySelect().getBranches()
        cdef ast_decl.IActivitySelectBranch *__ep;
        ret = []
        of = ObjFactory()
        for __i in range(__lp.size()):
            __ep = __lp.at(__i).get()
            ret.append(__ep.accept(of._hndl))
        return ret
    cpdef getBranche(self, i):
        cdef ast_decl.IActivitySelectBranch *__ep = self.asActivitySelect().getBranches().at(i).get();
        of = ObjFactory()
        __ep.accept(of._hndl)
        return of._obj
    cpdef void addBranche(self, ActivitySelectBranch i):
        i._owned = False
        self.asActivitySelect().getBranches().push_back(ast_decl.IActivitySelectBranchUP(i.asActivitySelectBranch(), True))
    cpdef numBranches(self):
        return self.asActivitySelect().getBranches().size()

cdef class ActivitySuper(ActivityLabeledStmt):
    
    cdef ast_decl.IActivitySuper *asActivitySuper(self):
        return dynamic_cast[ast_decl.IActivitySuperP](self._hndl)
    @staticmethod
    cdef ActivitySuper mk(ast_decl.IActivitySuper *hndl, bool owned):
        '''Creates a Python wrapper around native class'''
        ret = ActivitySuper()
        ret._hndl = hndl
        ret._owned = owned
        return ret
    

cdef class ProceduralStmtRepeatWhile(ProceduralStmtBody):
    
    cdef ast_decl.IProceduralStmtRepeatWhile *asProceduralStmtRepeatWhile(self):
        return dynamic_cast[ast_decl.IProceduralStmtRepeatWhileP](self._hndl)
    @staticmethod
    cdef ProceduralStmtRepeatWhile mk(ast_decl.IProceduralStmtRepeatWhile *hndl, bool owned):
        '''Creates a Python wrapper around native class'''
        ret = ProceduralStmtRepeatWhile()
        ret._hndl = hndl
        ret._owned = owned
        return ret
    
    cpdef Expr getExpr(self):
        if self.asProceduralStmtRepeatWhile().getExpr() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asProceduralStmtRepeatWhile().getExpr().accept(of._hndl)
            return <Expr>(of._obj)

cdef class ConstraintBlock(ConstraintScope):
    
    cdef ast_decl.IConstraintBlock *asConstraintBlock(self):
        return dynamic_cast[ast_decl.IConstraintBlockP](self._hndl)
    @staticmethod
    cdef ConstraintBlock mk(ast_decl.IConstraintBlock *hndl, bool owned):
        '''Creates a Python wrapper around native class'''
        ret = ConstraintBlock()
        ret._hndl = hndl
        ret._owned = owned
        return ret
    
    cpdef str getName(self):
        return dynamic_cast[ast_decl.IConstraintBlockP](self._hndl).getName().decode()
    cpdef void setName(self, str v):
        dynamic_cast[ast_decl.IConstraintBlockP](self._hndl).setName(v.encode())
    cpdef bool getIs_dynamic(self):
        return dynamic_cast[ast_decl.IConstraintBlockP](self._hndl).getIs_dynamic()

cdef class ProceduralStmtWhile(ProceduralStmtBody):
    
    cdef ast_decl.IProceduralStmtWhile *asProceduralStmtWhile(self):
        return dynamic_cast[ast_decl.IProceduralStmtWhileP](self._hndl)
    @staticmethod
    cdef ProceduralStmtWhile mk(ast_decl.IProceduralStmtWhile *hndl, bool owned):
        '''Creates a Python wrapper around native class'''
        ret = ProceduralStmtWhile()
        ret._hndl = hndl
        ret._owned = owned
        return ret
    
    cpdef Expr getExpr(self):
        if self.asProceduralStmtWhile().getExpr() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asProceduralStmtWhile().getExpr().accept(of._hndl)
            return <Expr>(of._obj)

cdef class ConstraintStmtForall(ConstraintScope):
    
    cdef ast_decl.IConstraintStmtForall *asConstraintStmtForall(self):
        return dynamic_cast[ast_decl.IConstraintStmtForallP](self._hndl)
    @staticmethod
    cdef ConstraintStmtForall mk(ast_decl.IConstraintStmtForall *hndl, bool owned):
        '''Creates a Python wrapper around native class'''
        ret = ConstraintStmtForall()
        ret._hndl = hndl
        ret._owned = owned
        return ret
    
    cpdef ExprId getIterator_id(self):
        if self.asConstraintStmtForall().getIterator_id() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asConstraintStmtForall().getIterator_id().accept(of._hndl)
            return <ExprId>(of._obj)
    cpdef DataTypeUserDefined getType_id(self):
        if self.asConstraintStmtForall().getType_id() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asConstraintStmtForall().getType_id().accept(of._hndl)
            return <DataTypeUserDefined>(of._obj)
    cpdef ExprRefPath getRef_path(self):
        if self.asConstraintStmtForall().getRef_path() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asConstraintStmtForall().getRef_path().accept(of._hndl)
            return <ExprRefPath>(of._obj)
    cpdef ConstraintSymbolScope getSymtab(self):
        if self.asConstraintStmtForall().getSymtab() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asConstraintStmtForall().getSymtab().accept(of._hndl)
            return <ConstraintSymbolScope>(of._obj)

cdef class ConstraintStmtForeach(ConstraintScope):
    
    cdef ast_decl.IConstraintStmtForeach *asConstraintStmtForeach(self):
        return dynamic_cast[ast_decl.IConstraintStmtForeachP](self._hndl)
    @staticmethod
    cdef ConstraintStmtForeach mk(ast_decl.IConstraintStmtForeach *hndl, bool owned):
        '''Creates a Python wrapper around native class'''
        ret = ConstraintStmtForeach()
        ret._hndl = hndl
        ret._owned = owned
        return ret
    
    cpdef ConstraintStmtField getIt(self):
        if self.asConstraintStmtForeach().getIt() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asConstraintStmtForeach().getIt().accept(of._hndl)
            return <ConstraintStmtField>(of._obj)
    cpdef ConstraintStmtField getIdx(self):
        if self.asConstraintStmtForeach().getIdx() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asConstraintStmtForeach().getIdx().accept(of._hndl)
            return <ConstraintStmtField>(of._obj)
    cpdef Expr getExpr(self):
        if self.asConstraintStmtForeach().getExpr() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asConstraintStmtForeach().getExpr().accept(of._hndl)
            return <Expr>(of._obj)
    cpdef ConstraintSymbolScope getSymtab(self):
        if self.asConstraintStmtForeach().getSymtab() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asConstraintStmtForeach().getSymtab().accept(of._hndl)
            return <ConstraintSymbolScope>(of._obj)

cdef class ConstraintStmtImplication(ConstraintScope):
    
    cdef ast_decl.IConstraintStmtImplication *asConstraintStmtImplication(self):
        return dynamic_cast[ast_decl.IConstraintStmtImplicationP](self._hndl)
    @staticmethod
    cdef ConstraintStmtImplication mk(ast_decl.IConstraintStmtImplication *hndl, bool owned):
        '''Creates a Python wrapper around native class'''
        ret = ConstraintStmtImplication()
        ret._hndl = hndl
        ret._owned = owned
        return ret
    
    cpdef Expr getCond(self):
        if self.asConstraintStmtImplication().getCond() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asConstraintStmtImplication().getCond().accept(of._hndl)
            return <Expr>(of._obj)

cdef class SymbolScope(SymbolChildrenScope):
    
    cdef ast_decl.ISymbolScope *asSymbolScope(self):
        return dynamic_cast[ast_decl.ISymbolScopeP](self._hndl)
    @staticmethod
    cdef SymbolScope mk(ast_decl.ISymbolScope *hndl, bool owned):
        '''Creates a Python wrapper around native class'''
        ret = SymbolScope()
        ret._hndl = hndl
        ret._owned = owned
        return ret
    
    cpdef bool symtabHas(self, str i):
        cdef std_unordered_map[std_string,int32_t].const_iterator it = self.asSymbolScope().getSymtab().find(i.encode())
        return (it != self.asSymbolScope().getSymtab().end())
    cpdef int32_t symtabAt(self, str i):
        cdef std_unordered_map[std_string,int32_t].const_iterator it = self.asSymbolScope().getSymtab().find(i.encode())
        return dereference(it).second
    cpdef SymbolImportSpec getImports(self):
        if self.asSymbolScope().getImports() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asSymbolScope().getImports().accept(of._hndl)
            return <SymbolImportSpec>(of._obj)
    cpdef bool getSynthetic(self):
        return dynamic_cast[ast_decl.ISymbolScopeP](self._hndl).getSynthetic()
    cpdef bool getOpaque(self):
        return dynamic_cast[ast_decl.ISymbolScopeP](self._hndl).getOpaque()

cdef class TypeScope(NamedScope):
    
    cdef ast_decl.ITypeScope *asTypeScope(self):
        return dynamic_cast[ast_decl.ITypeScopeP](self._hndl)
    @staticmethod
    cdef TypeScope mk(ast_decl.ITypeScope *hndl, bool owned):
        '''Creates a Python wrapper around native class'''
        ret = TypeScope()
        ret._hndl = hndl
        ret._owned = owned
        return ret
    
    cpdef TypeIdentifier getSuper_t(self):
        if self.asTypeScope().getSuper_t() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asTypeScope().getSuper_t().accept(of._hndl)
            return <TypeIdentifier>(of._obj)
    cpdef TemplateParamDeclList getParams(self):
        if self.asTypeScope().getParams() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asTypeScope().getParams().accept(of._hndl)
            return <TemplateParamDeclList>(of._obj)
    cpdef bool getOpaque(self):
        return dynamic_cast[ast_decl.ITypeScopeP](self._hndl).getOpaque()

cdef class ExprRefPathStaticFunc(ExprRefPathStatic):
    
    cdef ast_decl.IExprRefPathStaticFunc *asExprRefPathStaticFunc(self):
        return dynamic_cast[ast_decl.IExprRefPathStaticFuncP](self._hndl)
    @staticmethod
    cdef ExprRefPathStaticFunc mk(ast_decl.IExprRefPathStaticFunc *hndl, bool owned):
        '''Creates a Python wrapper around native class'''
        ret = ExprRefPathStaticFunc()
        ret._hndl = hndl
        ret._owned = owned
        return ret
    
    cpdef MethodParameterList getParams(self):
        if self.asExprRefPathStaticFunc().getParams() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asExprRefPathStaticFunc().getParams().accept(of._hndl)
            return <MethodParameterList>(of._obj)

cdef class ExprRefPathSuper(ExprRefPathContext):
    
    cdef ast_decl.IExprRefPathSuper *asExprRefPathSuper(self):
        return dynamic_cast[ast_decl.IExprRefPathSuperP](self._hndl)
    @staticmethod
    cdef ExprRefPathSuper mk(ast_decl.IExprRefPathSuper *hndl, bool owned):
        '''Creates a Python wrapper around native class'''
        ret = ExprRefPathSuper()
        ret._hndl = hndl
        ret._owned = owned
        return ret
    

cdef class Action(TypeScope):
    
    cdef ast_decl.IAction *asAction(self):
        return dynamic_cast[ast_decl.IActionP](self._hndl)
    @staticmethod
    cdef Action mk(ast_decl.IAction *hndl, bool owned):
        '''Creates a Python wrapper around native class'''
        ret = Action()
        ret._hndl = hndl
        ret._owned = owned
        return ret
    
    cpdef bool getIs_abstract(self):
        return dynamic_cast[ast_decl.IActionP](self._hndl).getIs_abstract()
    cpdef bool getIs_override(self):
        return dynamic_cast[ast_decl.IActionP](self._hndl).getIs_override()

cdef class MonitorActivityDecl(SymbolScope):
    
    cdef ast_decl.IMonitorActivityDecl *asMonitorActivityDecl(self):
        return dynamic_cast[ast_decl.IMonitorActivityDeclP](self._hndl)
    @staticmethod
    cdef MonitorActivityDecl mk(ast_decl.IMonitorActivityDecl *hndl, bool owned):
        '''Creates a Python wrapper around native class'''
        ret = MonitorActivityDecl()
        ret._hndl = hndl
        ret._owned = owned
        return ret
    

cdef class ActivityDecl(SymbolScope):
    
    cdef ast_decl.IActivityDecl *asActivityDecl(self):
        return dynamic_cast[ast_decl.IActivityDeclP](self._hndl)
    @staticmethod
    cdef ActivityDecl mk(ast_decl.IActivityDecl *hndl, bool owned):
        '''Creates a Python wrapper around native class'''
        ret = ActivityDecl()
        ret._hndl = hndl
        ret._owned = owned
        return ret
    

cdef class MonitorActivitySchedule(SymbolScope):
    
    cdef ast_decl.IMonitorActivitySchedule *asMonitorActivitySchedule(self):
        return dynamic_cast[ast_decl.IMonitorActivityScheduleP](self._hndl)
    @staticmethod
    cdef MonitorActivitySchedule mk(ast_decl.IMonitorActivitySchedule *hndl, bool owned):
        '''Creates a Python wrapper around native class'''
        ret = MonitorActivitySchedule()
        ret._hndl = hndl
        ret._owned = owned
        return ret
    
    cpdef ExprId getLabel(self):
        if self.asMonitorActivitySchedule().getLabel() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asMonitorActivitySchedule().getLabel().accept(of._hndl)
            return <ExprId>(of._obj)

cdef class MonitorActivitySequence(SymbolScope):
    
    cdef ast_decl.IMonitorActivitySequence *asMonitorActivitySequence(self):
        return dynamic_cast[ast_decl.IMonitorActivitySequenceP](self._hndl)
    @staticmethod
    cdef MonitorActivitySequence mk(ast_decl.IMonitorActivitySequence *hndl, bool owned):
        '''Creates a Python wrapper around native class'''
        ret = MonitorActivitySequence()
        ret._hndl = hndl
        ret._owned = owned
        return ret
    
    cpdef ExprId getLabel(self):
        if self.asMonitorActivitySequence().getLabel() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asMonitorActivitySequence().getLabel().accept(of._hndl)
            return <ExprId>(of._obj)

cdef class ActivityLabeledScope(SymbolScope):
    
    cdef ast_decl.IActivityLabeledScope *asActivityLabeledScope(self):
        return dynamic_cast[ast_decl.IActivityLabeledScopeP](self._hndl)
    @staticmethod
    cdef ActivityLabeledScope mk(ast_decl.IActivityLabeledScope *hndl, bool owned):
        '''Creates a Python wrapper around native class'''
        ret = ActivityLabeledScope()
        ret._hndl = hndl
        ret._owned = owned
        return ret
    
    cpdef ExprId getLabel(self):
        if self.asActivityLabeledScope().getLabel() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asActivityLabeledScope().getLabel().accept(of._hndl)
            return <ExprId>(of._obj)

cdef class AnnotationDecl(TypeScope):
    
    cdef ast_decl.IAnnotationDecl *asAnnotationDecl(self):
        return dynamic_cast[ast_decl.IAnnotationDeclP](self._hndl)
    @staticmethod
    cdef AnnotationDecl mk(ast_decl.IAnnotationDecl *hndl, bool owned):
        '''Creates a Python wrapper around native class'''
        ret = AnnotationDecl()
        ret._hndl = hndl
        ret._owned = owned
        return ret
    

cdef class Component(TypeScope):
    
    cdef ast_decl.IComponent *asComponent(self):
        return dynamic_cast[ast_decl.IComponentP](self._hndl)
    @staticmethod
    cdef Component mk(ast_decl.IComponent *hndl, bool owned):
        '''Creates a Python wrapper around native class'''
        ret = Component()
        ret._hndl = hndl
        ret._owned = owned
        return ret
    

cdef class ProceduralStmtSymbolBodyScope(SymbolScope):
    
    cdef ast_decl.IProceduralStmtSymbolBodyScope *asProceduralStmtSymbolBodyScope(self):
        return dynamic_cast[ast_decl.IProceduralStmtSymbolBodyScopeP](self._hndl)
    @staticmethod
    cdef ProceduralStmtSymbolBodyScope mk(ast_decl.IProceduralStmtSymbolBodyScope *hndl, bool owned):
        '''Creates a Python wrapper around native class'''
        ret = ProceduralStmtSymbolBodyScope()
        ret._hndl = hndl
        ret._owned = owned
        return ret
    
    cpdef ScopeChild getBody(self):
        if self.asProceduralStmtSymbolBodyScope().getBody() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asProceduralStmtSymbolBodyScope().getBody().accept(of._hndl)
            return <ScopeChild>(of._obj)

cdef class RootSymbolScope(SymbolScope):
    
    cdef ast_decl.IRootSymbolScope *asRootSymbolScope(self):
        return dynamic_cast[ast_decl.IRootSymbolScopeP](self._hndl)
    @staticmethod
    cdef RootSymbolScope mk(ast_decl.IRootSymbolScope *hndl, bool owned):
        '''Creates a Python wrapper around native class'''
        ret = RootSymbolScope()
        ret._hndl = hndl
        ret._owned = owned
        return ret
    
    def units(self) -> ListUtil:
        return ListUtil(self.numUnits, self.getUnit)
    
    cpdef getUnits(self):
        cdef const std_vector[ast_decl.IGlobalScopeUP] *__lp = &self.asRootSymbolScope().getUnits()
        cdef ast_decl.IGlobalScope *__ep;
        ret = []
        of = ObjFactory()
        for __i in range(__lp.size()):
            __ep = __lp.at(__i).get()
            ret.append(__ep.accept(of._hndl))
        return ret
    cpdef getUnit(self, i):
        cdef ast_decl.IGlobalScope *__ep = self.asRootSymbolScope().getUnits().at(i).get();
        of = ObjFactory()
        __ep.accept(of._hndl)
        return of._obj
    cpdef void addUnit(self, GlobalScope i):
        i._owned = False
        self.asRootSymbolScope().getUnits().push_back(ast_decl.IGlobalScopeUP(i.asGlobalScope(), True))
    cpdef numUnits(self):
        return self.asRootSymbolScope().getUnits().size()
    cpdef bool filenamesHas(self, int32_t i):
        cdef std_unordered_map[int32_t,std_string].const_iterator it = self.asRootSymbolScope().getFilenames().find(i)
        return (it != self.asRootSymbolScope().getFilenames().end())
    cpdef str filenamesAt(self, int32_t i):
        cdef std_unordered_map[int32_t,std_string].const_iterator it = self.asRootSymbolScope().getFilenames().find(i)
        return dereference(it).second.decode()
    cpdef bool id2idxHas(self, int32_t i):
        cdef std_unordered_map[int32_t,int32_t].const_iterator it = self.asRootSymbolScope().getId2idx().find(i)
        return (it != self.asRootSymbolScope().getId2idx().end())
    cpdef int32_t id2idxAt(self, int32_t i):
        cdef std_unordered_map[int32_t,int32_t].const_iterator it = self.asRootSymbolScope().getId2idx().find(i)
        return dereference(it).second
    def fileOutRef(self) -> ListUtil:
        return ListUtil(self.numFileOutRef, self.getFileOutRef)
    
    def fileInRef(self) -> ListUtil:
        return ListUtil(self.numFileInRef, self.getFileInRef)
    

cdef class ConstraintSymbolScope(SymbolScope):
    
    cdef ast_decl.IConstraintSymbolScope *asConstraintSymbolScope(self):
        return dynamic_cast[ast_decl.IConstraintSymbolScopeP](self._hndl)
    @staticmethod
    cdef ConstraintSymbolScope mk(ast_decl.IConstraintSymbolScope *hndl, bool owned):
        '''Creates a Python wrapper around native class'''
        ret = ConstraintSymbolScope()
        ret._hndl = hndl
        ret._owned = owned
        return ret
    
    cpdef ConstraintStmt getConstraint(self):
        if self.asConstraintSymbolScope().getConstraint() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asConstraintSymbolScope().getConstraint().accept(of._hndl)
            return <ConstraintStmt>(of._obj)

cdef class Struct(TypeScope):
    
    cdef ast_decl.IStruct *asStruct(self):
        return dynamic_cast[ast_decl.IStructP](self._hndl)
    @staticmethod
    cdef Struct mk(ast_decl.IStruct *hndl, bool owned):
        '''Creates a Python wrapper around native class'''
        ret = Struct()
        ret._hndl = hndl
        ret._owned = owned
        return ret
    
    cpdef  getKind(self):
        return dynamic_cast[ast_decl.IStructP](self._hndl).getKind()

cdef class SymbolEnumScope(SymbolScope):
    
    cdef ast_decl.ISymbolEnumScope *asSymbolEnumScope(self):
        return dynamic_cast[ast_decl.ISymbolEnumScopeP](self._hndl)
    @staticmethod
    cdef SymbolEnumScope mk(ast_decl.ISymbolEnumScope *hndl, bool owned):
        '''Creates a Python wrapper around native class'''
        ret = SymbolEnumScope()
        ret._hndl = hndl
        ret._owned = owned
        return ret
    

cdef class SymbolExtendScope(SymbolScope):
    
    cdef ast_decl.ISymbolExtendScope *asSymbolExtendScope(self):
        return dynamic_cast[ast_decl.ISymbolExtendScopeP](self._hndl)
    @staticmethod
    cdef SymbolExtendScope mk(ast_decl.ISymbolExtendScope *hndl, bool owned):
        '''Creates a Python wrapper around native class'''
        ret = SymbolExtendScope()
        ret._hndl = hndl
        ret._owned = owned
        return ret
    

cdef class SymbolFunctionScope(SymbolScope):
    
    cdef ast_decl.ISymbolFunctionScope *asSymbolFunctionScope(self):
        return dynamic_cast[ast_decl.ISymbolFunctionScopeP](self._hndl)
    @staticmethod
    cdef SymbolFunctionScope mk(ast_decl.ISymbolFunctionScope *hndl, bool owned):
        '''Creates a Python wrapper around native class'''
        ret = SymbolFunctionScope()
        ret._hndl = hndl
        ret._owned = owned
        return ret
    
    def prototypes(self) -> ListUtil:
        return ListUtil(self.numPrototypes, self.getPrototype)
    
    cpdef getPrototypes(self):
        cdef const std_vector[ast_decl.IFunctionPrototypeP] *__lp = &self.asSymbolFunctionScope().getPrototypes()
        cdef ast_decl.IFunctionPrototype *__ep;
        ret = []
        of = ObjFactory()
        for __i in range(__lp.size()):
            __ep = __lp.at(__i)
            ret.append(__ep.accept(of._hndl))
        return ret
    cpdef getPrototype(self, i):
        cdef ast_decl.IFunctionPrototype *__ep = self.asSymbolFunctionScope().getPrototypes().at(i);
        of = ObjFactory()
        __ep.accept(of._hndl)
        return of._obj
    cpdef void addPrototype(self, FunctionPrototype i):
        self.asSymbolFunctionScope().getPrototypes().push_back(i.asFunctionPrototype())
    cpdef numPrototypes(self):
        return self.asSymbolFunctionScope().getPrototypes().size()
    def import_specs(self) -> ListUtil:
        return ListUtil(self.numImport_specs, self.getImport_spec)
    
    cpdef getImport_specs(self):
        cdef const std_vector[ast_decl.IFunctionImportUP] *__lp = &self.asSymbolFunctionScope().getImport_specs()
        cdef ast_decl.IFunctionImport *__ep;
        ret = []
        of = ObjFactory()
        for __i in range(__lp.size()):
            __ep = __lp.at(__i).get()
            ret.append(__ep.accept(of._hndl))
        return ret
    cpdef getImport_spec(self, i):
        cdef ast_decl.IFunctionImport *__ep = self.asSymbolFunctionScope().getImport_specs().at(i).get();
        of = ObjFactory()
        __ep.accept(of._hndl)
        return of._obj
    cpdef void addImport_spec(self, FunctionImport i):
        i._owned = False
        self.asSymbolFunctionScope().getImport_specs().push_back(ast_decl.IFunctionImportUP(i.asFunctionImport(), True))
    cpdef numImport_specs(self):
        return self.asSymbolFunctionScope().getImport_specs().size()
    cpdef FunctionDefinition getDefinition(self):
        if self.asSymbolFunctionScope().getDefinition() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asSymbolFunctionScope().getDefinition().accept(of._hndl)
            return <FunctionDefinition>(of._obj)
    cpdef SymbolScope getPlist(self):
        if self.asSymbolFunctionScope().getPlist() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asSymbolFunctionScope().getPlist().accept(of._hndl)
            return <SymbolScope>(of._obj)
    cpdef ExecScope getBody(self):
        if self.asSymbolFunctionScope().getBody() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asSymbolFunctionScope().getBody().accept(of._hndl)
            return <ExecScope>(of._obj)

cdef class SymbolTypeScope(SymbolScope):
    
    cdef ast_decl.ISymbolTypeScope *asSymbolTypeScope(self):
        return dynamic_cast[ast_decl.ISymbolTypeScopeP](self._hndl)
    @staticmethod
    cdef SymbolTypeScope mk(ast_decl.ISymbolTypeScope *hndl, bool owned):
        '''Creates a Python wrapper around native class'''
        ret = SymbolTypeScope()
        ret._hndl = hndl
        ret._owned = owned
        return ret
    
    cpdef SymbolScope getPlist(self):
        if self.asSymbolTypeScope().getPlist() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asSymbolTypeScope().getPlist().accept(of._hndl)
            return <SymbolScope>(of._obj)
    def spec_types(self) -> ListUtil:
        return ListUtil(self.numSpec_types, self.getSpec_type)
    
    cpdef getSpec_types(self):
        cdef const std_vector[ast_decl.ISymbolTypeScopeUP] *__lp = &self.asSymbolTypeScope().getSpec_types()
        cdef ast_decl.ISymbolTypeScope *__ep;
        ret = []
        of = ObjFactory()
        for __i in range(__lp.size()):
            __ep = __lp.at(__i).get()
            ret.append(__ep.accept(of._hndl))
        return ret
    cpdef getSpec_type(self, i):
        cdef ast_decl.ISymbolTypeScope *__ep = self.asSymbolTypeScope().getSpec_types().at(i).get();
        of = ObjFactory()
        __ep.accept(of._hndl)
        return of._obj
    cpdef void addSpec_type(self, SymbolTypeScope i):
        i._owned = False
        self.asSymbolTypeScope().getSpec_types().push_back(ast_decl.ISymbolTypeScopeUP(i.asSymbolTypeScope(), True))
    cpdef numSpec_types(self):
        return self.asSymbolTypeScope().getSpec_types().size()

cdef class ExecScope(SymbolScope):
    
    cdef ast_decl.IExecScope *asExecScope(self):
        return dynamic_cast[ast_decl.IExecScopeP](self._hndl)
    @staticmethod
    cdef ExecScope mk(ast_decl.IExecScope *hndl, bool owned):
        '''Creates a Python wrapper around native class'''
        ret = ExecScope()
        ret._hndl = hndl
        ret._owned = owned
        return ret
    
    cpdef Location getEndLocation(self):
        return Location.wrap(dynamic_cast[ast_decl.IExecScopeP](self._hndl).getEndLocation())

cdef class GenericConstraintDeclBool(ConstraintBlock):
    
    cdef ast_decl.IGenericConstraintDeclBool *asGenericConstraintDeclBool(self):
        return dynamic_cast[ast_decl.IGenericConstraintDeclBoolP](self._hndl)
    @staticmethod
    cdef GenericConstraintDeclBool mk(ast_decl.IGenericConstraintDeclBool *hndl, bool owned):
        '''Creates a Python wrapper around native class'''
        ret = GenericConstraintDeclBool()
        ret._hndl = hndl
        ret._owned = owned
        return ret
    
    cpdef bool getIs_static(self):
        return dynamic_cast[ast_decl.IGenericConstraintDeclBoolP](self._hndl).getIs_static()
    def parameters(self) -> ListUtil:
        return ListUtil(self.numParameters, self.getParameter)
    
    cpdef getParameters(self):
        cdef const std_vector[ast_decl.IGenericConstraintParamUP] *__lp = &self.asGenericConstraintDeclBool().getParameters()
        cdef ast_decl.IGenericConstraintParam *__ep;
        ret = []
        of = ObjFactory()
        for __i in range(__lp.size()):
            __ep = __lp.at(__i).get()
            ret.append(__ep.accept(of._hndl))
        return ret
    cpdef getParameter(self, i):
        cdef ast_decl.IGenericConstraintParam *__ep = self.asGenericConstraintDeclBool().getParameters().at(i).get();
        of = ObjFactory()
        __ep.accept(of._hndl)
        return of._obj
    cpdef void addParameter(self, GenericConstraintParam i):
        i._owned = False
        self.asGenericConstraintDeclBool().getParameters().push_back(ast_decl.IGenericConstraintParamUP(i.asGenericConstraintParam(), True))
    cpdef numParameters(self):
        return self.asGenericConstraintDeclBool().getParameters().size()

cdef class Monitor(TypeScope):
    
    cdef ast_decl.IMonitor *asMonitor(self):
        return dynamic_cast[ast_decl.IMonitorP](self._hndl)
    @staticmethod
    cdef Monitor mk(ast_decl.IMonitor *hndl, bool owned):
        '''Creates a Python wrapper around native class'''
        ret = Monitor()
        ret._hndl = hndl
        ret._owned = owned
        return ret
    
    cpdef bool getIs_abstract(self):
        return dynamic_cast[ast_decl.IMonitorP](self._hndl).getIs_abstract()

cdef class ProceduralStmtRepeat(ProceduralStmtSymbolBodyScope):
    
    cdef ast_decl.IProceduralStmtRepeat *asProceduralStmtRepeat(self):
        return dynamic_cast[ast_decl.IProceduralStmtRepeatP](self._hndl)
    @staticmethod
    cdef ProceduralStmtRepeat mk(ast_decl.IProceduralStmtRepeat *hndl, bool owned):
        '''Creates a Python wrapper around native class'''
        ret = ProceduralStmtRepeat()
        ret._hndl = hndl
        ret._owned = owned
        return ret
    
    cpdef ExprId getIt_id(self):
        if self.asProceduralStmtRepeat().getIt_id() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asProceduralStmtRepeat().getIt_id().accept(of._hndl)
            return <ExprId>(of._obj)
    cpdef Expr getCount(self):
        if self.asProceduralStmtRepeat().getCount() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asProceduralStmtRepeat().getCount().accept(of._hndl)
            return <Expr>(of._obj)

cdef class ActivityParallel(ActivityLabeledScope):
    
    cdef ast_decl.IActivityParallel *asActivityParallel(self):
        return dynamic_cast[ast_decl.IActivityParallelP](self._hndl)
    @staticmethod
    cdef ActivityParallel mk(ast_decl.IActivityParallel *hndl, bool owned):
        '''Creates a Python wrapper around native class'''
        ret = ActivityParallel()
        ret._hndl = hndl
        ret._owned = owned
        return ret
    
    cpdef ActivityJoinSpec getJoin_spec(self):
        if self.asActivityParallel().getJoin_spec() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asActivityParallel().getJoin_spec().accept(of._hndl)
            return <ActivityJoinSpec>(of._obj)

cdef class ActivitySchedule(ActivityLabeledScope):
    
    cdef ast_decl.IActivitySchedule *asActivitySchedule(self):
        return dynamic_cast[ast_decl.IActivityScheduleP](self._hndl)
    @staticmethod
    cdef ActivitySchedule mk(ast_decl.IActivitySchedule *hndl, bool owned):
        '''Creates a Python wrapper around native class'''
        ret = ActivitySchedule()
        ret._hndl = hndl
        ret._owned = owned
        return ret
    
    cpdef ActivityJoinSpec getJoin_spec(self):
        if self.asActivitySchedule().getJoin_spec() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asActivitySchedule().getJoin_spec().accept(of._hndl)
            return <ActivityJoinSpec>(of._obj)

cdef class ProceduralStmtForeach(ProceduralStmtSymbolBodyScope):
    
    cdef ast_decl.IProceduralStmtForeach *asProceduralStmtForeach(self):
        return dynamic_cast[ast_decl.IProceduralStmtForeachP](self._hndl)
    @staticmethod
    cdef ProceduralStmtForeach mk(ast_decl.IProceduralStmtForeach *hndl, bool owned):
        '''Creates a Python wrapper around native class'''
        ret = ProceduralStmtForeach()
        ret._hndl = hndl
        ret._owned = owned
        return ret
    
    cpdef ExprRefPath getPath(self):
        if self.asProceduralStmtForeach().getPath() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asProceduralStmtForeach().getPath().accept(of._hndl)
            return <ExprRefPath>(of._obj)
    cpdef ExprId getIt_id(self):
        if self.asProceduralStmtForeach().getIt_id() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asProceduralStmtForeach().getIt_id().accept(of._hndl)
            return <ExprId>(of._obj)
    cpdef ExprId getIdx_id(self):
        if self.asProceduralStmtForeach().getIdx_id() == NULL:
            return None
        else:
            of = ObjFactory()
            self.asProceduralStmtForeach().getIdx_id().accept(of._hndl)
            return <ExprId>(of._obj)

cdef class ActivitySequence(ActivityLabeledScope):
    
    cdef ast_decl.IActivitySequence *asActivitySequence(self):
        return dynamic_cast[ast_decl.IActivitySequenceP](self._hndl)
    @staticmethod
    cdef ActivitySequence mk(ast_decl.IActivitySequence *hndl, bool owned):
        '''Creates a Python wrapper around native class'''
        ret = ActivitySequence()
        ret._hndl = hndl
        ret._owned = owned
        return ret
    

cdef class ExecBlock(ExecScope):
    
    cdef ast_decl.IExecBlock *asExecBlock(self):
        return dynamic_cast[ast_decl.IExecBlockP](self._hndl)
    @staticmethod
    cdef ExecBlock mk(ast_decl.IExecBlock *hndl, bool owned):
        '''Creates a Python wrapper around native class'''
        ret = ExecBlock()
        ret._hndl = hndl
        ret._owned = owned
        return ret
    
    cpdef  getKind(self):
        return dynamic_cast[ast_decl.IExecBlockP](self._hndl).getKind()


cdef class VisitorBase(object):
    def __cinit__(self):
        self._hndl = new ast_decl.PyBaseVisitor(<cpy_ref.PyObject*>self)
    cpdef void visitTemplateParamDeclList(self, TemplateParamDeclList i):
        self._hndl.py_visitTemplateParamDeclListBase(dynamic_cast[ast_decl.ITemplateParamDeclListP](i._hndl));
    cpdef void visitAssocData(self, AssocData i):
        self._hndl.py_visitAssocDataBase(dynamic_cast[ast_decl.IAssocDataP](i._hndl));
    cpdef void visitExecTargetTemplateParam(self, ExecTargetTemplateParam i):
        self._hndl.py_visitExecTargetTemplateParamBase(dynamic_cast[ast_decl.IExecTargetTemplateParamP](i._hndl));
    cpdef void visitExpr(self, Expr i):
        self._hndl.py_visitExprBase(dynamic_cast[ast_decl.IExprP](i._hndl));
    cpdef void visitTemplateParamValue(self, TemplateParamValue i):
        self._hndl.py_visitTemplateParamValueBase(dynamic_cast[ast_decl.ITemplateParamValueP](i._hndl));
    cpdef void visitMonitorActivityMatchChoice(self, MonitorActivityMatchChoice i):
        self._hndl.py_visitMonitorActivityMatchChoiceBase(dynamic_cast[ast_decl.IMonitorActivityMatchChoiceP](i._hndl));
    cpdef void visitTemplateParamValueList(self, TemplateParamValueList i):
        self._hndl.py_visitTemplateParamValueListBase(dynamic_cast[ast_decl.ITemplateParamValueListP](i._hndl));
    cpdef void visitExprAggrMapElem(self, ExprAggrMapElem i):
        self._hndl.py_visitExprAggrMapElemBase(dynamic_cast[ast_decl.IExprAggrMapElemP](i._hndl));
    cpdef void visitRefExpr(self, RefExpr i):
        self._hndl.py_visitRefExprBase(dynamic_cast[ast_decl.IRefExprP](i._hndl));
    cpdef void visitExprAggrStructElem(self, ExprAggrStructElem i):
        self._hndl.py_visitExprAggrStructElemBase(dynamic_cast[ast_decl.IExprAggrStructElemP](i._hndl));
    cpdef void visitMonitorActivitySelectBranch(self, MonitorActivitySelectBranch i):
        self._hndl.py_visitMonitorActivitySelectBranchBase(dynamic_cast[ast_decl.IMonitorActivitySelectBranchP](i._hndl));
    cpdef void visitScopeChild(self, ScopeChild i):
        self._hndl.py_visitScopeChildBase(dynamic_cast[ast_decl.IScopeChildP](i._hndl));
    cpdef void visitActivityMatchChoice(self, ActivityMatchChoice i):
        self._hndl.py_visitActivityMatchChoiceBase(dynamic_cast[ast_decl.IActivityMatchChoiceP](i._hndl));
    cpdef void visitSymbolImportSpec(self, SymbolImportSpec i):
        self._hndl.py_visitSymbolImportSpecBase(dynamic_cast[ast_decl.ISymbolImportSpecP](i._hndl));
    cpdef void visitSymbolRefPath(self, SymbolRefPath i):
        self._hndl.py_visitSymbolRefPathBase(dynamic_cast[ast_decl.ISymbolRefPathP](i._hndl));
    cpdef void visitActivitySelectBranch(self, ActivitySelectBranch i):
        self._hndl.py_visitActivitySelectBranchBase(dynamic_cast[ast_decl.IActivitySelectBranchP](i._hndl));
    cpdef void visitActionFieldInitializer(self, ActionFieldInitializer i):
        self._hndl.py_visitActionFieldInitializerBase(dynamic_cast[ast_decl.IActionFieldInitializerP](i._hndl));
    cpdef void visitActivityJoinSpec(self, ActivityJoinSpec i):
        self._hndl.py_visitActivityJoinSpecBase(dynamic_cast[ast_decl.IActivityJoinSpecP](i._hndl));
    cpdef void visitMonitorActivityStmt(self, MonitorActivityStmt i):
        self._hndl.py_visitMonitorActivityStmtBase(dynamic_cast[ast_decl.IMonitorActivityStmtP](i._hndl));
    cpdef void visitNamedScopeChild(self, NamedScopeChild i):
        self._hndl.py_visitNamedScopeChildBase(dynamic_cast[ast_decl.INamedScopeChildP](i._hndl));
    cpdef void visitPackageImportStmt(self, PackageImportStmt i):
        self._hndl.py_visitPackageImportStmtBase(dynamic_cast[ast_decl.IPackageImportStmtP](i._hndl));
    cpdef void visitActivitySchedulingConstraint(self, ActivitySchedulingConstraint i):
        self._hndl.py_visitActivitySchedulingConstraintBase(dynamic_cast[ast_decl.IActivitySchedulingConstraintP](i._hndl));
    cpdef void visitActivityStmt(self, ActivityStmt i):
        self._hndl.py_visitActivityStmtBase(dynamic_cast[ast_decl.IActivityStmtP](i._hndl));
    cpdef void visitProceduralStmtIfClause(self, ProceduralStmtIfClause i):
        self._hndl.py_visitProceduralStmtIfClauseBase(dynamic_cast[ast_decl.IProceduralStmtIfClauseP](i._hndl));
    cpdef void visitAnnotation(self, Annotation i):
        self._hndl.py_visitAnnotationBase(dynamic_cast[ast_decl.IAnnotationP](i._hndl));
    cpdef void visitAnnotationParam(self, AnnotationParam i):
        self._hndl.py_visitAnnotationParamBase(dynamic_cast[ast_decl.IAnnotationParamP](i._hndl));
    cpdef void visitConstraintStmt(self, ConstraintStmt i):
        self._hndl.py_visitConstraintStmtBase(dynamic_cast[ast_decl.IConstraintStmtP](i._hndl));
    cpdef void visitPyImportFromStmt(self, PyImportFromStmt i):
        self._hndl.py_visitPyImportFromStmtBase(dynamic_cast[ast_decl.IPyImportFromStmtP](i._hndl));
    cpdef void visitPyImportStmt(self, PyImportStmt i):
        self._hndl.py_visitPyImportStmtBase(dynamic_cast[ast_decl.IPyImportStmtP](i._hndl));
    cpdef void visitRefExprScopeIndex(self, RefExprScopeIndex i):
        self._hndl.py_visitRefExprScopeIndexBase(dynamic_cast[ast_decl.IRefExprScopeIndexP](i._hndl));
    cpdef void visitRefExprTypeScopeContext(self, RefExprTypeScopeContext i):
        self._hndl.py_visitRefExprTypeScopeContextBase(dynamic_cast[ast_decl.IRefExprTypeScopeContextP](i._hndl));
    cpdef void visitRefExprTypeScopeGlobal(self, RefExprTypeScopeGlobal i):
        self._hndl.py_visitRefExprTypeScopeGlobalBase(dynamic_cast[ast_decl.IRefExprTypeScopeGlobalP](i._hndl));
    cpdef void visitScope(self, Scope i):
        self._hndl.py_visitScopeBase(dynamic_cast[ast_decl.IScopeP](i._hndl));
    cpdef void visitCoverStmtInline(self, CoverStmtInline i):
        self._hndl.py_visitCoverStmtInlineBase(dynamic_cast[ast_decl.ICoverStmtInlineP](i._hndl));
    cpdef void visitCoverStmtReference(self, CoverStmtReference i):
        self._hndl.py_visitCoverStmtReferenceBase(dynamic_cast[ast_decl.ICoverStmtReferenceP](i._hndl));
    cpdef void visitDataType(self, DataType i):
        self._hndl.py_visitDataTypeBase(dynamic_cast[ast_decl.IDataTypeP](i._hndl));
    cpdef void visitScopeChildRef(self, ScopeChildRef i):
        self._hndl.py_visitScopeChildRefBase(dynamic_cast[ast_decl.IScopeChildRefP](i._hndl));
    cpdef void visitSymbolChild(self, SymbolChild i):
        self._hndl.py_visitSymbolChildBase(dynamic_cast[ast_decl.ISymbolChildP](i._hndl));
    cpdef void visitSymbolScopeRef(self, SymbolScopeRef i):
        self._hndl.py_visitSymbolScopeRefBase(dynamic_cast[ast_decl.ISymbolScopeRefP](i._hndl));
    cpdef void visitTemplateParamDecl(self, TemplateParamDecl i):
        self._hndl.py_visitTemplateParamDeclBase(dynamic_cast[ast_decl.ITemplateParamDeclP](i._hndl));
    cpdef void visitExecStmt(self, ExecStmt i):
        self._hndl.py_visitExecStmtBase(dynamic_cast[ast_decl.IExecStmtP](i._hndl));
    cpdef void visitExecTargetTemplateBlock(self, ExecTargetTemplateBlock i):
        self._hndl.py_visitExecTargetTemplateBlockBase(dynamic_cast[ast_decl.IExecTargetTemplateBlockP](i._hndl));
    cpdef void visitTemplateParamExprValue(self, TemplateParamExprValue i):
        self._hndl.py_visitTemplateParamExprValueBase(dynamic_cast[ast_decl.ITemplateParamExprValueP](i._hndl));
    cpdef void visitExportFunction(self, ExportFunction i):
        self._hndl.py_visitExportFunctionBase(dynamic_cast[ast_decl.IExportFunctionP](i._hndl));
    cpdef void visitTemplateParamTypeValue(self, TemplateParamTypeValue i):
        self._hndl.py_visitTemplateParamTypeValueBase(dynamic_cast[ast_decl.ITemplateParamTypeValueP](i._hndl));
    cpdef void visitTypeIdentifier(self, TypeIdentifier i):
        self._hndl.py_visitTypeIdentifierBase(dynamic_cast[ast_decl.ITypeIdentifierP](i._hndl));
    cpdef void visitExprAggrLiteral(self, ExprAggrLiteral i):
        self._hndl.py_visitExprAggrLiteralBase(dynamic_cast[ast_decl.IExprAggrLiteralP](i._hndl));
    cpdef void visitTypeIdentifierElem(self, TypeIdentifierElem i):
        self._hndl.py_visitTypeIdentifierElemBase(dynamic_cast[ast_decl.ITypeIdentifierElemP](i._hndl));
    cpdef void visitTypedefDeclaration(self, TypedefDeclaration i):
        self._hndl.py_visitTypedefDeclarationBase(dynamic_cast[ast_decl.ITypedefDeclarationP](i._hndl));
    cpdef void visitExprBin(self, ExprBin i):
        self._hndl.py_visitExprBinBase(dynamic_cast[ast_decl.IExprBinP](i._hndl));
    cpdef void visitExprBitSlice(self, ExprBitSlice i):
        self._hndl.py_visitExprBitSliceBase(dynamic_cast[ast_decl.IExprBitSliceP](i._hndl));
    cpdef void visitExprBool(self, ExprBool i):
        self._hndl.py_visitExprBoolBase(dynamic_cast[ast_decl.IExprBoolP](i._hndl));
    cpdef void visitExprCast(self, ExprCast i):
        self._hndl.py_visitExprCastBase(dynamic_cast[ast_decl.IExprCastP](i._hndl));
    cpdef void visitExprCompileHas(self, ExprCompileHas i):
        self._hndl.py_visitExprCompileHasBase(dynamic_cast[ast_decl.IExprCompileHasP](i._hndl));
    cpdef void visitExprCond(self, ExprCond i):
        self._hndl.py_visitExprCondBase(dynamic_cast[ast_decl.IExprCondP](i._hndl));
    cpdef void visitExprDomainOpenRangeList(self, ExprDomainOpenRangeList i):
        self._hndl.py_visitExprDomainOpenRangeListBase(dynamic_cast[ast_decl.IExprDomainOpenRangeListP](i._hndl));
    cpdef void visitExprDomainOpenRangeValue(self, ExprDomainOpenRangeValue i):
        self._hndl.py_visitExprDomainOpenRangeValueBase(dynamic_cast[ast_decl.IExprDomainOpenRangeValueP](i._hndl));
    cpdef void visitExprHierarchicalId(self, ExprHierarchicalId i):
        self._hndl.py_visitExprHierarchicalIdBase(dynamic_cast[ast_decl.IExprHierarchicalIdP](i._hndl));
    cpdef void visitExprId(self, ExprId i):
        self._hndl.py_visitExprIdBase(dynamic_cast[ast_decl.IExprIdP](i._hndl));
    cpdef void visitExprIn(self, ExprIn i):
        self._hndl.py_visitExprInBase(dynamic_cast[ast_decl.IExprInP](i._hndl));
    cpdef void visitExprListLiteral(self, ExprListLiteral i):
        self._hndl.py_visitExprListLiteralBase(dynamic_cast[ast_decl.IExprListLiteralP](i._hndl));
    cpdef void visitExprMemberPathElem(self, ExprMemberPathElem i):
        self._hndl.py_visitExprMemberPathElemBase(dynamic_cast[ast_decl.IExprMemberPathElemP](i._hndl));
    cpdef void visitExprNull(self, ExprNull i):
        self._hndl.py_visitExprNullBase(dynamic_cast[ast_decl.IExprNullP](i._hndl));
    cpdef void visitExprNumber(self, ExprNumber i):
        self._hndl.py_visitExprNumberBase(dynamic_cast[ast_decl.IExprNumberP](i._hndl));
    cpdef void visitExprOpenRangeList(self, ExprOpenRangeList i):
        self._hndl.py_visitExprOpenRangeListBase(dynamic_cast[ast_decl.IExprOpenRangeListP](i._hndl));
    cpdef void visitExprOpenRangeValue(self, ExprOpenRangeValue i):
        self._hndl.py_visitExprOpenRangeValueBase(dynamic_cast[ast_decl.IExprOpenRangeValueP](i._hndl));
    cpdef void visitExprRefPath(self, ExprRefPath i):
        self._hndl.py_visitExprRefPathBase(dynamic_cast[ast_decl.IExprRefPathP](i._hndl));
    cpdef void visitExprRefPathElem(self, ExprRefPathElem i):
        self._hndl.py_visitExprRefPathElemBase(dynamic_cast[ast_decl.IExprRefPathElemP](i._hndl));
    cpdef void visitExprStaticRefPath(self, ExprStaticRefPath i):
        self._hndl.py_visitExprStaticRefPathBase(dynamic_cast[ast_decl.IExprStaticRefPathP](i._hndl));
    cpdef void visitExprString(self, ExprString i):
        self._hndl.py_visitExprStringBase(dynamic_cast[ast_decl.IExprStringP](i._hndl));
    cpdef void visitExprStructLiteral(self, ExprStructLiteral i):
        self._hndl.py_visitExprStructLiteralBase(dynamic_cast[ast_decl.IExprStructLiteralP](i._hndl));
    cpdef void visitExprStructLiteralItem(self, ExprStructLiteralItem i):
        self._hndl.py_visitExprStructLiteralItemBase(dynamic_cast[ast_decl.IExprStructLiteralItemP](i._hndl));
    cpdef void visitExprSubscript(self, ExprSubscript i):
        self._hndl.py_visitExprSubscriptBase(dynamic_cast[ast_decl.IExprSubscriptP](i._hndl));
    cpdef void visitExprSubstring(self, ExprSubstring i):
        self._hndl.py_visitExprSubstringBase(dynamic_cast[ast_decl.IExprSubstringP](i._hndl));
    cpdef void visitExprUnary(self, ExprUnary i):
        self._hndl.py_visitExprUnaryBase(dynamic_cast[ast_decl.IExprUnaryP](i._hndl));
    cpdef void visitExtendEnum(self, ExtendEnum i):
        self._hndl.py_visitExtendEnumBase(dynamic_cast[ast_decl.IExtendEnumP](i._hndl));
    cpdef void visitFunctionDefinition(self, FunctionDefinition i):
        self._hndl.py_visitFunctionDefinitionBase(dynamic_cast[ast_decl.IFunctionDefinitionP](i._hndl));
    cpdef void visitFunctionImport(self, FunctionImport i):
        self._hndl.py_visitFunctionImportBase(dynamic_cast[ast_decl.IFunctionImportP](i._hndl));
    cpdef void visitFunctionParamDecl(self, FunctionParamDecl i):
        self._hndl.py_visitFunctionParamDeclBase(dynamic_cast[ast_decl.IFunctionParamDeclP](i._hndl));
    cpdef void visitGenericConstraintDeclValue(self, GenericConstraintDeclValue i):
        self._hndl.py_visitGenericConstraintDeclValueBase(dynamic_cast[ast_decl.IGenericConstraintDeclValueP](i._hndl));
    cpdef void visitGenericConstraintParam(self, GenericConstraintParam i):
        self._hndl.py_visitGenericConstraintParamBase(dynamic_cast[ast_decl.IGenericConstraintParamP](i._hndl));
    cpdef void visitMethodParameterList(self, MethodParameterList i):
        self._hndl.py_visitMethodParameterListBase(dynamic_cast[ast_decl.IMethodParameterListP](i._hndl));
    cpdef void visitMonitorActivityActionTraversal(self, MonitorActivityActionTraversal i):
        self._hndl.py_visitMonitorActivityActionTraversalBase(dynamic_cast[ast_decl.IMonitorActivityActionTraversalP](i._hndl));
    cpdef void visitMonitorActivityConcat(self, MonitorActivityConcat i):
        self._hndl.py_visitMonitorActivityConcatBase(dynamic_cast[ast_decl.IMonitorActivityConcatP](i._hndl));
    cpdef void visitActionHandleField(self, ActionHandleField i):
        self._hndl.py_visitActionHandleFieldBase(dynamic_cast[ast_decl.IActionHandleFieldP](i._hndl));
    cpdef void visitMonitorActivityEventually(self, MonitorActivityEventually i):
        self._hndl.py_visitMonitorActivityEventuallyBase(dynamic_cast[ast_decl.IMonitorActivityEventuallyP](i._hndl));
    cpdef void visitMonitorActivityIfElse(self, MonitorActivityIfElse i):
        self._hndl.py_visitMonitorActivityIfElseBase(dynamic_cast[ast_decl.IMonitorActivityIfElseP](i._hndl));
    cpdef void visitMonitorActivityMatch(self, MonitorActivityMatch i):
        self._hndl.py_visitMonitorActivityMatchBase(dynamic_cast[ast_decl.IMonitorActivityMatchP](i._hndl));
    cpdef void visitActivityBindStmt(self, ActivityBindStmt i):
        self._hndl.py_visitActivityBindStmtBase(dynamic_cast[ast_decl.IActivityBindStmtP](i._hndl));
    cpdef void visitActivityConstraint(self, ActivityConstraint i):
        self._hndl.py_visitActivityConstraintBase(dynamic_cast[ast_decl.IActivityConstraintP](i._hndl));
    cpdef void visitMonitorActivityMonitorTraversal(self, MonitorActivityMonitorTraversal i):
        self._hndl.py_visitMonitorActivityMonitorTraversalBase(dynamic_cast[ast_decl.IMonitorActivityMonitorTraversalP](i._hndl));
    cpdef void visitMonitorActivityOverlap(self, MonitorActivityOverlap i):
        self._hndl.py_visitMonitorActivityOverlapBase(dynamic_cast[ast_decl.IMonitorActivityOverlapP](i._hndl));
    cpdef void visitMonitorActivityRepeatCount(self, MonitorActivityRepeatCount i):
        self._hndl.py_visitMonitorActivityRepeatCountBase(dynamic_cast[ast_decl.IMonitorActivityRepeatCountP](i._hndl));
    cpdef void visitMonitorActivityRepeatWhile(self, MonitorActivityRepeatWhile i):
        self._hndl.py_visitMonitorActivityRepeatWhileBase(dynamic_cast[ast_decl.IMonitorActivityRepeatWhileP](i._hndl));
    cpdef void visitActivityJoinSpecBranch(self, ActivityJoinSpecBranch i):
        self._hndl.py_visitActivityJoinSpecBranchBase(dynamic_cast[ast_decl.IActivityJoinSpecBranchP](i._hndl));
    cpdef void visitActivityJoinSpecFirst(self, ActivityJoinSpecFirst i):
        self._hndl.py_visitActivityJoinSpecFirstBase(dynamic_cast[ast_decl.IActivityJoinSpecFirstP](i._hndl));
    cpdef void visitActivityJoinSpecNone(self, ActivityJoinSpecNone i):
        self._hndl.py_visitActivityJoinSpecNoneBase(dynamic_cast[ast_decl.IActivityJoinSpecNoneP](i._hndl));
    cpdef void visitActivityJoinSpecSelect(self, ActivityJoinSpecSelect i):
        self._hndl.py_visitActivityJoinSpecSelectBase(dynamic_cast[ast_decl.IActivityJoinSpecSelectP](i._hndl));
    cpdef void visitMonitorActivitySelect(self, MonitorActivitySelect i):
        self._hndl.py_visitMonitorActivitySelectBase(dynamic_cast[ast_decl.IMonitorActivitySelectP](i._hndl));
    cpdef void visitActivityLabeledStmt(self, ActivityLabeledStmt i):
        self._hndl.py_visitActivityLabeledStmtBase(dynamic_cast[ast_decl.IActivityLabeledStmtP](i._hndl));
    cpdef void visitMonitorConstraint(self, MonitorConstraint i):
        self._hndl.py_visitMonitorConstraintBase(dynamic_cast[ast_decl.IMonitorConstraintP](i._hndl));
    cpdef void visitNamedScope(self, NamedScope i):
        self._hndl.py_visitNamedScopeBase(dynamic_cast[ast_decl.INamedScopeP](i._hndl));
    cpdef void visitPackageScope(self, PackageScope i):
        self._hndl.py_visitPackageScopeBase(dynamic_cast[ast_decl.IPackageScopeP](i._hndl));
    cpdef void visitProceduralStmtAssignment(self, ProceduralStmtAssignment i):
        self._hndl.py_visitProceduralStmtAssignmentBase(dynamic_cast[ast_decl.IProceduralStmtAssignmentP](i._hndl));
    cpdef void visitProceduralStmtBody(self, ProceduralStmtBody i):
        self._hndl.py_visitProceduralStmtBodyBase(dynamic_cast[ast_decl.IProceduralStmtBodyP](i._hndl));
    cpdef void visitProceduralStmtBreak(self, ProceduralStmtBreak i):
        self._hndl.py_visitProceduralStmtBreakBase(dynamic_cast[ast_decl.IProceduralStmtBreakP](i._hndl));
    cpdef void visitProceduralStmtContinue(self, ProceduralStmtContinue i):
        self._hndl.py_visitProceduralStmtContinueBase(dynamic_cast[ast_decl.IProceduralStmtContinueP](i._hndl));
    cpdef void visitProceduralStmtDataDeclaration(self, ProceduralStmtDataDeclaration i):
        self._hndl.py_visitProceduralStmtDataDeclarationBase(dynamic_cast[ast_decl.IProceduralStmtDataDeclarationP](i._hndl));
    cpdef void visitProceduralStmtExpr(self, ProceduralStmtExpr i):
        self._hndl.py_visitProceduralStmtExprBase(dynamic_cast[ast_decl.IProceduralStmtExprP](i._hndl));
    cpdef void visitProceduralStmtFunctionCall(self, ProceduralStmtFunctionCall i):
        self._hndl.py_visitProceduralStmtFunctionCallBase(dynamic_cast[ast_decl.IProceduralStmtFunctionCallP](i._hndl));
    cpdef void visitProceduralStmtIfElse(self, ProceduralStmtIfElse i):
        self._hndl.py_visitProceduralStmtIfElseBase(dynamic_cast[ast_decl.IProceduralStmtIfElseP](i._hndl));
    cpdef void visitProceduralStmtMatch(self, ProceduralStmtMatch i):
        self._hndl.py_visitProceduralStmtMatchBase(dynamic_cast[ast_decl.IProceduralStmtMatchP](i._hndl));
    cpdef void visitProceduralStmtMatchChoice(self, ProceduralStmtMatchChoice i):
        self._hndl.py_visitProceduralStmtMatchChoiceBase(dynamic_cast[ast_decl.IProceduralStmtMatchChoiceP](i._hndl));
    cpdef void visitProceduralStmtRandomize(self, ProceduralStmtRandomize i):
        self._hndl.py_visitProceduralStmtRandomizeBase(dynamic_cast[ast_decl.IProceduralStmtRandomizeP](i._hndl));
    cpdef void visitProceduralStmtReturn(self, ProceduralStmtReturn i):
        self._hndl.py_visitProceduralStmtReturnBase(dynamic_cast[ast_decl.IProceduralStmtReturnP](i._hndl));
    cpdef void visitConstraintScope(self, ConstraintScope i):
        self._hndl.py_visitConstraintScopeBase(dynamic_cast[ast_decl.IConstraintScopeP](i._hndl));
    cpdef void visitConstraintStmtDefault(self, ConstraintStmtDefault i):
        self._hndl.py_visitConstraintStmtDefaultBase(dynamic_cast[ast_decl.IConstraintStmtDefaultP](i._hndl));
    cpdef void visitConstraintStmtDefaultDisable(self, ConstraintStmtDefaultDisable i):
        self._hndl.py_visitConstraintStmtDefaultDisableBase(dynamic_cast[ast_decl.IConstraintStmtDefaultDisableP](i._hndl));
    cpdef void visitConstraintStmtExpr(self, ConstraintStmtExpr i):
        self._hndl.py_visitConstraintStmtExprBase(dynamic_cast[ast_decl.IConstraintStmtExprP](i._hndl));
    cpdef void visitConstraintStmtField(self, ConstraintStmtField i):
        self._hndl.py_visitConstraintStmtFieldBase(dynamic_cast[ast_decl.IConstraintStmtFieldP](i._hndl));
    cpdef void visitProceduralStmtYield(self, ProceduralStmtYield i):
        self._hndl.py_visitProceduralStmtYieldBase(dynamic_cast[ast_decl.IProceduralStmtYieldP](i._hndl));
    cpdef void visitConstraintStmtIf(self, ConstraintStmtIf i):
        self._hndl.py_visitConstraintStmtIfBase(dynamic_cast[ast_decl.IConstraintStmtIfP](i._hndl));
    cpdef void visitConstraintStmtUnique(self, ConstraintStmtUnique i):
        self._hndl.py_visitConstraintStmtUniqueBase(dynamic_cast[ast_decl.IConstraintStmtUniqueP](i._hndl));
    cpdef void visitSymbolChildrenScope(self, SymbolChildrenScope i):
        self._hndl.py_visitSymbolChildrenScopeBase(dynamic_cast[ast_decl.ISymbolChildrenScopeP](i._hndl));
    cpdef void visitDataTypeBool(self, DataTypeBool i):
        self._hndl.py_visitDataTypeBoolBase(dynamic_cast[ast_decl.IDataTypeBoolP](i._hndl));
    cpdef void visitDataTypeChandle(self, DataTypeChandle i):
        self._hndl.py_visitDataTypeChandleBase(dynamic_cast[ast_decl.IDataTypeChandleP](i._hndl));
    cpdef void visitDataTypeEnum(self, DataTypeEnum i):
        self._hndl.py_visitDataTypeEnumBase(dynamic_cast[ast_decl.IDataTypeEnumP](i._hndl));
    cpdef void visitDataTypeInt(self, DataTypeInt i):
        self._hndl.py_visitDataTypeIntBase(dynamic_cast[ast_decl.IDataTypeIntP](i._hndl));
    cpdef void visitDataTypePyObj(self, DataTypePyObj i):
        self._hndl.py_visitDataTypePyObjBase(dynamic_cast[ast_decl.IDataTypePyObjP](i._hndl));
    cpdef void visitDataTypeRef(self, DataTypeRef i):
        self._hndl.py_visitDataTypeRefBase(dynamic_cast[ast_decl.IDataTypeRefP](i._hndl));
    cpdef void visitDataTypeString(self, DataTypeString i):
        self._hndl.py_visitDataTypeStringBase(dynamic_cast[ast_decl.IDataTypeStringP](i._hndl));
    cpdef void visitDataTypeUserDefined(self, DataTypeUserDefined i):
        self._hndl.py_visitDataTypeUserDefinedBase(dynamic_cast[ast_decl.IDataTypeUserDefinedP](i._hndl));
    cpdef void visitEnumDecl(self, EnumDecl i):
        self._hndl.py_visitEnumDeclBase(dynamic_cast[ast_decl.IEnumDeclP](i._hndl));
    cpdef void visitEnumItem(self, EnumItem i):
        self._hndl.py_visitEnumItemBase(dynamic_cast[ast_decl.IEnumItemP](i._hndl));
    cpdef void visitTemplateCategoryTypeParamDecl(self, TemplateCategoryTypeParamDecl i):
        self._hndl.py_visitTemplateCategoryTypeParamDeclBase(dynamic_cast[ast_decl.ITemplateCategoryTypeParamDeclP](i._hndl));
    cpdef void visitTemplateGenericTypeParamDecl(self, TemplateGenericTypeParamDecl i):
        self._hndl.py_visitTemplateGenericTypeParamDeclBase(dynamic_cast[ast_decl.ITemplateGenericTypeParamDeclP](i._hndl));
    cpdef void visitExprAggrEmpty(self, ExprAggrEmpty i):
        self._hndl.py_visitExprAggrEmptyBase(dynamic_cast[ast_decl.IExprAggrEmptyP](i._hndl));
    cpdef void visitExprAggrList(self, ExprAggrList i):
        self._hndl.py_visitExprAggrListBase(dynamic_cast[ast_decl.IExprAggrListP](i._hndl));
    cpdef void visitTemplateValueParamDecl(self, TemplateValueParamDecl i):
        self._hndl.py_visitTemplateValueParamDeclBase(dynamic_cast[ast_decl.ITemplateValueParamDeclP](i._hndl));
    cpdef void visitExprAggrMap(self, ExprAggrMap i):
        self._hndl.py_visitExprAggrMapBase(dynamic_cast[ast_decl.IExprAggrMapP](i._hndl));
    cpdef void visitExprAggrStruct(self, ExprAggrStruct i):
        self._hndl.py_visitExprAggrStructBase(dynamic_cast[ast_decl.IExprAggrStructP](i._hndl));
    cpdef void visitExprRefPathContext(self, ExprRefPathContext i):
        self._hndl.py_visitExprRefPathContextBase(dynamic_cast[ast_decl.IExprRefPathContextP](i._hndl));
    cpdef void visitExprRefPathId(self, ExprRefPathId i):
        self._hndl.py_visitExprRefPathIdBase(dynamic_cast[ast_decl.IExprRefPathIdP](i._hndl));
    cpdef void visitExprRefPathStatic(self, ExprRefPathStatic i):
        self._hndl.py_visitExprRefPathStaticBase(dynamic_cast[ast_decl.IExprRefPathStaticP](i._hndl));
    cpdef void visitExprRefPathStaticRooted(self, ExprRefPathStaticRooted i):
        self._hndl.py_visitExprRefPathStaticRootedBase(dynamic_cast[ast_decl.IExprRefPathStaticRootedP](i._hndl));
    cpdef void visitExprSignedNumber(self, ExprSignedNumber i):
        self._hndl.py_visitExprSignedNumberBase(dynamic_cast[ast_decl.IExprSignedNumberP](i._hndl));
    cpdef void visitExprUnsignedNumber(self, ExprUnsignedNumber i):
        self._hndl.py_visitExprUnsignedNumberBase(dynamic_cast[ast_decl.IExprUnsignedNumberP](i._hndl));
    cpdef void visitExtendType(self, ExtendType i):
        self._hndl.py_visitExtendTypeBase(dynamic_cast[ast_decl.IExtendTypeP](i._hndl));
    cpdef void visitField(self, Field i):
        self._hndl.py_visitFieldBase(dynamic_cast[ast_decl.IFieldP](i._hndl));
    cpdef void visitFieldClaim(self, FieldClaim i):
        self._hndl.py_visitFieldClaimBase(dynamic_cast[ast_decl.IFieldClaimP](i._hndl));
    cpdef void visitFieldCompRef(self, FieldCompRef i):
        self._hndl.py_visitFieldCompRefBase(dynamic_cast[ast_decl.IFieldCompRefP](i._hndl));
    cpdef void visitFieldRef(self, FieldRef i):
        self._hndl.py_visitFieldRefBase(dynamic_cast[ast_decl.IFieldRefP](i._hndl));
    cpdef void visitFunctionImportProto(self, FunctionImportProto i):
        self._hndl.py_visitFunctionImportProtoBase(dynamic_cast[ast_decl.IFunctionImportProtoP](i._hndl));
    cpdef void visitFunctionImportType(self, FunctionImportType i):
        self._hndl.py_visitFunctionImportTypeBase(dynamic_cast[ast_decl.IFunctionImportTypeP](i._hndl));
    cpdef void visitFunctionPrototype(self, FunctionPrototype i):
        self._hndl.py_visitFunctionPrototypeBase(dynamic_cast[ast_decl.IFunctionPrototypeP](i._hndl));
    cpdef void visitGlobalScope(self, GlobalScope i):
        self._hndl.py_visitGlobalScopeBase(dynamic_cast[ast_decl.IGlobalScopeP](i._hndl));
    cpdef void visitActivityActionHandleTraversal(self, ActivityActionHandleTraversal i):
        self._hndl.py_visitActivityActionHandleTraversalBase(dynamic_cast[ast_decl.IActivityActionHandleTraversalP](i._hndl));
    cpdef void visitActivityActionTypeTraversal(self, ActivityActionTypeTraversal i):
        self._hndl.py_visitActivityActionTypeTraversalBase(dynamic_cast[ast_decl.IActivityActionTypeTraversalP](i._hndl));
    cpdef void visitActivityAtomicBlock(self, ActivityAtomicBlock i):
        self._hndl.py_visitActivityAtomicBlockBase(dynamic_cast[ast_decl.IActivityAtomicBlockP](i._hndl));
    cpdef void visitActivityForeach(self, ActivityForeach i):
        self._hndl.py_visitActivityForeachBase(dynamic_cast[ast_decl.IActivityForeachP](i._hndl));
    cpdef void visitActivityIfElse(self, ActivityIfElse i):
        self._hndl.py_visitActivityIfElseBase(dynamic_cast[ast_decl.IActivityIfElseP](i._hndl));
    cpdef void visitActivityMatch(self, ActivityMatch i):
        self._hndl.py_visitActivityMatchBase(dynamic_cast[ast_decl.IActivityMatchP](i._hndl));
    cpdef void visitActivityRepeatCount(self, ActivityRepeatCount i):
        self._hndl.py_visitActivityRepeatCountBase(dynamic_cast[ast_decl.IActivityRepeatCountP](i._hndl));
    cpdef void visitActivityRepeatWhile(self, ActivityRepeatWhile i):
        self._hndl.py_visitActivityRepeatWhileBase(dynamic_cast[ast_decl.IActivityRepeatWhileP](i._hndl));
    cpdef void visitActivityReplicate(self, ActivityReplicate i):
        self._hndl.py_visitActivityReplicateBase(dynamic_cast[ast_decl.IActivityReplicateP](i._hndl));
    cpdef void visitActivitySelect(self, ActivitySelect i):
        self._hndl.py_visitActivitySelectBase(dynamic_cast[ast_decl.IActivitySelectP](i._hndl));
    cpdef void visitActivitySuper(self, ActivitySuper i):
        self._hndl.py_visitActivitySuperBase(dynamic_cast[ast_decl.IActivitySuperP](i._hndl));
    cpdef void visitProceduralStmtRepeatWhile(self, ProceduralStmtRepeatWhile i):
        self._hndl.py_visitProceduralStmtRepeatWhileBase(dynamic_cast[ast_decl.IProceduralStmtRepeatWhileP](i._hndl));
    cpdef void visitConstraintBlock(self, ConstraintBlock i):
        self._hndl.py_visitConstraintBlockBase(dynamic_cast[ast_decl.IConstraintBlockP](i._hndl));
    cpdef void visitProceduralStmtWhile(self, ProceduralStmtWhile i):
        self._hndl.py_visitProceduralStmtWhileBase(dynamic_cast[ast_decl.IProceduralStmtWhileP](i._hndl));
    cpdef void visitConstraintStmtForall(self, ConstraintStmtForall i):
        self._hndl.py_visitConstraintStmtForallBase(dynamic_cast[ast_decl.IConstraintStmtForallP](i._hndl));
    cpdef void visitConstraintStmtForeach(self, ConstraintStmtForeach i):
        self._hndl.py_visitConstraintStmtForeachBase(dynamic_cast[ast_decl.IConstraintStmtForeachP](i._hndl));
    cpdef void visitConstraintStmtImplication(self, ConstraintStmtImplication i):
        self._hndl.py_visitConstraintStmtImplicationBase(dynamic_cast[ast_decl.IConstraintStmtImplicationP](i._hndl));
    cpdef void visitSymbolScope(self, SymbolScope i):
        self._hndl.py_visitSymbolScopeBase(dynamic_cast[ast_decl.ISymbolScopeP](i._hndl));
    cpdef void visitTypeScope(self, TypeScope i):
        self._hndl.py_visitTypeScopeBase(dynamic_cast[ast_decl.ITypeScopeP](i._hndl));
    cpdef void visitExprRefPathStaticFunc(self, ExprRefPathStaticFunc i):
        self._hndl.py_visitExprRefPathStaticFuncBase(dynamic_cast[ast_decl.IExprRefPathStaticFuncP](i._hndl));
    cpdef void visitExprRefPathSuper(self, ExprRefPathSuper i):
        self._hndl.py_visitExprRefPathSuperBase(dynamic_cast[ast_decl.IExprRefPathSuperP](i._hndl));
    cpdef void visitAction(self, Action i):
        self._hndl.py_visitActionBase(dynamic_cast[ast_decl.IActionP](i._hndl));
    cpdef void visitMonitorActivityDecl(self, MonitorActivityDecl i):
        self._hndl.py_visitMonitorActivityDeclBase(dynamic_cast[ast_decl.IMonitorActivityDeclP](i._hndl));
    cpdef void visitActivityDecl(self, ActivityDecl i):
        self._hndl.py_visitActivityDeclBase(dynamic_cast[ast_decl.IActivityDeclP](i._hndl));
    cpdef void visitMonitorActivitySchedule(self, MonitorActivitySchedule i):
        self._hndl.py_visitMonitorActivityScheduleBase(dynamic_cast[ast_decl.IMonitorActivityScheduleP](i._hndl));
    cpdef void visitMonitorActivitySequence(self, MonitorActivitySequence i):
        self._hndl.py_visitMonitorActivitySequenceBase(dynamic_cast[ast_decl.IMonitorActivitySequenceP](i._hndl));
    cpdef void visitActivityLabeledScope(self, ActivityLabeledScope i):
        self._hndl.py_visitActivityLabeledScopeBase(dynamic_cast[ast_decl.IActivityLabeledScopeP](i._hndl));
    cpdef void visitAnnotationDecl(self, AnnotationDecl i):
        self._hndl.py_visitAnnotationDeclBase(dynamic_cast[ast_decl.IAnnotationDeclP](i._hndl));
    cpdef void visitComponent(self, Component i):
        self._hndl.py_visitComponentBase(dynamic_cast[ast_decl.IComponentP](i._hndl));
    cpdef void visitProceduralStmtSymbolBodyScope(self, ProceduralStmtSymbolBodyScope i):
        self._hndl.py_visitProceduralStmtSymbolBodyScopeBase(dynamic_cast[ast_decl.IProceduralStmtSymbolBodyScopeP](i._hndl));
    cpdef void visitRootSymbolScope(self, RootSymbolScope i):
        self._hndl.py_visitRootSymbolScopeBase(dynamic_cast[ast_decl.IRootSymbolScopeP](i._hndl));
    cpdef void visitConstraintSymbolScope(self, ConstraintSymbolScope i):
        self._hndl.py_visitConstraintSymbolScopeBase(dynamic_cast[ast_decl.IConstraintSymbolScopeP](i._hndl));
    cpdef void visitStruct(self, Struct i):
        self._hndl.py_visitStructBase(dynamic_cast[ast_decl.IStructP](i._hndl));
    cpdef void visitSymbolEnumScope(self, SymbolEnumScope i):
        self._hndl.py_visitSymbolEnumScopeBase(dynamic_cast[ast_decl.ISymbolEnumScopeP](i._hndl));
    cpdef void visitSymbolExtendScope(self, SymbolExtendScope i):
        self._hndl.py_visitSymbolExtendScopeBase(dynamic_cast[ast_decl.ISymbolExtendScopeP](i._hndl));
    cpdef void visitSymbolFunctionScope(self, SymbolFunctionScope i):
        self._hndl.py_visitSymbolFunctionScopeBase(dynamic_cast[ast_decl.ISymbolFunctionScopeP](i._hndl));
    cpdef void visitSymbolTypeScope(self, SymbolTypeScope i):
        self._hndl.py_visitSymbolTypeScopeBase(dynamic_cast[ast_decl.ISymbolTypeScopeP](i._hndl));
    cpdef void visitExecScope(self, ExecScope i):
        self._hndl.py_visitExecScopeBase(dynamic_cast[ast_decl.IExecScopeP](i._hndl));
    cpdef void visitGenericConstraintDeclBool(self, GenericConstraintDeclBool i):
        self._hndl.py_visitGenericConstraintDeclBoolBase(dynamic_cast[ast_decl.IGenericConstraintDeclBoolP](i._hndl));
    cpdef void visitMonitor(self, Monitor i):
        self._hndl.py_visitMonitorBase(dynamic_cast[ast_decl.IMonitorP](i._hndl));
    cpdef void visitProceduralStmtRepeat(self, ProceduralStmtRepeat i):
        self._hndl.py_visitProceduralStmtRepeatBase(dynamic_cast[ast_decl.IProceduralStmtRepeatP](i._hndl));
    cpdef void visitActivityParallel(self, ActivityParallel i):
        self._hndl.py_visitActivityParallelBase(dynamic_cast[ast_decl.IActivityParallelP](i._hndl));
    cpdef void visitActivitySchedule(self, ActivitySchedule i):
        self._hndl.py_visitActivityScheduleBase(dynamic_cast[ast_decl.IActivityScheduleP](i._hndl));
    cpdef void visitProceduralStmtForeach(self, ProceduralStmtForeach i):
        self._hndl.py_visitProceduralStmtForeachBase(dynamic_cast[ast_decl.IProceduralStmtForeachP](i._hndl));
    cpdef void visitActivitySequence(self, ActivitySequence i):
        self._hndl.py_visitActivitySequenceBase(dynamic_cast[ast_decl.IActivitySequenceP](i._hndl));
    cpdef void visitExecBlock(self, ExecBlock i):
        self._hndl.py_visitExecBlockBase(dynamic_cast[ast_decl.IExecBlockP](i._hndl));
cdef public api ast_call_visitTemplateParamDeclList(object self, ast_decl.ITemplateParamDeclList *i) with gil:
    self.visitTemplateParamDeclList(TemplateParamDeclList.mk(i, False))
cdef public api ast_call_visitAssocData(object self, ast_decl.IAssocData *i) with gil:
    self.visitAssocData(AssocData.mk(i, False))
cdef public api ast_call_visitExecTargetTemplateParam(object self, ast_decl.IExecTargetTemplateParam *i) with gil:
    self.visitExecTargetTemplateParam(ExecTargetTemplateParam.mk(i, False))
cdef public api ast_call_visitExpr(object self, ast_decl.IExpr *i) with gil:
    self.visitExpr(Expr.mk(i, False))
cdef public api ast_call_visitTemplateParamValue(object self, ast_decl.ITemplateParamValue *i) with gil:
    self.visitTemplateParamValue(TemplateParamValue.mk(i, False))
cdef public api ast_call_visitMonitorActivityMatchChoice(object self, ast_decl.IMonitorActivityMatchChoice *i) with gil:
    self.visitMonitorActivityMatchChoice(MonitorActivityMatchChoice.mk(i, False))
cdef public api ast_call_visitTemplateParamValueList(object self, ast_decl.ITemplateParamValueList *i) with gil:
    self.visitTemplateParamValueList(TemplateParamValueList.mk(i, False))
cdef public api ast_call_visitExprAggrMapElem(object self, ast_decl.IExprAggrMapElem *i) with gil:
    self.visitExprAggrMapElem(ExprAggrMapElem.mk(i, False))
cdef public api ast_call_visitRefExpr(object self, ast_decl.IRefExpr *i) with gil:
    self.visitRefExpr(RefExpr.mk(i, False))
cdef public api ast_call_visitExprAggrStructElem(object self, ast_decl.IExprAggrStructElem *i) with gil:
    self.visitExprAggrStructElem(ExprAggrStructElem.mk(i, False))
cdef public api ast_call_visitMonitorActivitySelectBranch(object self, ast_decl.IMonitorActivitySelectBranch *i) with gil:
    self.visitMonitorActivitySelectBranch(MonitorActivitySelectBranch.mk(i, False))
cdef public api ast_call_visitScopeChild(object self, ast_decl.IScopeChild *i) with gil:
    self.visitScopeChild(ScopeChild.mk(i, False))
cdef public api ast_call_visitActivityMatchChoice(object self, ast_decl.IActivityMatchChoice *i) with gil:
    self.visitActivityMatchChoice(ActivityMatchChoice.mk(i, False))
cdef public api ast_call_visitSymbolImportSpec(object self, ast_decl.ISymbolImportSpec *i) with gil:
    self.visitSymbolImportSpec(SymbolImportSpec.mk(i, False))
cdef public api ast_call_visitSymbolRefPath(object self, ast_decl.ISymbolRefPath *i) with gil:
    self.visitSymbolRefPath(SymbolRefPath.mk(i, False))
cdef public api ast_call_visitActivitySelectBranch(object self, ast_decl.IActivitySelectBranch *i) with gil:
    self.visitActivitySelectBranch(ActivitySelectBranch.mk(i, False))
cdef public api ast_call_visitActionFieldInitializer(object self, ast_decl.IActionFieldInitializer *i) with gil:
    self.visitActionFieldInitializer(ActionFieldInitializer.mk(i, False))
cdef public api ast_call_visitActivityJoinSpec(object self, ast_decl.IActivityJoinSpec *i) with gil:
    self.visitActivityJoinSpec(ActivityJoinSpec.mk(i, False))
cdef public api ast_call_visitMonitorActivityStmt(object self, ast_decl.IMonitorActivityStmt *i) with gil:
    self.visitMonitorActivityStmt(MonitorActivityStmt.mk(i, False))
cdef public api ast_call_visitNamedScopeChild(object self, ast_decl.INamedScopeChild *i) with gil:
    self.visitNamedScopeChild(NamedScopeChild.mk(i, False))
cdef public api ast_call_visitPackageImportStmt(object self, ast_decl.IPackageImportStmt *i) with gil:
    self.visitPackageImportStmt(PackageImportStmt.mk(i, False))
cdef public api ast_call_visitActivitySchedulingConstraint(object self, ast_decl.IActivitySchedulingConstraint *i) with gil:
    self.visitActivitySchedulingConstraint(ActivitySchedulingConstraint.mk(i, False))
cdef public api ast_call_visitActivityStmt(object self, ast_decl.IActivityStmt *i) with gil:
    self.visitActivityStmt(ActivityStmt.mk(i, False))
cdef public api ast_call_visitProceduralStmtIfClause(object self, ast_decl.IProceduralStmtIfClause *i) with gil:
    self.visitProceduralStmtIfClause(ProceduralStmtIfClause.mk(i, False))
cdef public api ast_call_visitAnnotation(object self, ast_decl.IAnnotation *i) with gil:
    self.visitAnnotation(Annotation.mk(i, False))
cdef public api ast_call_visitAnnotationParam(object self, ast_decl.IAnnotationParam *i) with gil:
    self.visitAnnotationParam(AnnotationParam.mk(i, False))
cdef public api ast_call_visitConstraintStmt(object self, ast_decl.IConstraintStmt *i) with gil:
    self.visitConstraintStmt(ConstraintStmt.mk(i, False))
cdef public api ast_call_visitPyImportFromStmt(object self, ast_decl.IPyImportFromStmt *i) with gil:
    self.visitPyImportFromStmt(PyImportFromStmt.mk(i, False))
cdef public api ast_call_visitPyImportStmt(object self, ast_decl.IPyImportStmt *i) with gil:
    self.visitPyImportStmt(PyImportStmt.mk(i, False))
cdef public api ast_call_visitRefExprScopeIndex(object self, ast_decl.IRefExprScopeIndex *i) with gil:
    self.visitRefExprScopeIndex(RefExprScopeIndex.mk(i, False))
cdef public api ast_call_visitRefExprTypeScopeContext(object self, ast_decl.IRefExprTypeScopeContext *i) with gil:
    self.visitRefExprTypeScopeContext(RefExprTypeScopeContext.mk(i, False))
cdef public api ast_call_visitRefExprTypeScopeGlobal(object self, ast_decl.IRefExprTypeScopeGlobal *i) with gil:
    self.visitRefExprTypeScopeGlobal(RefExprTypeScopeGlobal.mk(i, False))
cdef public api ast_call_visitScope(object self, ast_decl.IScope *i) with gil:
    self.visitScope(Scope.mk(i, False))
cdef public api ast_call_visitCoverStmtInline(object self, ast_decl.ICoverStmtInline *i) with gil:
    self.visitCoverStmtInline(CoverStmtInline.mk(i, False))
cdef public api ast_call_visitCoverStmtReference(object self, ast_decl.ICoverStmtReference *i) with gil:
    self.visitCoverStmtReference(CoverStmtReference.mk(i, False))
cdef public api ast_call_visitDataType(object self, ast_decl.IDataType *i) with gil:
    self.visitDataType(DataType.mk(i, False))
cdef public api ast_call_visitScopeChildRef(object self, ast_decl.IScopeChildRef *i) with gil:
    self.visitScopeChildRef(ScopeChildRef.mk(i, False))
cdef public api ast_call_visitSymbolChild(object self, ast_decl.ISymbolChild *i) with gil:
    self.visitSymbolChild(SymbolChild.mk(i, False))
cdef public api ast_call_visitSymbolScopeRef(object self, ast_decl.ISymbolScopeRef *i) with gil:
    self.visitSymbolScopeRef(SymbolScopeRef.mk(i, False))
cdef public api ast_call_visitTemplateParamDecl(object self, ast_decl.ITemplateParamDecl *i) with gil:
    self.visitTemplateParamDecl(TemplateParamDecl.mk(i, False))
cdef public api ast_call_visitExecStmt(object self, ast_decl.IExecStmt *i) with gil:
    self.visitExecStmt(ExecStmt.mk(i, False))
cdef public api ast_call_visitExecTargetTemplateBlock(object self, ast_decl.IExecTargetTemplateBlock *i) with gil:
    self.visitExecTargetTemplateBlock(ExecTargetTemplateBlock.mk(i, False))
cdef public api ast_call_visitTemplateParamExprValue(object self, ast_decl.ITemplateParamExprValue *i) with gil:
    self.visitTemplateParamExprValue(TemplateParamExprValue.mk(i, False))
cdef public api ast_call_visitExportFunction(object self, ast_decl.IExportFunction *i) with gil:
    self.visitExportFunction(ExportFunction.mk(i, False))
cdef public api ast_call_visitTemplateParamTypeValue(object self, ast_decl.ITemplateParamTypeValue *i) with gil:
    self.visitTemplateParamTypeValue(TemplateParamTypeValue.mk(i, False))
cdef public api ast_call_visitTypeIdentifier(object self, ast_decl.ITypeIdentifier *i) with gil:
    self.visitTypeIdentifier(TypeIdentifier.mk(i, False))
cdef public api ast_call_visitExprAggrLiteral(object self, ast_decl.IExprAggrLiteral *i) with gil:
    self.visitExprAggrLiteral(ExprAggrLiteral.mk(i, False))
cdef public api ast_call_visitTypeIdentifierElem(object self, ast_decl.ITypeIdentifierElem *i) with gil:
    self.visitTypeIdentifierElem(TypeIdentifierElem.mk(i, False))
cdef public api ast_call_visitTypedefDeclaration(object self, ast_decl.ITypedefDeclaration *i) with gil:
    self.visitTypedefDeclaration(TypedefDeclaration.mk(i, False))
cdef public api ast_call_visitExprBin(object self, ast_decl.IExprBin *i) with gil:
    self.visitExprBin(ExprBin.mk(i, False))
cdef public api ast_call_visitExprBitSlice(object self, ast_decl.IExprBitSlice *i) with gil:
    self.visitExprBitSlice(ExprBitSlice.mk(i, False))
cdef public api ast_call_visitExprBool(object self, ast_decl.IExprBool *i) with gil:
    self.visitExprBool(ExprBool.mk(i, False))
cdef public api ast_call_visitExprCast(object self, ast_decl.IExprCast *i) with gil:
    self.visitExprCast(ExprCast.mk(i, False))
cdef public api ast_call_visitExprCompileHas(object self, ast_decl.IExprCompileHas *i) with gil:
    self.visitExprCompileHas(ExprCompileHas.mk(i, False))
cdef public api ast_call_visitExprCond(object self, ast_decl.IExprCond *i) with gil:
    self.visitExprCond(ExprCond.mk(i, False))
cdef public api ast_call_visitExprDomainOpenRangeList(object self, ast_decl.IExprDomainOpenRangeList *i) with gil:
    self.visitExprDomainOpenRangeList(ExprDomainOpenRangeList.mk(i, False))
cdef public api ast_call_visitExprDomainOpenRangeValue(object self, ast_decl.IExprDomainOpenRangeValue *i) with gil:
    self.visitExprDomainOpenRangeValue(ExprDomainOpenRangeValue.mk(i, False))
cdef public api ast_call_visitExprHierarchicalId(object self, ast_decl.IExprHierarchicalId *i) with gil:
    self.visitExprHierarchicalId(ExprHierarchicalId.mk(i, False))
cdef public api ast_call_visitExprId(object self, ast_decl.IExprId *i) with gil:
    self.visitExprId(ExprId.mk(i, False))
cdef public api ast_call_visitExprIn(object self, ast_decl.IExprIn *i) with gil:
    self.visitExprIn(ExprIn.mk(i, False))
cdef public api ast_call_visitExprListLiteral(object self, ast_decl.IExprListLiteral *i) with gil:
    self.visitExprListLiteral(ExprListLiteral.mk(i, False))
cdef public api ast_call_visitExprMemberPathElem(object self, ast_decl.IExprMemberPathElem *i) with gil:
    self.visitExprMemberPathElem(ExprMemberPathElem.mk(i, False))
cdef public api ast_call_visitExprNull(object self, ast_decl.IExprNull *i) with gil:
    self.visitExprNull(ExprNull.mk(i, False))
cdef public api ast_call_visitExprNumber(object self, ast_decl.IExprNumber *i) with gil:
    self.visitExprNumber(ExprNumber.mk(i, False))
cdef public api ast_call_visitExprOpenRangeList(object self, ast_decl.IExprOpenRangeList *i) with gil:
    self.visitExprOpenRangeList(ExprOpenRangeList.mk(i, False))
cdef public api ast_call_visitExprOpenRangeValue(object self, ast_decl.IExprOpenRangeValue *i) with gil:
    self.visitExprOpenRangeValue(ExprOpenRangeValue.mk(i, False))
cdef public api ast_call_visitExprRefPath(object self, ast_decl.IExprRefPath *i) with gil:
    self.visitExprRefPath(ExprRefPath.mk(i, False))
cdef public api ast_call_visitExprRefPathElem(object self, ast_decl.IExprRefPathElem *i) with gil:
    self.visitExprRefPathElem(ExprRefPathElem.mk(i, False))
cdef public api ast_call_visitExprStaticRefPath(object self, ast_decl.IExprStaticRefPath *i) with gil:
    self.visitExprStaticRefPath(ExprStaticRefPath.mk(i, False))
cdef public api ast_call_visitExprString(object self, ast_decl.IExprString *i) with gil:
    self.visitExprString(ExprString.mk(i, False))
cdef public api ast_call_visitExprStructLiteral(object self, ast_decl.IExprStructLiteral *i) with gil:
    self.visitExprStructLiteral(ExprStructLiteral.mk(i, False))
cdef public api ast_call_visitExprStructLiteralItem(object self, ast_decl.IExprStructLiteralItem *i) with gil:
    self.visitExprStructLiteralItem(ExprStructLiteralItem.mk(i, False))
cdef public api ast_call_visitExprSubscript(object self, ast_decl.IExprSubscript *i) with gil:
    self.visitExprSubscript(ExprSubscript.mk(i, False))
cdef public api ast_call_visitExprSubstring(object self, ast_decl.IExprSubstring *i) with gil:
    self.visitExprSubstring(ExprSubstring.mk(i, False))
cdef public api ast_call_visitExprUnary(object self, ast_decl.IExprUnary *i) with gil:
    self.visitExprUnary(ExprUnary.mk(i, False))
cdef public api ast_call_visitExtendEnum(object self, ast_decl.IExtendEnum *i) with gil:
    self.visitExtendEnum(ExtendEnum.mk(i, False))
cdef public api ast_call_visitFunctionDefinition(object self, ast_decl.IFunctionDefinition *i) with gil:
    self.visitFunctionDefinition(FunctionDefinition.mk(i, False))
cdef public api ast_call_visitFunctionImport(object self, ast_decl.IFunctionImport *i) with gil:
    self.visitFunctionImport(FunctionImport.mk(i, False))
cdef public api ast_call_visitFunctionParamDecl(object self, ast_decl.IFunctionParamDecl *i) with gil:
    self.visitFunctionParamDecl(FunctionParamDecl.mk(i, False))
cdef public api ast_call_visitGenericConstraintDeclValue(object self, ast_decl.IGenericConstraintDeclValue *i) with gil:
    self.visitGenericConstraintDeclValue(GenericConstraintDeclValue.mk(i, False))
cdef public api ast_call_visitGenericConstraintParam(object self, ast_decl.IGenericConstraintParam *i) with gil:
    self.visitGenericConstraintParam(GenericConstraintParam.mk(i, False))
cdef public api ast_call_visitMethodParameterList(object self, ast_decl.IMethodParameterList *i) with gil:
    self.visitMethodParameterList(MethodParameterList.mk(i, False))
cdef public api ast_call_visitMonitorActivityActionTraversal(object self, ast_decl.IMonitorActivityActionTraversal *i) with gil:
    self.visitMonitorActivityActionTraversal(MonitorActivityActionTraversal.mk(i, False))
cdef public api ast_call_visitMonitorActivityConcat(object self, ast_decl.IMonitorActivityConcat *i) with gil:
    self.visitMonitorActivityConcat(MonitorActivityConcat.mk(i, False))
cdef public api ast_call_visitActionHandleField(object self, ast_decl.IActionHandleField *i) with gil:
    self.visitActionHandleField(ActionHandleField.mk(i, False))
cdef public api ast_call_visitMonitorActivityEventually(object self, ast_decl.IMonitorActivityEventually *i) with gil:
    self.visitMonitorActivityEventually(MonitorActivityEventually.mk(i, False))
cdef public api ast_call_visitMonitorActivityIfElse(object self, ast_decl.IMonitorActivityIfElse *i) with gil:
    self.visitMonitorActivityIfElse(MonitorActivityIfElse.mk(i, False))
cdef public api ast_call_visitMonitorActivityMatch(object self, ast_decl.IMonitorActivityMatch *i) with gil:
    self.visitMonitorActivityMatch(MonitorActivityMatch.mk(i, False))
cdef public api ast_call_visitActivityBindStmt(object self, ast_decl.IActivityBindStmt *i) with gil:
    self.visitActivityBindStmt(ActivityBindStmt.mk(i, False))
cdef public api ast_call_visitActivityConstraint(object self, ast_decl.IActivityConstraint *i) with gil:
    self.visitActivityConstraint(ActivityConstraint.mk(i, False))
cdef public api ast_call_visitMonitorActivityMonitorTraversal(object self, ast_decl.IMonitorActivityMonitorTraversal *i) with gil:
    self.visitMonitorActivityMonitorTraversal(MonitorActivityMonitorTraversal.mk(i, False))
cdef public api ast_call_visitMonitorActivityOverlap(object self, ast_decl.IMonitorActivityOverlap *i) with gil:
    self.visitMonitorActivityOverlap(MonitorActivityOverlap.mk(i, False))
cdef public api ast_call_visitMonitorActivityRepeatCount(object self, ast_decl.IMonitorActivityRepeatCount *i) with gil:
    self.visitMonitorActivityRepeatCount(MonitorActivityRepeatCount.mk(i, False))
cdef public api ast_call_visitMonitorActivityRepeatWhile(object self, ast_decl.IMonitorActivityRepeatWhile *i) with gil:
    self.visitMonitorActivityRepeatWhile(MonitorActivityRepeatWhile.mk(i, False))
cdef public api ast_call_visitActivityJoinSpecBranch(object self, ast_decl.IActivityJoinSpecBranch *i) with gil:
    self.visitActivityJoinSpecBranch(ActivityJoinSpecBranch.mk(i, False))
cdef public api ast_call_visitActivityJoinSpecFirst(object self, ast_decl.IActivityJoinSpecFirst *i) with gil:
    self.visitActivityJoinSpecFirst(ActivityJoinSpecFirst.mk(i, False))
cdef public api ast_call_visitActivityJoinSpecNone(object self, ast_decl.IActivityJoinSpecNone *i) with gil:
    self.visitActivityJoinSpecNone(ActivityJoinSpecNone.mk(i, False))
cdef public api ast_call_visitActivityJoinSpecSelect(object self, ast_decl.IActivityJoinSpecSelect *i) with gil:
    self.visitActivityJoinSpecSelect(ActivityJoinSpecSelect.mk(i, False))
cdef public api ast_call_visitMonitorActivitySelect(object self, ast_decl.IMonitorActivitySelect *i) with gil:
    self.visitMonitorActivitySelect(MonitorActivitySelect.mk(i, False))
cdef public api ast_call_visitActivityLabeledStmt(object self, ast_decl.IActivityLabeledStmt *i) with gil:
    self.visitActivityLabeledStmt(ActivityLabeledStmt.mk(i, False))
cdef public api ast_call_visitMonitorConstraint(object self, ast_decl.IMonitorConstraint *i) with gil:
    self.visitMonitorConstraint(MonitorConstraint.mk(i, False))
cdef public api ast_call_visitNamedScope(object self, ast_decl.INamedScope *i) with gil:
    self.visitNamedScope(NamedScope.mk(i, False))
cdef public api ast_call_visitPackageScope(object self, ast_decl.IPackageScope *i) with gil:
    self.visitPackageScope(PackageScope.mk(i, False))
cdef public api ast_call_visitProceduralStmtAssignment(object self, ast_decl.IProceduralStmtAssignment *i) with gil:
    self.visitProceduralStmtAssignment(ProceduralStmtAssignment.mk(i, False))
cdef public api ast_call_visitProceduralStmtBody(object self, ast_decl.IProceduralStmtBody *i) with gil:
    self.visitProceduralStmtBody(ProceduralStmtBody.mk(i, False))
cdef public api ast_call_visitProceduralStmtBreak(object self, ast_decl.IProceduralStmtBreak *i) with gil:
    self.visitProceduralStmtBreak(ProceduralStmtBreak.mk(i, False))
cdef public api ast_call_visitProceduralStmtContinue(object self, ast_decl.IProceduralStmtContinue *i) with gil:
    self.visitProceduralStmtContinue(ProceduralStmtContinue.mk(i, False))
cdef public api ast_call_visitProceduralStmtDataDeclaration(object self, ast_decl.IProceduralStmtDataDeclaration *i) with gil:
    self.visitProceduralStmtDataDeclaration(ProceduralStmtDataDeclaration.mk(i, False))
cdef public api ast_call_visitProceduralStmtExpr(object self, ast_decl.IProceduralStmtExpr *i) with gil:
    self.visitProceduralStmtExpr(ProceduralStmtExpr.mk(i, False))
cdef public api ast_call_visitProceduralStmtFunctionCall(object self, ast_decl.IProceduralStmtFunctionCall *i) with gil:
    self.visitProceduralStmtFunctionCall(ProceduralStmtFunctionCall.mk(i, False))
cdef public api ast_call_visitProceduralStmtIfElse(object self, ast_decl.IProceduralStmtIfElse *i) with gil:
    self.visitProceduralStmtIfElse(ProceduralStmtIfElse.mk(i, False))
cdef public api ast_call_visitProceduralStmtMatch(object self, ast_decl.IProceduralStmtMatch *i) with gil:
    self.visitProceduralStmtMatch(ProceduralStmtMatch.mk(i, False))
cdef public api ast_call_visitProceduralStmtMatchChoice(object self, ast_decl.IProceduralStmtMatchChoice *i) with gil:
    self.visitProceduralStmtMatchChoice(ProceduralStmtMatchChoice.mk(i, False))
cdef public api ast_call_visitProceduralStmtRandomize(object self, ast_decl.IProceduralStmtRandomize *i) with gil:
    self.visitProceduralStmtRandomize(ProceduralStmtRandomize.mk(i, False))
cdef public api ast_call_visitProceduralStmtReturn(object self, ast_decl.IProceduralStmtReturn *i) with gil:
    self.visitProceduralStmtReturn(ProceduralStmtReturn.mk(i, False))
cdef public api ast_call_visitConstraintScope(object self, ast_decl.IConstraintScope *i) with gil:
    self.visitConstraintScope(ConstraintScope.mk(i, False))
cdef public api ast_call_visitConstraintStmtDefault(object self, ast_decl.IConstraintStmtDefault *i) with gil:
    self.visitConstraintStmtDefault(ConstraintStmtDefault.mk(i, False))
cdef public api ast_call_visitConstraintStmtDefaultDisable(object self, ast_decl.IConstraintStmtDefaultDisable *i) with gil:
    self.visitConstraintStmtDefaultDisable(ConstraintStmtDefaultDisable.mk(i, False))
cdef public api ast_call_visitConstraintStmtExpr(object self, ast_decl.IConstraintStmtExpr *i) with gil:
    self.visitConstraintStmtExpr(ConstraintStmtExpr.mk(i, False))
cdef public api ast_call_visitConstraintStmtField(object self, ast_decl.IConstraintStmtField *i) with gil:
    self.visitConstraintStmtField(ConstraintStmtField.mk(i, False))
cdef public api ast_call_visitProceduralStmtYield(object self, ast_decl.IProceduralStmtYield *i) with gil:
    self.visitProceduralStmtYield(ProceduralStmtYield.mk(i, False))
cdef public api ast_call_visitConstraintStmtIf(object self, ast_decl.IConstraintStmtIf *i) with gil:
    self.visitConstraintStmtIf(ConstraintStmtIf.mk(i, False))
cdef public api ast_call_visitConstraintStmtUnique(object self, ast_decl.IConstraintStmtUnique *i) with gil:
    self.visitConstraintStmtUnique(ConstraintStmtUnique.mk(i, False))
cdef public api ast_call_visitSymbolChildrenScope(object self, ast_decl.ISymbolChildrenScope *i) with gil:
    self.visitSymbolChildrenScope(SymbolChildrenScope.mk(i, False))
cdef public api ast_call_visitDataTypeBool(object self, ast_decl.IDataTypeBool *i) with gil:
    self.visitDataTypeBool(DataTypeBool.mk(i, False))
cdef public api ast_call_visitDataTypeChandle(object self, ast_decl.IDataTypeChandle *i) with gil:
    self.visitDataTypeChandle(DataTypeChandle.mk(i, False))
cdef public api ast_call_visitDataTypeEnum(object self, ast_decl.IDataTypeEnum *i) with gil:
    self.visitDataTypeEnum(DataTypeEnum.mk(i, False))
cdef public api ast_call_visitDataTypeInt(object self, ast_decl.IDataTypeInt *i) with gil:
    self.visitDataTypeInt(DataTypeInt.mk(i, False))
cdef public api ast_call_visitDataTypePyObj(object self, ast_decl.IDataTypePyObj *i) with gil:
    self.visitDataTypePyObj(DataTypePyObj.mk(i, False))
cdef public api ast_call_visitDataTypeRef(object self, ast_decl.IDataTypeRef *i) with gil:
    self.visitDataTypeRef(DataTypeRef.mk(i, False))
cdef public api ast_call_visitDataTypeString(object self, ast_decl.IDataTypeString *i) with gil:
    self.visitDataTypeString(DataTypeString.mk(i, False))
cdef public api ast_call_visitDataTypeUserDefined(object self, ast_decl.IDataTypeUserDefined *i) with gil:
    self.visitDataTypeUserDefined(DataTypeUserDefined.mk(i, False))
cdef public api ast_call_visitEnumDecl(object self, ast_decl.IEnumDecl *i) with gil:
    self.visitEnumDecl(EnumDecl.mk(i, False))
cdef public api ast_call_visitEnumItem(object self, ast_decl.IEnumItem *i) with gil:
    self.visitEnumItem(EnumItem.mk(i, False))
cdef public api ast_call_visitTemplateCategoryTypeParamDecl(object self, ast_decl.ITemplateCategoryTypeParamDecl *i) with gil:
    self.visitTemplateCategoryTypeParamDecl(TemplateCategoryTypeParamDecl.mk(i, False))
cdef public api ast_call_visitTemplateGenericTypeParamDecl(object self, ast_decl.ITemplateGenericTypeParamDecl *i) with gil:
    self.visitTemplateGenericTypeParamDecl(TemplateGenericTypeParamDecl.mk(i, False))
cdef public api ast_call_visitExprAggrEmpty(object self, ast_decl.IExprAggrEmpty *i) with gil:
    self.visitExprAggrEmpty(ExprAggrEmpty.mk(i, False))
cdef public api ast_call_visitExprAggrList(object self, ast_decl.IExprAggrList *i) with gil:
    self.visitExprAggrList(ExprAggrList.mk(i, False))
cdef public api ast_call_visitTemplateValueParamDecl(object self, ast_decl.ITemplateValueParamDecl *i) with gil:
    self.visitTemplateValueParamDecl(TemplateValueParamDecl.mk(i, False))
cdef public api ast_call_visitExprAggrMap(object self, ast_decl.IExprAggrMap *i) with gil:
    self.visitExprAggrMap(ExprAggrMap.mk(i, False))
cdef public api ast_call_visitExprAggrStruct(object self, ast_decl.IExprAggrStruct *i) with gil:
    self.visitExprAggrStruct(ExprAggrStruct.mk(i, False))
cdef public api ast_call_visitExprRefPathContext(object self, ast_decl.IExprRefPathContext *i) with gil:
    self.visitExprRefPathContext(ExprRefPathContext.mk(i, False))
cdef public api ast_call_visitExprRefPathId(object self, ast_decl.IExprRefPathId *i) with gil:
    self.visitExprRefPathId(ExprRefPathId.mk(i, False))
cdef public api ast_call_visitExprRefPathStatic(object self, ast_decl.IExprRefPathStatic *i) with gil:
    self.visitExprRefPathStatic(ExprRefPathStatic.mk(i, False))
cdef public api ast_call_visitExprRefPathStaticRooted(object self, ast_decl.IExprRefPathStaticRooted *i) with gil:
    self.visitExprRefPathStaticRooted(ExprRefPathStaticRooted.mk(i, False))
cdef public api ast_call_visitExprSignedNumber(object self, ast_decl.IExprSignedNumber *i) with gil:
    self.visitExprSignedNumber(ExprSignedNumber.mk(i, False))
cdef public api ast_call_visitExprUnsignedNumber(object self, ast_decl.IExprUnsignedNumber *i) with gil:
    self.visitExprUnsignedNumber(ExprUnsignedNumber.mk(i, False))
cdef public api ast_call_visitExtendType(object self, ast_decl.IExtendType *i) with gil:
    self.visitExtendType(ExtendType.mk(i, False))
cdef public api ast_call_visitField(object self, ast_decl.IField *i) with gil:
    self.visitField(Field.mk(i, False))
cdef public api ast_call_visitFieldClaim(object self, ast_decl.IFieldClaim *i) with gil:
    self.visitFieldClaim(FieldClaim.mk(i, False))
cdef public api ast_call_visitFieldCompRef(object self, ast_decl.IFieldCompRef *i) with gil:
    self.visitFieldCompRef(FieldCompRef.mk(i, False))
cdef public api ast_call_visitFieldRef(object self, ast_decl.IFieldRef *i) with gil:
    self.visitFieldRef(FieldRef.mk(i, False))
cdef public api ast_call_visitFunctionImportProto(object self, ast_decl.IFunctionImportProto *i) with gil:
    self.visitFunctionImportProto(FunctionImportProto.mk(i, False))
cdef public api ast_call_visitFunctionImportType(object self, ast_decl.IFunctionImportType *i) with gil:
    self.visitFunctionImportType(FunctionImportType.mk(i, False))
cdef public api ast_call_visitFunctionPrototype(object self, ast_decl.IFunctionPrototype *i) with gil:
    self.visitFunctionPrototype(FunctionPrototype.mk(i, False))
cdef public api ast_call_visitGlobalScope(object self, ast_decl.IGlobalScope *i) with gil:
    self.visitGlobalScope(GlobalScope.mk(i, False))
cdef public api ast_call_visitActivityActionHandleTraversal(object self, ast_decl.IActivityActionHandleTraversal *i) with gil:
    self.visitActivityActionHandleTraversal(ActivityActionHandleTraversal.mk(i, False))
cdef public api ast_call_visitActivityActionTypeTraversal(object self, ast_decl.IActivityActionTypeTraversal *i) with gil:
    self.visitActivityActionTypeTraversal(ActivityActionTypeTraversal.mk(i, False))
cdef public api ast_call_visitActivityAtomicBlock(object self, ast_decl.IActivityAtomicBlock *i) with gil:
    self.visitActivityAtomicBlock(ActivityAtomicBlock.mk(i, False))
cdef public api ast_call_visitActivityForeach(object self, ast_decl.IActivityForeach *i) with gil:
    self.visitActivityForeach(ActivityForeach.mk(i, False))
cdef public api ast_call_visitActivityIfElse(object self, ast_decl.IActivityIfElse *i) with gil:
    self.visitActivityIfElse(ActivityIfElse.mk(i, False))
cdef public api ast_call_visitActivityMatch(object self, ast_decl.IActivityMatch *i) with gil:
    self.visitActivityMatch(ActivityMatch.mk(i, False))
cdef public api ast_call_visitActivityRepeatCount(object self, ast_decl.IActivityRepeatCount *i) with gil:
    self.visitActivityRepeatCount(ActivityRepeatCount.mk(i, False))
cdef public api ast_call_visitActivityRepeatWhile(object self, ast_decl.IActivityRepeatWhile *i) with gil:
    self.visitActivityRepeatWhile(ActivityRepeatWhile.mk(i, False))
cdef public api ast_call_visitActivityReplicate(object self, ast_decl.IActivityReplicate *i) with gil:
    self.visitActivityReplicate(ActivityReplicate.mk(i, False))
cdef public api ast_call_visitActivitySelect(object self, ast_decl.IActivitySelect *i) with gil:
    self.visitActivitySelect(ActivitySelect.mk(i, False))
cdef public api ast_call_visitActivitySuper(object self, ast_decl.IActivitySuper *i) with gil:
    self.visitActivitySuper(ActivitySuper.mk(i, False))
cdef public api ast_call_visitProceduralStmtRepeatWhile(object self, ast_decl.IProceduralStmtRepeatWhile *i) with gil:
    self.visitProceduralStmtRepeatWhile(ProceduralStmtRepeatWhile.mk(i, False))
cdef public api ast_call_visitConstraintBlock(object self, ast_decl.IConstraintBlock *i) with gil:
    self.visitConstraintBlock(ConstraintBlock.mk(i, False))
cdef public api ast_call_visitProceduralStmtWhile(object self, ast_decl.IProceduralStmtWhile *i) with gil:
    self.visitProceduralStmtWhile(ProceduralStmtWhile.mk(i, False))
cdef public api ast_call_visitConstraintStmtForall(object self, ast_decl.IConstraintStmtForall *i) with gil:
    self.visitConstraintStmtForall(ConstraintStmtForall.mk(i, False))
cdef public api ast_call_visitConstraintStmtForeach(object self, ast_decl.IConstraintStmtForeach *i) with gil:
    self.visitConstraintStmtForeach(ConstraintStmtForeach.mk(i, False))
cdef public api ast_call_visitConstraintStmtImplication(object self, ast_decl.IConstraintStmtImplication *i) with gil:
    self.visitConstraintStmtImplication(ConstraintStmtImplication.mk(i, False))
cdef public api ast_call_visitSymbolScope(object self, ast_decl.ISymbolScope *i) with gil:
    self.visitSymbolScope(SymbolScope.mk(i, False))
cdef public api ast_call_visitTypeScope(object self, ast_decl.ITypeScope *i) with gil:
    self.visitTypeScope(TypeScope.mk(i, False))
cdef public api ast_call_visitExprRefPathStaticFunc(object self, ast_decl.IExprRefPathStaticFunc *i) with gil:
    self.visitExprRefPathStaticFunc(ExprRefPathStaticFunc.mk(i, False))
cdef public api ast_call_visitExprRefPathSuper(object self, ast_decl.IExprRefPathSuper *i) with gil:
    self.visitExprRefPathSuper(ExprRefPathSuper.mk(i, False))
cdef public api ast_call_visitAction(object self, ast_decl.IAction *i) with gil:
    self.visitAction(Action.mk(i, False))
cdef public api ast_call_visitMonitorActivityDecl(object self, ast_decl.IMonitorActivityDecl *i) with gil:
    self.visitMonitorActivityDecl(MonitorActivityDecl.mk(i, False))
cdef public api ast_call_visitActivityDecl(object self, ast_decl.IActivityDecl *i) with gil:
    self.visitActivityDecl(ActivityDecl.mk(i, False))
cdef public api ast_call_visitMonitorActivitySchedule(object self, ast_decl.IMonitorActivitySchedule *i) with gil:
    self.visitMonitorActivitySchedule(MonitorActivitySchedule.mk(i, False))
cdef public api ast_call_visitMonitorActivitySequence(object self, ast_decl.IMonitorActivitySequence *i) with gil:
    self.visitMonitorActivitySequence(MonitorActivitySequence.mk(i, False))
cdef public api ast_call_visitActivityLabeledScope(object self, ast_decl.IActivityLabeledScope *i) with gil:
    self.visitActivityLabeledScope(ActivityLabeledScope.mk(i, False))
cdef public api ast_call_visitAnnotationDecl(object self, ast_decl.IAnnotationDecl *i) with gil:
    self.visitAnnotationDecl(AnnotationDecl.mk(i, False))
cdef public api ast_call_visitComponent(object self, ast_decl.IComponent *i) with gil:
    self.visitComponent(Component.mk(i, False))
cdef public api ast_call_visitProceduralStmtSymbolBodyScope(object self, ast_decl.IProceduralStmtSymbolBodyScope *i) with gil:
    self.visitProceduralStmtSymbolBodyScope(ProceduralStmtSymbolBodyScope.mk(i, False))
cdef public api ast_call_visitRootSymbolScope(object self, ast_decl.IRootSymbolScope *i) with gil:
    self.visitRootSymbolScope(RootSymbolScope.mk(i, False))
cdef public api ast_call_visitConstraintSymbolScope(object self, ast_decl.IConstraintSymbolScope *i) with gil:
    self.visitConstraintSymbolScope(ConstraintSymbolScope.mk(i, False))
cdef public api ast_call_visitStruct(object self, ast_decl.IStruct *i) with gil:
    self.visitStruct(Struct.mk(i, False))
cdef public api ast_call_visitSymbolEnumScope(object self, ast_decl.ISymbolEnumScope *i) with gil:
    self.visitSymbolEnumScope(SymbolEnumScope.mk(i, False))
cdef public api ast_call_visitSymbolExtendScope(object self, ast_decl.ISymbolExtendScope *i) with gil:
    self.visitSymbolExtendScope(SymbolExtendScope.mk(i, False))
cdef public api ast_call_visitSymbolFunctionScope(object self, ast_decl.ISymbolFunctionScope *i) with gil:
    self.visitSymbolFunctionScope(SymbolFunctionScope.mk(i, False))
cdef public api ast_call_visitSymbolTypeScope(object self, ast_decl.ISymbolTypeScope *i) with gil:
    self.visitSymbolTypeScope(SymbolTypeScope.mk(i, False))
cdef public api ast_call_visitExecScope(object self, ast_decl.IExecScope *i) with gil:
    self.visitExecScope(ExecScope.mk(i, False))
cdef public api ast_call_visitGenericConstraintDeclBool(object self, ast_decl.IGenericConstraintDeclBool *i) with gil:
    self.visitGenericConstraintDeclBool(GenericConstraintDeclBool.mk(i, False))
cdef public api ast_call_visitMonitor(object self, ast_decl.IMonitor *i) with gil:
    self.visitMonitor(Monitor.mk(i, False))
cdef public api ast_call_visitProceduralStmtRepeat(object self, ast_decl.IProceduralStmtRepeat *i) with gil:
    self.visitProceduralStmtRepeat(ProceduralStmtRepeat.mk(i, False))
cdef public api ast_call_visitActivityParallel(object self, ast_decl.IActivityParallel *i) with gil:
    self.visitActivityParallel(ActivityParallel.mk(i, False))
cdef public api ast_call_visitActivitySchedule(object self, ast_decl.IActivitySchedule *i) with gil:
    self.visitActivitySchedule(ActivitySchedule.mk(i, False))
cdef public api ast_call_visitProceduralStmtForeach(object self, ast_decl.IProceduralStmtForeach *i) with gil:
    self.visitProceduralStmtForeach(ProceduralStmtForeach.mk(i, False))
cdef public api ast_call_visitActivitySequence(object self, ast_decl.IActivitySequence *i) with gil:
    self.visitActivitySequence(ActivitySequence.mk(i, False))
cdef public api ast_call_visitExecBlock(object self, ast_decl.IExecBlock *i) with gil:
    self.visitExecBlock(ExecBlock.mk(i, False))
cdef class ObjFactory(VisitorBase):
    def __init__(self):
        super().__init__()
        self._obj = None
        self._obj_owned = False
    cpdef void visitTemplateParamDeclList(self, TemplateParamDeclList i):
        self._obj = i
    cpdef void visitAssocData(self, AssocData i):
        self._obj = i
    cpdef void visitExecTargetTemplateParam(self, ExecTargetTemplateParam i):
        self._obj = i
    cpdef void visitExpr(self, Expr i):
        self._obj = i
    cpdef void visitTemplateParamValue(self, TemplateParamValue i):
        self._obj = i
    cpdef void visitMonitorActivityMatchChoice(self, MonitorActivityMatchChoice i):
        self._obj = i
    cpdef void visitTemplateParamValueList(self, TemplateParamValueList i):
        self._obj = i
    cpdef void visitExprAggrMapElem(self, ExprAggrMapElem i):
        self._obj = i
    cpdef void visitRefExpr(self, RefExpr i):
        self._obj = i
    cpdef void visitExprAggrStructElem(self, ExprAggrStructElem i):
        self._obj = i
    cpdef void visitMonitorActivitySelectBranch(self, MonitorActivitySelectBranch i):
        self._obj = i
    cpdef void visitScopeChild(self, ScopeChild i):
        self._obj = i
    cpdef void visitActivityMatchChoice(self, ActivityMatchChoice i):
        self._obj = i
    cpdef void visitSymbolImportSpec(self, SymbolImportSpec i):
        self._obj = i
    cpdef void visitSymbolRefPath(self, SymbolRefPath i):
        self._obj = i
    cpdef void visitActivitySelectBranch(self, ActivitySelectBranch i):
        self._obj = i
    cpdef void visitActionFieldInitializer(self, ActionFieldInitializer i):
        self._obj = i
    cpdef void visitActivityJoinSpec(self, ActivityJoinSpec i):
        self._obj = i
    cpdef void visitMonitorActivityStmt(self, MonitorActivityStmt i):
        self._obj = i
    cpdef void visitNamedScopeChild(self, NamedScopeChild i):
        self._obj = i
    cpdef void visitPackageImportStmt(self, PackageImportStmt i):
        self._obj = i
    cpdef void visitActivitySchedulingConstraint(self, ActivitySchedulingConstraint i):
        self._obj = i
    cpdef void visitActivityStmt(self, ActivityStmt i):
        self._obj = i
    cpdef void visitProceduralStmtIfClause(self, ProceduralStmtIfClause i):
        self._obj = i
    cpdef void visitAnnotation(self, Annotation i):
        self._obj = i
    cpdef void visitAnnotationParam(self, AnnotationParam i):
        self._obj = i
    cpdef void visitConstraintStmt(self, ConstraintStmt i):
        self._obj = i
    cpdef void visitPyImportFromStmt(self, PyImportFromStmt i):
        self._obj = i
    cpdef void visitPyImportStmt(self, PyImportStmt i):
        self._obj = i
    cpdef void visitRefExprScopeIndex(self, RefExprScopeIndex i):
        self._obj = i
    cpdef void visitRefExprTypeScopeContext(self, RefExprTypeScopeContext i):
        self._obj = i
    cpdef void visitRefExprTypeScopeGlobal(self, RefExprTypeScopeGlobal i):
        self._obj = i
    cpdef void visitScope(self, Scope i):
        self._obj = i
    cpdef void visitCoverStmtInline(self, CoverStmtInline i):
        self._obj = i
    cpdef void visitCoverStmtReference(self, CoverStmtReference i):
        self._obj = i
    cpdef void visitDataType(self, DataType i):
        self._obj = i
    cpdef void visitScopeChildRef(self, ScopeChildRef i):
        self._obj = i
    cpdef void visitSymbolChild(self, SymbolChild i):
        self._obj = i
    cpdef void visitSymbolScopeRef(self, SymbolScopeRef i):
        self._obj = i
    cpdef void visitTemplateParamDecl(self, TemplateParamDecl i):
        self._obj = i
    cpdef void visitExecStmt(self, ExecStmt i):
        self._obj = i
    cpdef void visitExecTargetTemplateBlock(self, ExecTargetTemplateBlock i):
        self._obj = i
    cpdef void visitTemplateParamExprValue(self, TemplateParamExprValue i):
        self._obj = i
    cpdef void visitExportFunction(self, ExportFunction i):
        self._obj = i
    cpdef void visitTemplateParamTypeValue(self, TemplateParamTypeValue i):
        self._obj = i
    cpdef void visitTypeIdentifier(self, TypeIdentifier i):
        self._obj = i
    cpdef void visitExprAggrLiteral(self, ExprAggrLiteral i):
        self._obj = i
    cpdef void visitTypeIdentifierElem(self, TypeIdentifierElem i):
        self._obj = i
    cpdef void visitTypedefDeclaration(self, TypedefDeclaration i):
        self._obj = i
    cpdef void visitExprBin(self, ExprBin i):
        self._obj = i
    cpdef void visitExprBitSlice(self, ExprBitSlice i):
        self._obj = i
    cpdef void visitExprBool(self, ExprBool i):
        self._obj = i
    cpdef void visitExprCast(self, ExprCast i):
        self._obj = i
    cpdef void visitExprCompileHas(self, ExprCompileHas i):
        self._obj = i
    cpdef void visitExprCond(self, ExprCond i):
        self._obj = i
    cpdef void visitExprDomainOpenRangeList(self, ExprDomainOpenRangeList i):
        self._obj = i
    cpdef void visitExprDomainOpenRangeValue(self, ExprDomainOpenRangeValue i):
        self._obj = i
    cpdef void visitExprHierarchicalId(self, ExprHierarchicalId i):
        self._obj = i
    cpdef void visitExprId(self, ExprId i):
        self._obj = i
    cpdef void visitExprIn(self, ExprIn i):
        self._obj = i
    cpdef void visitExprListLiteral(self, ExprListLiteral i):
        self._obj = i
    cpdef void visitExprMemberPathElem(self, ExprMemberPathElem i):
        self._obj = i
    cpdef void visitExprNull(self, ExprNull i):
        self._obj = i
    cpdef void visitExprNumber(self, ExprNumber i):
        self._obj = i
    cpdef void visitExprOpenRangeList(self, ExprOpenRangeList i):
        self._obj = i
    cpdef void visitExprOpenRangeValue(self, ExprOpenRangeValue i):
        self._obj = i
    cpdef void visitExprRefPath(self, ExprRefPath i):
        self._obj = i
    cpdef void visitExprRefPathElem(self, ExprRefPathElem i):
        self._obj = i
    cpdef void visitExprStaticRefPath(self, ExprStaticRefPath i):
        self._obj = i
    cpdef void visitExprString(self, ExprString i):
        self._obj = i
    cpdef void visitExprStructLiteral(self, ExprStructLiteral i):
        self._obj = i
    cpdef void visitExprStructLiteralItem(self, ExprStructLiteralItem i):
        self._obj = i
    cpdef void visitExprSubscript(self, ExprSubscript i):
        self._obj = i
    cpdef void visitExprSubstring(self, ExprSubstring i):
        self._obj = i
    cpdef void visitExprUnary(self, ExprUnary i):
        self._obj = i
    cpdef void visitExtendEnum(self, ExtendEnum i):
        self._obj = i
    cpdef void visitFunctionDefinition(self, FunctionDefinition i):
        self._obj = i
    cpdef void visitFunctionImport(self, FunctionImport i):
        self._obj = i
    cpdef void visitFunctionParamDecl(self, FunctionParamDecl i):
        self._obj = i
    cpdef void visitGenericConstraintDeclValue(self, GenericConstraintDeclValue i):
        self._obj = i
    cpdef void visitGenericConstraintParam(self, GenericConstraintParam i):
        self._obj = i
    cpdef void visitMethodParameterList(self, MethodParameterList i):
        self._obj = i
    cpdef void visitMonitorActivityActionTraversal(self, MonitorActivityActionTraversal i):
        self._obj = i
    cpdef void visitMonitorActivityConcat(self, MonitorActivityConcat i):
        self._obj = i
    cpdef void visitActionHandleField(self, ActionHandleField i):
        self._obj = i
    cpdef void visitMonitorActivityEventually(self, MonitorActivityEventually i):
        self._obj = i
    cpdef void visitMonitorActivityIfElse(self, MonitorActivityIfElse i):
        self._obj = i
    cpdef void visitMonitorActivityMatch(self, MonitorActivityMatch i):
        self._obj = i
    cpdef void visitActivityBindStmt(self, ActivityBindStmt i):
        self._obj = i
    cpdef void visitActivityConstraint(self, ActivityConstraint i):
        self._obj = i
    cpdef void visitMonitorActivityMonitorTraversal(self, MonitorActivityMonitorTraversal i):
        self._obj = i
    cpdef void visitMonitorActivityOverlap(self, MonitorActivityOverlap i):
        self._obj = i
    cpdef void visitMonitorActivityRepeatCount(self, MonitorActivityRepeatCount i):
        self._obj = i
    cpdef void visitMonitorActivityRepeatWhile(self, MonitorActivityRepeatWhile i):
        self._obj = i
    cpdef void visitActivityJoinSpecBranch(self, ActivityJoinSpecBranch i):
        self._obj = i
    cpdef void visitActivityJoinSpecFirst(self, ActivityJoinSpecFirst i):
        self._obj = i
    cpdef void visitActivityJoinSpecNone(self, ActivityJoinSpecNone i):
        self._obj = i
    cpdef void visitActivityJoinSpecSelect(self, ActivityJoinSpecSelect i):
        self._obj = i
    cpdef void visitMonitorActivitySelect(self, MonitorActivitySelect i):
        self._obj = i
    cpdef void visitActivityLabeledStmt(self, ActivityLabeledStmt i):
        self._obj = i
    cpdef void visitMonitorConstraint(self, MonitorConstraint i):
        self._obj = i
    cpdef void visitNamedScope(self, NamedScope i):
        self._obj = i
    cpdef void visitPackageScope(self, PackageScope i):
        self._obj = i
    cpdef void visitProceduralStmtAssignment(self, ProceduralStmtAssignment i):
        self._obj = i
    cpdef void visitProceduralStmtBody(self, ProceduralStmtBody i):
        self._obj = i
    cpdef void visitProceduralStmtBreak(self, ProceduralStmtBreak i):
        self._obj = i
    cpdef void visitProceduralStmtContinue(self, ProceduralStmtContinue i):
        self._obj = i
    cpdef void visitProceduralStmtDataDeclaration(self, ProceduralStmtDataDeclaration i):
        self._obj = i
    cpdef void visitProceduralStmtExpr(self, ProceduralStmtExpr i):
        self._obj = i
    cpdef void visitProceduralStmtFunctionCall(self, ProceduralStmtFunctionCall i):
        self._obj = i
    cpdef void visitProceduralStmtIfElse(self, ProceduralStmtIfElse i):
        self._obj = i
    cpdef void visitProceduralStmtMatch(self, ProceduralStmtMatch i):
        self._obj = i
    cpdef void visitProceduralStmtMatchChoice(self, ProceduralStmtMatchChoice i):
        self._obj = i
    cpdef void visitProceduralStmtRandomize(self, ProceduralStmtRandomize i):
        self._obj = i
    cpdef void visitProceduralStmtReturn(self, ProceduralStmtReturn i):
        self._obj = i
    cpdef void visitConstraintScope(self, ConstraintScope i):
        self._obj = i
    cpdef void visitConstraintStmtDefault(self, ConstraintStmtDefault i):
        self._obj = i
    cpdef void visitConstraintStmtDefaultDisable(self, ConstraintStmtDefaultDisable i):
        self._obj = i
    cpdef void visitConstraintStmtExpr(self, ConstraintStmtExpr i):
        self._obj = i
    cpdef void visitConstraintStmtField(self, ConstraintStmtField i):
        self._obj = i
    cpdef void visitProceduralStmtYield(self, ProceduralStmtYield i):
        self._obj = i
    cpdef void visitConstraintStmtIf(self, ConstraintStmtIf i):
        self._obj = i
    cpdef void visitConstraintStmtUnique(self, ConstraintStmtUnique i):
        self._obj = i
    cpdef void visitSymbolChildrenScope(self, SymbolChildrenScope i):
        self._obj = i
    cpdef void visitDataTypeBool(self, DataTypeBool i):
        self._obj = i
    cpdef void visitDataTypeChandle(self, DataTypeChandle i):
        self._obj = i
    cpdef void visitDataTypeEnum(self, DataTypeEnum i):
        self._obj = i
    cpdef void visitDataTypeInt(self, DataTypeInt i):
        self._obj = i
    cpdef void visitDataTypePyObj(self, DataTypePyObj i):
        self._obj = i
    cpdef void visitDataTypeRef(self, DataTypeRef i):
        self._obj = i
    cpdef void visitDataTypeString(self, DataTypeString i):
        self._obj = i
    cpdef void visitDataTypeUserDefined(self, DataTypeUserDefined i):
        self._obj = i
    cpdef void visitEnumDecl(self, EnumDecl i):
        self._obj = i
    cpdef void visitEnumItem(self, EnumItem i):
        self._obj = i
    cpdef void visitTemplateCategoryTypeParamDecl(self, TemplateCategoryTypeParamDecl i):
        self._obj = i
    cpdef void visitTemplateGenericTypeParamDecl(self, TemplateGenericTypeParamDecl i):
        self._obj = i
    cpdef void visitExprAggrEmpty(self, ExprAggrEmpty i):
        self._obj = i
    cpdef void visitExprAggrList(self, ExprAggrList i):
        self._obj = i
    cpdef void visitTemplateValueParamDecl(self, TemplateValueParamDecl i):
        self._obj = i
    cpdef void visitExprAggrMap(self, ExprAggrMap i):
        self._obj = i
    cpdef void visitExprAggrStruct(self, ExprAggrStruct i):
        self._obj = i
    cpdef void visitExprRefPathContext(self, ExprRefPathContext i):
        self._obj = i
    cpdef void visitExprRefPathId(self, ExprRefPathId i):
        self._obj = i
    cpdef void visitExprRefPathStatic(self, ExprRefPathStatic i):
        self._obj = i
    cpdef void visitExprRefPathStaticRooted(self, ExprRefPathStaticRooted i):
        self._obj = i
    cpdef void visitExprSignedNumber(self, ExprSignedNumber i):
        self._obj = i
    cpdef void visitExprUnsignedNumber(self, ExprUnsignedNumber i):
        self._obj = i
    cpdef void visitExtendType(self, ExtendType i):
        self._obj = i
    cpdef void visitField(self, Field i):
        self._obj = i
    cpdef void visitFieldClaim(self, FieldClaim i):
        self._obj = i
    cpdef void visitFieldCompRef(self, FieldCompRef i):
        self._obj = i
    cpdef void visitFieldRef(self, FieldRef i):
        self._obj = i
    cpdef void visitFunctionImportProto(self, FunctionImportProto i):
        self._obj = i
    cpdef void visitFunctionImportType(self, FunctionImportType i):
        self._obj = i
    cpdef void visitFunctionPrototype(self, FunctionPrototype i):
        self._obj = i
    cpdef void visitGlobalScope(self, GlobalScope i):
        self._obj = i
    cpdef void visitActivityActionHandleTraversal(self, ActivityActionHandleTraversal i):
        self._obj = i
    cpdef void visitActivityActionTypeTraversal(self, ActivityActionTypeTraversal i):
        self._obj = i
    cpdef void visitActivityAtomicBlock(self, ActivityAtomicBlock i):
        self._obj = i
    cpdef void visitActivityForeach(self, ActivityForeach i):
        self._obj = i
    cpdef void visitActivityIfElse(self, ActivityIfElse i):
        self._obj = i
    cpdef void visitActivityMatch(self, ActivityMatch i):
        self._obj = i
    cpdef void visitActivityRepeatCount(self, ActivityRepeatCount i):
        self._obj = i
    cpdef void visitActivityRepeatWhile(self, ActivityRepeatWhile i):
        self._obj = i
    cpdef void visitActivityReplicate(self, ActivityReplicate i):
        self._obj = i
    cpdef void visitActivitySelect(self, ActivitySelect i):
        self._obj = i
    cpdef void visitActivitySuper(self, ActivitySuper i):
        self._obj = i
    cpdef void visitProceduralStmtRepeatWhile(self, ProceduralStmtRepeatWhile i):
        self._obj = i
    cpdef void visitConstraintBlock(self, ConstraintBlock i):
        self._obj = i
    cpdef void visitProceduralStmtWhile(self, ProceduralStmtWhile i):
        self._obj = i
    cpdef void visitConstraintStmtForall(self, ConstraintStmtForall i):
        self._obj = i
    cpdef void visitConstraintStmtForeach(self, ConstraintStmtForeach i):
        self._obj = i
    cpdef void visitConstraintStmtImplication(self, ConstraintStmtImplication i):
        self._obj = i
    cpdef void visitSymbolScope(self, SymbolScope i):
        self._obj = i
    cpdef void visitTypeScope(self, TypeScope i):
        self._obj = i
    cpdef void visitExprRefPathStaticFunc(self, ExprRefPathStaticFunc i):
        self._obj = i
    cpdef void visitExprRefPathSuper(self, ExprRefPathSuper i):
        self._obj = i
    cpdef void visitAction(self, Action i):
        self._obj = i
    cpdef void visitMonitorActivityDecl(self, MonitorActivityDecl i):
        self._obj = i
    cpdef void visitActivityDecl(self, ActivityDecl i):
        self._obj = i
    cpdef void visitMonitorActivitySchedule(self, MonitorActivitySchedule i):
        self._obj = i
    cpdef void visitMonitorActivitySequence(self, MonitorActivitySequence i):
        self._obj = i
    cpdef void visitActivityLabeledScope(self, ActivityLabeledScope i):
        self._obj = i
    cpdef void visitAnnotationDecl(self, AnnotationDecl i):
        self._obj = i
    cpdef void visitComponent(self, Component i):
        self._obj = i
    cpdef void visitProceduralStmtSymbolBodyScope(self, ProceduralStmtSymbolBodyScope i):
        self._obj = i
    cpdef void visitRootSymbolScope(self, RootSymbolScope i):
        self._obj = i
    cpdef void visitConstraintSymbolScope(self, ConstraintSymbolScope i):
        self._obj = i
    cpdef void visitStruct(self, Struct i):
        self._obj = i
    cpdef void visitSymbolEnumScope(self, SymbolEnumScope i):
        self._obj = i
    cpdef void visitSymbolExtendScope(self, SymbolExtendScope i):
        self._obj = i
    cpdef void visitSymbolFunctionScope(self, SymbolFunctionScope i):
        self._obj = i
    cpdef void visitSymbolTypeScope(self, SymbolTypeScope i):
        self._obj = i
    cpdef void visitExecScope(self, ExecScope i):
        self._obj = i
    cpdef void visitGenericConstraintDeclBool(self, GenericConstraintDeclBool i):
        self._obj = i
    cpdef void visitMonitor(self, Monitor i):
        self._obj = i
    cpdef void visitProceduralStmtRepeat(self, ProceduralStmtRepeat i):
        self._obj = i
    cpdef void visitActivityParallel(self, ActivityParallel i):
        self._obj = i
    cpdef void visitActivitySchedule(self, ActivitySchedule i):
        self._obj = i
    cpdef void visitProceduralStmtForeach(self, ProceduralStmtForeach i):
        self._obj = i
    cpdef void visitActivitySequence(self, ActivitySequence i):
        self._obj = i
    cpdef void visitExecBlock(self, ExecBlock i):
        self._obj = i
