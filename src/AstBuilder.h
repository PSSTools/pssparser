/*
 * AstBuilder.h
 *
 *  Created on: Oct 10, 2020
 *      Author: ballance
 */

#pragma once
#include <memory>
#include <iostream>
#include "dmgr/IDebugMgr.h"
#include "pssp/IAstBuilder.h"
#include "pssp/ast/IFactory.h"
#include "pssp/ast/IGlobalScope.h"
#include "pssp/IMarkerListener.h"

namespace antlr4 {
namespace atn {
    class ParseInfo;
}
}

namespace pssp {



class AstBuilderInt;
typedef std::unique_ptr<AstBuilderInt> AstBuilderIntUP;

class AstBuilder : public virtual IAstBuilder {
public:
	AstBuilder(
        dmgr::IDebugMgr     *dmgr,
		ast::IFactory		*factory,
		IMarkerListener 	*marker_l);

	virtual ~AstBuilder();

	virtual void build(
			ast::IGlobalScope	*global,
			std::istream		*in) override;

    virtual pssp::ast::IFactory *getFactory() override;

    virtual void setMarkerListener(IMarkerListener *l) override;

    virtual void setCollectDocStrings(bool c) override;

    virtual bool getCollectDocStrings() override;

    virtual void setEnableProfile(bool e) override;

    virtual bool getEnableProfile() override;

    virtual bool hasProfileInfo() const;

    virtual IParseProfileInfo *getProfileInfo();

private:
	AstBuilderIntUP				m_builder_int;
};

}
