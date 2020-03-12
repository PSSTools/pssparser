'''
Created on Mar 9, 2020

@author: ballance
'''

class TypeDecl(object):
    """Stores a reference to a type declared in a CU"""
    
    def __init__(self, 
                 name : [str], 
                 ref):
        self.name = name
        self.ref = ref
        
    def get_target(self):
        return self.ref
        
    