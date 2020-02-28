'''
Created on Feb 17, 2020

@author: ballance
'''
from pssparser.model.type_scope import TypeScope

class PackageType(TypeScope):
    
    def __init__(self, parent):
        super().__init__(parent)
        
    def accept(self, v):
        v.visit_package(self)
        
