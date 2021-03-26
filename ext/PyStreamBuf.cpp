/*
 * PyIStream.cpp
 *
 *  Created on: Mar 25, 2021
 *      Author: mballance
 */

#include "PyStreamBuf.h"
#include "pssparser_api.h"

namespace pssp {

PyStreamBuf::PyStreamBuf(PyObject *istream) : m_istream(istream) {
	import_pssparser__core();

	Py_XINCREF(m_istream);
	// TODO Auto-generated constructor stub

}

PyStreamBuf::~PyStreamBuf() {
	// TODO Auto-generated destructor stub
	Py_XDECREF(m_istream);
}

}
