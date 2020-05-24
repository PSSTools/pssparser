'''
Created on Apr 26, 2020

@author: ballance
'''
from pssparser.model.expr_type import ExprType
from pssparser.model.expr_hierarchical_id import ExprHierarchicalId

class ExprFunctionCall(ExprType):
    
    def __init__(self, name : ExprHierarchicalId, params=None):
        self.name = name
        if params is None:
            self.params = []
        else:
            self.params = params
        
    def accept(self, v):
        v.visit_expr_function_call(self)