'''
Created on Mar 9, 2020

@author: ballance
'''
from pssparser.model.attr_decl_stmt import AttrDeclStmt

class TypeModelVisitor(object):
    pass

    def visit_type_scope(self, t):
        pass
            
    def visit_composite_type(self, t):
        if t.super_type is not None:
            t.super_type.accept(self)
            
        self.visit_type_scope(t)
        
        for c in t.children:
            c.accept(self)

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
    
    def visit_component(self, c):
        self.visit_composite_type(c)
        
    def visit_composite_stmt(self, c):
        for ch in c.children:
            ch.accept(self)
        
    def visit_extend_stmt(self, e):
        e.target.accept(self)
        self.visit_composite_stmt(e)
        
        
    def visit_import_stmt(self, i):
        i.ref.accept(self)
        
    def visit_reference(self, r):
        pass
    