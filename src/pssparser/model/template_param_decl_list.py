'''
Created on Mar 30, 2020

@author: ballance
'''
from typing import List
from pssparser.model.template_param_decl import TemplateParamDecl

class TemplateParamDeclList(object):
    
    def __init__(self, params : List[TemplateParamDecl]):
        self.params = params 
    
    def accept(self, v):
        v.visit_template_param_decl_list(self)
        