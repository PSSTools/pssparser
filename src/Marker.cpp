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
		const ast::Location	&loc) :
				m_msg(msg), m_severity(severity), m_loc(loc) {
	// TODO Auto-generated constructor stub

}

Marker::Marker(
		const std::string	&msg,
		MarkerSeverityE		severity,
		const ast::Location	&loc,
		const std::string	&id) :
				m_msg(msg), m_severity(severity), m_loc(loc), m_id(id) {

}

Marker::~Marker() {
	// TODO Auto-generated destructor stub
}

IMarker *Marker::clone() const {
	Marker *ret = new Marker(m_msg, m_severity, m_loc, m_id);
	ret->m_related = m_related;
	return ret;
}

}
