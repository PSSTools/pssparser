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
            super_type : 'TypeRef',
            is_abstract = False):
        super().__init__(name, super_type)
        self.is_abstract = is_abstract
        
    def accept(self, v):
        v.visit_action(self)
        
        
    
        