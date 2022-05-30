/*
 * NameResolver.h
 *
 *  Created on: Oct 29, 2020
 *      Author: ballance
 */

#pragma once
#include "pssp/ast/impl/VisitorBase.h"
#include "pssp/IMarkerListener.h"

namespace pssp {

class NameResolver : public ast::VisitorBase {
public:
	NameResolver(
			IMarkerListener 						*marker_l,
			const std::vector<ast::IGlobalScope *>	&context);

	virtual ~NameResolver();

	void resolve(const std::vector<ast::IGlobalScope *> &target);

    virtual void visitDataTypeUserDefined(ast::IDataTypeUserDefined *i) override;

private:
    IMarkerListener						*m_marker_l;
    std::vector<ast::IGlobalScope *>	m_context;
    uint32_t							m_phase;
    std::vector<ast::IScope *>			m_scopes;
};

} /* namespace pssp */

