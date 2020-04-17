'''
Created on Apr 17, 2020

@author: ballance
'''

class ActivityJoinNone(object):
    
    def __init__(self):
        pass
    
    def accept(self, v):
        v.visit_activity_join_none(self)