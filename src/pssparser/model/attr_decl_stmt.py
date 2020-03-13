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