'''
Created on Mar 17, 2020

@author: ballance
'''
from pssparser.model.expr_type import ExprType

class ExprOpenRangeValue(ExprType):
    
    def __init__(self, lhs, rhs):
        super().__init__()
        self.lhs = lhs
        self.rhs = rhs
        
    def accept(self, v):
        v.visit_expr_open_range_value(self)