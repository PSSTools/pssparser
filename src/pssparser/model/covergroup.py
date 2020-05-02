'''
Created on May 1, 2020

@author: ballance
'''
from pssparser.model.expr_id import ExprId

class Covergroup(object):
    
    def __init__(self,
                 name : ExprId):
        self.ports = []
        self.body_items = []
        
    def accept(self, v):
        v.visit_covergroup(self)