
# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#  http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.

from pssparser.model.field_pool import FieldPool
from pssparser.model.activity import Activity
from pssparser.model.exec_block_target_template import ExecBlockTargetTemplate
from pssparser.model.exec_kind import ExecKind
from pssparser.model.exec_block_file import ExecBlockFile
from pssparser.model.exec_block_procedural_interface import ExecBlockProceduralInterface
from pssparser.model.exec_stmt_super import ExecStmtSuper
from pssparser.model.method_prototype import MethodPrototype
from pssparser.model.method_parameter_dir import MethodParameterDir
from pssparser.model.method_parameter import MethodParameter
from pssparser.model.function_qualifier_spec import FunctionQualifierSpec
from pssparser.model.function_import import FunctionImport
from pssparser.model.function_qualifiers import FunctionQualifiers
from pssparser.model.method_qualifiers import MethodQualifiers
from pssparser.model.function_target_template import FunctionTargetTemplate
from _ast import FunctionDef
from pssparser.model.function_definition import FunctionDefinition
from pssparser.model.exec_block_stmt import ExecBlockStmt
from pssparser.model.exec_stmt_return import ExecStmtReturn
from pssparser.model.exec_stmt_expr import ExecStmtExpr
from pssparser.model.exec_stmt_assign import ExecStmtAssign
from pssparser.model.exec_assign_op import ExecAssignOp
from pssparser.model.exec_stmt_if_else import ExecStmtIfElse
from pssparser.model.exec_stmt_match_choice import ExecStmtMatchChoice
from pssparser.model.exec_stmt_match import ExecStmtMatch
from pssparser.model.exec_stmt_while import ExecStmtWhile
from pssparser.model.exec_stmt_repeat import ExecStmtRepeat
from pssparser.model.exec_stmt_repeat_while import ExecStmtRepeatWhile
from pssparser.model.exec_stmt_break import ExecStmtBreak
from pssparser.model.exec_stmt_continue import ExecStmtContinue
from pssparser.model.exec_stmt_foreach import ExecStmtForeach
from pssparser.model.activity_stmt_match import ActivityStmtMatch
from pssparser.model.activity_stmt_match_branch import ActivityStmtMatchBranch
from pssparser.model.activity_stmt_bind import ActivityStmtBind
from pssparser.model.activity_stmt_super import ActivityStmtSuper
from pssparser.model.pool_bind_stmt import PoolBindStmt
from pssparser.model.activity_stmt_traverse_handle import ActivityStmtTraverseHandle
from pssparser.model.activity_stmt_traverse_type import ActivityStmtTraverseType
from pssparser.model.data_type_string import DataTypeString
from pssparser.model.domain_open_range_list import DomainOpenRangeList
from pssparser.model.domain_open_range_value import DomainOpenRangeValue
from pssparser.model.expr_function_call import ExprFunctionCall
from pssparser.model.expr_cast import ExprCast
from pssparser.model.expr_method_call import ExprMethodCall

# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#  http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.

'''
Created on Feb 17, 2020

@author: ballance
'''
from typing import List, Tuple

from antlr4.BufferedTokenStream import TokenStream
from antlr4.CommonTokenStream import CommonTokenStream
from antlr4.error.ErrorListener import ErrorListener
from antlr4.tree.Tree import TerminalNodeImpl

from pssparser.antlr_gen.PSSLexer import PSSLexer
from pssparser.antlr_gen.PSSParser import PSSParser
from pssparser.antlr_gen.PSSVisitor import PSSVisitor
from pssparser.model.action_type import ActionType
from pssparser.model.attr_decl_stmt import AttrFlags
from pssparser.model.buffer_type import BufferType
from pssparser.model.compilation_unit import CompilationUnit
from pssparser.model.component_type import ComponentType
from pssparser.model.constraint_block import ConstraintBlock
from pssparser.model.constraint_declaration import ConstraintDeclaration
from pssparser.model.constraint_expression import ConstraintExpression
from pssparser.model.constraint_implies import ConstraintImplies
from pssparser.model.cu_type import CUType
from pssparser.model.data_type_enum import DataTypeEnum
from pssparser.model.data_type_scalar import DataTypeScalar, ScalarType
from pssparser.model.enum_declaration import EnumDeclaration
from pssparser.model.enum_item import EnumItem
from pssparser.model.expr_bin_type import ExprBinType, ExprBinOp
from pssparser.model.expr_bool_literal import ExprBoolLiteral
from pssparser.model.expr_compile_has import ExprCompileHas
from pssparser.model.expr_cond_type import ExprCondType
from pssparser.model.expr_hierarchical_id import ExprHierarchicalId
from pssparser.model.expr_hierarchical_id_elem import ExprHierarchicalIdElem
from pssparser.model.expr_hierarchical_id_list import ExprHierarchicalIdList
from pssparser.model.expr_id import ExprId
from pssparser.model.expr_in import ExprIn
from pssparser.model.expr_num_literal import ExprNumLiteral
from pssparser.model.expr_open_range_list import ExprOpenRangeList
from pssparser.model.expr_open_range_value import ExprOpenRangeValue
from pssparser.model.expr_static_ref_path import ExprStaticRefPath
from pssparser.model.expr_static_ref_path_elem import ExprStaticRefPathElem
from pssparser.model.expr_str_literal import ExprStrLiteral
from pssparser.model.expr_template_param_value import ExprTemplateParamValue
from pssparser.model.expr_template_param_value_list import ExprTemplateParamValueList
from pssparser.model.expr_unary import UnaryOp, ExprUnary
from pssparser.model.expr_var_ref_path import ExprVarRefPath
from pssparser.model.extend_stmt import ExtendStmt, ExtendTarget
from pssparser.model.import_stmt import ImportStmt
from pssparser.model.marker import Marker
from pssparser.model.package_type import PackageType
from pssparser.model.reference import Reference
from pssparser.model.resource_type import ResourceType
from pssparser.model.source_info import SourceInfo
from pssparser.model.state_type import StateType
from pssparser.model.stream_type import StreamType
from pssparser.model.struct_type import StructType
from pssparser.model.template_category_type_param_decl import TemplateCategoryTypeParamDecl, \
    TemplateTypeCategory
from pssparser.model.template_generic_type_param_decl import TemplateGenericTypeParamDecl
from pssparser.model.template_param_decl_list import TemplateParamDeclList
from pssparser.model.template_value_param_decl import TemplateValueParamDecl
from pssparser.model.type_identifier import TypeIdentifier
from pssparser.model.type_identifier_elem import TypeIdentifierElem
from pssparser.model.typedef import Typedef
from pssparser.model.constraint_default import ConstraintDefault
from pssparser.model.constraint_default_disable import ConstraintDefaultDisable
from pssparser.model.constraint_forall import ConstraintForall
from pssparser.model.constraint_if_else import ConstraintIfElse
from pssparser.model.constraint_unique import ConstraintUnique
from pssparser.model.constraint_foreach import ConstraintForeach
from pssparser.model.activity_stmt_if_else import ActivityStmtIfElse
from pssparser.model.activity_stmt_while import ActivityStmtWhile
from pssparser.model.activity_stmt_repeat import ActivityStmtRepeat
from pssparser.model.activity_stmt_do_while import ActivityStmtDoWhile
from pssparser.model.activity_stmt_replicate import ActivityStmtReplicate
from pssparser.model.activity_stmt_sequence import ActivityStmtSequence
from pssparser.model.activity_stmt_constraint import ActivityStmtConstraint
from pssparser.model.activity_stmt_foreach import ActivityStmtForeach
from pssparser.model.activity_stmt_parallel import ActivityStmtParallel
from pssparser.model.activity_stmt_schedule import ActivityStmtSchedule
from pssparser.model.activity_stmt_select import ActivityStmtSelect
from pssparser.model.activity_stmt_select_branch import ActivityStmtSelectBranch
from pssparser.model.activity_join_branch import ActivityJoinBranch
from pssparser.model.activity_join_select import ActivityJoinSelect
from pssparser.model.activity_join_none import ActivityJoinNone
from pssparser.model.activity_join_first import ActivityJoinFirst
from pssparser.model.data_type_user import DataTypeUser
from pssparser.model.field_attr import FieldAttr, FieldAttrFlags
from pssparser.model.override_block import OverrideBlock
from pssparser.model.override_stmt_type import OverrideStmtType
from pssparser.model.override_stmt_inst import OverrideStmtInst
from pssparser.model.compile_if import CompileIf
from pssparser.model.compile_assert import CompileAssert


