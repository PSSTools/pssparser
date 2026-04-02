/*
 * NameResolver.cpp
 *
 *  Created on: Oct 29, 2020
 *      Author: ballance
 */
#include "dmgr/impl/DebugMacros.h"
#include "NameResolver.h"
#include "RefExprUtil.h"
#include "TaskCollectDeclarations.h"

namespace pssp {



NameResolver::NameResolver(
		IFactory								*factory,
		IMarkerListener							*marker_l) :
			m_factory(factory), m_marker_l(marker_l), m_phase(0) {
    DEBUG_INIT("NameResolver", factory->getDebugMgr());

}

NameResolver::~NameResolver() {
	// TODO Auto-generated destructor stub
}

void NameResolver::resolve(ast::ISymbolScope *root) {
	DEBUG_ENTER("resolve");

	// First, collect the declarations
//	TaskCollectDeclarations(m_marker_l, m_symtab).collect(root);

	m_sym_it_s.push_back(ISymbolTableIteratorUP(
		m_factory->mkAstSymbolTableIterator(root)));

	root->accept(this);

	m_sym_it_s.pop_back();

	/*
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
	 */
	DEBUG_LEAVE("resolve");
}

void NameResolver::visitPackageScope(ast::IPackageScope *i) {
	DEBUG_ENTER("visitPackage %s", i->getId().at(0)->getId().c_str());
	// A
	if (!sym_it()->pushNamedScope(i->getId().at(0)->getId())) {
		// TODO: internal error
		fprintf(stdout, "Error: Failed to find package scope %s\n",
			i->getId().at(0)->getId().c_str());
	}

	for (std::vector<ast::IScopeChildUP>::const_iterator
		it=i->getChildren().begin();
		it!=i->getChildren().end(); it++) {
		(*it)->accept(this);
	}

	sym_it()->popScope();

	DEBUG_LEAVE("visitPackage %s", i->getId().at(0)->getId().c_str());
}

void NameResolver::visitComponent(ast::IComponent *i) {
	DEBUG_ENTER("visitComponent %s", i->getName()->getId().c_str());
	if (!sym_it()->pushNamedScope(i->getName()->getId())) {
		// TODO: internal error
		fprintf(stdout, "Error: Failed to find component scope %s\n",
			i->getName()->getId().c_str());
	}

	for (std::vector<ast::IScopeChildUP>::const_iterator
		it=i->getChildren().begin();
		it!=i->getChildren().end(); it++) {
		(*it)->accept(this);
	}

	sym_it()->popScope();
	DEBUG_LEAVE("visitComponent %s", i->getName()->getId().c_str());
}

void NameResolver::visitExprRefPathId(ast::IExprRefPathId *i) {
    DEBUG_ENTER("visitExprRefPathId");

    DEBUG_LEAVE("visitExprRefPathId");
}

void NameResolver::visitEnumDecl(ast::IEnumDecl *i) {
	if (!sym_it()->pushNamedScope(i->getName()->getId())) {
		// TODO: internal error
		fprintf(stdout, "Error: Failed to find enum scope %s\n",
			i->getName()->getId().c_str());
	}

	for (std::vector<ast::IEnumItemUP>::const_iterator
		it=i->getItems().begin();
		it!=i->getItems().end(); it++) {
		(*it)->accept(this);
	}

	sym_it()->popScope();
}

void NameResolver::visitStruct(ast::IStruct *i) {
	if (!sym_it()->pushNamedScope(i->getName()->getId())) {
		// TODO: internal error
		fprintf(stdout, "Error");
	}

	for (std::vector<ast::IScopeChildUP>::const_iterator
		it=i->getChildren().begin();
		it!=i->getChildren().end(); it++) {
		(*it)->accept(this);
	}

	sym_it()->popScope();
}

void NameResolver::visitSymbolScope(ast::ISymbolScope *i) {
	DEBUG_ENTER("visitSymbolScope");

	m_sym_it_s.back()->pushNamedScope(i->getName());
	for (std::vector<ast::IScopeChildUP>::const_iterator
		it=i->getChildren().begin();
		it!=i->getChildren().end(); it++) {
		it->get()->accept(this);
	}
	m_sym_it_s.back()->popScope();

	DEBUG_LEAVE("visitSymbolScope");
}

void NameResolver::visitSymbolTypeScope(ast::ISymbolTypeScope *i) {
	DEBUG_ENTER("visitSymbolTypeScope");

	m_sym_it_s.back()->pushNamedScope(i->getName());
	for (std::vector<ast::IScopeChildUP>::const_iterator
		it=i->getChildren().begin();
		it!=i->getChildren().end(); it++) {
		it->get()->accept(this);
	}
	m_sym_it_s.back()->popScope();

	DEBUG_LEAVE("visitSymbolTypeScope");
}

void NameResolver::visitDataTypeUserDefined(ast::IDataTypeUserDefined *i) {
	DEBUG_ENTER("visitDataTypeUserDefined");
	// ISymbolTableIteratorUP it(sym_it()->clone());

	// // Find the first element

	// fprintf(stdout, "Searching for %s\n", i->getElems().at(0)->getId()->getId().c_str());
	// for (std::vector<ast::ITypeIdentifierElemUP>::const_iterator
	// 	ti_it=i->getElems().begin();
	// 	ti_it!=i->getElems().end(); ti_it++) {

	// 	if (ti_it == i->getElems().begin()) {
	// 		bool found = false;

	// 		while (it->hasScopes()) {
	// 			if (it->pushNamedScope((*ti_it)->getId()->getId())) {
	// 				fprintf(stdout, "Found!\n");
	// 				found = true;
	// 				break;
	// 			} else {
	// 				fprintf(stdout, "Uplevel\n");
	// 				it->popScope();
	// 			}
	// 		}

	// 		if (!found) {
	// 			fprintf(stdout, "Error: Failed to find first type elem %s\n",
	// 				i->getElems().at(0)->getId()->getId().c_str());
	// 			return;
	// 		}
	// 	} else {
	// 		if (it->pushNamedScope((*ti_it)->getId()->getId())) {
	// 			fprintf(stdout, "... found\n");
	// 		} else {
	// 			fprintf(stdout, "... failed to find subsequent element\n");
	// 			break;
	// 		}
	// 	}
	// }

	DEBUG_LEAVE("visitDataTypeUserDefined");
}

ISymbolTableIterator *NameResolver::sym_it() const {
	return (m_sym_it_s.size() > 0)?m_sym_it_s.back().get():0;
}

dmgr::IDebug *NameResolver::m_dbg = 0;

}
