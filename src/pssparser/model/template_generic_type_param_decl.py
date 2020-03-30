'''
Created on Mar 30, 2020

@author: ballance
'''
from pssparser.model.template_param_decl import TemplateParamDecl
from pssparser.model.reference import Reference
from pssparser.model.expr_id import ExprId
from pssparser.model.type_identifier import TypeIdentifier

class TemplateGenericTypeParamDecl(TemplateParamDecl):
    
    def __init__(self, name : ExprId, default_type : TypeIdentifier):
        super().__init__(name)
        self.default_type = default_type
    
    
    def accept(self, v):
        v.visit_template_generic_type_param_decl(self)
        