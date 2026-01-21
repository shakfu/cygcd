add_custom_command(
    OUTPUT _core.c
    COMMAND Python::Interpreter -m cython
          "${CMAKE_CURRENT_SOURCE_DIR}/_core.pyx" --output-file _core.c
    DEPENDS _core.pyx
)

python_add_library(_core MODULE _core.c WITH_SOABI)

set_target_properties(_core PROPERTIES OUTPUT_NAME "_core")

# Compile as Objective-C for block support (required for dispatch_io)
set_source_files_properties(${CMAKE_CURRENT_BINARY_DIR}/_core.c
    PROPERTIES LANGUAGE OBJC)

# Link against the dispatch framework (GCD) on macOS
if(APPLE)
    target_link_libraries(_core PRIVATE "-framework CoreFoundation")
    target_compile_options(_core PRIVATE -fblocks)
endif()

install(TARGETS _core DESTINATION cygcd)
