/*
 * BaseMarkerListener.h
 *
 *  Created on: Mar 24, 2021
 *      Author: mballance
 */

#pragma once
#include "IMarkerListener.h"

namespace pssp {

class BaseMarkerListener : public IMarkerListener {
public:
	BaseMarkerListener();

	virtual ~BaseMarkerListener();

	virtual void marker(const Marker &m) override { }

	virtual bool hasSeverity(MarkerSeverityE s) override { }

};

} /* namespace pssp */

