#****************************************************************************
#* CMakeLists.txt
#* 
#* Builds dependencies for the Python extension
#****************************************************************************

if (NOT DEFINED ENV{EXT_PYTHON})
   set(ENV{EXT_PYTHON} ${PYTHON})
endif()

#add_custom_target(build_ext ALL
#	COMMAND ${PYTHON} ${CMAKE_CURRENT_SOURCE_DIR}/setup.py sdist bdist_wheel
#	)
#add_custom_target(build_ext ALL
#	COMMAND ${PYTHON} ${CMAKE_CURRENT_SOURCE_DIR}/setup.py sdist bdist_wheel build_ext
#	)
add_custom_target(build_ext ALL
	COMMAND $ENV{EXT_PYTHON} ${CMAKE_CURRENT_SOURCE_DIR}/setup.py build_ext --inplace
	COMMAND $ENV{EXT_PYTHON} ${CMAKE_CURRENT_SOURCE_DIR}/setup.py bdist_wheel
	)

#add_custom_target(gen_ast_ext ALL
#	COMMAND ${PYTHON} -m astbuilder gen-pyext -name pssast -astdir ${CMAKE_CURRENT_SOURCE_DIR}/../ast
#	)
	
#add_dependencies(build_ext pssparser gen_ast_ext)
add_dependencies(build_ext pssparser)

	
