
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
Created on Mar 9, 2020

@author: ballance
'''
from _io import StringIO
import sys
from unittest.case import TestCase

from antlr4 import InputStream

from pssparser.cu_parser import CUParser


class SyntaxTestBase(TestCase):

    def _runTest(self, text):
        name = self._testMethodName
        input_stream = InputStream(text)
        parser = CUParser(input_stream, name)
        cu = parser.parse()
        
        if len(cu.markers) > 0:
            print("Test Failed:")
            in_reader = StringIO(text)
            i=1
            while True:
                line = in_reader.readline()
                if line == "":
                    break
                line = line[:-1]
                print("%3d: %s" % (i, line))
                i+=1
        
        self.assertEqual(len(cu.markers), 0, "Errors")
        
    def setUp(self):
        super().setUp()
        print("--> " + self._testMethodName + "********************************")
        sys.stdout.flush()
        
    def tearDown(self):
        print("<-- " + self._testMethodName + "********************************")
        sys.stdout.flush()
        super().tearDown()
        
    
