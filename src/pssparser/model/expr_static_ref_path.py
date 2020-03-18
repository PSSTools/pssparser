'''
Created on Mar 18, 2020

@author: ballance
'''
from pssparser.model.expr_type import ExprType
from typing import List
from pssparser.model.expr_static_ref_path_elem import ExprStaticRefPathElem

class ExprStaticRefPath(ExprType):
    
    def __init__(self, is_rooted:bool, path : List[ExprStaticRefPathElem]=None):
        self.is_rooted = is_rooted
        self.path = path if path is not None else []

    def accept(self, v):
        v.visit_expr_static_ref_path(self)