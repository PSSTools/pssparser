/*
 * DocAnchorScope.h
 *
 * Establishes the token a doc comment is looked up from for the declarations
 * built while the scope is alive.
 *
 * A doc comment leads the declaration *as written in source*, but the visitor
 * that constructs the AST node sees only its own grammar rule.  Where a
 * wrapper rule contributes tokens ahead of it -- `rand` and `static const`
 * ahead of `data_declaration` under `attr_field`, for instance -- the
 * constructing visitor's start token sits after the comment, and the backward
 * scan finds nothing but whitespace.  That is defect D2, and it is a property
 * of every wrapper rule, not of `attr_field` alone.
 *
 * A wrapper visitor therefore opens one of these over its delegation:
 *
 *     DocAnchorScope anchor(this, ctx->start);
 *     return visitChildren(ctx);
 *
 * Nesting is safe, and push_scope() suspends the anchor so a declaration
 * inside a nested scope finds its own comment.
 */

#pragma once

namespace antlr4 {
    class Token;
}

namespace pssp {

class AstBuilderInt;

class DocAnchorScope {
public:
    DocAnchorScope(AstBuilderInt *builder, antlr4::Token *tok);

    ~DocAnchorScope();

    DocAnchorScope(const DocAnchorScope &) = delete;
    DocAnchorScope &operator = (const DocAnchorScope &) = delete;

private:
    AstBuilderInt       *m_builder;
};

} /* namespace pssp */
