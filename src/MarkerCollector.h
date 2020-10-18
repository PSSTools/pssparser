/*
 * MarkerCollector.h
 *
 *  Created on: Oct 10, 2020
 *      Author: ballance
 */

#pragma once
#include <vector>
#include "IMarkerListener.h"

namespace pssp {

class MarkerCollector : public virtual IMarkerListener {
public:
	MarkerCollector();

	virtual ~MarkerCollector();

	virtual void marker(const Marker &m) override;

	virtual bool hasSeverity(MarkerSeverityE s) override;

	const std::vector<Marker> &markers() const {
		return m_markers;
	}

private:
	uint32_t					m_count[Severity_NumLevels];
	std::vector<Marker>			m_markers;


};

} /* namespace pssp */

