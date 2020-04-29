'''
Created on Apr 26, 2020

@author: ballance
'''
from pssparser.model.expr_type import ExprType

class ExprMethodCall(ExprType):
    
    def __init__(self, hid, params=None):
        self.hid = hid
        self.params = [] if params is None else params
        
    def accept(self, v):
        v.visit_expr_method_call(self)