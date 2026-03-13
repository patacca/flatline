.text
.globl fx_add_arm64
fx_add_arm64:
    add w0, w0, w1
    ret

    # Ghidra performs a small decode/lookahead past the terminal return.
    .fill 16, 1, 0x00
