w, h = map(int, open("/sys/class/graphics/fb0/virtual_size").read().strip().split(","))
bpp = int(open("/sys/class/graphics/fb0/bits_per_pixel").read())
colores = [(255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 255)]

def px(r, g, b):
    if bpp == 16:
        return (((r >> 3) << 11) | ((g >> 2) << 5) | (b >> 3)).to_bytes(2, "little")
    return bytes([b, g, r, 0])

fila = b"".join(px(*colores[x * 4 // w]) for x in range(w))
open("/dev/fb0", "wb").write(fila * h)
print(w, h, bpp)
