import pytest
from io import StringIO

def build(docs):
    from pssparser import core as zspp_core
    from pssparser import ast as zspp_ast

    factory = zspp_core.Factory.inst()
      
    marker_l = factory.mkMarkerCollector()
      
    parser = factory.mkAstBuilder(marker_l)
    linker = factory.mkAstLinker()
    ast_f = factory.getAstFactory()

    parser.setCollectDocStrings(True)

    cu_l = []
    for i,doc in enumerate(docs):
        cu = ast_f.mkGlobalScope(i)
        input = StringIO(doc)

        parser.build(cu, input)

        assert not marker_l.hasSeverity(zspp_core.MarkerSeverityE.Error)

        cu_l.append(cu)

    linked = linker.link(marker_l, cu_l)

    assert not marker_l.hasSeverity(zspp_core.MarkerSeverityE.Error)

    return (cu_l, linked)

def linepos(doc, idx):
    lineno = 1
    linepos = 1

    i = 0
    while i < idx:
        if doc[i] == '\n':
            lineno += 1
            linepos = 1
        else:
            linepos += 1

        i += 1
    return (lineno,linepos)

def test_smoke():
    from pssparser import core as zspp_core
    doc = """
component C {

}

component pss_top {
    struct A { 
    }
    struct B {

    }
    C       c1, c2;
    struct D {

    }
    struct E {

    }
}
"""
    factory = zspp_core.Factory.inst()
    
    cu_l, linked = build([doc])

    idx = doc.find("pss_top")
    idx = doc.find("C", idx)
    print("idx: %d" % idx)

    pos = linepos(doc, idx)
    print("pos: %s" % str(pos))

    factory.lookupLocation(linked, cu_l[0], pos[0], pos[1])
    pass


def test_package_nested():
    from pssparser import core as zspp_core
    doc = """
component C {

}

package p {
package q {
package r {
component pss_top {
    /**
     * Struct A: 
     */
    struct A { 
    }

    /**
     * Struct B: 
     */
    struct B {

    }

    /* c1 belongs here */
    C       c1; /* c1 beside comment */
    C       c2;
    struct D {

    }
    struct E {

    }
}
}
}
}
"""
    factory = zspp_core.Factory.inst()
    
    cu_l, linked = build([doc])

    idx = doc.find("pss_top")
    idx = doc.find("C", idx)
    print("idx: %d" % idx)

    pos = linepos(doc, idx)
    print("pos: %s" % str(pos))

    factory.lookupLocation(linked, cu_l[0], pos[0], pos[1])
    pass
