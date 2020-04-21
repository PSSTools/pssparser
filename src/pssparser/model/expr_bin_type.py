
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
Created on Mar 17, 2020

@author: ballance
'''
from enum import Enum, auto

from pssparser.model.expr_type import ExprType


class ExprBinOp(Enum):
    LogOr = auto()
    LogAnd = auto()
    BinOr = auto()
    BinXor = auto()
    BinAnd = auto()
    LT = auto()
    LE = auto()
    GT = auto()
    GE = auto()
    Exp = auto()
    Mul = auto()
    Div = auto()
    Mod = auto()
    Add = auto()
    Sub = auto()
    Sll = auto()
    Srl = auto()
    EqEq = auto()
    Neq = auto()
    
    
class ExprBinType(ExprType):
    
    def __init__(self, 
                 lhs : ExprType, 
                 op : ExprBinOp, 
                 rhs : ExprType):
        super().__init__()
        self.lhs = lhs
        self.op = op
        self.rhs = rhs
        
    def accept(self, v):
        v.visit_expr_bin(self)