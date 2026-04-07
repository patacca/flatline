"""Unit tests for VarnodeInfo subclass hierarchy.

These tests verify:
- All 8 VarnodeInfo subclasses exist and are importable
- Liskov substitution principle (issubclass checks)
- Frozen dataclass behavior (mutation raises error)
- SPACE_TO_CLASS dispatch table has correct entries
- No new fields added to subclasses
"""

from __future__ import annotations

import dataclasses

import pytest

from flatline.models.enums import VarnodeSpace
from flatline.models.types import VarnodeInfo
from flatline.models.varnodes import (
    SPACE_TO_CLASS,
    ConstVarnode,
    FspecVarnode,
    IopVarnode,
    JoinVarnode,
    RamVarnode,
    RegisterVarnode,
    StackVarnode,
    UniqueVarnode,
)


class TestVarnodeSubclassExistence:
    """Tests for subclass existence and importability."""

    def test_const_varnode_exists(self) -> None:
        """ConstVarnode class exists."""
        assert ConstVarnode is not None

    def test_register_varnode_exists(self) -> None:
        """RegisterVarnode class exists."""
        assert RegisterVarnode is not None

    def test_unique_varnode_exists(self) -> None:
        """UniqueVarnode class exists."""
        assert UniqueVarnode is not None

    def test_ram_varnode_exists(self) -> None:
        """RamVarnode class exists."""
        assert RamVarnode is not None

    def test_fspec_varnode_exists(self) -> None:
        """FspecVarnode class exists."""
        assert FspecVarnode is not None

    def test_iop_varnode_exists(self) -> None:
        """IopVarnode class exists."""
        assert IopVarnode is not None

    def test_join_varnode_exists(self) -> None:
        """JoinVarnode class exists."""
        assert JoinVarnode is not None

    def test_stack_varnode_exists(self) -> None:
        """StackVarnode class exists."""
        assert StackVarnode is not None


class TestLiskovSubstitution:
    """Tests for Liskov substitution principle."""

    def test_const_varnode_is_varnode_info(self) -> None:
        """ConstVarnode is a subclass of VarnodeInfo."""
        assert issubclass(ConstVarnode, VarnodeInfo)

    def test_register_varnode_is_varnode_info(self) -> None:
        """RegisterVarnode is a subclass of VarnodeInfo."""
        assert issubclass(RegisterVarnode, VarnodeInfo)

    def test_unique_varnode_is_varnode_info(self) -> None:
        """UniqueVarnode is a subclass of VarnodeInfo."""
        assert issubclass(UniqueVarnode, VarnodeInfo)

    def test_ram_varnode_is_varnode_info(self) -> None:
        """RamVarnode is a subclass of VarnodeInfo."""
        assert issubclass(RamVarnode, VarnodeInfo)

    def test_fspec_varnode_is_varnode_info(self) -> None:
        """FspecVarnode is a subclass of VarnodeInfo."""
        assert issubclass(FspecVarnode, VarnodeInfo)

    def test_iop_varnode_is_varnode_info(self) -> None:
        """IopVarnode is a subclass of VarnodeInfo."""
        assert issubclass(IopVarnode, VarnodeInfo)

    def test_join_varnode_is_varnode_info(self) -> None:
        """JoinVarnode is a subclass of VarnodeInfo."""
        assert issubclass(JoinVarnode, VarnodeInfo)

    def test_stack_varnode_is_varnode_info(self) -> None:
        """StackVarnode is a subclass of VarnodeInfo."""
        assert issubclass(StackVarnode, VarnodeInfo)


