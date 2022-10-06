
#pragma once
#include "pssp/ast/INamedScopeChild.h"

namespace pssp {

class ISymbolScope;

struct ResolveResult {
    bool                                is_terminal;
    union {
        pssp::ast::INamedScopeChild     *terminal;
        ISymbolScope                    *scope;
    };
};

class ISymbolResolver {
public:

    virtual ~ISymbolResolver() { }

    virtual bool resolve(
        const std::string       &name,
        ResolveResult           &result) = 0;

};

}