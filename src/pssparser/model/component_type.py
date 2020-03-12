'''
Created on Feb 24, 2020

@author: ballance
'''
from pssparser.model.type_scope import TypeScope
from typing import Tuple
from pssparser.model.composite_type import CompositeType

class ComponentType(CompositeType):
    
    def __init__(self, name : Tuple[str], super_type):
        super().__init__(name, super_type)
        
    def accept(self, v):
        v.visit_component(self)
