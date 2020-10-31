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

NamedScopeChild *ScopeUtil::findChild(Scope *s, const std::string &name) {
	std::map<std::string,NamedScopeChild *>::iterator it;

	if ((it=s->symtab().find(name)) != s->symtab().end()) {
		return it->second;
	} else {
		return 0;
	}
}

bool ScopeUtil::addChild(Scope *s, NamedScopeChild *c) {
	std::map<std::string,NamedScopeChild*>::iterator it;

	if ((it=s->symtab().find(c->name()->id())) == s->symtab().end()) {
		s->children().push_back(ScopeChildUP(c));
		s->symtab().insert({c->name()->id(), c});
		c->parent(s);
		return true;
	} else {
		return false;
	}
}

void ScopeUtil::addChild(Scope *s, ScopeChild *c) {
	s->children().push_back(ScopeChildUP(c));
	c->parent(s);
}

} /* namespace pssp */
