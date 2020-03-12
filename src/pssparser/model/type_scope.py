'''
Created on Feb 17, 2020

@author: ballance
'''

class TypeScope(object):
    """Base for types in which types are declared"""
    
    def __init__(self, name):
        self.parent = None
        self.name = name
        self.types = []
        self.imports = []
        
    def add_type(self, c):
        if c is not None:
            c.parent = self
            c.types.append(c)
            
    def add_import(self, imp):
        self.imports.append(imp)
        
    def get_cu(self) -> 'CompilationUnit':
        """Returns the containing compilation unit for this typescope"""
        cu = self
        
        while cu.parent is not None:
            cu = cu.parent
            
        return cu
    
    def accept(self, v):
        raise NotImplementedError("accept not implemented for " + str(self))
        
        