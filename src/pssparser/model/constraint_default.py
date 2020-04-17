'''
Created on Apr 13, 2020

@author: ballance
'''

class ConstraintDefault(object):
    
    def __init__(self, hid, e):
        self.hid = hid
        self.e = e
        
    def accept(self, v):
        v.visit_constraint_default(self)