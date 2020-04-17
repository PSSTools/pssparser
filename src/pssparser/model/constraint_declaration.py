'''
Created on Apr 13, 2020

@author: ballance
'''
from pssparser.model.constraint_block import ConstraintBlock


class ConstraintDeclaration(ConstraintBlock):
    
    def __init__(self, name, is_dynamic):
        super().__init__()
        self.name = name
        self.is_dynamic = is_dynamic
        
    def accept(self, v):
        v.visit_constraint_declaration(self)
    