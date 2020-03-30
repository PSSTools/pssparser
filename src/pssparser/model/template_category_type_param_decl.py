'''
Created on Mar 30, 2020

@author: ballance
'''
from enum import Enum, auto
from pssparser.model.template_param_decl import TemplateParamDecl
from pssparser.model.expr_id import ExprId
from pssparser.model.type_identifier import TypeIdentifier

class TemplateTypeCategory(Enum):
    Action = auto()
    Component = auto()
    Struct = auto()
    Buffer = auto()
    Stream = auto()
    State = auto()
    Resource = auto()

class TemplateCategoryTypeParamDecl(TemplateParamDecl):
    
    def __init__(self, 
                 name : ExprId,
                 category : TemplateTypeCategory,
                 type_restriction : TypeIdentifier,
                 default_type : TypeIdentifier ):
        super().__init__(name)
        self.category = category
        self.type_restriction = type_restriction
        self.default_type = default_type
        
    def accept(self, v):
        v.visit_template_category_type_param_decl(self)