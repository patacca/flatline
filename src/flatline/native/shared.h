#pragma once

#include <nanobind/nanobind.h>
#include <nanobind/stl/string.h>

#include <cstddef>
#include <cstdint>
#include <optional>
#include <string>

namespace ghidra {
class Address;
class Architecture;
class Datatype;
class FuncProto;
class Funcdata;
class PcodeOp;
class Symbol;
}  // namespace ghidra

namespace flatline::native_bridge {

struct NativeRequest {
    std::string memory_image;
    std::uint64_t base_address;
    std::uint64_t function_address;
    std::string language_id;
    std::optional<std::string> compiler_spec;
    std::uint32_t max_instructions;
    bool enriched;
    std::optional<std::string> tail_padding;
};

NativeRequest parse_request(const nanobind::dict& request);
bool checked_add_u64(std::uint64_t left, std::uint64_t right, std::uint64_t* result);

nanobind::dict type_info_to_dict(const ghidra::Datatype* datatype);
nanobind::object storage_info_from_address(const ghidra::Address& address, std::int64_t size);
nanobind::object storage_info_from_symbol(const ghidra::Symbol* symbol);
nanobind::dict diagnostics_to_dict(const ghidra::Funcdata& function);
nanobind::list warnings_from_comment_database(const ghidra::Funcdata& function,
                                              const ghidra::Architecture& architecture);
nanobind::list call_sites_to_list(const ghidra::Funcdata& function);
nanobind::list jump_tables_to_list(ghidra::Funcdata& function);
nanobind::list local_variables_to_list(const ghidra::Funcdata& function);
nanobind::dict prototype_to_dict(const ghidra::FuncProto& prototype);
nanobind::dict function_info_to_dict(ghidra::Funcdata& function);
nanobind::dict metadata_dict(const std::string& decompiler_version, const std::string& language_id,
                             const std::string& compiler_spec, const nanobind::dict& diagnostics);
nanobind::dict error_result(const std::string& category, const std::string& message,
                            const std::string& decompiler_version, const std::string& language_id,
                            const std::string& compiler_spec);
nanobind::dict success_result(const std::string& c_code, const nanobind::dict& function_info,
                              const nanobind::list& warnings,
                              const std::string& decompiler_version,
                              const std::string& language_id, const std::string& compiler_spec,
                              const nanobind::dict& diagnostics, const nanobind::object& enriched);
nanobind::dict pcode_to_dict(const ghidra::Funcdata& function);
std::string classifier_for_lowlevel_error(const std::string& message);
void fill_repeating_bytes(std::uint8_t* ptr, std::size_t size, const std::string& pattern);

}  // namespace flatline::native_bridge
