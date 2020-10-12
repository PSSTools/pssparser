/*
 * MarkerCollector.h
 *
 *  Created on: Oct 10, 2020
 *      Author: ballance
 */

#pragma once
#include "IMarkerListener.h"

namespace pssp {

class MarkerCollector : public virtual IMarkerListener {
public:
	MarkerCollector();

	virtual ~MarkerCollector();


};

} /* namespace pssp */

