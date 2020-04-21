'''
Created on Mar 9, 2020

@author: ballance
'''
from pssparser.model.attr_decl_stmt import AttrDeclStmt
from pssparser.model.expr_open_range_list import ExprOpenRangeList
from pssparser.model.expr_open_range_value import ExprOpenRangeValue
from pssparser.model.expr_template_param_value_list import ExprTemplateParamValueList
from pssparser.model.expr_static_ref_path import ExprStaticRefPath
from pssparser.model.type_identifier import TypeIdentifier
from pssparser.model.type_identifier_elem import TypeIdentifierElem
from pssparser.model.expr_template_param_value import ExprTemplateParamValue
from pssparser.model.template_param_decl_list import TemplateParamDeclList
from pssparser.model.template_category_type_param_decl import TemplateCategoryTypeParamDecl
from pssparser.model.template_generic_type_param_decl import TemplateGenericTypeParamDecl
from pssparser.model.template_value_param_decl import TemplateValueParamDecl
from pssparser.model.typedef import Typedef
from pssparser.model.activity_stmt_repeat import ActivityStmtRepeat
from pssparser.model.activity_stmt_replicate import ActivityStmtReplicate
from pssparser.model.activity_stmt_foreach import ActivityStmtForeach

class TypeModelVisitor(object):
    pass

    def visit_type_scope(self, t):
        pass
    
    def visit_activity_stmt_base(self, s):
        if s.label is not None:
            s.label.accept(self)
            
    def visit_activity_stmt_scope(self, s):
        self.visit_activity_stmt_base(s)
        
        for stmt in s.statements:
            stmt.accept(self)
            
    def visit_activity_join_branch(self, s):
        for l in s.label_identifiers:
            l.accept(self)
            
    def visit_activity_join_first(self, s):
        s.accept(self)
            
    def visit_activity_join_none(self, s):
        pass
        
    def visit_activity_join_select(self, s):
        s.e.accept(self)
            
    def visit_activity_stmt_constraint(self, s):
        self.visit_activity_stmt_base(s)
        s.cs.accept(self)
        
    def visit_activity_stmt_foreach(self, s : ActivityStmtForeach):
        self.visit_activity_stmt_base(s)
        if s.it_id is not None:
            s.it_id.accept(self)
            
        if s.idx_id is not None:
            s.idx_id.accept(self)
            
        s.e.accept(self)
        s.s.accept(self)
        
            
    def visit_activity_stmt_do_while(self, s):
        self.visit_activity_stmt_base(s)
        s.e.accept(self)
        s.s.accept(self)
    
    def visit_activity_stmt_if_else(self, s):
        self.visit_activity_stmt_base(s)
        s.e.accept(self)
        
        s.true_s.accept(self)
        if s.false_s is not None:
            self.false_s.accept(self)
            
    def visit_activity_stmt_parallel(self, s):
        if s.join_spec is not None:
            s.join_spec.accept(self)
        self.visit_activity_stmt_scope(s)
            
    def visit_activity_stmt_repeat(self, s):
        self.visit_activity_stmt_base(s)
        if s.loop_var is not None:
            s.loop_var.accept(self)
            
        s.e.accept(self)
        s.s.accept(self)
        
    def visit_activity_stmt_replicate(self, s : ActivityStmtReplicate):
        self.visit_activity_stmt_base(s)
        if s.idx_id is not None:
            self.idx_id.accept(self)
        if s.arr_label is not None:
            s.arr_label.accept(self)
        s.e.accept(self)
        s.s.accept(self)
        
    def visit_activity_stmt_schedule(self, s):
        if s.join_spec is not None:
            s.join_spec.accept(self)
        self.visit_activity_stmt_scope(s)
        
    def visit_activity_stmt_select(self, s):
        self.visit_activity_stmt_scope(s)
        
    def visit_activity_stmt_select_branch(self, s):
        if s.guard is not None:
            s.guard.accept(self)
        if s.weight is not None:
            s.weight.accept(self)
        s.s.accept(self)
        
    def visit_activity_stmt_sequence(self, s):
        self.visit_activity_stmt_base(s)
        for stmt in s.statements:
            stmt.accept(self)
        
            
    def visit_activity_stmt_while(self, s):
        self.visit_activity_stmt_base(s)
        s.e.accept(self)
        s.s.accept(self)
            
    def visit_composite_type(self, t):
        if t.template_params is not None:
            t.template_params.accept(self)
            
        if t.super_type is not None:
            t.super_type.accept(self)
            
        self.visit_type_scope(t)
        
        for c in t.children:
            c.accept(self)
            
    def visit_constraint_block(self, c):
        for ci in c.constraints:
            ci.accept(self)
            
    def visit_constraint_declaration(self, c):
        if c.name is not None:
            c.name.accept(self)
            
        self.visit_constraint_block(c)
        
    def visit_constraint_default(self, c):
        c.hid.accept(self)
        c.e.accept(self)
        
    def visit_constraint_default_disable(self, c):
        c.hid.accept(self)
        
    def visit_constraint_expression(self, c):
        c.e.accept(self)
        
    def visit_constraint_forall(self, c):
        c.id.accept(self)
        c.tid.accept(self)
        if c.in_path is not None:
            c.in_path.accept(self)
            
        c.cs.accept(self)
        
    def visit_constraint_foreach(self, c):
        if c.it_id is not None:
            c.it_id.accept(self)
        
        c.e.accept(self)
        
        if c.idx_id is not None:
            c.idx_id.accept(self)
            
        self.cs.accept(self)
        
    def visit_constraint_if_else(self, c):
        c.e.accept(self)
        c.true_cs.accept(self)
        if c.false_cs is not None:
            c.false_cs.accept(self)
        
    def visit_constraint_implies(self, c):
        c.e.accept(self)
        c.cs.accept(self)
        
    def visit_constraint_unique(self, c):
        c.hid_l.accept(self)
        

    def visit_package(self, p):
        self.visit_composite_type(p)

    def visit_action(self, a):
        self.visit_composite_type(a)
        pass
    
    def visit_attr_decl_stmt(self, a : AttrDeclStmt):
        a.typeref.accept(self)
    
    def visit_compilation_unit(self, cu):
