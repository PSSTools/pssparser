'''
Created on Apr 13, 2020

@author: ballance
'''

class ConstraintImplies(object):
    
    def __init__(self, e, cs):
        self.e = e
        self.cs = cs
        
    def accept(self, v):
        v.visit_constraint_implies(self)