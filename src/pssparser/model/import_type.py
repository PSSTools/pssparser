'''
Created on Mar 9, 2020

@author: ballance
'''
from typing import Tuple
from pssparser.model.type_ref import TypeRef

class ImportType(object):
    
    def __init__(self, name : Tuple[str], is_wildcard : bool):
        self.ref = TypeRef(name)
        self.is_wildcard = is_wildcard