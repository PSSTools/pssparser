'''
Created on Feb 17, 2020

@author: ballance
'''

class TypeScope():
    """Base for types in which types are declared"""
    
    def __init__(self, name):
        self.parent = None
        self.name = name
        self.children = []
        
    def add_child(self, c):
        if c is not None:
            c.parent = self
            c.children.append(c)
        
    def get_cu(self) -> 'CompilationUnit':
        """Returns the containing compilation unit for this typescope"""
        cu = self
        
        while cu.parent is not None:
            cu = cu.parent
            
        return cu
    
    def accept(self, v):
        raise NotImplementedError("accept not implemented for " + str(self))
        
        