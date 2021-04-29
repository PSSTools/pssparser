
#include "pyiostream.h"

namespace pyiostream {

streambuf::streambuf(PyObject *s) {
    m_stream_obj = s;
    Py_XINCREF(m_stream_obj);
    m_str = 0;
    m_count = 0;
}

streambuf::~streambuf() {
    Py_XDECREF(m_stream_obj);
    Py_XDECREF(m_str);
}

std::streambuf::int_type streambuf::underflow() {
    Py_XDECREF(m_str);
    m_str = PyObject_CallMethod(m_stream_obj, "read", "L", 4096);
    Py_XINCREF(m_str);
    Py_ssize_t sz;
    char *str = 0;

    if (PyUnicode_Check(m_str)) {
        str = PyUnicode_AsUTF8AndSize(m_str, &sz);
    } else if (PyBytes_Check(m_str)) {
        PyBytes_AsStringAndSize(m_str, &str, &sz);
    } else {
        fprintf(stdout, "Unknown\n");
    }

    if (sz == 0) {
        return traits_type::eof();
    } else {
        setg(str, str, str+sz);
        return traits_type::to_int_type(str[0]);
    }
}


istream::istream(PyObject *stream) : std::istream(&m_buf), m_buf(stream) {

}

istream::~istream() {

}

}
