/*
 * Location.cpp
 *
 *  Created on: Oct 8, 2020
 *      Author: ballance
 */

#include "Location.h"

namespace pssp {

Location::Location(
		uint32_t		fileid,
		uint32_t		lineno,
		uint32_t		linepos) :
			m_fileid(fileid), m_lineno(lineno),
			m_linepos(linepos), m_filename(0) {
	// TODO Auto-generated constructor stub

}

Location::~Location() {
	// TODO Auto-generated destructor stub
}

} /* namespace pls */
