/*
 * MarkerCollector.cpp
 *
 *  Created on: Oct 10, 2020
 *      Author: ballance
 */

#include "Marker.h"
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
	if (m_stopped) {
		// Cap already announced via PSS029; drop everything further so a
		// hopelessly-broken file cannot flood the caller with cascades.
		return;
	}

	if (m_max_errors > 0 && m->severity() == MarkerSeverityE::Error) {
		m_error_count++;
		if (m_error_count > m_max_errors) {
			Marker cap(
					"too many errors (" + std::to_string(m_max_errors) +
					"); stopped reporting further errors for this file",
					MarkerSeverityE::Error,
					m->loc(),
					"PSS029");
			m_markers.push_back(IMarkerUP(cap.clone()));
			m_count[static_cast<uint32_t>(MarkerSeverityE::Error)]++;
			m_stopped = true;
			return;
		}
	}

	m_markers.push_back(IMarkerUP(m->clone()));
	m_count[static_cast<uint32_t>(m->severity())]++;
}

bool MarkerCollector::hasSeverity(MarkerSeverityE s) {
	return m_count[static_cast<uint32_t>(s)];
}

}
