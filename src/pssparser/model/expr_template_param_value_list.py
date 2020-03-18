'''
Created on Mar 18, 2020

@author: ballance
'''
from pssparser.model.expr_type import ExprType
from typing import List
from pssparser.model.expr_template_param_value import ExprTemplateParamValue

class ExprTemplateParamValueList(ExprType):
    
    def __init__(self):
        self.param_l : List[ExprTemplateParamValue] = []
        pass
    
    def accept(self, v):
        v.visit_expr_template_param_value_list(self)