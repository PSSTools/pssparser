'''
Created on Mar 31, 2020

@author: ballance
'''
from syntax_test_base import SyntaxTestBase

class TestExpressions(SyntaxTestBase):
    
    def test_shift_left(self):
        text = """
        struct my_s {
            rand int a;
            rand int b;
            
            constraint a == b << 2;
        }
        """
        self._runTest(text)
        
    def test_shift_right(self):
        text = """
        struct my_s {
            rand int a;
            rand int b;
            
            constraint a == b >> 2;
        }
        """
        self._runTest(text)