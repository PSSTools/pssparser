'''
Created on Mar 18, 2020

@author: ballance
'''
from pssparser.model.expr_type import ExprType
from pssparser.model.expr_var_ref_path import ExprVarRefPath

class ExprSuperRef(ExprType):
    
    def __init__(self, ref : ExprVarRefPath):
        super().__init__()
        self.ref = ref

    def accept(self, v):
        v.visit_expr_super_ref(self)