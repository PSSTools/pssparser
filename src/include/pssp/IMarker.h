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

/**
 * A machine-applicable repair: replace `span` with `replacement`.
 *
 * The span is its own field rather than the diagnostic's, because the two are
 * routinely different. "expected ';' after 'a'" underlines one column so the
 * caret has something to point at, but the repair inserts a character and
 * replaces nothing -- `span.extent == 0`. Reusing the diagnostic's span for
 * the edit would delete whatever that column held.
 *
 * A fix must be complete: applying it has to produce a file the tool accepts.
 * Offer nothing rather than a guess -- a repair that does not repair costs the
 * reader more than silence does.
 */
struct MarkerFix {
    ast::Location   span;           //< `span.extent` characters from `span`
    std::string     replacement;    //< "" deletes the span
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

    virtual const std::vector<MarkerFix> &fixes() const = 0;

    virtual void addFix(const ast::Location &span,
                        const std::string &replacement) = 0;

    virtual IMarker *clone() const = 0;

};

}
