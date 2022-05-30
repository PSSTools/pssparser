/*
 * Marker.h
 *
 *  Created on: Oct 8, 2020
 *      Author: ballance
 */

#pragma once
#include <memory>
#include <string>

//#include "Location.h"
#include "MarkerSeverityE.h"

namespace pssp {

struct Location {
	int32_t		file = -1;
	int32_t		line = -1;
	int32_t		pos = -1;

	Location(int32_t f, int32_t l, int32_t p) : file(f), line(l), pos(p) {}
};

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

