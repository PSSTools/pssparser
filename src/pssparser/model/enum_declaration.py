'''
Created on Mar 30, 2020

@author: ballance
'''

class EnumDeclaration(object):
    
    def __init__(self, name, enumerators):
        self.name = name
        self.enumerators = enumerators
        
    def accept(self, v):
        v.visit_enum_declaration(self)