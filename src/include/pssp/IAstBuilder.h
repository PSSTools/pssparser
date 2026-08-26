/*
 * IAstBuilder.h
 *
 *  Created on: May 27, 2022
 *      Author: mballance
 */

#pragma once
#include <iostream>
#include <memory>
#include "pssp/IMarkerListener.h"
#include "pssp/IParseProfileInfo.h"
#include "pssp/ast/IGlobalScope.h"
#include "pssp/ast/IFactory.h"


namespace pssp {


class IAstBuilder;
using IAstBuilderUP=std::unique_ptr<IAstBuilder>;
class IAstBuilder {
public:

	virtual ~IAstBuilder() { }

	virtual void build(
		ast::IGlobalScope		*global,
		std::istream			*in) = 0;

    virtual pssp::ast::IFactory *getFactory() = 0;

    virtual void setMarkerListener(IMarkerListener *l) = 0;

    virtual void setCollectDocStrings(bool c) = 0;

    /**
     * Collect every comment, not only the docstring of a declaration.
     * Implies docstring collection.
     */
    virtual void setCollectComments(bool c) = 0;

    virtual bool getCollectComments() = 0;

    virtual bool getCollectDocStrings() = 0;

    /** Columns a tab advances when a doc comment is dedented (default 4). */
    virtual void setDocCommentTabWidth(int32_t w) = 0;

    virtual int32_t getDocCommentTabWidth() = 0;

    //! When true, only the marked comment forms count as documentation.
    //! Default false: an ordinary comment above a declaration documents it.
    virtual void setDocCommentStrictMarkers(bool s) = 0;

    virtual bool getDocCommentStrictMarkers() = 0;

    virtual void setEnableProfile(bool e) = 0;

    virtual bool getEnableProfile() = 0;

    virtual IParseProfileInfo *getProfileInfo() = 0;

};

}