class CUParser(PSSVisitor, ErrorListener):
    
    class ScopeTracker(object):
        def __init__(self, parser, name, scope):
            self.parser = parser
            self.name = name
            self.scope = scope
            
        def __enter__(self):
            self.parser._enter_type_scope(self.name, self.scope)
        
        def __exit__(self, t, v, tb):
            self.parser._leave_type_scope(self.name, self.scope)
    
    def __init__(self, input_stream, filename):
        lexer = PSSLexer(input_stream)
        stream = CommonTokenStream(lexer)
        self._parser = PSSParser(stream)
#        self._parser.removeErrorListeners()
        self._parser.addErrorListener(self)

        self._scope_s : List['CompositeType'] = []
        self._namespace_s : List[str] = []
        self._package_m : Dict[str, PackageType] = {}
        self._attr_flags_s : List[AttrFlags] = []
        
        cu = CUType(filename)
        self._scope_s.append(cu)
        
    def _typescope(self, name, scope):
        return CUParser.ScopeTracker(self, name, scope)
        
    def parse(self) -> CompilationUnit:
        cu_model = self._parser.compilation_unit()
        
        cu = self._scope_s[-1]
        
        if len(cu.markers) > 0:
            # Don't try to process with errors
            return cu
        
        cu_model.accept(self)
