/*
 * MarkerCollector.h
 *
 *  Created on: Oct 10, 2020
 *      Author: ballance
 */

#pragma once
#include <vector>
#include "pssp/IMarkerCollector.h"

namespace pssp {



class MarkerCollector : public virtual IMarkerCollector {
public:
	MarkerCollector();

	virtual ~MarkerCollector();

	virtual void marker(const IMarker *m) override;

	virtual bool hasSeverity(MarkerSeverityE s) override;

	const std::vector<IMarkerUP> &markers() const {
		return m_markers;
	}

	virtual void setMaxErrors(int32_t max) override {
		m_max_errors = max;
	}

	virtual bool maxErrorsExceeded() const override {
		return m_stopped;
	}

private:
	uint32_t					m_count[static_cast<uint32_t>(MarkerSeverityE::NumLevels)];
	std::vector<IMarkerUP>		m_markers;
	int32_t						m_max_errors = 0; // 0 = unlimited
	int32_t						m_error_count = 0;
	bool						m_stopped = false;


};

}
