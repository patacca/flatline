/* gcc-flags: -O1 -fno-stack-protector -fno-pie -no-pie -nostdlib -static */

int target_func(int x, int y) {
    if (x > y) {
        return x - y;
    } else {
        return y - x;
    }
}
