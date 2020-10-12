/*
 * Marker.h
 *
 *  Created on: Oct 8, 2020
 *      Author: ballance
 */

#pragma once
#include <memory>
#include <string>

#include "Location.h"
#include "MarkerSeverityE.h"

namespace pssp {

class Marker {
public:
	Marker(
			const std::string	&msg,
			MarkerSeverityE		severity,
			const Location		&loc);

	virtual ~Marker();

	const std::string &msg() const { return m_msg; }

	MarkerSeverityE severity() const { return m_severity; }

	const Location &loc() const { return m_loc; }

private:
	std::string			m_msg;
	MarkerSeverityE		m_severity;
	Location			m_loc;

};

typedef std::unique_ptr<Marker> MarkerUP;

} /* namespace pls */

