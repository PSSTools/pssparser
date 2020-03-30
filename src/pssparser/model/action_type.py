'''
Created on Feb 24, 2020

@author: ballance
'''
from typing import Tuple
from pssparser.model.type_scope import TypeScope
from pssparser.model.composite_type import CompositeType

class ActionType(CompositeType):
    
    def __init__(
            self, 
            name : Tuple[str], 
            is_abstract,
            template_params,
            super_type):
        super().__init__(name, template_params, super_type)
        self.is_abstract = is_abstract
        
    def accept(self, v):
        v.visit_action(self)
        
        
    
        