/*
 * PyIStream.h
 *
 *  Created on: Mar 25, 2021
 *      Author: mballance
 */

#pragma once
#include <fstream>
#include "Python.h"

namespace pssp {

class PyStreamBuf : public std::streambuf {
public:
	PyStreamBuf(PyObject *istream);

	virtual ~PyStreamBuf();

private:
	PyObject			*m_istream;

};

}
