'''
Created on Mar 13, 2020

@author: ballance
'''
from enum import Enum, auto

from pssparser.model.composite_stmt import CompositeStmt
from pssparser.model.reference import Reference


class ExtendTarget(Enum):
    Action = auto()
    Component = auto()
    Struct = auto()
    Enum = auto()
    
class ExtendStmt(CompositeStmt):
    
    def __init__(self,
                 ext_type : ExtendTarget,
                 target : Reference):
        super().__init__()
        self.ext_type = ext_type
        self.target = target
    
    def accept(self, v):
        v.visit_extend_stmt(self)
        