
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
Created on Mar 30, 2020

@author: ballance
'''
from enum import Enum, auto
from pssparser.model.data_type import DataType


class ScalarType(Enum):
    Bit = auto()
    Bool = auto()
    Chandle = auto()
    Integer = auto()
    String = auto()
    
    
class DataTypeScalar(DataType):
    
    def __init__(self, 
        scalar_type : ScalarType, 
        lhs,
        rhs,
        in_range):
        super().__init__()
        self.scalar_type = scalar_type
        self.lhs = lhs
        self.rhs = rhs
        self.in_range = in_range
        
    def accept(self, v):
        v.visit_data_type_scalar(self)
    