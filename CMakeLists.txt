cmake_minimum_required(VERSION 3.15...3.30)

project(${SKBUILD_PROJECT_NAME} VERSION ${SKBUILD_PROJECT_VERSION} LANGUAGES C OBJC)

find_package(Python REQUIRED COMPONENTS Interpreter Development.Module)

add_subdirectory(src)
