'''
Created on Feb 17, 2020

@author: ballance
'''
from antlr4.BufferedTokenStream import TokenStream
from pssparser.antlr_gen.PSSLexer import PSSLexer
from antlr4.CommonTokenStream import CommonTokenStream
from pssparser.antlr_gen.PSSParser import PSSParser
from pssparser.model.compilation_unit import CompilationUnit
from pssparser.antlr_gen.PSSVisitor import PSSVisitor
from antlr4.error.ErrorListener import ErrorListener
from pssparser.model.marker import Marker
from pssparser.model.component_type import ComponentType
from pssparser.model.package_type import PackageType
from pssparser.model.cu_type import CUType
from pssparser.model.action_type import ActionType

class CUParser(PSSVisitor, ErrorListener):
    
    def __init__(self, input_stream, filename):
        lexer = PSSLexer(input_stream)
        stream = CommonTokenStream(lexer)
        self._parser = PSSParser(stream)
#        self._parser.removeErrorListeners()
        self._parser.addErrorListener(self)
        
        self._typescope_s = []
        self._namespace = []
        self._package_m = {}
        
        cu = CUType(filename)
        self._typescope_s.append(cu)
        
    def parse(self) -> CompilationUnit:
        cu_model = self._parser.compilation_unit()
        
        cu = self._typescope_s[-1]
        
        if len(cu.markers) > 0:
            # Don't try to process with errors
            return cu
        
        cu_model.accept(self)
#         for c in cu_model.portable_stimulus_description():
#             cu_elem = c.accept(self)
#             
#             self.check_elem(cu_elem, c)
# 
#             # Don't add packages now
#             if isinstance(cu_elem, PackageType):
#                 # Add a package to the compilation unit the first we see it`
#                 if not cu_elem.name in self._package_m.keys():
#                     self._package_m[cu_elem.name] = cu_elem
#                     cu.add_child(cu_elem)
#             else:
#                 cu.add_elem(cu_elem)
        
        return cu
    
    def _get_typescope(self):
        return self._typescope_s[-1] if len(self._typescope_s) > 0 else None
    
    def visitAction_declaration(self, ctx:PSSParser.Action_declarationContext):
        ret = ActionType()
        
        return ret
    
    def visitComponent_declaration(self, ctx:PSSParser.Component_declarationContext):
        print("visitComponent_declaration")
        ret = ComponentType(self._get_typescope())
        
        self._typescope_s.append(ret)
        for c in ctx.component_body_item():
            c_elem = c.accept(self)
            self.check_elem(c_elem, c)
            ret.add_child(c_elem)
        self._typescope_s.pop()

        return ret
    
    def visitPackage_declaration(self, ctx:PSSParser.Package_declarationContext):
        print("visitPackage_declaration")
        ns = ctx.name
        
        if ns in self._package_m.keys():
            pkg = self._package_m[ns]
        else:
            pkg = PackageType(ns)
            self._package_m[ns] = pkg
        
        self._typescope_s.append(pkg)   
        for c in ctx.package_body_item():
            pkg_e = c.accept(self)
            
            self.check_elem(pkg_e, c)
            pkg.add_child(pkg_e)
            
        self._typescope_s.pop()
        
    def check_elem(self, e, t):
        if e is None:
            print()
            print("Note: Failed to elaborate a \"" + str(type(t)) + "\" " + t.getText())
#            raise Exception("Failed to elaborate a \"" + str(type(t)) + "\" " + t.getText())
    
    def syntaxError(self, recognizer, offendingSymbol, line, column, msg, e):
        self._typescope_s[-1].add_marker(Marker(line, column, msg))
        super().syntaxError(recognizer, offendingSymbol, line, column, msg, e)
        # TODO: Add error to CU output
   #     raise Exception("TODO: parse error")
    
    
        
        