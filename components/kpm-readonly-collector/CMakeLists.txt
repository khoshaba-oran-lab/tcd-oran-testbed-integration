cmake_minimum_required(VERSION 3.16)

project(tcd_kpm_collector LANGUAGES C)

if(NOT TARGET e42_xapp)
    message(
        FATAL_ERROR
        "tcd_kpm_collector must be built inside the validated FlexRIC tree"
    )
endif()

if(NOT TARGET e2_time_obj)
    message(
        FATAL_ERROR
        "required FlexRIC target e2_time_obj is unavailable"
    )
endif()

set(CMAKE_C_STANDARD 11)
set(CMAKE_C_STANDARD_REQUIRED ON)
set(CMAKE_C_EXTENSIONS OFF)

add_library(
    tcd_kpm_collector_core
    STATIC
    src/config.c
    src/counters.c
    src/lifecycle.c
    src/record.c
)

target_include_directories(
    tcd_kpm_collector_core
    PUBLIC
    "${CMAKE_CURRENT_SOURCE_DIR}/include"
)

target_compile_definitions(
    tcd_kpm_collector_core
    PRIVATE
    _POSIX_C_SOURCE=200809L
)

target_compile_options(
    tcd_kpm_collector_core
    PRIVATE
    -Wall
    -Wextra
    -Wpedantic
)

add_executable(
    tcd_kpm_collector
    src/main.c
    src/flexric_discovery.c
    src/kpm_callback.c
    src/kpm_validation.c
    src/kpm_subscription.c
)

target_include_directories(
    tcd_kpm_collector
    PRIVATE
    "${CMAKE_CURRENT_SOURCE_DIR}/include"
    "${CMAKE_SOURCE_DIR}/src"
)

target_compile_definitions(
    tcd_kpm_collector
    PRIVATE
    _POSIX_C_SOURCE=200809L
)

target_compile_options(
    tcd_kpm_collector
    PRIVATE
    -Wall
    -Wextra
    -Wpedantic
)

target_link_libraries(
    tcd_kpm_collector
    PUBLIC
    tcd_kpm_collector_core
    e42_xapp
    $<TARGET_OBJECTS:e2_time_obj>
    -pthread
    -lsctp
    -ldl
)

install(
    TARGETS tcd_kpm_collector
    RUNTIME DESTINATION bin/flexric/xApp/c
)
