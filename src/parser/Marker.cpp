/*
 * Marker.cpp
 *
 *  Created on: Oct 8, 2020
 *      Author: ballance
 */

#include "Marker.h"

namespace pssp {

Marker::Marker(
		const std::string	&msg,
		MarkerSeverityE		severity,
		const Location		&loc) :
				m_msg(msg), m_severity(severity), m_loc(loc) {
	// TODO Auto-generated constructor stub

}

Marker::~Marker() {
	// TODO Auto-generated destructor stub
}

} /* namespace pls */
