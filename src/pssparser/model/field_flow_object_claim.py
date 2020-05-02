'''
Created on May 1, 2020

@author: ballance
'''
from pssparser.model.field import Field
from pssparser.model.type_identifier import TypeIdentifier
from pssparser.model.expr_id import ExprId
from pssparser.model.expr_type import ExprType

class FieldFlowObjectClaim(Field):
    
    def __init__(
            self,
            name : ExprId,
            is_input : bool,
            flow_object_type : TypeIdentifier,
            array_dim : ExprType
            ):
        super().__init__(name)
        self.is_input = is_input
        self.flow_object_type = flow_object_type
        self.array_dim = array_dim
    
    def accept(self, v):
        v.visit_field_flow_object_claim(self)