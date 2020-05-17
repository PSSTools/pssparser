'''
Created on May 1, 2020

@author: ballance
'''
from pssparser.model.field import Field
from pssparser.model.expr_id import ExprId
from pssparser.model.type_identifier import TypeIdentifier
from pssparser.model.expr_type import ExprType
from pssparser.model.field_composite import FieldComposite


class FieldResourceClaim(FieldComposite):
    
    def __init__(self,
                 name : ExprId,
                 is_lock : bool,
                 resource_object_type : TypeIdentifier,
                 array_dim : ExprType):
        super().__init__(name, resource_object_type)
        self.is_lock = is_lock
        self.array_dim = array_dim
        
    def accept(self, v):
        v.visit_field_resource_claim(self)