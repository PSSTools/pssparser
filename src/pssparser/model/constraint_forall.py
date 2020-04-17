'''
Created on Apr 13, 2020

@author: ballance
'''

class ConstraintForall(object):
    
    def __init__(self, 
                id, 
                tid, 
                in_path,
                cs):
        self.id = id
        self.tid = tid
        self.in_path = in_path
        self.cs = cs
        
    def accept(self, v):
        v.visit_constraint_forall(self)