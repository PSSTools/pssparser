'''
Created on Mar 18, 2020

@author: ballance
'''
from pssparser.model.expr_type import ExprType

class ExprCompileHas(ExprType):
    
    def __init__(self, ref):
        super().__init__()
        self.ref = ref
        
    def accept(self, v):
        v.visit_expr_compile_has(self)
        