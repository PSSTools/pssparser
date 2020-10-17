/*
 * Location.h
 *
 *  Created on: Oct 8, 2020
 *      Author: ballance
 */

#pragma once
#include <stdint.h>

namespace pssp {

class Location {
public:
	Location(
			uint32_t		fileid,
			uint32_t		lineno,
			uint32_t		linepos);

	virtual ~Location();

	uint32_t fileid() const { return m_fileid; }

	uint32_t lineno() const { return m_lineno; }

	uint32_t linepos() const { return m_linepos; }

	const char *filename() const { return m_filename; }

	void filename(const char *n) { m_filename = n; }

private:
	uint32_t			m_fileid;
	uint32_t			m_lineno;
	uint32_t			m_linepos;
	const char			*m_filename;

};

} /* namespace pls */

