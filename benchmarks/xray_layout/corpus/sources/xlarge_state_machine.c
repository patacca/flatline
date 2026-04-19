/* gcc-flags: -O1 -fno-stack-protector -fno-pie -no-pie -nostdlib -static */

typedef struct {
    int state;
    int counter;
    int accum;
    int prev;
    int flags;
    int temp_a;
    int temp_b;
    int temp_c;
} MachineState;

int target_func(int input, int limit) {
    MachineState m;
    int result = 0;
    int i = 0;

    m.state = 0;
    m.counter = 0;
    m.accum = 0;
    m.prev = 0;
    m.flags = 0;
    m.temp_a = 0;
    m.temp_b = 0;
    m.temp_c = 0;

state_start:
    if (i >= limit) goto state_exit;
    m.counter = i;
    m.temp_a = input + i;

state_check_a:
    if (m.temp_a < 10) goto state_low;
    if (m.temp_a < 50) goto state_mid_low;
    if (m.temp_a < 100) goto state_mid_high;
    goto state_high;

state_low:
    m.state = 1;
    m.accum = m.accum + m.temp_a;
    m.temp_b = m.temp_a * 2;
    m.temp_c = m.temp_b + 5;
    if (m.temp_c > 20) {
        m.flags = m.flags | 1;
    }
    m.prev = m.temp_c;
    i = i + 1;
    goto state_start;

state_mid_low:
    m.state = 2;
    m.temp_b = m.temp_a - 10;
    m.temp_c = m.temp_b * 3;
    m.accum = m.accum + m.temp_c;
    if (m.accum > 100) {
        m.flags = m.flags | 2;
        m.accum = m.accum - 50;
    }
    m.prev = m.temp_b;
    result = result + m.accum;
    i = i + 1;
    goto state_start;

state_mid_high:
    m.state = 3;
    m.temp_b = m.temp_a - 50;
    m.temp_c = m.temp_b * 4;
    m.temp_a = m.temp_c + m.prev;
    m.accum = m.accum + m.temp_a;
    if (m.temp_a % 2 == 0) {
        m.flags = m.flags | 4;
    } else {
        m.flags = m.flags | 8;
    }
    if (m.accum > 200) {
        m.accum = m.accum / 2;
        m.flags = m.flags | 16;
    }
    m.prev = m.temp_a;
    result = result + m.temp_c;
    i = i + 1;
    goto state_start;

state_high:
    m.state = 4;
    m.temp_b = m.temp_a - 100;
    m.temp_c = m.temp_b * m.temp_b;
    m.accum = m.accum + m.temp_c;
    m.temp_a = m.temp_c - m.prev;
    if (m.temp_a < 0) {
        m.temp_a = -m.temp_a;
        m.flags = m.flags | 32;
    }
    m.prev = m.temp_a;
    result = result + m.accum;
    if (m.counter % 3 == 0) {
        result = result * 2;
    } else if (m.counter % 3 == 1) {
        result = result / 2;
    } else {
        result = result + 1;
    }
    i = i + 1;
    goto state_start;

state_exit:
    result = result + m.accum;
    if (m.flags & 1) {
        result = result + 1;
    }
    if (m.flags & 2) {
        result = result + 10;
    }
    if (m.flags & 4) {
        result = result + 100;
    }
    if (m.flags & 8) {
        result = result - 50;
    }
    if (m.flags & 16) {
        result = result * 2;
    }
    if (m.flags & 32) {
        result = result / 2;
    }
    return result;
}
