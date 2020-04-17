'''
Created on Apr 13, 2020

@author: ballance
'''

class ConstraintForeach(object):
    
    def __init__(self, 
                it_id,
                e,
                idx_id,
                cs):
        self.it_id = it_id
        self.e = e
        self.idx_id = idx_id
        self.cs = cs
        
    def accept(self, v):
        v.visit_constraint_foreach(self)