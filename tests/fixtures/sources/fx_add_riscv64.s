.text
.globl fx_add_riscv64
fx_add_riscv64:
    addw a0, a0, a1
    ret

    # Ghidra performs a small decode/lookahead past the terminal return.
    .fill 16, 1, 0x00
