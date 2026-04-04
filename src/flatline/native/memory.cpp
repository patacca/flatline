#include "memory.h"

#include <cstring>
#include <string>

#include "shared.h"

namespace {

// Keep the public compatibility helper thin and delegate byte-pattern filling
// to the shared native utility used by the decompile path.
static void fill_buffer_from_pattern(std::uint8_t* ptr, std::size_t size,
                                     const std::string& pattern) {
    flatline::native_bridge::fill_repeating_bytes(ptr, size, pattern);
}

}  // namespace

MemoryLoadImageSkeleton::MemoryLoadImageSkeleton(std::uint64_t base_address,
                                                 nanobind::bytes memory_image,
                                                 nanobind::object tail_padding_obj)
    : base_address_(base_address), memory_image_(memory_image.c_str(), memory_image.size()) {
    if (tail_padding_obj.is_none()) {
        return;
    }
    nanobind::bytes raw_tail_padding = nanobind::cast<nanobind::bytes>(tail_padding_obj);
    if (raw_tail_padding.size() == 0) {
        return;
    }
    tail_padding_ = std::string(raw_tail_padding.c_str(), raw_tail_padding.size());
}

nanobind::bytes MemoryLoadImageSkeleton::read(std::uint64_t address, std::size_t size) const {
    std::uint64_t end = 0;
    if (!flatline::native_bridge::checked_add_u64(
            base_address_, static_cast<std::uint64_t>(memory_image_.size()), &end)) {
        throw nanobind::value_error("memory_image bounds overflow");
    }
    std::uint64_t requested_end = 0;
    if (!flatline::native_bridge::checked_add_u64(address, static_cast<std::uint64_t>(size),
                                                  &requested_end)) {
        throw nanobind::value_error("requested address range overflow");
    }
    if (address < base_address_ || address >= end) {
        throw nanobind::value_error("requested address range is outside memory_image");
    }

    const std::size_t offset = static_cast<std::size_t>(address - base_address_);
    if (requested_end > end) {
        if (!tail_padding_.has_value()) {
            throw nanobind::value_error("requested address range is outside memory_image");
        }
        std::string output(size, '\0');
        const std::size_t available_size = static_cast<std::size_t>(end - address);
        std::memcpy(output.data(), memory_image_.data() + offset, available_size);
        fill_buffer_from_pattern(reinterpret_cast<std::uint8_t*>(output.data() + available_size),
                                 size - available_size, *tail_padding_);
        return nanobind::bytes(output.data(), size);
    }
    return nanobind::bytes(memory_image_.data() + offset, size);
}
