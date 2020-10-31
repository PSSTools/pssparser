/*
 * NameResolver.h
 *
 *  Created on: Oct 29, 2020
 *      Author: ballance
 */

#pragma once
#include "BaseVisitor.h"
#include "IMarkerListener.h"

namespace pssp {

class NameResolver : public BaseVisitor {
public:
	NameResolver(
			IMarkerListener 					*marker_l,
			const std::vector<GlobalScope *>	&context);

	virtual ~NameResolver();

	void resolve(const std::vector<GlobalScope *> &target);

    virtual void visitDataTypeUserDefined(DataTypeUserDefined *i) override;

private:
    IMarkerListener						*m_marker_l;
    std::vector<GlobalScope *>			m_context;
    uint32_t							m_phase;
    std::vector<Scope *>				m_scopes;
};

} /* namespace pssp */

