'''
Created on Feb 24, 2020

@author: ballance
'''

class Visitor():
    
    def _visit_type_scope(self, t):
        # Internal method
        
        for c in t.children:
            c.accept(self)
    
    def visit_action(self, a):
        self._visit_type_scope(a)
    
    def visit_package(self, p):
        
        self._visit_type_scope(p)
        pass
    
    