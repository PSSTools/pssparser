'''
Created on Apr 13, 2020

@author: ballance
'''

class ConstraintBlock(object):
    
    def __init__(self):
        self.constraints = []
        
    def add_constraint(self, c):
        self.constraints.append(c)
        
    def accept(self, v):
        v.visit_constraint_block(self)
        
        