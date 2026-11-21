cmake_minimum_required(VERSION 3.14)
project(fluidian VERSION 1.2.0 DESCRIPTION "Build AI-native interfaces from C++" LANGUAGES CXX)

add_library(fluidian INTERFACE)
add_library(fluidian::fluidian ALIAS fluidian)
target_include_directories(fluidian INTERFACE
  $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
  $<INSTALL_INTERFACE:include>)
target_compile_features(fluidian INTERFACE cxx_std_17)

option(FLUIDIAN_BUILD_EXAMPLES "Build the Fluidian examples" ON)
if(FLUIDIAN_BUILD_EXAMPLES)
  add_executable(quickstart examples/quickstart.cpp)
  target_link_libraries(quickstart PRIVATE fluidian::fluidian)
  add_executable(conformance examples/conformance.cpp)
  target_link_libraries(conformance PRIVATE fluidian::fluidian)
endif()

install(DIRECTORY include/ DESTINATION include)
