'''
Created on May 3, 2020

@author: ballance
'''
from pssparser.model.expr_id import ExprId
from pssparser.model.expr_type import ExprType

class ComponentPathElem(object):
    
    def __init__(self, 
                 is_wildcard : bool,
                 elem : ExprId,
                 index : ExprType):
        self.is_wildcard = is_wildcard
        self.elem = elem
        self.index = index
        
    def accept(self, v):
        v.visit_component_path_elem(self)
