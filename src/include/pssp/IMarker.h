/****************************************************************************
 * IMarker.h
 ****************************************************************************/
#pragma once
#include <memory>
#include "pssp/ast/Location.h"

namespace pssp {

enum class MarkerSeverityE {
	Error,
	Warn,
	Info,
	Hint,
	NumLevels
};

class IMarker;
using IMarkerUP=std::unique_ptr<IMarker>;
class IMarker {
public:

    virtual ~IMarker() { }

    virtual const std::string &msg() const = 0;

    virtual MarkerSeverityE severity() const = 0;

    virtual const ast::Location &loc() const = 0;

    virtual IMarker *clone() const = 0;

};

}