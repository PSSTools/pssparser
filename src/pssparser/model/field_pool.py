'''
Created on Apr 21, 2020

@author: ballance
'''
from pssparser.model.field import Field
from pssparser.model.expr_id import ExprId
from pssparser.model.type_identifier import TypeIdentifier
from pssparser.model.expr_type import ExprType

class FieldPool(Field):
    
    def __init__(self, 
                name : ExprId, 
                typeid : TypeIdentifier,
                size : ExprType):
        super().__init__(name)
        self.typeid = typeid
        self.size = size
        
    def accept(self, v):
        v.visit_field_pool(self)
        