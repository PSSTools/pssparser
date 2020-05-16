'''
Created on May 1, 2020

@author: ballance
'''
from pssparser.model.field import Field
from pssparser.model.type_identifier import TypeIdentifier
from pssparser.model.expr_id import ExprId
from pssparser.model.expr_type import ExprType
from pssparser.model.field_composite import FieldComposite

class FieldFlowObjectClaim(FieldComposite):
    
    def __init__(
            self,
            name : ExprId,
            is_input : bool,
            flow_object_type : TypeIdentifier,
            array_dim : ExprType
            ):
        super().__init__(name, flow_object_type)
        self.is_input = is_input
        self.array_dim = array_dim
        
    def accept(self, v):
        v.visit_field_flow_object_claim(self)