#         for c in cu_model.portable_stimulus_description():
#             cu_elem = c.accept(self)
#             
#             self.check_elem(cu_elem, c)
# 
#             # Don't add packages now
#             if isinstance(cu_elem, PackageType):
#                 # Add a package to the compilation unit the first we see it`
#                 if not cu_elem.name in self._package_m.keys():
#                     self._package_m[cu_elem.name] = cu_elem
#                     cu.add_child(cu_elem)
#             else:
#                 cu.add_elem(cu_elem)
        
        return cu
    
    def _get_typescope(self):
        return self._typescope_s[-1] if len(self._typescope_s) > 0 else None

    #****************************************************************
    #* B02 Action
    #****************************************************************
        
    def visitAction_declaration(self, ctx:PSSParser.Action_declarationContext):
        
        name = ctx.action_identifier()
        ret = ActionType(
            ctx.action_identifier().accept(self),
            False,
            None if ctx.template_param_decl_list() is None else ctx.template_param_decl_list().accept(self),
            None if ctx.action_super_spec() is None else ctx.action_super_spec().accept(self))
        self._set_srcinfo(ret, ctx.start)
        
        with self._typescope(name, ret):
            for i in ctx.action_body_item():
                a_elem = i.accept(self)
                
                if a_elem is not None:
                    if isinstance(a_elem, list):
                        for a in a_elem:
                            ret.add_child(a)
                    else:
                        ret.add_child(a_elem)
        
        return ret
    
    def visitAbstract_action_declaration(self, ctx:PSSParser.Abstract_action_declarationContext):
        name = ctx.action_identifier()
        ret = ActionType(
            self._get_type_qname(name),
            True,
            None if ctx.template_param_decl_list() is None else ctx.template_param_decl_list().accept(self),
            None if ctx.action_super_spec() is None else ctx.action_super_spec().accept(self))
        self._set_srcinfo(ret, ctx.start)
        
        with self._typescope(name, ret):
            for i in ctx.action_body_item():
                a_elem = i.accept(self)
                
                if a_elem is not None:
                    if isinstance(a_elem, list):
                        for e in a_elem:
                            ret.add_child(e)
                    else:
                        ret.add_child(a_elem)
        
        return ret        
    
    def visitActivity_declaration(self, ctx:PSSParser.Activity_declarationContext):
        ret = Activity()
        
        for s in ctx.activity_stmt():
            stmt = s.accept(self)
            
            if stmt is not None:
                if isinstance(stmt, list):
                    ret.statements.extend(stmt)
                else:
                    ret.statements.append(stmt)
        
        return ret
    
    def visitExec_block(self, ctx:PSSParser.Exec_blockContext):
        ret = ExecBlockProceduralInterface(
            ExecKind[ctx.exec_kind_identifier().getText()])
        
        for s in ctx.exec_stmt():
            stmt = s.accept(self)
            
            if stmt is not None:
                if isinstance(stmt, list):
                    ret.statements.extend(stmt)
                else:
                    ret.statements.append(stmt)
        
        return ret
    
    def visitExec_super_stmt(self, ctx:PSSParser.Exec_super_stmtContext):
        ret = ExecStmtSuper()
        
        return ret
    
    def visitTarget_code_exec_block(self, ctx:PSSParser.Target_code_exec_blockContext):
        # TODO: do we need to massage the content string?
        ret = ExecBlockTargetTemplate(
            ExecKind[ctx.exec_kind_identifier().getText()], 
            ctx.language_identifier().getText(),
            ctx.string())
        
        return ret
    
    def visitTarget_file_exec_block(self, ctx:PSSParser.Target_file_exec_blockContext):
        # TODO: do we need to massage the content string?
        ret = ExecBlockFile(
            ctx.filename_string().getText(),
            ctx.string().getText()
            )

        return ret
    
    
    def visitAttr_field(self, ctx:PSSParser.Attr_fieldContext):
        ret = ctx.data_declaration().accept(self)
        
        for a in ret:
            a.is_rand = ctx.rand is not None
            
        return ret
    
    #****************************************************************
    #* B03 Struct
    #****************************************************************
    
    def visitStruct_declaration(self, ctx:PSSParser.Struct_declarationContext):
        s_ctor = {
            "struct" : StructType,
            "buffer" : BufferType,
            "stream" : StreamType,
            "state" :  StateType,
            "resource" : ResourceType}[ctx.struct_kind().getText()]
             
        name = self._get_type_qname(ctx.identifier())
        ret = s_ctor(
            name,
            None if ctx.template_param_decl_list() is None else ctx.template_param_decl_list().accept(self),
            None if ctx.struct_super_spec() is None else ctx.struct_super_spec().accept(self)
            )
        
        with self._typescope(name, ret):
            for i in ctx.struct_body_item():
                s_elem = i.accept(self)
                if s_elem is not None:
                    if isinstance(s_elem, list):
                        for e in s_elem:
                            ret.add_child(e)
                    else:
                        ret.add_child(s_elem)

            
        return ret
    
    #****************************************************************
    #* B04 PI
    #****************************************************************
    
    def visitMethod_prototype(self, ctx:PSSParser.Method_prototypeContext):
        ret = MethodPrototype(
            ctx.method_identifier().accept(self),
            None if ctx.method_return_type().getText() == "void" else ctx.method_return_type().accept(self))

        last_dir = MethodParameterDir.input        
        for p in ctx.method_parameter_list_prototype().method_parameter():
            p_t = p.accept(self)
            if p_t.direction is None:
                p_t.direction = last_dir
            else:
                last_dir = p_t.direction
            ret.parameters.append(p_t)
        
        return ret
    
    def visitMethod_parameter(self, ctx:PSSParser.Method_parameterContext):
        direction = None if ctx.method_parameter_dir() is None else MethodParameterDir[ctx.method_parameter_dir().getText()]
        ret = MethodParameter(
            ctx.identifier().accept(self),
            direction,
            ctx.data_type().accept(self))

        return ret
    
    def visitMethod_parameter_list(self, ctx:PSSParser.Method_parameter_listContext):
        ret = []
        for e in ctx.expression():
            ret.append(e.accept(self))
            
        return ret
    
    def visitFunction_qualifiers(self, ctx:PSSParser.Function_qualifiersContext):
        if ctx.type_identifier() is not None:
            # Specification on an existing function
            ret = FunctionQualifierSpec(
                ctx.type_identifier().accept(self),
                None if ctx.import_function_qualifiers() is None else ctx.import_function_qualifiers().accept(self))
        else:
            # Standalone import of an external function
            ret = FunctionImport(
                ctx.method_prototype().accept(self),
                None if ctx.import_function_qualifiers() is None else ctx.import_function_qualifiers().accept(self))
            
        return ret

    def visitImport_function_qualifiers(self, ctx:PSSParser.Import_function_qualifiersContext):
        phase = None if ctx.method_qualifiers() is None else MethodQualifiers[ctx.method_qualifiers().getText()]
        language = None if ctx.language_identifier() is None else ctx.language_identifier().getText()

        ret = FunctionQualifiers(phase, language)
        
        return ret
    
    def visitTarget_template_function(self, ctx:PSSParser.Target_template_functionContext):
        ret = FunctionTargetTemplate(
            ctx.method_prototype().accept(self),
            ctx.language_identifier().getText(),
            ctx.string().getText())

        return ret        
    
    def visitPss_function_defn(self, ctx:PSSParser.Pss_function_defnContext):
        ret = FunctionDefinition(
            ctx.method_prototype().accept(self),
            None if ctx.method_qualifiers() is None else ctx.method_qualifiers().accept(self))
        
        for s in ctx.procedural_stmt():
            stmt = s.accept(self)
            
            if stmt is not None:
                if isinstance(stmt, list):
                    ret.statements.extend(stmt)
                else:
                    ret.statements.append(stmt)
        
        return ret
    
    def visitProcedural_block_stmt(self, ctx:PSSParser.Procedural_block_stmtContext):
        ret = ExecBlockStmt()
        
        for s in ctx.procedural_stmt():
            stmt = s.accept(self)
            if stmt is not None:
                if isinstance(stmt, list):
                    ret.statements.extend(stmt)
                else:
                    ret.statements.append(stmt)
        
        return ret
    
    def visitProcedural_var_decl_stmt(self, ctx:PSSParser.Procedural_var_decl_stmtContext):
        var_l = ctx.data_declaration().accept(self)
        return var_l
    
    def visitProcedural_expr_stmt(self, ctx:PSSParser.Procedural_expr_stmtContext):
        if ctx.variable_ref_path() is not None:
            op = {
                "=" : ExecAssignOp.Eq,
                "+=" : ExecAssignOp.PlusEq,
                "-=" : ExecAssignOp.MinusEq,
                "<<=" : ExecAssignOp.SllEq,
                ">>=" : ExecAssignOp.SrlEq,
                "|=" : ExecAssignOp.OrEq,
                "&=" : ExecAssignOp.AndEq
                 }[ctx.assign_op().getText()]
            ret = ExecStmtAssign(
                ctx.variable_ref_path().accept(self),
                op,
                ctx.expression().accept(self))
        else:
            ret = ExecStmtExpr(ctx.expression().accept(self))

        return ret   
    
    def visitProcedural_if_else_stmt(self, ctx:PSSParser.Procedural_if_else_stmtContext):
        ret = ExecStmtIfElse(
            ctx.expression().accept(self),
            ctx.procedural_stmt(0).accept(),
            None if ctx.procedural_stmt(1) is None else ctx.procedural_stmt(1).accept(self))
        
        return ret
    
    def visitProcedural_return_stmt(self, ctx:PSSParser.Procedural_return_stmtContext):
        ret = ExecStmtReturn(
            None if ctx.expression() is None else ctx.expression().accept(self))
        
        return ret
    
    def visitProcedural_match_stmt(self, ctx:PSSParser.Procedural_match_stmtContext):
        ret = ExecStmtMatch(ctx.expression().accept(self))
        
        for c in ctx.procedural_match_choice():
            ret.choices.append(c.accept(self))

        return ret            
    
    def visitProcedural_match_choice(self, ctx:PSSParser.Procedural_match_choiceContext):
        ret = ExecStmtMatchChoice(
            None if ctx.open_range_list() is None else ctx.open_range_list().accept(self),
            ctx.procedural_stmt().accept(self))
        
        return ret
    
    def visitProcedural_repeat_stmt(self, ctx:PSSParser.Procedural_repeat_stmtContext):
        if ctx.is_while is not None:
            ret = ExecStmtWhile(
                ctx.expression().accept(self),
                ctx.procedural_stmt().accept(self))
        elif ctx.is_repeat is not None:
            ret = ExecStmtRepeat(
                ctx.expression().accept(self),
                None if ctx.identifier() is None else ctx.identifier().accept(self),
                ctx.procedural_stmt().accept(self))
        else:
            ret = ExecStmtRepeatWhile(
                ctx.expression().accept(self),
                ctx.procedural_stmt().accept(self))
            
        return ret
    
    def visitProcedural_foreach_stmt(self, ctx:PSSParser.Procedural_foreach_stmtContext):
        ret = ExecStmtForeach(
            None if ctx.iterator_identifier() is None else ctx.iterator_identifier().accept(self),
            ctx.expression().accept(self),
            None if ctx.index_identifier() is None else ctx.index_identifier().accelt(self))
        
        return ret
    
    def visitProcedural_break_stmt(self, ctx:PSSParser.Procedural_break_stmtContext):
        ret = ExecStmtBreak()
        
        return ret

    def visitProcedural_continue_stmt(self, ctx:PSSParser.Procedural_continue_stmtContext):
        ret = ExecStmtContinue()
        
        return ret
    
    #****************************************************************
    #* B04 Component
    #****************************************************************
    
    def visitComponent_declaration(self, ctx:PSSParser.Component_declarationContext):
        name = ctx.component_identifier()        
        ret = ComponentType(
            ctx.component_identifier().accept(self),
            None if ctx.template_param_decl_list() is None else ctx.template_param_decl_list().accept(self),
            None if ctx.component_super_spec() is None else ctx.component_super_spec().accept(self)
            )

        self._set_srcinfo(ret, ctx.start)
        
        self._scope_s[-1].add_child(ret)
        
        with self._typescope(name, ret):
            for c in ctx.component_body_item():
                c_elem = c.accept(self)
                if c_elem is not None:
                    if isinstance(c_elem, list):
                        for e in c_elem:
                            ret.add_child(e)
                    else:
                        ret.add_child(c_elem)

        return ret
    
    def visitComponent_data_declaration(self, ctx:PSSParser.Component_data_declarationContext):
        field_l = ctx.data_declaration().accept(self)

        for f in field_l:
            if ctx.is_static is not None:
                f.flags |= FieldAttrFlags.Static
                
            if ctx.is_const is not None:
                f.flags |= FieldAttrFlags.Const
        
        return field_l
    
    def visitComponent_pool_declaration(self, ctx:PSSParser.Component_pool_declarationContext):
        field_l = []
        size = None if ctx.expression() is None else ctx.expression().accept(self)
        typeid = ctx.type_identifier().accept(self)
        
        for id in ctx.identifier():
            field_l.append(FieldPool(
                id,
                typeid,
                size))
                
        return field_l
    
    def visitObject_bind_stmt(self, ctx:PSSParser.Object_bind_stmtContext):
        ret = PoolBindStmt(
            ctx.hierarchical_id().accept(self))
        
        for p in ctx.object_bind_item_or_list().component_path():
            ret.bindlist.append(p.accept(self))
            
        return ret

   
    def visitType_identifier(self, ctx:PSSParser.Type_identifierContext):
        ret = TypeIdentifier(ctx.is_global is not None)
        
        for tie in ctx.type_identifier_elem():
            ret.path.append(tie.accept(self))
            
        return ret
        
    def visitType_identifier_elem(self, ctx:PSSParser.Type_identifier_elemContext):
        ret = TypeIdentifierElem(ctx.identifier().accept(self))
        
        if ctx.template_param_value_list() is not None:
            ret.templ_pvl = ctx.template_param_value_list().accept(self)
            
        return ret
        
    def visitExpression(self, ctx:PSSParser.ExpressionContext):
        ret = None
        
        lhs_e = None if ctx.lhs is None else ctx.lhs.accept(self)
        rhs_e = None if ctx.rhs is None else ctx.rhs.accept(self)

        if ctx.unary_op() is not None:
            op = {
                "+" : UnaryOp.Plus,
                "-" : UnaryOp.Minus,
                "!" : UnaryOp.BoolNot,
                "~" : UnaryOp.BitNot,
                "&" : UnaryOp.BitAnd,
                "|" : UnaryOp.BitOr,
                "^" : UnaryOp.BitXor
                }[ctx.unary_op().getText()]
            ret = ExprUnary(lhs_e, op)
        elif ctx.exp_op() is not None:
            ret = ExprBinType(
                lhs_e,
                ExprBinOp.Exp,
                rhs_e)
        elif ctx.mul_div_mod_op() is not None:
            op = {
                "*" : ExprBinOp.Mul,
                "/" : ExprBinOp.Div,
                "%" : ExprBinOp.Mod}[ctx.mul_div_mod_op().getText()]
            
            ret = ExprBinType(
                lhs_e,
                op,
                rhs_e)
        elif ctx.add_sub_op() is not None:
            op = {
                "+" : ExprBinOp.Add,
                "-" : ExprBinOp.Sub}[ctx.add_sub_op().getText()]
            ret = ExprBinType(
                lhs_e,
                op,
                rhs_e)
        elif ctx.shift_op() is not None:
            # TODO: the op might show up as ">" ... ">"
            op = {
                "<<" : ExprBinOp.Sll,
                ">>" : ExprBinOp.Srl}[ctx.shift_op().getText()]
            ret = ExprBinType(
                lhs_e,
                op,
                rhs_e)
        elif ctx.inside_expr_term() is not None:
            ret = ExprIn(
                lhs_e,
                ctx.inside_expr_term().accept(self))
        elif ctx.logical_inequality_op() is not None:
            op = {
                "<" : ExprBinOp.LT,
                ">" : ExprBinOp.GT,
                "<=" : ExprBinOp.LE,
                ">=" : ExprBinOp.GE}[ctx.logical_inequality_op().getText()]
            ret = ExprBinType(
                lhs_e,
                op,
                rhs_e)
        elif ctx.eq_neq_op() is not None:
            op = {
                "==" : ExprBinOp.EqEq,
                "!=" : ExprBinOp.Neq}[ctx.eq_neq_op().getText()]
            ret = ExprBinType(
                lhs_e,
                op,
                rhs_e)
        elif ctx.binary_and_op() is not None:
            ret = ExprBinType(
                lhs_e,
                ExprBinOp.BinAnd,
                rhs_e)
        elif ctx.binary_xor_op() is not None:
            ret = ExprBinType(
                lhs_e,
                ExprBinOp.BinXor,
                rhs_e)
        elif ctx.binary_or_op() is not None:
            ret = ExprBinType(
                lhs_e,
                ExprBinOp.BinOr,
                rhs_e)
        elif ctx.logical_and_op() is not None:
            ret = ExprBinType(
                lhs_e,
                ExprBinOp.LogAnd,
                rhs_e)
        elif ctx.logical_or_op() is not None:
            ret = ExprBinType(
                lhs_e,
                ExprBinOp.LogOr,
                rhs_e)
        elif ctx.conditional_expr():
            ret = ExprCondType(
                lhs_e,
                ctx.conditional_expr().true_expr.accept(self),
                ctx.conditional_expr().false_expr.accept(self))
        elif ctx.primary():
            ret = ctx.primary().accept(self)
        else:
            print("Unknown expression op")
            
        
        return ret
    
    def visitPrimary(self, ctx:PSSParser.PrimaryContext):
        if ctx.is_super is not None:
            # TODO:
            pass
        else:
            return super().visitPrimary(ctx)

    def visitNumber(self, ctx:PSSParser.NumberContext):
        # TODO:
        return ExprNumLiteral(0, "todo")
    
    def visitBool_literal(self, ctx:PSSParser.Bool_literalContext):
        return ExprBoolLiteral(ctx.getText() == "true")
    
    def visitParen_expr(self, ctx:PSSParser.Paren_exprContext):
        return ctx.expression().accept(self)
    
    def visitString(self, ctx:PSSParser.StringContext):
        if ctx.DOUBLE_QUOTED_STRING() is not None:
            return ExprStrLiteral(ctx.DOUBLE_QUOTED_STRING().getText())
        else:
            return ExprStrLiteral(ctx.TRIPLE_DOUBLE_QUOTED_STRING().getText())
        
    def visitCast_expression(self, ctx:PSSParser.Cast_expressionContext):
        ret = ExprCast(
            ctx.casting_type().accept(self),
            ctx.expression().accept(self))
        
        return ret
    
    def visitVariable_ref_path(self, ctx:PSSParser.Variable_ref_pathContext):
        hid = ctx.hierarchical_id().accept(self)
        
        ret = ExprVarRefPath(hid)
        
        if ctx.expression(0) is not None:
            ret.lhs = ctx.expression(0).accept(self)
            
            if ctx.expression(1) is not None:
                ret.rhs = ctx.expression(1).accept(self)
            
            
        return ret
    
    def visitFunction_symbol_call(self, ctx:PSSParser.Function_symbol_callContext):
        hid = ExprHierarchicalId()
        if ctx.function_symbol_id().function_id() is not None:
            for id in ctx.function_symbol_id().function_id().identifier():
                hid.path_l.append(ExprHierarchicalIdElem(id.accept(self)))
        else:
            hid.path_l.append(ExprHierarchicalIdElem(ctx.function_symbol_id().symbol_identifier().accept(self)))
        ret = ExprFunctionCall(
            hid,
            ctx.method_parameter_list().accept(self))
        
        return ret
    
    def visitMethod_call(self, ctx:PSSParser.Method_callContext):
        ret = ExprMethodCall(
            ctx.hierarchical_id().accept(self),
            ctx.method_parameter_list().accept(self))
        
        return ret
    
    def visitHierarchical_id(self, ctx:PSSParser.Hierarchical_idContext):
        ret = ExprHierarchicalId()

        for e in ctx.hierarchical_id_elem():
            ret.path_l.append(e.accept(self))
        
        return ret
    
    def visitHierarchical_id_elem(self, ctx:PSSParser.Hierarchical_id_elemContext):
        ret = ExprHierarchicalIdElem(ctx.identifier().accept(self))
        
        if ctx.expression() is not None:
            ret.lhs = ctx.expression().accept(self)
            
        return ret
    
    def visitHierarchical_id_list(self, ctx:PSSParser.Hierarchical_id_listContext):
        ret = ExprHierarchicalIdList()
        
        for e in ctx.hierarchical_id():
            ret.hid_l.append(e.accept(self))
        
        return ret
    
    def visitIdentifier(self, ctx:PSSParser.IdentifierContext):
        if ctx.ID() is not None:
            id = ctx.ID().getText()
        else:
            id = ctx.ESCAPED_ID().getText()

        ret = ExprId(id)
        
        return ret
    
    def visitTemplate_param_value(self, ctx:PSSParser.Template_param_valueContext):
        if ctx.constant_expression():
            ret = ExprTemplateParamValue(True, ctx.constant_expression().accept(self))
        else:
            ret = ExprTemplateParamValue(False, ctx.type_identifier().accept(self))
            
        return ret
    
    def visitTemplate_param_value_list(self, ctx:PSSParser.Template_param_value_listContext):
        ret = ExprTemplateParamValueList()
        
        for pv in ctx.template_param_value():
            ret.param_l.append(pv.accept(self))
        
        return ret
    
    #****************************************************************
    #* B06 Activity Statements
    #****************************************************************
    def visitActivity_stmt(self, ctx:PSSParser.Activity_stmtContext):
        s = PSSVisitor.visitActivity_stmt(self, ctx)

        # Note: null statement returns None        
        if ctx.identifier() is not None and s is not None:
            s.label = ctx.identifier().accept(self)
            
        return s

    def visitActivity_constraint_stmt(self, ctx:PSSParser.Activity_constraint_stmtContext):
        ret = ActivityStmtConstraint(ctx.constraint_set().accept(self))
        
        return ret
    
    def visitForeach_constraint_item(self, ctx:PSSParser.Foreach_constraint_itemContext):
        ret = ActivityStmtForeach(
            None if ctx.iterator_identifier() is None else ctx.iterator_identifier().accept(self),
            ctx.expression().accept(self),
            None if ctx.index_identifier() is None else ctx.index_identifier().accept(self),
            ctx.activity_stmt().accept(self)
            )
        
        return ret
    
    def visitActivity_if_else_stmt(self, ctx:PSSParser.Activity_if_else_stmtContext):
        ret = ActivityStmtIfElse(
            ctx.expression().accept(self),
            ctx.activity_stmt(0).accept(self),
            None if len(ctx.activity_stmt()) == 1 else ctx.activity_stmt(1).accept(self))
        
        return ret
    
    def visitActivity_join_branch_spec(self, ctx:PSSParser.Activity_join_branch_specContext):
        ret = ActivityJoinBranch()
        
        for l in ctx.label_identifier():
            ret.label_identifiers.append(l.accept(self))
        
        return ret
    
    def visitActivity_join_first_spec(self, ctx:PSSParser.Activity_join_first_specContext):
        ret = ActivityJoinFirst(ctx.expression().accept(self))
        
        return ret
    
    def visitActivity_join_none_spec(self, ctx:PSSParser.Activity_join_none_specContext):
        ret = ActivityJoinNone()
        
        return ret
    
    def visitActivity_join_select_spec(self, ctx:PSSParser.Activity_join_select_specContext):
        ret = ActivityJoinSelect(ctx.expression().accept(self))
        
        return ret
    
    def visitActivity_match_stmt(self, ctx:PSSParser.Activity_match_stmtContext):
        ret = ActivityStmtMatch(
            ctx.expression().accept(self))
        
        for c in ctx.match_choice():
            ret.branches.append(c.accept(self))
            
        return ret
    
    def visitMatch_choice(self, ctx:PSSParser.Match_choiceContext):
        ret = ActivityStmtMatchBranch(
            None if ctx.is_default is not None else ctx.open_range_list().accept(self),
            ctx.activity_stmt().accept(self))
        
        return ret
    
    def visitActivity_parallel_stmt(self, ctx:PSSParser.Activity_parallel_stmtContext):
        ret = ActivityStmtParallel(
            None if ctx.activity_join_spec() is None else ctx.activity_join_spec().accept(self)
            )
        
        for stmt in ctx.activity_stmt():
            s = stmt.accept(self)
            if s is not None:
                ret.statements.append(s)
        
        return ret
    
    def visitActivity_repeat_stmt(self, ctx:PSSParser.Activity_repeat_stmtContext):
        if ctx.is_while is not None:
            ret = ActivityStmtWhile(
                ctx.expression().accept(self),
                ctx.activity_stmt().accept(self))
            
        elif ctx.is_repeat is not None:
            ret = ActivityStmtRepeat(
                None if ctx.identifier() is None else ctx.identifier().accept(self),
                ctx.expression().accept(self),
                ctx.activity_stmt().accept(self))
        else:
            ret = ActivityStmtDoWhile(
                ctx.expression().accept(self),
                ctx.activity_stmt().accept(self))
            
            
        return ret
    
    def visitActivity_replicate_stmt(self, ctx:PSSParser.Activity_replicate_stmtContext):
        ret = ActivityStmtReplicate(
            None if ctx.index_identifier() is None else ctx.index_identifier().accept(self),
            ctx.expression().accept(self),
            None if ctx.identifier() is None else ctx.identifier().accept(self),
            ctx.labeled_activity_stmt().accept(self))
        
        return ret
    
    def visitActivity_schedule_stmt(self, ctx:PSSParser.Activity_schedule_stmtContext):
        ret = ActivityStmtSchedule(
            None if ctx.activity_join_spec() is None else ctx.activity_join_spec().accept(self)
            )
        
        return ret
    
    def visitActivity_foreach_stmt(self, ctx:PSSParser.Activity_foreach_stmtContext):
        ret = ActivityStmtForeach(
            None if ctx.iterator_identifier() is None else ctx.iterator_identifier().accept(self),
            ctx.expression().accept(self),
            None if ctx.index_identifier() is None else ctx.index_identifier().accept(self),
            ctx.activity_stmt().accept(self))

        return ret
    
    def visitActivity_action_traversal_stmt(self, ctx:PSSParser.Activity_action_traversal_stmtContext):
        if ctx.is_do is not None:
            ret = ActivityStmtTraverseType(
                ctx.type_identifier().accept(self),
                None if ctx.constraint_set() is None else ctx.constraint_set().accept(self))
        else:
            path = ExprVarRefPath(ExprHierarchicalId([ctx.identifier()]))
            
            if ctx.expression() is not None:
                path.lhs = ctx.expression().accept(self)
            
            ret = ActivityStmtTraverseHandle(
                path,
                None if ctx.constraint_set() is None else ctx.constraint_set().accept(self))
            
        return ret
    
    def visitActivity_select_stmt(self, ctx:PSSParser.Activity_select_stmtContext):
        ret = ActivityStmtSelect()
        
        for b in ctx.select_branch():
            ret.statements.append(b)
        
        return ret
    
    def visitSelect_branch(self, ctx:PSSParser.Select_branchContext):
        ret = ActivityStmtSelectBranch(
            None if ctx.guard is None else ctx.guard.accept(self),
            None if ctx.weight is None else ctx.weight.accept(self),
            ctx.activity_stmt().accept(self)
            )
        
        return ret
    
    def visitActivity_sequence_block_stmt(self, ctx:PSSParser.Activity_sequence_block_stmtContext):
        ret = ActivityStmtSequence()
        
        for stmt in ctx.activity_stmt():
            s = stmt.accept(self)
            if s is not None:
                ret.statements.append(s)
                
        return ret
    
    def visitActivity_bind_stmt(self, ctx:PSSParser.Activity_bind_stmtContext):
        ret = ActivityStmtBind()
        
        ret.targets.append(ctx.hierarchical_id().accept(self))
        
        for hid in ctx.activity_bind_item_or_list().hierarchical_id():
            ret.targets.append(hid.accept(self))
        
        return ret
    
    def visitActivity_super_stmt(self, ctx:PSSParser.Activity_super_stmtContext):
        ret = ActivityStmtSuper()
        
        return ret
    
    #****************************************************************
    #* B07 Activity Statements
    #****************************************************************
    def visitOverrides_declaration(self, ctx:PSSParser.Overrides_declarationContext):
        ret = OverrideBlock()
        
        for sm in ctx.override_stmt():
            s = sm.accept(self)
            if s is not None:
                ret.statements.append(s)
        
        return ret
    
    def visitType_override(self, ctx:PSSParser.Type_overrideContext):
        ret = OverrideStmtType(
            ctx.type_identifier(0).accept(self),
            ctx.type_identifier(1).accept(self))

        return ret
    
    def visitInstance_override(self, ctx:PSSParser.Instance_overrideContext):
        ret = OverrideStmtInst(
            ctx.hierarchical_id().accept(self),
            ctx.type_identifier().accept(self))
        
        return ret
    
    #****************************************************************
    #* B10 Constraints
    #****************************************************************
    
    def visitConstraint_declaration(self, ctx:PSSParser.Constraint_declarationContext):
        ret = ConstraintDeclaration(
            None if ctx.identifier() is None else ctx.identifier().accept(self),
            ctx.is_dynamic is not None)
        
        if ctx.constraint_set() is not None:
            if ctx.constraint_set().constraint_body_item() is not None:
                # Single constraint
                c = ctx.constraint_set().constraint_body_item().accept(self)
                if c is not None:
                    ret.add_constraint(c)
            else:
                # Block of constraints
                for ci in ctx.constraint_set().constraint_block().constraint_body_item():
                    c = ci.accept(self)
                    if c is not None:
                        ret.add_constraint(c)
        else:
            for ci in ctx.constraint_body_item():
                c = ci.accept(self)
                if c is not None:
                    ret.add_constraint(c)
                    
        return ret
    
    def visitDefault_constraint(self, ctx:PSSParser.Default_constraintContext):
        ret = ConstraintDefault(
            ctx.hierarchical_id().accept(self),
            ctx.constant_expression().accept(self)
            )
        
        return ret
    
    def visitDefault_disable_constraint(self, ctx:PSSParser.Default_disable_constraintContext):
        ret = ConstraintDefaultDisable(
            ctx.hierarchical_id().accept(self))
        
        return ret
    
    def visitForall_constraint_item(self, ctx:PSSParser.Forall_constraint_itemContext):
        ret = ConstraintForall(
            ctx.identifier().accept(self),
            ctx.type_identifier().accept(self),
            None if ctx.variable_ref_path() is None else ctx.variable_ref_path().accept(self),
            ctx.constraint_set())
        
        return ret;
    
    def visitForeach_constraint_item(self, ctx:PSSParser.Foreach_constraint_itemContext):
        ret = ConstraintForeach(
            None if ctx.iterator_identifier() is None else ctx.iterator_identifier().accept(self),
            ctx.expression().accept(self),
            None if ctx.index_identifier() is None else ctx.index_identifier().accept(self),
            ctx.constraint_set().accept(self))
        
        return ret
    
    def visitIf_constraint_item(self, ctx:PSSParser.If_constraint_itemContext):
        ret = ConstraintIfElse(
            ctx.expression().accept(self),
            ctx.constraint_set(0).accept(self),
            None if len(ctx.constraint_set()) == 1 else ctx.constraint_set(1).accept(self)
            )
        
        return ret
    
    def visitConstraint_set(self, ctx:PSSParser.Constraint_setContext):
        ret = ConstraintBlock()

        if ctx.constraint_body_item() is not None:
            # Single constraint
            c = ctx.constraint_body_item().accept(self)
            if c is not None:
                ret.add_constraint(c)
        else:
            # Block of constraints
            for ci in ctx.constraint_block().constraint_body_item():
                c = ci.accept(self)
                if c is not None:
                    ret.add_constraint(c)        
        
        return ret
    
    def visitUnique_constraint_item(self, ctx:PSSParser.Unique_constraint_itemContext):
        ret = ConstraintUnique(
            ctx.hierarchical_id_list().accept(self))
        
        return ret
    
    def visitExpression_constraint_item(self, ctx:PSSParser.Expression_constraint_itemContext):
        return ConstraintExpression(ctx.expression().accept(self))
        
    def visitImplication_constraint_item(self, ctx:PSSParser.Implication_constraint_itemContext):
        return ConstraintImplies(
            ctx.expression().accept(self),
            ctx.constraint_set().accept(self))
        
    #****************************************************************
    #* B12 Conditional Compile
    #****************************************************************
    
    def visitPackage_body_compile_if(self, ctx:PSSParser.Package_body_compile_ifContext):
        ret = CompileIf(ctx.constant_expression().accept(self))
        
        for elem in map(lambda e:e.accept(self), ctx.package_body_compile_if_item(0).package_body_item()):
            if isinstance(elem, list):
                for e in elem:
                    ret.statements_true.append(e)
            else:
                ret.statements_true.append(elem)

        if ctx.package_body_compile_if_item(1) is not None:
            for elem in map(lambda e:e.accept(self), ctx.package_body_compile_if_item(1).package_body_item()):
                if isinstance(elem, list):
                    for e in elem:
                        ret.statements_false.append(e)
                else:
                    ret.statements_false.append(elem)
                
        return ret
    
    def visitAction_body_compile_if(self, ctx:PSSParser.Action_body_compile_ifContext):
        ret = CompileIf(ctx.constant_expression().accept(self))
        
        for elem in map(lambda e:e.accept(self), ctx.action_body_compile_if_item(0).action_body_item()):
            if isinstance(elem, list):
                for e in elem:
                    ret.statements_true.append(e)
            else:
                ret.statements_true.append(elem)

        if ctx.action_body_compile_if_item(1) is not None:
            for elem in map(lambda e:e.accept(self), ctx.action_body_compile_if_item(1).action_body_item()):
                if isinstance(elem, list):
                    for e in elem:
                        ret.statements_false.append(e)
                else:
                    ret.statements_false.append(elem)
                
        return ret        
    
    def visitComponent_body_compile_if(self, ctx:PSSParser.Component_body_compile_ifContext):
        ret = CompileIf(ctx.constant_expression().accept(self))
        
        for elem in map(lambda e:e.accept(self), ctx.component_body_compile_if_item(0).component_body_item()):
            if isinstance(elem, list):
                for e in elem:
                    ret.statements_true.append(e)
            else:
                ret.statements_true.append(elem)

        if ctx.component_body_compile_if_item(1) is not None:
            for elem in map(lambda e:e.accept(self), ctx.component_body_compile_if_item(1).component_body_item()):
                if isinstance(elem, list):
                    for e in elem:
                        ret.statements_false.append(e)
                else:
                    ret.statements_false.append(elem)
                
        return ret        
    
    def visitStruct_body_compile_if(self, ctx:PSSParser.Struct_body_compile_ifContext):
        ret = CompileIf(ctx.constant_expression().accept(self))
        
        for elem in map(lambda e:e.accept(self), ctx.struct_body_compile_if_item(0).struct_body_item()):
            if isinstance(elem, list):
                for e in elem:
                    ret.statements_true.append(e)
            else:
                ret.statements_true.append(elem)

        if ctx.struct_body_compile_if_item(1) is not None:
            for elem in map(lambda e:e.accept(self), ctx.struct_body_compile_if_item(1).struct_body_item()):
                if isinstance(elem, list):
                    for e in elem:
                        ret.statements_false.append(e)
                else:
                    ret.statements_false.append(elem)
                
        return ret        
    
    def visitCompile_assert_stmt(self, ctx:PSSParser.Compile_assert_stmtContext):
        ret = CompileAssert(
            ctx.constant_expression().accept(self),
            None if ctx.msg is None else ctx.msg.getText())
        
        return ret
    
    def visitStatic_ref_path(self, ctx:PSSParser.Static_ref_pathContext):

        ret = ExprStaticRefPath(ctx.is_global is not None)
        
        for elem in ctx.static_ref_path_elem():
            ret.path.append(elem.accept(self))
            
        return ret
    
    def visitStatic_ref_path_elem(self, ctx:PSSParser.Static_ref_path_elemContext):
        ret = ExprStaticRefPathElem(ctx.identifier().accept(self))
        
        if ctx.template_param_value_list() is not None:
            ret.templ_param_values = ctx.template_param_value_list().accept(self)
        
        return ret
    
    def visitCompile_has_expr(self, ctx:PSSParser.Compile_has_exprContext):
        ret = ExprCompileHas(ctx.static_ref_path().accept(self))
        
        return ret;
    
    def visitCast_expression(self, ctx:PSSParser.Cast_expressionContext):
        # TODO:
        return PSSVisitor.visitCast_expression(self, ctx)
    
    def visitOpen_range_list(self, ctx:PSSParser.Open_range_listContext):
        ret = ExprOpenRangeList()
        
        for rv in ctx.open_range_value():
            ret.val_l.append(rv.accept(self))
            
        return ret
    
    def visitOpen_range_value(self, ctx:PSSParser.Open_range_valueContext):
        lhs = ctx.lhs.accept(self)
        rhs = None if ctx.rhs is None else ctx.rhs.accept(self)
        
        ret = ExprOpenRangeValue(lhs, rhs)
        
        return ret
    
    
    def visitExtend_stmt(self, ctx:PSSParser.Extend_stmtContext):

        if ctx.ext_type is None:
            ext_type = ExtendTarget.Struct
        else:
            ext_type = {
                "action" : ExtendTarget.Action,
                "component" : ExtendTarget.Component,
                "enum" : ExtendTarget.Enum}[ctx.ext_type.text]

        ext = ExtendStmt(
            ext_type,
            self._typeid2reference(ctx.type_identifier())
            )
        
        self._scope_s[-1].add_child(ext)
        self._scope_s.append(ext)
        # TODO: we may need to treat action/component extend and enum extend differently

        if ext_type == ExtendTarget.Action:
            for it in ctx.action_body_item():
                it.accept(self)
        elif ext_type == ExtendTarget.Component:
            for it in ctx.component_body_item():
                it.accept(self)
        elif ext_type == ExtendTarget.Struct:
            for it in ctx.struct_body_item():
                it.accept(self)
        else:
            print("TODO: handle extend enum")
            
        self._scope_s.pop()
        
        return ext
    
    #****************************************************************
    #* B01 Package
    #****************************************************************
    
    def visitImport_stmt(self, ctx:PSSParser.Import_stmtContext):
        
        imp = ImportStmt(
            self._typeid2reference(
                ctx.package_import_pattern().type_identifier()),
            ctx.package_import_pattern().wildcard
            )
        self._set_srcinfo(imp, ctx.start)
        
        self._scope_s[-1].add_child(imp)

        return PSSVisitor.visitImport_stmt(self, ctx)
    
    def visitPackage_declaration(self, ctx:PSSParser.Package_declarationContext):
        cu = self._scope_s[-1]
        pkg_name = self._identifier2str(ctx.name.identifier())

        # Note: package doesn't have a source location associated
        # with it, because we combine content from multiple package statements
        if pkg_name in cu.package_m.keys():
            pkg = self.package_m[pkg_name]
        else:
            pkg = PackageType((pkg_name,))
            cu.package_m[pkg_name] = pkg
            cu.add_child(pkg)
        
        with self._typescope(ctx.name, pkg):
            for c in ctx.package_body_item():
                c.accept(self)
                
    def visitConst_field_declaration(self, ctx:PSSParser.Const_field_declarationContext):
        field_l = ctx.const_data_declaration().accept(self)
        
        for f in field_l:
            f.flags |= FieldAttrFlags.Const
            
        return field_l
    
    def visitConst_data_declaration(self, ctx:PSSParser.Const_data_declarationContext):
        data_type = ctx.scalar_data_type().accept(self)
        
        field_l = map(lambda e:e.accept(self), ctx.const_data_instantiation())
        
        for f in field_l:
            f.ftype = data_type
            
        return field_l
    
    def visitConst_data_instantiation(self, ctx:PSSParser.Const_data_instantiationContext):
        ret = FieldAttr(
            ctx.identifier().accept(self),
            0, # Flags
            False, # is_rand
            None, # field-type
            None, # array-dim
            ctx.constant_expression().accept(self)
            )
        
        return ret
    
    def visitStatic_const_field_declaration(self, ctx:PSSParser.Static_const_field_declarationContext):
        field_l = ctx.const_data_declaration().accept(self)
        
        for f in field_l:
            f.flags |= FieldAttrFlags.Static
            f.flags |= FieldAttrFlags.Const
            
        return field_l
        
    def visitTemplate_param_decl_list(self, ctx:PSSParser.Template_param_decl_listContext):
        params = []
        for p in ctx.template_param_decl():
            params.append(p.accept(self))
            
        return TemplateParamDeclList(params)
    
    def visitGeneric_type_param_decl(self, ctx:PSSParser.Generic_type_param_declContext):
        ret = TemplateGenericTypeParamDecl(
            ctx.identifier().accept(self),
            None if ctx.type_identifier() is None else ctx.type_identifier().accept(self)
            )
        
        return ret
    
    def visitCategory_type_param_decl(self, ctx:PSSParser.Category_type_param_declContext):
        category = {
            "action" : TemplateTypeCategory.Action,
            "component" : TemplateTypeCategory.Component,
            "struct" : TemplateTypeCategory.Struct,
            "buffer" : TemplateTypeCategory.Buffer,
            "stream" : TemplateTypeCategory.Stream,
            "state" : TemplateTypeCategory.State,
            "resource" : TemplateTypeCategory.Resource}[ctx.type_category().getText()]
        
        ret = TemplateCategoryTypeParamDecl(
            ctx.identifier().accept(self),
            category,
            None if ctx.type_restriction() is None else ctx.type_restriction().accept(self),
            None if ctx.type_identifier() is None else ctx.type_identifier().accept(self)
            )
        
        return ret
    
    def visitValue_param_decl(self, ctx:PSSParser.Value_param_declContext):
        ret = TemplateValueParamDecl(
            ctx.identifier().accept(self),
            ctx.data_type().accept(self),
            None if ctx.constant_expression() is None else ctx.constant_expression().accept(self))
        
        return ret
    
    # B09_DataTypes
    
    def visitDomain_open_range_list(self, ctx:PSSParser.Domain_open_range_listContext):
        ret = DomainOpenRangeList()
        
        for e in ctx.domain_open_range_value():
            ret.rangelist.append(e.accept(self))

        return ret            
    
    def visitDomain_open_range_value(self, ctx:PSSParser.Domain_open_range_valueContext):
        
        if ctx.limit_low is not None or ctx.limit_high is not None:
            # 
            ret = DomainOpenRangeValue(
                None if ctx.lhs is None else ctx.lhs.accept(self),
                None if ctx.rhs is None else ctx.rhs.accept(self))
        else:
            ret = ctx.lhs.accept(self)

        return ret        
    
    def visitString_type(self, ctx:PSSParser.String_typeContext):
        if ctx.DOUBLE_QUOTED_STRING(0) is not None:
            in_spec = []
            for s in ctx.DOUBLE_QUOTED_STRING():
                in_spec.append(s.getText())
        else:
            in_spec = None
            
        ret = DataTypeString(in_spec)
        
        return ret

    def visitBool_type(self, ctx:PSSParser.Bool_typeContext):
        return DataTypeScalar(ScalarType.Bool, None, None, None)

    def visitChandle_type(self, ctx:PSSParser.Chandle_typeContext):
        return DataTypeScalar(ScalarType.Chandle, None, None, None)
    
    def visitInteger_type(self, ctx:PSSParser.Integer_typeContext):
        if ctx.integer_atom_type().getText() == "int":
            scalar_type = ScalarType.Integer
        else:
            scalar_type = ScalarType.Bit

        ret = DataTypeScalar(
            scalar_type,
            None if ctx.lhs is None else ctx.lhs.accept(self),
            None if ctx.rhs is None else ctx.rhs.accept(self),
            None if ctx.domain_open_range_list() is None else ctx.domain_open_range_list().accept(self))
        
        return ret
    
    def visitEnum_declaration(self, ctx:PSSParser.Enum_declarationContext):
        enumerators = []
        for ei in ctx.enum_item():
            enumerators.append(ei.accept(self))
            
        ret = EnumDeclaration(
            ctx.enum_identifier().accept(self),
            enumerators)
        
        return ret
    
    def visitEnum_item(self, ctx:PSSParser.Enum_itemContext):
        ret = EnumItem(
            ctx.identifier().accept(self),
            None if ctx.constant_expression() is None else ctx.constant_expression().accept(self))
        
        return ret
    
    def visitEnum_type(self, ctx:PSSParser.Enum_typeContext):
        ret = DataTypeEnum(
            ctx.enum_type_identifier().accept(self),
            None if ctx.open_range_list() is None else ctx.open_range_list().accept(self))
       
        return ret         
    
    def visitTypedef_declaration(self, ctx:PSSParser.Typedef_declarationContext):
        ret = Typedef(
            ctx.data_type().accept(self),
            ctx.type_identifier().accept(self))
        
        return ret
    
    def visitUser_defined_datatype(self, ctx:PSSParser.User_defined_datatypeContext):
        ret = DataTypeUser(
            ctx.type_identifier())
        
        return ret

    #****************************************************************    
    #* B08 Data Declarations
    #****************************************************************    
    def visitData_declaration(self, ctx:PSSParser.Data_declarationContext):
        ret = []
        
        ftype = ctx.data_type().accept(self)
        
        for decl in ctx.data_instantiation():
            decl_i = decl.accept(self)
            decl_i.ftype = ftype
            ret.append(decl_i)
            
        return ret

    def visitData_instantiation(self, ctx:PSSParser.Data_instantiationContext):
        ret = FieldAttr(
            ctx.identifier().accept(self),
            0, # No flags for now
            False,
            None, # Type gets filled in later
            None if ctx.array_dim() is None else ctx.array_dim().accept(self),
            None if ctx.constant_expression() is None else ctx.constant_expression().accept(self)
            )
        
        return ret
    
    def check_elem(self, e, t):
        pass
