
#pragma once
#include <Python.h>
#include <iostream>

namespace pyiostream {

class streambuf : public std::streambuf {
public:
    streambuf(PyObject *s);

    virtual ~streambuf();

    virtual std::streambuf::int_type underflow() override;

private:
        PyObject                *m_stream_obj;
        PyObject                *m_str;
        char                    m_buf[4096];
        int                     m_count;
};

class istream : public std::istream {
public:
    istream(PyObject *);

    virtual ~istream();

private:
    streambuf                 m_buf;

};

}
