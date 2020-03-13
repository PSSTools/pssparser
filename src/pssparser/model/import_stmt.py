'''
Created on Mar 9, 2020

@author: ballance
'''

from pssparser.model.reference import Reference
from pssparser.model.StmtBase import StmtBase


class ImportStmt(StmtBase):
    
    def __init__(self, 
                 ref : Reference,
                 is_wildcard : bool):
        super().__init__()
        self.ref = ref
        self.is_wildcard = is_wildcard

    def accept(self, v):
        v.visit_import_stmt(self)
        