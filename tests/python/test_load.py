'''
Created on Mar 24, 2021

@author: mballance
'''
from unittest.case import TestCase

class TestLoad(TestCase):
    
    def test_smoke(self):
        import pssparser
        
        marker_l = pssparser.core.BaseMarkerListener()

        pssparser.core.doit(2)