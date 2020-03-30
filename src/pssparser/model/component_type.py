'''
Created on Feb 24, 2020

@author: ballance
'''
from pssparser.model.type_scope import TypeScope
from typing import Tuple
from pssparser.model.composite_type import CompositeType
from pssparser.model.type_identifier import TypeIdentifier

class ComponentType(CompositeType):
    
    def __init__(self, name : Tuple[str], template_params, super_type:TypeIdentifier):
        super().__init__(name, template_params, super_type)
        
    def accept(self, v):
        v.visit_component(self)
