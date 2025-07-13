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

#                              '<  12  4    8   6  34')  # 총 64 bytes
#                              '< OOO OO OOOO OOO xxx')  # 총 64 bytes
CityStateStruct = struct.Struct('<III HH HHHH HHH 34s')  # 총 64 bytes
class CityState:
    def __init__(self, num, name, raw_data):
        unpacked = CityStateStruct.unpack(raw_data)
        self.num = num
        self.name = name

        golds  = unpacked[0]
        foods  = unpacked[1]
        governor = unpacked[3]
        peoples = unpacked[4]
        
        devs = unpacked[5]
        devmax = unpacked[6]
        shops = unpacked[7]
        shopmax = unpacked[8]

        secu = unpacked[9]
        defs = unpacked[10]
        tech = unpacked[11]        

        self.golds = golds
        self.foods = foods
        self.governor = governor
        self.peoples = peoples

        self.devs = devs
        self.devmax = devmax
        self.shops = shops
        self.shopmax = shopmax

        self.secu = secu
        self.defs = defs
        self.tech = tech        


    def __repr__(self):

        name = "   -    "
        if( 0 <= self.governor and self.governor < len(generals)):
            gov = generals[self.governor]
            name = gov.fixed
        return self.name + \
            "[{0:>4}]".format( name ) + \
            "[{0:7},{1:7},{2:7}]".format( self.peoples*100, self.golds, self.foods) + \
            "[{0:4} /{1:4} {2:4} /{3:4}]".format( self.devs, self.devmax, self.shops,self.shopmax)+ \
            "[{0:3} {1:4} {2:4}]".format(self.secu, self.tech, self.defs)