#        if e is None:
#            print()
#            print("Note: Failed to elaborate a \"" + str(type(t)) + "\" " + t.getText())
#            raise Exception("Failed to elaborate a \"" + str(type(t)) + "\" " + t.getText())
    
    def syntaxError(self, recognizer, offendingSymbol, line, column, msg, e):
        self._scope_s[-1].add_marker(Marker(line, column, msg))
        super().syntaxError(recognizer, offendingSymbol, line, column, msg, e)
        # TODO: Add error to CU output
   #     raise Exception("TODO: parse error")

    def _enter_type_scope(self, name, scope):
        if hasattr(name, "identifier"):
            name = name.identifier().ID().getText()
            
        self._namespace_s.append(name)
        if scope is not None:
            self._scope_s.append(scope)
        
    def _leave_type_scope(self, name, scope):
        e = self._namespace_s.pop()
#        if e != name:
#            raise Exception("Type-scope mismatch: leaving scope \"" + e + "\", but expect to leave scope \"" + name + "\"")
        if scope is not None:
            self._scope_s.pop()
        
    def _get_type_qname(self, name : str) -> Tuple[str]:
        """Returns a qualified type name"""
        if hasattr(name, "identifier"):
            name = name.identifier().ID().getText()
            
        ret = self._namespace_s.copy()
        ret.append(name)
        
        return tuple(ret)
    
    def _type_identifier2tuple(self, ti : PSSParser.Type_identifierContext):
        ret = []
        for elem in ti.type_identifier_elem():
            ret.append(elem.identifier().ID().getText())
            
        return tuple(ret)
    
    def _identifier2str(self, id : PSSParser.IdentifierContext):
        return id.ID().getText()
    
    def _set_srcinfo(self, obj, tok):
        obj.srcinfo = SourceInfo(-1, tok.line, tok.column)
        
    def _typeid2reference(self, ti : PSSParser.Type_identifierContext):
        ref = []
        for elem in ti.type_identifier_elem():
            ref.append(elem.identifier().ID().getText())
            
        ret = Reference(tuple(ref), ti.is_global is not None)
        self._set_srcinfo(ret, ti.start)
            
        return ret
    
    def _get_attr_flags(self):
        
        flags = AttrFlags.Default
        
        # TODO: move back through the stack and aggregate flags
        
        return flags
        
