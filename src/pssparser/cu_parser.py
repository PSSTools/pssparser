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
from pssparser.model.compilation_unit import CompilationUnit
from pssparser.model.component_type import ComponentType
from pssparser.model.cu_type import CUType
from pssparser.model.expr_bin_type import ExprBinType, ExprBinOp
from pssparser.model.expr_bool_literal import ExprBoolLiteral
from pssparser.model.expr_cond_type import ExprCondType
from pssparser.model.expr_hierarchical_id import ExprHierarchicalId
from pssparser.model.expr_hierarchical_id_elem import ExprHierarchicalIdElem
from pssparser.model.expr_hierarchical_id_list import ExprHierarchicalIdList
from pssparser.model.expr_id import ExprId
from pssparser.model.expr_in import ExprIn
from pssparser.model.expr_num_literal import ExprNumLiteral
from pssparser.model.expr_open_range_list import ExprOpenRangeList
from pssparser.model.expr_open_range_value import ExprOpenRangeValue
from pssparser.model.expr_str_literal import ExprStrLiteral
from pssparser.model.expr_unary import UnaryOp, ExprUnary
from pssparser.model.extend_stmt import ExtendStmt, ExtendTarget
from pssparser.model.import_stmt import ImportStmt
from pssparser.model.marker import Marker
from pssparser.model.package_type import PackageType
from pssparser.model.reference import Reference
from pssparser.model.source_info import SourceInfo
from pssparser.model.expr_var_ref_path import ExprVarRefPath
from pssparser.model.expr_template_param_value import ExprTemplateParamValue
from pssparser.model.expr_template_param_value_list import ExprTemplateParamValueList
from pssparser.model.expr_static_ref_path import ExprStaticRefPath
from pssparser.model.expr_static_ref_path_elem import ExprStaticRefPathElem
from pssparser.model.expr_compile_has import ExprCompileHas
from pssparser.model.type_identifier_elem import TypeIdentifierElem
from pssparser.model.type_identifier import TypeIdentifier


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
    
    def visitAction_declaration(self, ctx:PSSParser.Action_declarationContext):
        
        if ctx.action_super_spec() is not None:
            super_type = ctx.action_super_spec().accept(self)
        else:
            super_type = None

        name = ctx.action_identifier()
        ret = ActionType(
            self._get_type_qname(name),
            super_type)
        self._set_srcinfo(ret, ctx.start)
        
        with self._typescope(name, ret):
            for i in ctx.action_body_item():
                a_elem = i.accept(self)
                
                if a_elem is not None:
                    ret.add_child(a_elem)
        
        return ret
    
    def visitAbstract_action_declaration(self, ctx:PSSParser.Abstract_action_declarationContext):
        if ctx.action_super_spec() is not None:
            super_spec = ctx.action_super_spec()
            super_type = self._typeid2reference(super_spec.type_identifier())
        else:
            super_type = None

        name = ctx.action_identifier()
        ret = ActionType(
            self._get_type_qname(name),
            super_type, True)
        self._set_srcinfo(ret, ctx.start)
        
        with self._typescope(name, ret):
            for i in ctx.action_body_item():
                a_elem = i.accept(self)
                
                if a_elem is not None:
                    ret.add_child(a_elem)
        
        return ret        
    
    def visitComponent_declaration(self, ctx:PSSParser.Component_declarationContext):
        print("visitComponent_declaration")
        
        if ctx.component_super_spec() is not None:
            super_type = ctx.component_super_spec().accept(self)
        else:
            super_type = None

        name = ctx.component_identifier()        
        ret = ComponentType(
            self._get_type_qname(name),
            super_type)

        self._set_srcinfo(ret, ctx.start)
        
        self._scope_s[-1].add_child(ret)
        
        with self._typescope(name, ret):
            for c in ctx.component_body_item():
                c_elem = c.accept(self)
                self.check_elem(c_elem, c)
                ret.add_child(c_elem)

        return ret
   
    def visitConst_data_declaration(self, ctx:PSSParser.Const_data_declarationContext):
        pass

    def visitConst_field_declaration(self, ctx:PSSParser.Const_field_declarationContext):
        self._attr_flags_s.append(AttrFlags.Const)
        ctx.const_data_declaration().accept(self)
        self._attr_flags_s.pop()
        
    def visitStatic_const_field_declaration(self, ctx:PSSParser.Static_const_field_declarationContext):
        self._attr_flags_s.append(AttrFlags.Static)
        self._attr_flags_s.append(AttrFlags.Const)
        ctx.const_data_declaration().accept(self)
        self._attr_flags_s.pop()
        self._attr_flags_s.pop()
        
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
    
    def visitVariable_ref_path(self, ctx:PSSParser.Variable_ref_pathContext):
        hid = ctx.hierarchical_id().accept(self)
        
        ret = ExprVarRefPath(hid)
        
        if ctx.expression(0) is not None:
            ret.lhs = ctx.expression(0).accept(self)
            
            if ctx.expression(1) is not None:
                ret.rhs = ctx.expression(1).accept(self)
            
            
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
    
    def visitMethod_function_symbol_call(self, ctx:PSSParser.Method_function_symbol_callContext):
        # TODO:
        return PSSVisitor.visitMethod_function_symbol_call(self, ctx)
    
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
        
