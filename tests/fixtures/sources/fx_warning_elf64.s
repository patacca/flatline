.text
.globl fx_warning_elf64
fx_warning_elf64:
    cmpl $3, %edi
    ja .Ldefault
    leaq .Ltable(%rip), %rax
    movslq (%rax,%rdi,4), %rdi
    addq %rdi, %rax
    jmp *%rax
.Lcase0:
    movl $10, %eax
    ret
.Lcase1:
    movl $20, %eax
    ret
.Lcase2:
    movl $30, %eax
    ret
.Lcase3:
    movl $40, %eax
    ret
.Ldefault:
    movl $-1, %eax
    ret
    .p2align 2
.Ltable:
    .long .Lcase0 - .Ltable
    .long .Lcase1 - .Ltable
    .long .Lcase2 - .Ltable
    .long .Lcase3 - .Ltable
