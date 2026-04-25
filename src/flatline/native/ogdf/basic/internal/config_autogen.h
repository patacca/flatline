// Cross-platform replacement for OGDF's CMake-generated config_autogen.h.
// Hand-written so that Meson does not need to mirror OGDF's CMake configure
// step. Platform-conditional defines mirror the behaviour expected by OGDF's
// public headers.
#pragma once

#define OGDF_MEMORY_POOL_TS

#if defined(__LP64__) || defined(_WIN64) || defined(__x86_64__) \
		|| defined(__aarch64__)
#define OGDF_SIZEOF_POINTER 8
#else
#define OGDF_SIZEOF_POINTER 4
#endif

// COIN_OSI_CLP is referenced by OGDF headers that gate optional COIN-OR
// integration; defining it here keeps OGDF's macro arithmetic happy without
// pulling in any actual COIN-OR sources (the only OGDF translation unit that
// would dereference the stack is OptimalHierarchy{,Cluster}Layout.cpp, which
// is excluded or stubbed in this build).
#define COIN_OSI_CLP

#ifdef __linux__
#define OGDF_HAS_LINUX_CPU_MACROS
#define OGDF_HAS_MALLINFO2
#endif
