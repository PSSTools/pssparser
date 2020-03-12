'''
Created on Mar 9, 2020

@author: ballance
'''
from typing import Tuple
from pssparser.model.type_scope import TypeScope

class CompositeType(TypeScope):
    
    def __init__(self, name : Tuple[str], super_type):
        super().__init__(name)
        self.super_type = super_type
        self.children = []
        
    def add_child(self, c):
        if c is not None:
            c.parent = self
            self.children.append(c)
            
        
