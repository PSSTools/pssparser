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

	if ((it=s->get_symtab().find(name)) != s->get_symtab().end()) {
		return it->second;
	} else {
		return 0;
	}
}

bool ScopeUtil::addChild(Scope *s, NamedScopeChild *c) {
	std::map<std::string,NamedScopeChild*>::iterator it;

	if ((it=s->get_symtab().find(c->get_name()->get_id())) == s->get_symtab().end()) {
		s->get_children().push_back(ScopeChildUP(c));
		s->get_symtab().insert({c->get_name()->get_id(), c});
		c->set_parent(s);
		return true;
	} else {
		return false;
	}
}

void ScopeUtil::addChild(Scope *s, ScopeChild *c) {
	s->get_children().push_back(ScopeChildUP(c));
	c->set_parent(s);
}

} /* namespace pssp */
