/*
 * MarkerCollector.cpp
 *
 *  Created on: Oct 10, 2020
 *      Author: ballance
 */

#include "MarkerCollector.h"

namespace pssp {

MarkerCollector::MarkerCollector() {
	for (uint32_t i=0; i<static_cast<uint32_t>(MarkerSeverityE::NumLevels); i++) {
		m_count[i] = 0;
	}
}

MarkerCollector::~MarkerCollector() {
	// TODO Auto-generated destructor stub
}

void MarkerCollector::marker(const IMarker *m) {
	m_markers.push_back(IMarkerUP(m->clone()));
	m_count[static_cast<uint32_t>(m->severity())]++;
}

bool MarkerCollector::hasSeverity(MarkerSeverityE s) {
	return m_count[static_cast<uint32_t>(s)];
}

} /* namespace pssp */
