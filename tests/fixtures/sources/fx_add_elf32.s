.text
.globl fx_add_elf32
fx_add_elf32:
    movl 4(%esp), %eax
    addl 8(%esp), %eax
    ret

    # Ghidra performs a small decode/lookahead past the terminal return.
    .fill 16, 1, 0x00
