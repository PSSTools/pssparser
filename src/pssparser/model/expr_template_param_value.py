'''
Created on Mar 18, 2020

@author: ballance
'''
from pssparser.model.expr_type import ExprType

class ExprTemplateParamValue(ExprType):
    
    def __init__(self, is_value, expr):
        super().__init__()
        self.is_value = is_value
        self.expr = expr
        
    def accept(self, v):
        v.visit_expr_template_param_value(self)