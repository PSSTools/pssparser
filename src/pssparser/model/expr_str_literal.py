'''
Created on Mar 17, 2020

@author: ballance
'''
from pssparser.model.expr_type import ExprType

class ExprStrLiteral(ExprType):
    
    def __init__(self, val):
        super().__init__()
        self.val = val
        
    def accept(self, v):
        v.visit_expr_str_literal(self)
        