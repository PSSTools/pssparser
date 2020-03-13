'''
Created on Feb 17, 2020

@author: ballance
'''
from typing import List, Tuple

from antlr4.BufferedTokenStream import TokenStream
from antlr4.CommonTokenStream import CommonTokenStream
from antlr4.error.ErrorListener import ErrorListener
from antlr4.tree.Tree import TerminalNodeImpl

from pssparser.antlr_gen.PSSLexer import PSSLexer
from pssparser.antlr_gen.PSSParser import PSSParser
from pssparser.antlr_gen.PSSVisitor import PSSVisitor
from pssparser.model.action_type import ActionType
from pssparser.model.compilation_unit import CompilationUnit
from pssparser.model.component_type import ComponentType
from pssparser.model.cu_type import CUType
from pssparser.model.extend_stmt import ExtendStmt, ExtendTarget
from pssparser.model.import_stmt import ImportStmt
from pssparser.model.marker import Marker
from pssparser.model.package_type import PackageType
from pssparser.model.reference import Reference
from pssparser.model.source_info import SourceInfo
from pssparser.model.attr_decl_stmt import AttrFlags


class CUParser(PSSVisitor, ErrorListener):
    
    class ScopeTracker(object):
        def __init__(self, parser, name, scope):
            self.parser = parser
            self.name = name
            self.scope = scope
            
        def __enter__(self):
            self.parser._enter_type_scope(self.name, self.scope)
        
        def __exit__(self, t, v, tb):
            self.parser._leave_type_scope(self.name, self.scope)
    
    def __init__(self, input_stream, filename):
        lexer = PSSLexer(input_stream)
        stream = CommonTokenStream(lexer)
        self._parser = PSSParser(stream)
#        self._parser.removeErrorListeners()
        self._parser.addErrorListener(self)

        self._scope_s : List['CompositeType'] = []
        self._namespace_s : List[str] = []
        self._package_m : Dict[str, PackageType] = {}
        self._attr_flags_s : List[AttrFlags] = []
        
        cu = CUType(filename)
        self._scope_s.append(cu)
        
    def _typescope(self, name, scope):
        return CUParser.ScopeTracker(self, name, scope)
        
    def parse(self) -> CompilationUnit:
        cu_model = self._parser.compilation_unit()
        
        cu = self._scope_s[-1]
        
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
        
        if ctx.action_super_spec() is not None:
            super_spec = ctx.action_super_spec()
            super_type = self._typeid2reference(super_spec.type_identifier())
        else:
            super_type = None

        name = ctx.action_identifier()
        ret = ActionType(
            self._get_type_qname(name),
            super_type)
        self._set_srcinfo(ret, ctx.start)
        
        with self._typescope(name, ret):
            for i in ctx.action_body_item():
                a_elem = i.accept(self)
                
                if a_elem is not None:
                    ret.add_child(a_elem)
        
        return ret
    
    def visitComponent_declaration(self, ctx:PSSParser.Component_declarationContext):
        print("visitComponent_declaration")
        
        if ctx.component_super_spec() is not None:
            super_spec = ctx.component_super_spec()
            super_type = self._typeid2reference(super_spec.type_identifier())
        else:
            super_type = None

        name = ctx.component_identifier()        
        ret = ComponentType(
            self._get_type_qname(name),
            super_type)

        self._set_srcinfo(ret, ctx.start)
        
        self._scope_s[-1].add_child(ret)
        
        with self._typescope(name, ret):
            for c in ctx.component_body_item():
                c_elem = c.accept(self)
                self.check_elem(c_elem, c)
                ret.add_child(c_elem)

        return ret
   
    def visitConst_data_declaration(self, ctx:PSSParser.Const_data_declarationContext):
        pass

    def visitConst_field_declaration(self, ctx:PSSParser.Const_field_declarationContext):
        self._attr_flags_s.append(AttrFlags.Const)
        ctx.const_data_declaration().accept(self)
        self._attr_flags_s.pop()
        
    def visitStatic_const_field_declaration(self, ctx:PSSParser.Static_const_field_declarationContext):
        self._attr_flags_s.append(AttrFlags.Static)
        self._attr_flags_s.append(AttrFlags.Const)
        ctx.const_data_declaration().accept(self)
        self._attr_flags_s.pop()
        self._attr_flags_s.pop()
        
    
    def visitExtend_stmt(self, ctx:PSSParser.Extend_stmtContext):

        if ctx.ext_type is None:
            ext_type = ExtendTarget.Struct
        else:
            ext_type = {
                "action" : ExtendTarget.Action,
                "component" : ExtendTarget.Component,
                "enum" : ExtendTarget.Enum}[ctx.ext_type.text]

        ext = ExtendStmt(
            ext_type,
            self._typeid2reference(ctx.type_identifier())
            )
        
        self._scope_s[-1].add_child(ext)
        self._scope_s.append(ext)
        # TODO: we may need to treat action/component extend and enum extend differently

        if ext_type == ExtendTarget.Action:
            for it in ctx.action_body_item():
                it.accept(self)
        elif ext_type == ExtendTarget.Component:
            for it in ctx.component_body_item():
                it.accept(self)
        elif ext_type == ExtendTarget.Struct:
            for it in ctx.struct_body_item():
                it.accept(self)
        else:
            print("TODO: handle extend enum")
            
        self._scope_s.pop()
        
        return ext
    
    def visitImport_stmt(self, ctx:PSSParser.Import_stmtContext):
        
        imp = ImportStmt(
            self._typeid2reference(
                ctx.package_import_pattern().type_identifier()),
            ctx.package_import_pattern().wildcard
            )
        self._set_srcinfo(imp, ctx.start)
        
        self._scope_s[-1].add_child(imp)

        return PSSVisitor.visitImport_stmt(self, ctx)
    
    def visitPackage_declaration(self, ctx:PSSParser.Package_declarationContext):
        cu = self._scope_s[-1]
        pkg_name = self._identifier2str(ctx.name.identifier())

        # Note: package doesn't have a source location associated
        # with it, because we combine content from multiple package statements
        if pkg_name in cu.package_m.keys():
            pkg = self.package_m[pkg_name]
        else:
            pkg = PackageType((pkg_name,))
            cu.package_m[pkg_name] = pkg
            cu.add_child(pkg)
        
        with self._typescope(ctx.name, pkg):
            for c in ctx.package_body_item():
                c.accept(self)
            
        
    def check_elem(self, e, t):
        pass
