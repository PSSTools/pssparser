'''
Created on Mar 18, 2020

@author: ballance
'''
from pssparser.model.expr_id import ExprId
from pssparser.model.expr_template_param_value_list import ExprTemplateParamValueList

class TypeIdentifierElem(object):
    
    def __init__(self, ref : ExprId, templ_pvl : ExprTemplateParamValueList=None):
        super().__init__()
        self.ref = ref
        self.templ_pvl = templ_pvl
        
    def accept(self, v):
        v.visit_type_identifier_elem(self)