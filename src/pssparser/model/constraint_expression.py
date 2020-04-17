'''
Created on Apr 13, 2020

@author: ballance
'''

class ConstraintExpression(object):
    
    def __init__(self, e):
        self.e = e
        
    def accept(self, v):
        v.visit_constraint_expression(self)