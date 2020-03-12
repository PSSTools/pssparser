'''
Created on Mar 9, 2020

@author: ballance
'''

from typing import List

class TypeName(object):
    """Captures the fully-qualified name of a type"""
    
    def __init__(self, name : List[str]):
        self.name = name.copy()

