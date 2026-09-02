/*
 * Marker.h
 *
 *  Created on: Oct 8, 2020
 *      Author: ballance
 */

#pragma once
#include <memory>
#include <string>
#include "pssp/IMarker.h"
#include "pssp/ast/Location.h"

namespace pssp {



class Marker : public IMarker {
public:
	Marker(
			const std::string	&msg,
			MarkerSeverityE		severity,
			const ast::Location	&loc);

	Marker(
			const std::string	&msg,
			MarkerSeverityE		severity,
			const ast::Location	&loc,
			const std::string	&id);

	virtual ~Marker();

	virtual const std::string &msg() const override { 
		return m_msg; 
	}

    virtual void setMsg(const std::string &m) override {
		m_msg = m;
	}

	virtual MarkerSeverityE severity() const override { 
		return m_severity; 
	}

    virtual void setSeverity(MarkerSeverityE s) override {
		m_severity = s;
	}

	virtual const ast::Location &loc() const override { 
		return m_loc; 
	}

    virtual void setLocation(const ast::Location &l) override {
		m_loc = l;
	}

	virtual const std::string &id() const override {
		return m_id;
	}

	virtual void setId(const std::string &id) override {
		m_id = id;
	}

	virtual const std::vector<MarkerRelation> &related() const override {
		return m_related;
	}

	virtual void addRelated(const ast::Location &loc, const std::string &label) override {
		m_related.push_back(MarkerRelation{loc, label});
	}

	virtual IMarker *clone() const override;


private:
	std::string					m_msg;
	MarkerSeverityE				m_severity;
	ast::Location				m_loc;
	std::string					m_id;
	std::vector<MarkerRelation>	m_related;

};

typedef std::unique_ptr<Marker> MarkerUP;

}
