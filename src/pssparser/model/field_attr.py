from pssparser.model.data_type_user import DataTypeUser
from pssparser.model.component_type import ComponentType

# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#  http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.

'''
Created on Apr 20, 2020

@author: ballance
'''
from enum import Flag, auto, IntFlag

from pssparser.model.data_type import DataType
from pssparser.model.expr_id import ExprId
from pssparser.model.expr_type import ExprType
from pssparser.model.field import Field


class FieldAttrFlags(IntFlag):
    Builtin = auto()
    Static = auto()
    Const = auto()
    Rand = auto()
    Action = auto()
    Component = auto()
    CompHndl = auto()
    

class FieldAttr(Field):
    
    def __init__(self,
                name : ExprId,
                flags : FieldAttrFlags,
                ftype : DataType,
                array_dim : ExprType,
                init_expr : ExprType):
        super().__init__(name)
        self.flags = flags
        self.ftype = ftype
        self.array_dim = array_dim
        self.init_expr = init_expr

    @property        
    def children(self):
        if isinstance(self.ftype, DataTypeUser):
            return self.ftype.tid.target.children 
        else:
            return []

    def accept(self, v):
        v.visit_field_attr(self)
        