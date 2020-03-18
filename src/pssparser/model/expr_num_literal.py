'''
Created on Mar 17, 2020

@author: ballance
'''
from pssparser.model.expr_type import ExprType

class ExprNumLiteral(ExprType):
    
    def __init__(self, val, img):
        super().__init__()
        self.val = val
        self.img = img
    