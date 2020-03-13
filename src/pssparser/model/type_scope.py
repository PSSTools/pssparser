'''
Created on Feb 17, 2020

@author: ballance
'''
from typing import Tuple

class TypeScope(object):
    """Base for types in which types are declared"""
    
    def __init__(self, name : Tuple[str]):
        self.parent = None
        self.name = name
        self.imports = []
        
    def add_import(self, imp):
        self.imports.append(imp)
        
    def qname(self) -> str:
        return "::".join(self.name)
        
    def get_cu(self) -> 'CompilationUnit':
        """Returns the containing compilation unit for this typescope"""
        cu = self
        
        while cu.parent is not None:
            cu = cu.parent
            
        return cu
    
    def accept(self, v):
        raise NotImplementedError("accept not implemented for " + str(self))
        
        