#        for n,p in cu.package_m.items():
#            p.accept(self)

        self.visit_composite_type(cu)
        
    def visit_compile_assert(self, c):
        c.cond.accept(self)
        
    def visit_compile_if(self, ci):
        ci.cond.accept(self)
        
        for s in ci.statements_true:
            s.accept(self)
            
        for s in ci.statements_false:
            s.accept(self)
    
    def visit_component(self, c):
        self.visit_composite_type(c)
        
        
    def visit_composite_stmt(self, c):
        for ch in c.children:
            ch.accept(self)
            
    def visit_data_type_enum(self, e):
        e.identifier.accept(self)
        if e.rangelist is not None:
            e.rangelist.accept(self)
            
    def visit_data_type_scalar(self, t):
        if t.lhs is not None:
            t.lhs.accept(self)
        if t.rhs is not None:
            t.rhs.accept(self)
        if t.in_range is not None:
            t.in_range.accept(self)
            
    def visit_data_type_user(self, t):
        t.typeid.accept(self)

    def visit_enum_declaration(self, e):
        e.name.accept(self)
        for en in e.enumerators:
            en.accept(self)
            
    def visit_enum_item(self, e):
        e.name.accept(self)
        if e.value is not None:
            e.value.accept(self)
            
    def visit_expr_bin(self, e):
        e.lhs.accept(self)
        e.rhs.accept(self)
        
    def visit_expr_bool(self, e):
        pass
    
    def visit_expr_compile_has(self, c):
        c.ref.accept(self)
        
    def visit_expr_cond(self, c):
        c.cond_e.accept(self)
        c.true_e.accept(self)
        c.false_e.accept(self)
        
    def visit_expr_hierarchical_id(self, e):
        for p in e.path_l:
            p.accept(self)
        
    def visit_expr_hierarchical_id_elem(self, e):
        e.name.accept(self)
        if e.lhs is not None:
            e.lhs.accept(self)
            
    def visit_expr_hierarchical_id_list(self, hid_l):
        for hid in hid_l.hid_l:
            hid.accept(self)
            
    def visit_expr_id(self, i):
        pass
        
    def visit_expr_in(self, i):
        i.lhs.accept(self)
        i.open_range_l.accept(self)
        
    def visit_expr_num_literal(self, e):
        pass
        
    def visit_expr_open_range_list(self, r : ExprOpenRangeList):
        for v in r.val_l:
            v.accept(self)
            
    def visit_expr_open_range_value(self, rv : ExprOpenRangeValue):
        rv.lhs.accept(self)
        if rv.rhs is not None:
            rv.rhs.accept(self)
            
    def visit_expr_str_literal(self, s):
        pass
    
    def visit_expr_static_ref_path(self, r:ExprStaticRefPath):
        for p in r.path:
            p.accept(self)
        
    
    def visit_expr_super_ref(self, r):
        r.ref.accept(self)
    
    def visit_expr_template_param_value_list(self, pl:ExprTemplateParamValueList):
        for pv in pl.param_l:
            pv.accept(self)
    
    def visit_expr_template_value(self, pv:ExprTemplateParamValue):
        pv.expr.accept(self)
    
    def visit_expr_var_ref_path(self, r):
        r.hid.accept(self)
        if r.lhs is not None:
            r.lhs.accept(self)
            if r.rhs is not None:
                r.rhs.accept(self)
        
    def visit_expr_unary(self, e):
        e.expr.accept(self)
        
    def visit_extend_stmt(self, e):
        e.target.accept(self)
        self.visit_composite_stmt(e)
        
    def visit_field(self, f):
        f.name.accept(self)
        
    def visit_field_attr(self, f):
        self.visit_field(f)
        f.ftype.accept(self)
        
        if f.array_dim is not None:
            f.array_dim.accept(self)
            
        if f.init_expr is not None:
            f.init_expr.accept(self)
        pass
    
    def visit_override_block(self, o):
        for s in o.statements:
            s.accept(self)
            
    def visit_override_stmt_type(self, o):
        o.target.accept(self)
        o.override.accept(self)
        
    def visit_override_stmt_inst(self, o):
        o.target.accept(self)
        o.override.accept(self)
        
    def visit_struct_type(self, s):
        self.visit_composite_type(s)
        
    def visit_buffer_type(self, s):
        self.visit_composite_type(s)
        
    def visit_stream_type(self, s):
        self.visit_composite_type(s)
        
    def visit_state_type(self, s):
        self.visit_composite_type(s)
        
    def visit_resource_type(self, r):
        self.visit_composite_type(r)
        
        
    def visit_template_param_decl_list(self, t : TemplateParamDeclList):
        for p in t.params:
            p.accept(self)
            
    def visit_template_generic_type_param_decl(self, t : TemplateGenericTypeParamDecl):
        t.name.accept(self)
        if t.default_type is not None:
            t.default_type.accept(self)
            
    def visit_template_category_type_param_decl(self, t : TemplateCategoryTypeParamDecl):
        t.name.accept(self)
        if t.type_restriction is not None:
            t.type_restriction.accept(self)
        if t.default_type is not None:
            t.default_type.accept(self)
            
    def visit_template_value_param_decl(self, t : TemplateValueParamDecl):
        t.name.accept(self)
        t.data_type.accept(self)
        if t.default_value is not None:
            t.default_value.accept(self)
        
    def visit_type_identifier(self, tid:TypeIdentifier):
        for p in tid.path:
            p.accept(self)
            
    def visit_type_identifier_elem(self, tie:TypeIdentifierElem):
        tie.ref.accept(self)
        if tie.templ_pvl is not None:
            tie.templ_pvl.accept(self)
            
    def visit_typedef(self, t : Typedef):
        t.data_type.accept(self)
        t.identifier.accept(self)

        
    def visit_import_stmt(self, i):
        i.ref.accept(self)
        
    def visit_reference(self, r):
        pass
    