add_custom_command(
    OUTPUT _core.c
    COMMAND Python::Interpreter -m cython
          "${CMAKE_CURRENT_SOURCE_DIR}/_core.pyx" --output-file _core.c
    DEPENDS _core.pyx
)

python_add_library(_core MODULE _core.c WITH_SOABI)
set_target_properties(_core PROPERTIES OUTPUT_NAME "_core")

if(APPLE)
    # macOS: Compile as Objective-C for block support
    set_source_files_properties(${CMAKE_CURRENT_BINARY_DIR}/_core.c
        PROPERTIES LANGUAGE OBJC)
    target_link_libraries(_core PRIVATE "-framework CoreFoundation")
    target_compile_options(_core PRIVATE -fblocks)
    target_compile_definitions(_core PRIVATE CYGCD_MACOS=1)
else()
    # Linux: Find and link libdispatch
    find_package(PkgConfig REQUIRED)
    pkg_check_modules(DISPATCH REQUIRED libdispatch)

    target_include_directories(_core PRIVATE ${DISPATCH_INCLUDE_DIRS})
    target_link_libraries(_core PRIVATE ${DISPATCH_LIBRARIES})
    target_compile_definitions(_core PRIVATE CYGCD_LINUX=1)
endif()

install(TARGETS _core DESTINATION cygcd)
