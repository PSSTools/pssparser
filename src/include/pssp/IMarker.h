/****************************************************************************
 * IMarker.h
 ****************************************************************************/
#pragma once
#include <memory>
#include <string>
#include <vector>
#include "pssp/ast/Location.h"

namespace pssp {


enum class MarkerSeverityE {
	Error,
	Warn,
	Info,
	Hint,
	NumLevels
};

struct MarkerRelation {
    ast::Location   loc;
    std::string     label;
};

class IMarker;
using IMarkerUP=std::unique_ptr<IMarker>;
class IMarker {
public:

    virtual ~IMarker() { }

    virtual const std::string &msg() const = 0;

    virtual void setMsg(const std::string &m) = 0;

    virtual MarkerSeverityE severity() const = 0;

    virtual void setSeverity(MarkerSeverityE s) = 0;

    virtual const ast::Location &loc() const = 0;

    virtual void setLocation(const ast::Location &l) = 0;

    virtual const std::string &id() const = 0;

    virtual void setId(const std::string &id) = 0;

    virtual const std::vector<MarkerRelation> &related() const = 0;

    virtual void addRelated(const ast::Location &loc, const std::string &label) = 0;

    virtual IMarker *clone() const = 0;

};

}
