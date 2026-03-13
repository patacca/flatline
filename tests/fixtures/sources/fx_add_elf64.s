.text
.globl fx_add_elf64
fx_add_elf64:
    leal (%rdi,%rsi), %eax
    ret

    # Ghidra performs a small decode/lookahead past the terminal return.
    .fill 16, 1, 0x90
