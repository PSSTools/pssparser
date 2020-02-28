'''
Created on Feb 24, 2020

@author: ballance
'''
from pssparser.model.type_scope import TypeScope

class ComponentType(TypeScope):
    
    def __init__(self, parent):
        super().__init__(parent)
