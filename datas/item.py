import struct

# 포맷   의미	         크기
# b     signed char	    1바이트
# B	    unsigned char	1바이트
# h	    short	        2바이트
# H	    unsigned short	2바이트
# i	    int	            4바이트
# I	    unsigned int	4바이트
# f	    float	        4바이트
# d	    double	        8바이트
# s	    bytes	        지정 길이

#                              '< 4  16  20 ')  # 총 64 bytes
#                              '< OO O0 O00')  # 총 64 bytes
ItemStateStruct = struct.Struct('<HH 16s 10H')  # 총 40 bytes
class ItemState:
  def __init__(self, num, raw_data):
    unpacked = ItemStateStruct.unpack(raw_data)

    owner = unpacked[0]
    unkown01 = unpacked[1]
    name0 = unpacked[2]

    self.num = num    
    self.owner = owner
    self.name = name0.split(b'\x00')[0].decode("euc-kr", errors="ignore")
    
  def __repr__(self):
      return self.name + "[ " + str(self.owner)  +" ]"