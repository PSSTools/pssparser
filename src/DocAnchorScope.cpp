/*
 * DocAnchorScope.cpp
 */

#include "DocAnchorScope.h"
#include "AstBuilderInt.h"

namespace pssp {

DocAnchorScope::DocAnchorScope(
        AstBuilderInt   *builder,
        antlr4::Token   *tok) : m_builder(builder) {
    if (m_builder) {
        m_builder->pushDocAnchor(tok);
    }
}

DocAnchorScope::~DocAnchorScope() {
    if (m_builder) {
        m_builder->popDocAnchor();
    }
}

} /* namespace pssp */
