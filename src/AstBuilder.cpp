/*
 * AstBuilder.cpp
 *
 *  Created on: Oct 10, 2020
 *      Author: ballance
 */

#include <stdio.h>
#include "AstBuilder.h"
#include "atn/ParseInfo.h"
#include "ParseProfileInfo.h"

#include "AstBuilderInt.h"

namespace pssp {


using namespace antlr4;


AstBuilder::AstBuilder(
    dmgr::IDebugMgr     *dmgr,
	ast::IFactory		*factory,
	IMarkerListener 	*marker_l) :
	m_builder_int(new AstBuilderInt(dmgr, factory, marker_l)) {
	// TODO Auto-generated constructor stub

}

AstBuilder::~AstBuilder() {
	// TODO Auto-generated destructor stub
}

void AstBuilder::build(
		ast::IGlobalScope	*global,
		std::istream		*in) {
	m_builder_int->build(global, in);
}

pssp::ast::IFactory *AstBuilder::getFactory() {
    return m_builder_int->getFactory();
}

void AstBuilder::setMarkerListener(IMarkerListener *l) {
    m_builder_int->setMarkerListener(l);
}

void AstBuilder::setCollectDocStrings(bool c) {
    m_builder_int->setCollectDocStrings(c);
}

bool AstBuilder::getCollectDocStrings() {
    return m_builder_int->getCollectDocStrings();
}

void AstBuilder::setEnableProfile(bool e) {
    m_builder_int->setEnableProfile(e);
}

bool AstBuilder::getEnableProfile() {
    return m_builder_int->getEnableProfile();
}

bool AstBuilder::hasProfileInfo() const {
    return m_builder_int->hasProfileInfo();
}

IParseProfileInfo *AstBuilder::getProfileInfo() {
    const std::vector<atn::DecisionInfo> *decisions = m_builder_int->getProfileInfo();
    if (decisions) {
        ParseProfileInfo *info = new ParseProfileInfo(*decisions);
        return info;
    }
    return nullptr;
}

}
