
cimport pssparser.pssast as ast
cimport ciostream

cdef class Factory(object):
    def __init__(self):
        self._hndl = NULL
        pass

    cpdef AstBuilder mkAstBuilder(self):
        return AstBuilder.mk(self._hndl.mkAstBuilder())
        pass

    @staticmethod
    cdef Factory inst():
        global _factoryInst
        if _factoryInst is None:
            print("TODO: must create factory")
            pass
        pass

    @staticmethod
    def inst():
        global _factoryInst
        if _factoryInst is None:
            print("TODO: must create factory")
            _factoryInst = Factory()
            pass
        print("static")

cdef class AstBuilder(object):

    def __dealloc__(self):
        del self._hndl

    cpdef build(self,
        ast.GlobalScope         root,
        ciostream.cistream      in_s,
        MarkerListener          listener):
        self._hndl.build(
            root.asGlobalScope(),
            in_s.stream(),
            listener._hndl)

    @staticmethod
    cdef AstBuilder mk(decl.IAstBuilder *hndl):
        ret = AstBuilder()
        ret._hndl = hndl
        return ret
