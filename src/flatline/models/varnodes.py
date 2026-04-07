"""VarnodeInfo subclass hierarchy for typed varnode spaces.

This module provides specialized subclasses of VarnodeInfo for each address space
defined in VarnodeSpace. Each subclass is a frozen dataclass with no additional
fields, allowing type-safe varnode handling while preserving the base class contract.

The SPACE_TO_CLASS dispatch table maps space strings to their corresponding
subclass, enabling runtime type selection based on the varnode's space field.
"""

from __future__ import annotations

from dataclasses import dataclass

from flatline.models.types import VarnodeInfo


@dataclass(frozen=True)
class ConstVarnode(VarnodeInfo):
    """Varnode in the const address space.

    The offset field contains the literal constant value.
    """

    pass


@dataclass(frozen=True)
class RegisterVarnode(VarnodeInfo):
    """Varnode in the register address space.

    The offset field contains the register number in the processor specification.
    """

    pass


@dataclass(frozen=True)
class UniqueVarnode(VarnodeInfo):
    """Varnode in the unique address space.

    The offset field contains an internal temporary allocation ID (opaque).
    """

    pass


@dataclass(frozen=True)
class RamVarnode(VarnodeInfo):
    """Varnode in the ram address space.

    The offset field contains the virtual memory address.
    """

    pass


@dataclass(frozen=True)
class FspecVarnode(VarnodeInfo):
    """Varnode in the fspec address space.

    Call-spec reference. The offset field is set to 0; use call_site_index
    instead for the meaningful value.
    """

    pass


@dataclass(frozen=True)
class IopVarnode(VarnodeInfo):
    """Varnode in the iop address space.

    Internal op pointer. The offset field is set to 0; use target_op_id
    instead for the meaningful value.
    """

    pass


@dataclass(frozen=True)
class JoinVarnode(VarnodeInfo):
    """Varnode in the join address space.

    Split/merged variable storage (opaque).
    """

    pass


@dataclass(frozen=True)
class StackVarnode(VarnodeInfo):
    """Varnode in the stack address space.

    The offset field contains the stack-frame offset.
    """

    pass


# Dispatch table mapping space strings to VarnodeInfo subclasses.
# Used for runtime type selection based on the varnode's space field.
SPACE_TO_CLASS: dict[str, type[VarnodeInfo]] = {
    "const": ConstVarnode,
    "register": RegisterVarnode,
    "unique": UniqueVarnode,
    "ram": RamVarnode,
    "fspec": FspecVarnode,
    "iop": IopVarnode,
    "join": JoinVarnode,
    "stack": StackVarnode,
}


__all__ = [
    "SPACE_TO_CLASS",
    "ConstVarnode",
    "FspecVarnode",
    "IopVarnode",
    "JoinVarnode",
    "RamVarnode",
    "RegisterVarnode",
    "StackVarnode",
    "UniqueVarnode",
]
