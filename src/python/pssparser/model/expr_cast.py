'''
Created on Apr 26, 2020

@author: ballance
'''
from pssparser.model.expr_type import ExprType

class ExprCast(ExprType):
    
    def __init__(self, casting_type, expr):
        self.casting_type = casting_type
        self.expr = expr
        
    def accept(self, v):
        v.visit_expr_cast(self)
        