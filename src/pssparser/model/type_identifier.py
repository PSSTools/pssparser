'''
Created on Mar 18, 2020

@author: ballance
'''
from typing import List
from pssparser.model.type_identifier_elem import TypeIdentifierElem

class TypeIdentifier(object):
    
    def __init__(self, is_global):
        super().__init__()
        self.is_global = is_global
        self.path : List[TypeIdentifierElem] = []
        self.target = None
        
    def __str__(self):
        return "::".join(map(lambda e:e.ref.id, self.path))
        
    def accept(self, v):
        v.visit_type_identifier(self)