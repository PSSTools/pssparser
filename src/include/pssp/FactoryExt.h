
#pragma once
#include "pssp/IFactory.h"

/**
 * These factory entry points are the entire exported surface of the pssparser
 * shared library: everything else in the API is reached through the
 * pure-virtual interfaces they hand back, so nothing else needs to be visible
 * to a consumer.  Windows requires the visibility to be declared explicitly --
 * without it GetProcAddress/dlsym finds nothing (see pssp/impl/Loader.h and
 * Factory.inst() in core.pyx).
 */
#if defined(_WIN32)
#  if defined(PSSPARSER_BUILD_DLL)
#    define PSSPARSER_API __declspec(dllexport)
#  else
#    define PSSPARSER_API __declspec(dllimport)
#  endif
#else
#  define PSSPARSER_API
#endif

extern "C" PSSPARSER_API pssp::IFactory *pssparser_getFactory();

/* Legacy alias, retained for out-of-tree consumers. */
extern "C" PSSPARSER_API pssp::IFactory *getZuspecParserFactory();
