'''
Created on Mar 18, 2020

@author: ballance
'''
from pssparser.model.expr_type import ExprType

class ExprBoolLiteral(ExprType):
    
    def __init__(self, v):
        super().__init__()
        self.val = v
        
    def accept(self, v):
        v.visit_expr_bool_literal(self)
        