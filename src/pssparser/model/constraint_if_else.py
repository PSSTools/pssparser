'''
Created on Apr 13, 2020

@author: ballance
'''

class ConstraintIfElse(object):
    
    def __init__(self, e, true_cs, false_cs):
        self.e = e
        self.true_cs = true_cs
        self.false_cs = false_cs
        
    def accept(self, v):
        v.visit_constraint_if_else(self)