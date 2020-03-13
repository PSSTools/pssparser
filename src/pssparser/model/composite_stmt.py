'''
Created on Mar 13, 2020

@author: ballance
'''
from pssparser.model.StmtBase import StmtBase

class CompositeStmt(StmtBase):
    
    def __init__(self):
        super().__init__()
        self.children = []
        
    def add_child(self, c):
        self.children.append(c)
        