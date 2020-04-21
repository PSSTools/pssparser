'''
Created on Apr 20, 2020

@author: ballance
'''
from pssparser.model.type_identifier import TypeIdentifier

class OverrideStmtType(object):
    
    def __init__(self, 
                 target : TypeIdentifier,
                 override : TypeIdentifier):
        self.target = target
        self.override = override
        
    def accept(self, v):
        v.visit_override_stmt_type(self)
        