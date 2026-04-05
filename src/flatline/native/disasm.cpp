#include <cstdint>
#include <string>
#include <vector>

#include "shared.h"

namespace nb = nanobind;

namespace flatline::native_bridge {

nb::list instructions_to_list(const std::vector<InstructionEntry>& instructions) {
    nb::list result;
    for (const InstructionEntry& entry : instructions) {
        nb::dict item;
        item["address"] = entry.address;
        item["length"] = entry.length;
        item["mnemonic"] = entry.mnemonic;
        item["operands"] = entry.operands;
        result.append(item);
    }
    return result;
}

}  // namespace flatline::native_bridge
