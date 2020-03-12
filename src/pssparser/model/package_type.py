'''
Created on Feb 17, 2020

@author: ballance
'''
from pssparser.model.type_scope import TypeScope
from typing import Tuple
from pssparser.model.composite_type import CompositeType

class PackageType(CompositeType):
    
    def __init__(self, name : Tuple[str]):
        super().__init__(name, None)
        
    def accept(self, v):
        v.visit_package(self)
        
