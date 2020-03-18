'''
Created on Mar 17, 2020

@author: ballance
'''
from pssparser.model.expr_type import ExprType

class ExprOpenRangeList(ExprType):
    
    def __init__(self, val_l = None):
        super().__init__()
        self.val_l = val_l if val_l is not None else []

    def accept(self, v):
        v.visit_expr_open_range_list(self)