class TestFrozenDataclass:
    """Tests for frozen dataclass behavior."""

    def test_const_varnode_frozen(self) -> None:
        """ConstVarnode instances are immutable."""
        vn = ConstVarnode(
            id=1,
            space=VarnodeSpace.CONST,
            offset=42,
            size=4,
            flags=dataclasses.MISSING,
            defining_op_id=None,
            use_op_ids=[],
        )
        with pytest.raises(dataclasses.FrozenInstanceError):
            vn.id = 999  # type: ignore[misc]

    def test_register_varnode_frozen(self) -> None:
        """RegisterVarnode instances are immutable."""
        vn = RegisterVarnode(
            id=2,
            space=VarnodeSpace.REGISTER,
            offset=0,
            size=8,
            flags=dataclasses.MISSING,
            defining_op_id=None,
            use_op_ids=[],
        )
        with pytest.raises(dataclasses.FrozenInstanceError):
            vn.offset = 123  # type: ignore[misc]

    def test_unique_varnode_frozen(self) -> None:
        """UniqueVarnode instances are immutable."""
        vn = UniqueVarnode(
            id=3,
            space=VarnodeSpace.UNIQUE,
            offset=100,
            size=4,
            flags=dataclasses.MISSING,
            defining_op_id=5,
            use_op_ids=[10, 11],
        )
        with pytest.raises(dataclasses.FrozenInstanceError):
            vn.size = 8  # type: ignore[misc]

    def test_ram_varnode_frozen(self) -> None:
        """RamVarnode instances are immutable."""
        vn = RamVarnode(
            id=4,
            space=VarnodeSpace.RAM,
            offset=0x1000,
            size=1,
            flags=dataclasses.MISSING,
            defining_op_id=None,
            use_op_ids=[],
        )
        with pytest.raises(dataclasses.FrozenInstanceError):
            vn.offset = 0x2000  # type: ignore[misc]

    def test_fspec_varnode_frozen(self) -> None:
        """FspecVarnode instances are immutable."""
        vn = FspecVarnode(
            id=5,
            space=VarnodeSpace.FSPEC,
            offset=0,
            size=0,
            flags=dataclasses.MISSING,
            defining_op_id=None,
            use_op_ids=[],
            call_site_index=3,
        )
        with pytest.raises(dataclasses.FrozenInstanceError):
            vn.call_site_index = 999  # type: ignore[misc]

    def test_iop_varnode_frozen(self) -> None:
        """IopVarnode instances are immutable."""
        vn = IopVarnode(
            id=6,
            space=VarnodeSpace.IOP,
            offset=0,
            size=0,
            flags=dataclasses.MISSING,
            defining_op_id=None,
            use_op_ids=[],
            target_op_id=42,
        )
        with pytest.raises(dataclasses.FrozenInstanceError):
            vn.target_op_id = 999  # type: ignore[misc]

    def test_join_varnode_frozen(self) -> None:
        """JoinVarnode instances are immutable."""
        vn = JoinVarnode(
            id=7,
            space=VarnodeSpace.JOIN,
            offset=0,
            size=16,
            flags=dataclasses.MISSING,
            defining_op_id=None,
            use_op_ids=[],
        )
        with pytest.raises(dataclasses.FrozenInstanceError):
            vn.id = 999  # type: ignore[misc]

    def test_stack_varnode_frozen(self) -> None:
        """StackVarnode instances are immutable."""
        vn = StackVarnode(
            id=8,
            space=VarnodeSpace.STACK,
            offset=-16,
            size=8,
            flags=dataclasses.MISSING,
            defining_op_id=None,
            use_op_ids=[],
        )
        with pytest.raises(dataclasses.FrozenInstanceError):
            vn.offset = -32  # type: ignore[misc]


