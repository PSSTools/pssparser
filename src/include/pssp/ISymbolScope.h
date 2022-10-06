
#pragma once
#include <memory>
#include <string>
#include <vector>
#include "pssp/ast/INamedScopeChild.h"
#include "pssp/ast/IScopeChild.h"
#include "pssp/ISymbolResolver.h"

namespace pssp {

enum class SymbolScopeKind {
    Namespace,
    Type,
    Exec,
    Function
};

class ISymbolScope;
using ISymbolScopeUP=std::unique_ptr<ISymbolScope>;
class ISymbolScope : public virtual ISymbolResolver {
public:

    virtual ~ISymbolScope() { }

    virtual const std::string &getName() const = 0;

    virtual std::string getFullName() = 0;

    virtual SymbolScopeKind kind() const = 0;

    virtual ISymbolScope *getParent() const = 0;

    virtual void setParent(ISymbolScope *parent) = 0;

    virtual const std::vector<ast::IScopeChild *> &getDeclScopes() const = 0;

    virtual void addDeclScope(ast::IScopeChild *scope) = 0;

    virtual const std::vector<ISymbolScopeUP> &getSubscopes() const = 0;

    virtual bool addSubscope(ISymbolScope *scope) = 0;

    virtual const std::vector<pssp::ast::INamedScopeChild *> &getTerminals() const = 0;

    virtual bool addTerminal(pssp::ast::INamedScopeChild *terminal) = 0;

};

}