#        if e is None:
#            print()
#            print("Note: Failed to elaborate a \"" + str(type(t)) + "\" " + t.getText())
#            raise Exception("Failed to elaborate a \"" + str(type(t)) + "\" " + t.getText())
    
    def syntaxError(self, recognizer, offendingSymbol, line, column, msg, e):
        self._scope_s[-1].add_marker(Marker(line, column, msg))
        super().syntaxError(recognizer, offendingSymbol, line, column, msg, e)
        # TODO: Add error to CU output
   #     raise Exception("TODO: parse error")

    def _enter_type_scope(self, name, scope):
        if hasattr(name, "identifier"):
            name = name.identifier().ID().getText()
            
        self._namespace_s.append(name)
        if scope is not None:
            self._scope_s.append(scope)
        
    def _leave_type_scope(self, name, scope):
        e = self._namespace_s.pop()
#        if e != name:
#            raise Exception("Type-scope mismatch: leaving scope \"" + e + "\", but expect to leave scope \"" + name + "\"")
        if scope is not None:
            self._scope_s.pop()
        
    def _get_type_qname(self, name : str) -> Tuple[str]:
        """Returns a qualified type name"""
        if hasattr(name, "identifier"):
            name = name.identifier().ID().getText()
            
        ret = self._namespace_s.copy()
        ret.append(name)
        
        return tuple(ret)
    
    def _type_identifier2tuple(self, ti : PSSParser.Type_identifierContext):
        ret = []
        for elem in ti.type_identifier_elem():
            ret.append(elem.identifier().ID().getText())
            
        return tuple(ret)
    
    def _identifier2str(self, id : PSSParser.IdentifierContext):
        return id.ID().getText()
    
    def _set_srcinfo(self, obj, tok):
        print("srcinfo: " + str(tok.line) + ":" + str(tok.column))
        obj.srcinfo = SourceInfo(-1, tok.line, tok.column)
        
    def _typeid2reference(self, ti : PSSParser.Type_identifierContext):
        ref = []
        for elem in ti.type_identifier_elem():
            ref.append(elem.identifier().ID().getText())
            
        ret = Reference(tuple(ref), ti.is_global is not None)
        self._set_srcinfo(ret, ti.start)
            
        return ret
    
    def _get_attr_flags(self):
        
        flags = AttrFlags.Default
        
        # TODO: move back through the stack and aggregate flags
        
        return flags
        
