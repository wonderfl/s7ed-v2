import struct
from globals import generals, cities

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
RealmStateStruct = struct.Struct('<HH 6s 2s2s2s2s 8s 54s 54s HH 30s ')  # 총 168 bytes
class RealmState:
    def __init__(self, num, raw_data):
        self.unpack = RealmStateStruct.unpack(raw_data)
        self.unpacked = list(self.unpack)
      
        self.get_unpacked(num)

    def get_unpacked(self, num):
        ruler = self.unpacked[0]    
        staff = self.unpacked[1]
        
        name0 = self.unpacked[3]
        name1 = self.unpacked[4]
        name2 = self.unpacked[5]
        name3 = self.unpacked[6]

        self.num = num
        self.ruler = ruler
        self.staff = staff
        self.name = name0.split(b'\x00')[0].decode("euc-kr", errors="ignore") + \
            name1.split(b'\x00')[0].decode("euc-kr", errors="ignore") + \
            name2.split(b'\x00')[0].decode("euc-kr", errors="ignore") + \
            name3.split(b'\x00')[0].decode("euc-kr", errors="ignore")

    def __repr__(self):
        ruler = None
        if( 0 <= self.ruler and self.ruler < len(generals)):
            ruler = generals[self.ruler]

        staff = None
        if( 0 <= self.staff and self.staff < len(generals)):            
            staff = generals[self.staff]

        return ruler.states() + "[{0}] {1}".format(staff.fixed if staff is not None else "   -    ", self.name)