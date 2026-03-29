.text
.globl fx_external_call_arm64
fx_external_call_arm64:
    stp x29, x30, [sp, #-16]!
    mov x29, sp
    bl helper_call
    mov w0, wzr
    ldp x29, x30, [sp], #16
    ret

helper_call:
    mov w0, #42
    ret
