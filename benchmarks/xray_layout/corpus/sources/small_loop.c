/* gcc-flags: -O1 -fno-stack-protector -fno-pie -no-pie -nostdlib -static */

int target_func(int n, int offset) {
    int sum = 0;
    int i;
    for (i = 0; i < n; i++) {
        sum = sum + i + offset;
        if (sum < 0) {
            sum = 0;
        }
    }
    return sum;
}
