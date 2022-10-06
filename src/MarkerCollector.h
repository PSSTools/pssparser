/*
 * MarkerCollector.h
 *
 *  Created on: Oct 10, 2020
 *      Author: ballance
 */

#pragma once
#include <vector>
#include "pssp/IMarkerListener.h"

namespace pssp {

class MarkerCollector : public virtual IMarkerListener {
public:
	MarkerCollector();

	virtual ~MarkerCollector();

	virtual void marker(const IMarker *m) override;

	virtual bool hasSeverity(MarkerSeverityE s) override;

	const std::vector<IMarkerUP> &markers() const {
		return m_markers;
	}

private:
	uint32_t					m_count[static_cast<uint32_t>(MarkerSeverityE::NumLevels)];
	std::vector<IMarkerUP>		m_markers;


};

} /* namespace pssp */

