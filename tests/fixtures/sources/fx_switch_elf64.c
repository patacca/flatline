int switch_blocks(int x, int y) {
    switch (x) {
        case 0:
            y += 11;
            break;
        case 1:
            y = y * 3 - 1;
            break;
        case 2:
            y ^= 0x1234;
            break;
        case 3:
            y /= 3;
            break;
        case 4:
            y <<= 2;
            break;
        case 5:
            y -= 77;
            break;
        case 6:
            y = y * y;
            break;
        case 7:
            y %= 5;
            break;
        default:
            y = -1;
            break;
    }
    return y;
}
