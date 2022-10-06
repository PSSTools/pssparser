/*
 * BaseMarkerListener.h
 *
 *  Created on: Mar 24, 2021
 *      Author: mballance
 */

#pragma once
#include "pssp/IMarkerListener.h"

namespace pssp {

class BaseMarkerListener : public IMarkerListener {
public:
	BaseMarkerListener();

	virtual ~BaseMarkerListener();

	virtual void marker(const IMarker *m) override { }

	virtual bool hasSeverity(MarkerSeverityE s) override {
		return false;
	}

};

} /* namespace pssp */

