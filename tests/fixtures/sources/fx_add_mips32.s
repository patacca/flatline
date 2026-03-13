.text
.set noreorder
.globl fx_add_mips32
fx_add_mips32:
    addu $2, $4, $5
    jr $31
    nop

    # Ghidra performs a small decode/lookahead past the terminal return.
    .fill 16, 1, 0x00
