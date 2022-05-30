/*
 * ScopeUtil.cpp
 *
 *  Created on: Oct 29, 2020
 *      Author: ballance
 */

#include "ScopeUtil.h"

namespace pssp {

ScopeUtil::ScopeUtil() {
	// TODO Auto-generated constructor stub

}

ScopeUtil::~ScopeUtil() {
	// TODO Auto-generated destructor stub
}

ast::INamedScopeChild *ScopeUtil::findChild(ast::IScope *s, const std::string &name) {
	std::map<std::string,ast::INamedScopeChild *>::iterator it;

	if ((it=s->getSymtab().find(name)) != s->getSymtab().end()) {
		return it->second;
	} else {
		return 0;
	}
}

bool ScopeUtil::addChild(ast::IScope *s, ast::INamedScopeChild *c) {
	std::map<std::string,ast::INamedScopeChild*>::iterator it;

	if ((it=s->getSymtab().find(c->getName()->getId())) == s->getSymtab().end()) {
		s->getChildren().push_back(ast::IScopeChildUP(c));
		s->getSymtab().insert({c->getName()->getId(), c});
		c->setParent(s);
		return true;
	} else {
		return false;
	}
}

void ScopeUtil::addChild(ast::IScope *s, ast::IScopeChild *c) {
	s->getChildren().push_back(ast::IScopeChildUP(c));
	c->setParent(s);
}

} /* namespace pssp */
