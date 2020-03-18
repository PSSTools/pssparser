'''
Created on Mar 18, 2020

@author: ballance
'''
from pssparser.model.expr_type import ExprType
from pssparser.model.expr_open_range_list import ExprOpenRangeList

class ExprIn(ExprType):
    
    def __init__(self, lhs : ExprType, orl : ExprOpenRangeList):
        super().__init__()
        self.lhs = lhs
        self.open_range_l = orl
        
    def accept(self, v):
        v.visit_expr_in(self)