#include <stdexcept>
#include <unordered_map>
#include <vector>

#include "database.hh"
#include "funcdata.hh"
#include "opcodes.hh"
#include "shared.h"
#include "type.hh"

namespace nb = nanobind;

namespace flatline::native_bridge {
namespace {

struct EnrichedIndex {
    std::vector<const ghidra::PcodeOp*> pcode_ops;
    std::vector<const ghidra::Varnode*> varnodes;
    std::unordered_map<const ghidra::PcodeOp*, std::uint64_t> pcode_op_ids;
    std::unordered_map<const ghidra::Varnode*, std::uint64_t> varnode_ids;
};

static void register_varnode_for_pcode_index(const ghidra::Varnode* varnode,
                                             EnrichedIndex* index) {
    if (varnode == nullptr) {
        return;
    }
    const std::uint64_t next_id = static_cast<std::uint64_t>(index->varnodes.size());
    const auto [iter, inserted] = index->varnode_ids.emplace(varnode, next_id);
    if (!inserted) {
        return;
    }
    index->varnodes.push_back(iter->first);
}

static EnrichedIndex build_enriched_index(const ghidra::Funcdata& function) {
    EnrichedIndex index;
    for (ghidra::PcodeOpTree::const_iterator iter = function.beginOpAll();
         iter != function.endOpAll(); ++iter) {
        const ghidra::PcodeOp* op = iter->second;
        if (op == nullptr) {
            continue;
        }
        const std::uint64_t op_id = static_cast<std::uint64_t>(index.pcode_ops.size());
        index.pcode_op_ids.emplace(op, op_id);
        index.pcode_ops.push_back(op);

        register_varnode_for_pcode_index(op->getOut(), &index);
        const int input_count = op->numInput();
        for (int slot = 0; slot < input_count; ++slot) {
            register_varnode_for_pcode_index(op->getIn(slot), &index);
        }
    }
    return index;
}

static std::optional<std::uint64_t> lookup_pcode_op_id(const EnrichedIndex& index,
                                                       const ghidra::PcodeOp* op) {
    if (op == nullptr) {
        return std::nullopt;
    }
    const auto iter = index.pcode_op_ids.find(op);
    if (iter == index.pcode_op_ids.end()) {
        return std::nullopt;
    }
    return iter->second;
}

static std::optional<std::uint64_t> lookup_varnode_id(const EnrichedIndex& index,
                                                      const ghidra::Varnode* varnode) {
    if (varnode == nullptr) {
        return std::nullopt;
    }
    const auto iter = index.varnode_ids.find(varnode);
    if (iter == index.varnode_ids.end()) {
        return std::nullopt;
    }
    return iter->second;
}

static nb::dict varnode_flags_to_dict(const ghidra::Varnode& varnode) {
    nb::dict flags;
    flags["is_constant"] = varnode.isConstant();
    flags["is_input"] = varnode.isInput();
    flags["is_free"] = varnode.isFree();
    flags["is_implied"] = varnode.isImplied();
    flags["is_explicit"] = varnode.isExplicit();
    flags["is_read_only"] = varnode.isReadOnly();
    flags["is_persist"] = varnode.isPersist();
    flags["is_addr_tied"] = varnode.isAddrTied();
    return flags;
}

static nb::dict pcode_op_to_dict(const ghidra::PcodeOp& op, const EnrichedIndex& index) {
    nb::dict pcode_op;
    const auto op_id = lookup_pcode_op_id(index, &op);
    if (!op_id.has_value()) {
        throw std::runtime_error("enriched output missing PcodeOp id");
    }

    nb::list input_varnode_ids;
    const int input_count = op.numInput();
    for (int slot = 0; slot < input_count; ++slot) {
        const auto varnode_id = lookup_varnode_id(index, op.getIn(slot));
        if (!varnode_id.has_value()) {
            throw std::runtime_error("enriched output missing input varnode id");
        }
        input_varnode_ids.append(varnode_id.value());
    }

    pcode_op["id"] = op_id.value();
    pcode_op["opcode"] = ghidra::get_opname(op.code());
    pcode_op["instruction_address"] =
        static_cast<std::uint64_t>(op.getAddr().isInvalid() ? 0 : op.getAddr().getOffset());
    pcode_op["sequence_time"] = static_cast<std::uint64_t>(op.getSeqNum().getTime());
    pcode_op["sequence_order"] = static_cast<std::uint64_t>(op.getSeqNum().getOrder());
    pcode_op["input_varnode_ids"] = input_varnode_ids;

    const auto output_varnode_id = lookup_varnode_id(index, op.getOut());
    if (output_varnode_id.has_value()) {
        pcode_op["output_varnode_id"] = output_varnode_id.value();
    } else {
        pcode_op["output_varnode_id"] = nb::none();
    }
    return pcode_op;
}

static nb::dict varnode_to_dict(const ghidra::Varnode& varnode, const EnrichedIndex& index) {
    nb::dict varnode_item;
    const auto varnode_id = lookup_varnode_id(index, &varnode);
    if (!varnode_id.has_value()) {
        throw std::runtime_error("enriched output missing Varnode id");
    }

    nb::list use_op_ids;
    for (std::list<ghidra::PcodeOp*>::const_iterator iter = varnode.beginDescend();
         iter != varnode.endDescend(); ++iter) {
        const auto use_op_id = lookup_pcode_op_id(index, *iter);
        if (use_op_id.has_value()) {
            use_op_ids.append(use_op_id.value());
        }
    }

    const ghidra::AddrSpace* space = varnode.getSpace();
    varnode_item["id"] = varnode_id.value();
    varnode_item["space"] = space == nullptr ? "unknown" : space->getName();
    varnode_item["offset"] = static_cast<std::uint64_t>(varnode.getOffset());
    varnode_item["size"] = varnode.getSize();
    varnode_item["flags"] = varnode_flags_to_dict(varnode);

    const auto defining_op_id = lookup_pcode_op_id(index, varnode.getDef());
    if (defining_op_id.has_value()) {
        varnode_item["defining_op_id"] = defining_op_id.value();
    } else {
        varnode_item["defining_op_id"] = nb::none();
    }
    varnode_item["use_op_ids"] = use_op_ids;
    return varnode_item;
}

}  // namespace

nb::dict pcode_to_dict(const ghidra::Funcdata& function) {
    const EnrichedIndex index = build_enriched_index(function);
    nb::list pcode_ops;
    for (const ghidra::PcodeOp* op : index.pcode_ops) {
        pcode_ops.append(pcode_op_to_dict(*op, index));
    }

    nb::list varnodes;
    for (const ghidra::Varnode* varnode : index.varnodes) {
        varnodes.append(varnode_to_dict(*varnode, index));
    }

    nb::dict pcode;
    pcode["pcode_ops"] = pcode_ops;
    pcode["varnodes"] = varnodes;
    return pcode;
}

}  // namespace flatline::native_bridge
