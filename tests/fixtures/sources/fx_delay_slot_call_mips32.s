.text
.set noreorder
.globl fx_delay_slot_call_mips32
fx_delay_slot_call_mips32:
    jal helper
    addiu $4, $0, 9
    move $2, $4
    jr $31
    nop
helper:
    addu $2, $4, $5
    jr $31
    nop

    .fill 16, 1, 0x00
