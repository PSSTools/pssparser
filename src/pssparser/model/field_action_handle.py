'''
Created on May 1, 2020

@author: ballance
'''
from pssparser.model.field import Field
from pssparser.model.type_identifier import TypeIdentifier
from pssparser.model.expr_id import ExprId
from pssparser.model.expr_type import ExprType

class FieldActionHandle(Field):
    
    def __init__(self,
                 name : ExprId,
                 action_type : TypeIdentifier,
                 array_dim : ExprType):
        super().__init__(name)
        self.action_type = action_type
        self.array_dim = array_dim
        
    def accept(self, v):
        v.visit_field_action_handle(self)