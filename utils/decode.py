__str = \
"41 5C 19 E3 F0 3C EE 43 76 FE F1 A7 45 D9 C8 2A \
 CB C9 DC 8E 1B 59 5D 18 A1 08 82 F6 23 6B DB A6 \
 FD 1E 51 12 F3 4F EF E7 A5 E8 4B D6 7C 68 FF 56 \
 6C 86 17 F5 A3 95 AD 8F 83 0E EB 07 36 A0 39 AC \
 4C 74 49 11 8C D5 3F E2 42 5A EA 67 96 85 91 26 \
 9A C2 2F EC 97 24 46 32 64 20 65 B7 53 7F 40 E5 \
 2E DA CF 2D 4E ED FB 90 81 E9 B1 9D 80 77 F7 7E \
 A4 6A 57 09 62 35 55 BD 5F 9B 6D A8 16 C3 4D 75 \
 22 1C 03 0B 54 48 1D 3A 78 93 30 BA 92 9F 0A 02 \
 2C AF 50 6E 44 B3 FC 4A C5 79 31 FA 69 9C C0 CC \
 13 F8 1A 34 D8 B0 B4 14 72 84 BB E4 8A C4 AB E1 \
 B5 8D D0 0C 37 CA D1 47 CE 15 0D 0F 27 99 01 89 \
 58 61 A9 D3 C1 28 AE 00 70 21 5B 05 04 F2 B9 3B \
 5E 98 BC 06 AA 94 A2 F9 3E B8 29 7D F4 E0 B6 66 \
 63 73 C7 D2 38 8B 6F 52 33 88 3D 1F C6 10 7A 2B \
 D4 87 25 E6 9E DF B2 D7 DE 71 BF 7B 60 DD BE CD"

__list = __str.split()
__exch = bytes(int(h, 16) for h in __list)

def __decrypt(data: bytes ) -> bytes:
    return bytes( __exch[b] for b in data)