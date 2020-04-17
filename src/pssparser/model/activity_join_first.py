'''
Created on Apr 17, 2020

@author: ballance
'''

class ActivityJoinFirst(object):
    
    def __init__(self, e):
        self.e = e
        
    def accept(self, v):
        v.visit_activity_join_first(self)
        
        