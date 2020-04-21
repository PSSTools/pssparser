
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
Created on Mar 5, 2020

@author: ballance
'''

from _io import StringIO
from unittest import TestCase 

from antlr4 import InputStream

from pssparser.cu_parser import CUParser


class TestForall(TestCase):
    
    def _runTest(self, text, name):
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
    
    def test_example_1(self):
        text = """
        enum mode_e { MODE1, MODE2, MODE3, MODE4 }
        component C1 {
            action A_a {
                rand mode_e      mode;
                rand bit[3:0]    a, b;
            }
            action B_a {
                A_a    a1, a2;
                activity {
                    parallel { a1; a2; }
                }
            }
        }
        component pss_top {
            action entry {
                rand bit[3:0]    a_limit;
                C1::B_a  b;
                C1::A_a  a;
                constraint {
                    forall (a_it : C1::A_a) {
                        a_it.a <= a_limit;
                        a_it.mode in [MODE1, MODE3];
                    }
                }
                activity {
                    schedule { a; b; }
                }
            }
        }
        """
        
        self._runTest(text, "test_example_1")
        
    def test_example_2(self):
        text = """
        component pss_top {
            action entry {
                rand bit[3:0]    a_limit;
                C1::B_a  b;
                C1::A_a  a;
                constraint {
                    a.a <= a_limit;
                    a.mode in [MODE1, MODE3];
                    b.a1.a <= a_limit;
                    b.a1.a.mode in [MODE1, MODE3];
                    b.a2.a <= a_limit;
                    b.a2.a.mode in [MODE1, MODE3];
                }
                activity {
                    schedule { a; b; }
                }
            }
        }
        """
        self._runTest(text, "test_example_2")
        

    def test_example_3(self):
        text = """
        enum mode_e { MODE1, MODE2, MODE3, MODE4 }
        component C1 {
            action A_a {
                rand mode_e      mode;
                rand bit[3:0]    a, b;
            }
            action B_a {
                A_a    a1, a2;
                activity {
                    parallel { a1; a2; }
                }
            }
        }
        component pss_top {
            action entry {
                rand bit[3:0]    a_limit;
                C1::B_a  b1, b2;
                activity {
                    schedule {
                        b1; 
                        b2 with {
                            forall (a_it : C1::A_a) {
                                a_it.a <= a_limit;
                                a_it.mode in [MODE1, MODE3];
                            }
                        };
                    }
                }
            }
        }
        """
        self._runTest(text, "test_example_3")
        

    def test_example_4(self):
        text = """
        enum mode_e { MODE1, MODE2, MODE3, MODE4 }
        component C1 {
            action A_a {
                rand mode_e      mode;
                rand bit[3:0]    a, b;
            }
            action B_a {
                A_a    a1, a2;
                activity {
                    parallel { a1; a2; }
                }
            }
        }
        component pss_top {
            action entry {
                rand bit[3:0]    a_limit;
                C1::B_a  b;
                C1::A_a  a;
                constraint {
                    forall (a_it : C1::A_a) {
                        a_it.a <= a_limit;
                        a_it.mode in [MODE1, MODE3];
                    }
                }
                activity {
                    schedule { a; b; }
                }
            }
        }
        """
        self._runTest(text, "test_example_4")
        
    def test_example_5(self):
        text = """
        component pss_top {
            action entry {
                rand bit[3:0]    a_limit;
                C1::B_a  b;
                C1::A_a  a;
                activity {
                    a;
                    b;
                    do C1::B_a with {
                        forall (a_it : C1::A_a) {
                            a_it.a <= a_limit;
                            a_it.mode in [MODE1, MODE3];
                        }
                    };
                }
            }
        }
        """
        self._runTest(text, "test_example_5")
        
    def test_example_6(self):
        text = """
        component pss_top {
            action entry {
                rand bit[3:0]    a_limit;
                C1::B_a  b;
                C1::A_a  a;
                activity {
                    constraint {
                        forall (a_it : C1::A_a) {
                            a_it.a <= a_limit;
                            a_it.mode in [MODE1, MODE3];
                        }
                    }
                    a;
                    b;
                    do C1::B_a;
                }
            }
        }
        """
        self._runTest(text, "test_example_6")

    def test_example_7(self):
        text = """
        component pss_top {
            action entry {
                rand bit[3:0]    a_limit;
                C1::B_a  b;
                C1::A_a  a1, a2;
                activity {
                    if (a_limit == 0) {
                        constraint {
                            forall (a_it : C1::A_a) {
                                a_it.a > a_limit;
                                a_it.mode in [MODE1, MODE3];
                            }
                        }
                        a1;
                        do C1::B_a;
                    } else {
                        a1;
                    }
                    a2;
                }
            }
        }
        """
        self._runTest(text, "test_example_7")
        