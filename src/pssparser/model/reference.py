'''
Created on Mar 9, 2020

@author: ballance
'''

from typing import List, Tuple
from pssparser.model.source_info import SourceInfo

class Reference(object):
    """Captures a fully- or partially-qualified type reference"""
    
    def __init__(self, 
                 ref : Tuple[str],
                 is_global = False):
        self.ref = ref
        self.is_global = is_global # Indicates whether this is a rooted reference
        self.target = None # Pointer to a type declaration
        self.srcinfo : SourceInfo = None
        
    def get_target(self):
        if isinstance(self.target, Reference):
            return self.target.get_target()
        else:
            return self.target
        
    def qname(self) -> str:
        return "::".join(self.ref)
        
    def accept(self, v):
        v.visit_reference(self)
