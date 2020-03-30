'''
Created on Mar 30, 2020

@author: ballance
'''
from pssparser.model.expr_id import ExprId

class TemplateParamDecl(object):
    
    def __init__(self, name : ExprId):
        self.name = name
        