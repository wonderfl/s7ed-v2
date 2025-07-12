text0 = "낙랑"
text1 = "양평"
text2 = "하후돈"
text3 = "유여"
text3 = "주노"
hex_bytes0 = text0.encode("euc-kr")
hex_bytes1 = text1.encode("euc-kr")
hex_bytes2 = text2.encode("euc-kr")
hex_bytes3 = text3.encode("euc-kr")
print(hex_bytes0.hex().upper(), hex_bytes1.hex().upper(), hex_bytes2.hex().upper())  # 출력: BFC0BCD220C8ABBBE7
print(hex_bytes3.hex().upper())




hex1 = "C0B0B5B5"

hex_string = "BAF1B0CB"# 비검
hex_string = "B4DCB1D8"#단극
hex_string = "C3B6C1FABFA9B0F1C5B8"#철질여골타
hex_string = "C8BFB0E6C0FC"#효경전
hex_string = "B9E6C3B5C8ADB1D8"#방천화극
hex_string = "C1D6B3EB"#주노
hex_string = "C8B2BAB80000C0AF"

hex_string = "BEC6C8B8B3B2"
hex_string = "C0E5BFC2"
hex_string = "C0B0B5B5"
hex_string = "B4EBBAD8"
byte_data = bytes.fromhex(hex_string)
hangul_text = byte_data.decode("euc-kr")
print(hangul_text)  # 출력: 위소 홍사

