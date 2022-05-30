/*
 * NameResolver.cpp
 *
 *  Created on: Oct 29, 2020
 *      Author: ballance
 */

#include "NameResolver.h"
#include "RefExprUtil.h"
#include "ScopeUtil.h"

namespace pssp {

NameResolver::NameResolver(
		IMarkerListener							*marker_l,
		const std::vector<ast::IGlobalScope *>	&context) :
			m_marker_l(marker_l), m_context(context), m_phase(0) {
	// TODO Auto-generated constructor stub

}

NameResolver::~NameResolver() {
	// TODO Auto-generated destructor stub
}

void NameResolver::resolve(const std::vector<ast::IGlobalScope *> &target) {
	m_phase = 0;
	for (std::vector<ast::IGlobalScope *>::const_iterator
			it=target.begin(); it!=target.end(); it++) {
		(*it)->accept(this);
	}

	m_phase = 1;
	for (std::vector<ast::IGlobalScope *>::const_iterator
			it=target.begin(); it!=target.end(); it++) {
		(*it)->accept(this);
	}
}

void NameResolver::visitDataTypeUserDefined(ast::IDataTypeUserDefined *i) {
	ast::INamedScopeChild 	*root;
	ast::IRefExprSP 			ref;

	// First, find the root
	ast::ITypeIdentifierElem *elem = i->getElems().at(0).get();
	if (i->getIs_global()) {
		// Search for the root element across the context
		for (std::vector<ast::IGlobalScope *>::const_iterator
				it=m_context.begin(); it!=m_context.end(); it++) {
			if ((root=ScopeUtil::findChild(*it, elem->getId()->getId()))) {
				ref = RefExprUtil::mkScopeIndex(
						RefExprUtil::mkTypeScopeGlobal((*it)->getFileid()),
						root->getIndex());
				break;
			}
		}
	} else {
		// Search for the root element up the type-scope stack
		for (int32_t i=m_scopes.size()-1; i>=0; i--) {
			ast::IScope *s = m_scopes.at(i);

			if ((root=ScopeUtil::findChild(s, elem->getId()->getId()))) {

			}
		}
	}

	if (!root) {
		// TODO: error
		return;
	}

	// Now, continue resolving relative to root if there are
	// additional elements
	if (i->getElems().size() > 1) {

	} else {
		// Done
	}
}

} /* namespace pssp */
