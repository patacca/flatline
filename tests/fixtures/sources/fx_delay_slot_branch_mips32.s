.text
.set noreorder
.globl fx_delay_slot_branch_mips32
fx_delay_slot_branch_mips32:
    beq $4, $5, equal
    addiu $2, $0, 7
    addiu $2, $0, 3
equal:
    jr $31
    nop

    .fill 16, 1, 0x00
