'''
Created on Mar 18, 2020

@author: ballance
'''
from pssparser.model.expr_type import ExprType
from pssparser.model.expr_id import ExprId
from pssparser.model.expr_template_param_value_list import ExprTemplateParamValueList

class ExprStaticRefPathElem(ExprType):
    
    def __init__(self, id : ExprId, templ:ExprTemplateParamValueList=None):
        self.id = id
        self.templ_param_values = templ