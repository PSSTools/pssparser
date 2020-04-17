'''
Created on Apr 17, 2020

@author: ballance
'''

class ActivityJoinBranch(object):
    
    def __init__(self):
        self.label_identifiers = []
        
    def accept(self, v):
        v.visit_activity_join_branch(self)
        
        