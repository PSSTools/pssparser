'''
Created on May 1, 2020

@author: ballance
'''
from pssparser.model.expr_id import ExprId

class CovergroupInline(object):
    
    def __init__(self,
                 name : ExprId):
        self.name = name
        self.body_items = []
        
    def accept(self, v):
        v.visit_covergroup_inline(self)