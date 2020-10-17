/*
 * MarkerCollector.cpp
 *
 *  Created on: Oct 10, 2020
 *      Author: ballance
 */

#include "MarkerCollector.h"

namespace pssp {

MarkerCollector::MarkerCollector() {
	for (uint32_t i=0; i<Severity_NumLevels; i++) {
		m_count[i] = 0;
	}
}

MarkerCollector::~MarkerCollector() {
	// TODO Auto-generated destructor stub
}

void MarkerCollector::marker(const Marker &m) {
	m_markers.push_back(m);
	m_count[m.severity()]++;
}

bool MarkerCollector::hasSeverity(MarkerSeverityE s) {
	return m_count[s];
}

} /* namespace pssp */
