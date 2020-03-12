'''
Created on Mar 9, 2020

@author: ballance
'''

class TypeModelVisitor(object):
    pass

    def visit_type_scope(self, t):
        for t in t.types:
            t.accept(self)
            
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
    
    def visit_compilation_unit(self, cu):
#        for n,p in cu.package_m.items():
#            p.accept(self)

        self.visit_composite_type(cu)
    
    def visit_component(self, c):
        self.visit_composite_type(c)
    