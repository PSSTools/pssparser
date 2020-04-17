'''
Created on Apr 13, 2020

@author: ballance
'''

class ConstraintUnique(object):
    
    def __init__(self, hid_l):
        self.hid_l = hid_l
        
    def accept(self, v):
        v.visit_constraint_unique(self)