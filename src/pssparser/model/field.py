'''
Created on Apr 20, 2020

@author: ballance
'''
from enum import Enum, auto

from pssparser.model.expr_id import ExprId
from pssparser.model.data_type import DataType


class Field(object):

    # TODO: add in protection
    def __init__(self,
                name  : ExprId):
        self.name = name
        
    