'''
Created on Mar 9, 2020

@author: ballance
'''
from pssparser.model.type_model_visitor import TypeModelVisitor
from enum import Enum, auto
from typing import Set

class TypeCategory(Enum):
    Action = auto()
    Component = auto()
    Struct = auto()

class FindTypesVisitor(TypeModelVisitor):
    
    def __init__(self, types : Set[TypeCategory]):
        self.types = types
        self.type_l = []
        
    def visit_action(self, a):
        if len(self.types) == 0 or TypeCategory.Action in self.types:
            self.type_l.append(a)
        super().visit_action(a)
        
    def visit_component(self, c):
        if len(self.types) == 0 or TypeCategory.Component in self.types:
            self.type_l.append(c)
        super().visit_component(c)
        
            
            