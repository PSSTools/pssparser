'''
Created on Mar 13, 2020

@author: ballance
'''
from pssparser.model.reference import Reference
from pssparser.model.source_info import SourceInfo
from enum import Flag, auto

class AttrFlags(Flag):
    Rand = auto()
    Protected = auto()
    Private = auto()

class AttrType(object):
    
    def __init__(self, name, typeref : Reference, flags : AttrFlags):
        self.name = name
        self.typeref = typeref
        self.flags = flags
        self.srcinfo : SourceInfo = None

    def accept(self, v):
        v.visit_attr(self)