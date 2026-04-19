/* gcc-flags: -O1 -fno-stack-protector -fno-pie -no-pie -nostdlib -static */

typedef struct {
    int x;
    int y;
    int z;
    int w;
} Point;

int target_func(int rows, int cols, int depth) {
    Point p = {1, 2, 3, 4};
    int total = 0;
    int i, j, k;
    int tmp;

    for (i = 0; i < rows; i++) {
        p.x = i * 2;
        for (j = 0; j < cols; j++) {
            p.y = j * 3;
            if (p.x + p.y > 10) {
                for (k = 0; k < depth; k++) {
                    p.z = k * 4;
                    tmp = p.x + p.y + p.z;
                    if (tmp % 2 == 0) {
                        total = total + tmp + p.w;
                    } else {
                        total = total - tmp;
                    }
                    p.w = p.w + 1;
                }
            } else {
                total = total + p.x;
            }
        }
        if (i % 3 == 0) {
            total = total * 2;
        } else if (i % 3 == 1) {
            total = total / 2;
        }
    }

    return total;
}
