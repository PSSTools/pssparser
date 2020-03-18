'''
Created on Mar 17, 2020

@author: ballance
'''
from pssparser.model.expr_type import ExprType

class ExprCondType(ExprType):
    
    def __init__(self, cond_e, true_e, false_e):
        self.cond_e = cond_e
        self.true_e = true_e
        self.false_e = false_e
        
    def accept(self, v):
        v.visit_expr_cond(self)