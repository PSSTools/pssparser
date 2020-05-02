EXT_DIR := $(abspath $(dir $(lastword $(MAKEFILE_LIST))))
PSSPARSER_DIR := $(abspath $(EXT_DIR)/..)

all : grammar.d runtime.d libpssparser.so

RUNTIME_DIR=antlr4-cpp-runtime-4.8
RUNTIME_ZIP=$(RUNTIME_DIR)-source.zip
URL=https://www.antlr.org/download/antlr4-cpp-runtime-4.8-source.zip

$(RUNTIME_ZIP) :
      wget -O $@ $(URL)
      
CXXFLAGS += -I$(EXT_DIR)/$(RUNTIME_DIR)/runtime/src
CXXFLAGS += -I$(EXT_DIR)/antlr_gen

runtime.d : $(RUNTIME_ZIP)
	rm -rf $(RUNTIME_DIR)
	mkdir $(RUNTIME_DIR)
	cd $(RUNTIME_DIR) ; unzip -o ../$(RUNTIME_ZIP)
	rm -rf build
	mkdir build
	scl enable devtoolset-7 "cd build; cmake ../$(RUNTIME_DIR)"
	scl enable devtoolset-7 "cd build; $(MAKE)"
	touch $@

libpssparser.so : runtime.d CUParser.o


grammar.d : $(glob $(PSSPARSER_DIR)/grammar/*.g4)
	java -jar $(PSSPARSER_DIR)/scripts/antlr-4.8-complete.jar -Dlanguage=Cpp \
		$(PSSPARSER_DIR)/grammar/PSS.g4 -visitor -o antlr_gen
	touch $@
