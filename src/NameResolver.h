/*
 * NameResolver.h
 *
 *  Created on: Oct 29, 2020
 *      Author: ballance
 */

#pragma once
#include <vector>
#include "dmgr/IDebugMgr.h"
#include "pssp/IFactory.h"
#include "pssp/INameResolver.h"
#include "pssp/INameResolverClient.h"
#include "pssp/ast/impl/VisitorBase.h"
#include "pssp/IMarkerListener.h"
#include "pssp/ISymbolTable.h"

namespace pssp {



class NameResolver : 
    public virtual INameResolver,
    public virtual ast::VisitorBase {
public:
	NameResolver(
            IFactory                    *factory,
			IMarkerListener             *marker);

	virtual ~NameResolver();

	void resolve(ast::ISymbolScope *root);

    virtual void visitPackageScope(ast::IPackageScope *i) override;

    virtual void visitComponent(ast::IComponent *i) override;

    virtual void visitExprRefPathId(ast::IExprRefPathId *i) override;

    virtual void visitEnumDecl(ast::IEnumDecl *i) override;

    virtual void visitStruct(ast::IStruct *i) override;

    virtual void visitSymbolScope(ast::ISymbolScope *i) override;

    virtual void visitSymbolTypeScope(ast::ISymbolTypeScope *i) override;

    virtual void visitDataTypeUserDefined(ast::IDataTypeUserDefined *i) override;

protected:
    ISymbolTableIterator *sym_it() const;

private:
    static dmgr::IDebug                 *m_dbg;
    IFactory                            *m_factory;

    std::vector<ISymbolTableIteratorUP> m_sym_it_s;

    IMarkerListener						*m_marker_l;
    std::vector<ast::IGlobalScope *>	m_context;
    uint32_t							m_phase;
    std::vector<ast::IScope *>			m_scopes;
};

}
