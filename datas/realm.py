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

#                              '<  4  22s 54s 54s 4  30s  ')  # 총 168 bytes
#                              '<  OO xxx xxx xxx xx xxx ')  # 총 168 bytes
RealmStateStruct = struct.Struct('<HH 22s 54s 54s HH 30s ')  # 총 168 bytes
class RealmState:
  def __init__(self, num, raw_data):
    unpacked = RealmStateStruct.unpack(raw_data)

    ruler = unpacked[0]    
    staff = unpacked[1]

    self.num = num
    self.ruler = ruler
    self.staff = staff  

  def __repr__(self):
      return str(self.ruler) + "[ " + str(self.staff)  +" ]"    