
#pragma once

namespace pssp {

class IAstBuilder;
class IMarkerListener;

class IFactory {
public:

    virtual ~IFactory() { }

    virtual IAstBuilder *mkAstBuilder() = 0;


};

}