
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
Created on Mar 13, 2020

@author: ballance
'''
from pssparser.model.reference import Reference
from pssparser.model.source_info import SourceInfo
from enum import Flag, auto

class AttrFlags(Flag):
    Default = auto() # no qualifiers
    Rand = auto()
    Const = auto()
    Static = auto()
    Protected = auto()
    Private = auto()

class AttrDeclStmt(object):
    
    def __init__(self, name, typeref : Reference, flags : AttrFlags):
        self.name = name
        self.typeref = typeref
        self.flags = flags
        self.srcinfo : SourceInfo = None

    def accept(self, v):
        v.visit_attr_decl_stmt(self)