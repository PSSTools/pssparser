'''
Created on Mar 13, 2020

@author: ballance
'''

class SourceInfo(object):
    
    def __init__(self, fileid, lineno, linepos):
        self.fileid = fileid
        self.lineno = lineno
        self.linepos = linepos
        