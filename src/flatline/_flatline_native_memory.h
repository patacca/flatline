#pragma once

#include <cstdint>
#include <optional>
#include <string>

#include <nanobind/nanobind.h>

// Public helper kept for compatibility with existing tests and bindings.
class MemoryLoadImageSkeleton {
   public:
    MemoryLoadImageSkeleton(std::uint64_t base_address, nanobind::bytes memory_image,
                            nanobind::object tail_padding_obj);

    nanobind::bytes read(std::uint64_t address, std::size_t size) const;

   private:
    std::uint64_t base_address_;
    std::string memory_image_;
    std::optional<std::string> tail_padding_;
};
