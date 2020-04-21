'''
Created on Apr 20, 2020

@author: ballance
'''
from enum import Flag, auto

from pssparser.model.data_type import DataType
from pssparser.model.expr_id import ExprId
from pssparser.model.expr_type import ExprType
from pssparser.model.field import Field


class FieldAttrFlags(Flag):
    Static = auto()
    Const = auto()
    Rand = auto()
    

class FieldAttr(Field):
    
    def __init__(self,
                name : ExprId,
                flags : FieldAttrFlags,
                is_rand : bool,
                ftype : DataType,
                array_dim : ExprType,
                init_expr : ExprType):
        super().__init__(name)
        self.flags = flags
        self.is_rand = is_rand
        self.ftype = ftype
        self.array_dim = array_dim
        self.init_expr = init_expr

    def accept(self, v):
        v.visit_field_attr(self)
        