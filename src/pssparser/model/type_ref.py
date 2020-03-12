'''
Created on Mar 9, 2020

@author: ballance
'''

from typing import List

class TypeRef(object):
    """Captures a fully- or partially-qualified type reference"""
    
    def __init__(self, 
                 ref : List[str]):
        self.ref = ref
        self.decl : 'TypeDecl' = None # Pointer to a type declaration
        
    def get_target(self):
        if self.ref is not None:
            return self.target.get_target()
        else:
            return None
        