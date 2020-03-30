'''
Created on Mar 30, 2020

@author: ballance
'''
from pssparser.model.template_param_decl import TemplateParamDecl

class TemplateValueParamDecl(TemplateParamDecl):
    
    def __init__(self, name, data_type, default_value):
        super().__init__(name)
        self.data_type = data_type
        self.default_value = default_value
        
    def accept(self, v):
        v.visit_template_value_param_decl(self)