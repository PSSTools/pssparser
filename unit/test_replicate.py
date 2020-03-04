'''
Created on Mar 4, 2020

@author: ballance
'''

from _io import StringIO
from unittest import TestCase 

from antlr4 import InputStream

from pssparser.cu_parser import CUParser


class TestReplicate(TestCase):
    
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
        //<example>
        component container {
        //</example>
            action my_test {
                rand int in [2..4] count;
                activity {
                    parallel {
                        replicate (count) {
                            do A;
                            do B;
                        }
                    }
                }
            };
        //<example>
        }
        //</example>
        """
        self._runTest(text, "test_example_1")

    def test_example_2(self):
        text = """
        //<example>
        component container {
        //</example>
            action my_test {
                activity {
                    schedule {
                        do A;
                        replicate (i: 4) do B with { size == i*10; };
                    }
                }
            };
        //<example>
        }
        //</example>
        """
        self._runTest(text, "test_example_2")

    def test_example_3(self):
        text = """
        //<example>
        component container {
        //</example>
            action my_compound {
                // TODO: fix example "in"
                rand int in [2..4] count;
                activity {
                    parallel {
                        replicate (count) RL[]: {
                            A a;
                            B b;
                            a;
                            b;
                        }
                    }
                    if (RL[count-1].a.x ==0) { // 'a' of the last replicate expansion
                        do C;
                    }
                }
            };
            action my_test {
                activity {
                    do my_compound with {
                    RL[0].a.x == 10; // 'a' of the first replicate expansion
                };
            }
        };
        //<example>
        }
        //</example>
        """
        self._runTest(text, "test_example_3")    


#     def test_example_4(self):
#         text = """
#         //<example>
#         component container {
#         //</example>
#             action my_test {
#                 A a;
#                 activity {
#                     schedule {
#                         replicate (4) {
#                             B b;
#                             a; // Error - traversal of action-handle 
#                                // declared outside the replicate scope
#                             b; // OK – action-handle declared inside the replicate scope
#                             L: select { // Error – label causes name conflict in expansion
#                                 do A;
#                                 do B;
#                             }
#                         }
#                     }
#                 }
#             };
#         //<example>
#         }
#         //</example>
#         """
#         self._runTest(text, "test_example_4")        