class TestSpaceToClassDispatch:
    """Tests for SPACE_TO_CLASS dispatch table."""

    def test_dispatch_table_has_eight_entries(self) -> None:
        """SPACE_TO_CLASS has exactly 8 entries."""
        assert len(SPACE_TO_CLASS) == 8

    def test_dispatch_table_const_mapping(self) -> None:
        """SPACE_TO_CLASS maps 'const' to ConstVarnode."""
        assert SPACE_TO_CLASS["const"] is ConstVarnode

    def test_dispatch_table_register_mapping(self) -> None:
        """SPACE_TO_CLASS maps 'register' to RegisterVarnode."""
        assert SPACE_TO_CLASS["register"] is RegisterVarnode

    def test_dispatch_table_unique_mapping(self) -> None:
        """SPACE_TO_CLASS maps 'unique' to UniqueVarnode."""
        assert SPACE_TO_CLASS["unique"] is UniqueVarnode

    def test_dispatch_table_ram_mapping(self) -> None:
        """SPACE_TO_CLASS maps 'ram' to RamVarnode."""
        assert SPACE_TO_CLASS["ram"] is RamVarnode

    def test_dispatch_table_fspec_mapping(self) -> None:
        """SPACE_TO_CLASS maps 'fspec' to FspecVarnode."""
        assert SPACE_TO_CLASS["fspec"] is FspecVarnode

    def test_dispatch_table_iop_mapping(self) -> None:
        """SPACE_TO_CLASS maps 'iop' to IopVarnode."""
        assert SPACE_TO_CLASS["iop"] is IopVarnode

    def test_dispatch_table_join_mapping(self) -> None:
        """SPACE_TO_CLASS maps 'join' to JoinVarnode."""
        assert SPACE_TO_CLASS["join"] is JoinVarnode

    def test_dispatch_table_stack_mapping(self) -> None:
        """SPACE_TO_CLASS maps 'stack' to StackVarnode."""
        assert SPACE_TO_CLASS["stack"] is StackVarnode

    def test_dispatch_table_all_values_are_subclasses(self) -> None:
        """All SPACE_TO_CLASS values are VarnodeInfo subclasses."""
        for space, cls in SPACE_TO_CLASS.items():
            assert issubclass(cls, VarnodeInfo), (
                f"{cls} for space '{space}' is not a VarnodeInfo subclass"
            )


class TestNoNewFields:
    """Tests that subclasses have no new fields beyond the base class."""

    def test_const_varnode_no_new_fields(self) -> None:
        """ConstVarnode has the same fields as VarnodeInfo."""
        base_fields = set(dataclasses.fields(VarnodeInfo))
        subclass_fields = set(dataclasses.fields(ConstVarnode))
        assert subclass_fields == base_fields

    def test_register_varnode_no_new_fields(self) -> None:
        """RegisterVarnode has the same fields as VarnodeInfo."""
        base_fields = set(dataclasses.fields(VarnodeInfo))
        subclass_fields = set(dataclasses.fields(RegisterVarnode))
        assert subclass_fields == base_fields

    def test_unique_varnode_no_new_fields(self) -> None:
        """UniqueVarnode has the same fields as VarnodeInfo."""
        base_fields = set(dataclasses.fields(VarnodeInfo))
        subclass_fields = set(dataclasses.fields(UniqueVarnode))
        assert subclass_fields == base_fields

    def test_ram_varnode_no_new_fields(self) -> None:
        """RamVarnode has the same fields as VarnodeInfo."""
        base_fields = set(dataclasses.fields(VarnodeInfo))
        subclass_fields = set(dataclasses.fields(RamVarnode))
        assert subclass_fields == base_fields

    def test_fspec_varnode_no_new_fields(self) -> None:
        """FspecVarnode has the same fields as VarnodeInfo."""
        base_fields = set(dataclasses.fields(VarnodeInfo))
        subclass_fields = set(dataclasses.fields(FspecVarnode))
        assert subclass_fields == base_fields

    def test_iop_varnode_no_new_fields(self) -> None:
        """IopVarnode has the same fields as VarnodeInfo."""
        base_fields = set(dataclasses.fields(VarnodeInfo))
        subclass_fields = set(dataclasses.fields(IopVarnode))
        assert subclass_fields == base_fields

    def test_join_varnode_no_new_fields(self) -> None:
        """JoinVarnode has the same fields as VarnodeInfo."""
        base_fields = set(dataclasses.fields(VarnodeInfo))
        subclass_fields = set(dataclasses.fields(JoinVarnode))
        assert subclass_fields == base_fields

    def test_stack_varnode_no_new_fields(self) -> None:
        """StackVarnode has the same fields as VarnodeInfo."""
        base_fields = set(dataclasses.fields(VarnodeInfo))
        subclass_fields = set(dataclasses.fields(StackVarnode))
        assert subclass_fields == base_fields
