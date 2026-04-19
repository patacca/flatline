/* gcc-flags: -O1 -fno-stack-protector -fno-pie -no-pie -nostdlib -static */

int target_func(int opcode, int a, int b) {
    int result = 0;
    switch (opcode) {
        case 0:
            result = a + b;
            break;
        case 1:
            result = a - b;
            break;
        case 2:
            result = a * b;
            break;
        case 3:
            if (b != 0) {
                result = a / b;
            } else {
                result = 0;
            }
            break;
        case 4:
            result = a & b;
            result = result | (a ^ b);
            break;
        default:
            result = a + (b * 2);
            if (result > 100) {
                result = result - 100;
            }
            break;
    }
    return result;
}
