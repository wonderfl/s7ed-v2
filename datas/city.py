import struct

import globals  as gl

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

#                              '<  12  4    8   6   6      6 22')  # 총 64 bytes
#                              '< OOO OO OOOO OOO xxx Oxxxxx xx')  # 총 64 bytes
#                              '< 012 34 5678 901 234 567890 1')  # 총 64 bytes
CityStateStruct = struct.Struct('<III HH HHHH HHH HHH BBBBBB 22s')  # 총 64 bytes
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
        realm = unpacked[15]

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
        self.realm = realm


    def profiles(self):
        senti = gl.sentiments[self.num]
        name = "   -    "
        if( 0 <= self.governor and self.governor < len(gl.generals)):
            gov = gl.generals[self.governor]
            name = gov.fixed
        return self.name + "[{0:3},{1:>4}]".format( self.realm, name ) + "[{0:7},{1:3},{2:7},{3:7}]".format( self.peoples*100, senti, self.golds, self.foods)
    
    def profiles2(self):
        senti = gl.sentiments[self.num]
        return self.name + "[{0:7},{1:3},{2:7},{3:7}]".format( self.peoples*100, senti, self.golds, self.foods)    

    def details(self):
        return self.profiles()+ \
            "[{0:4} /{1:4} {2:4} /{3:4}]".format( self.devs, self.devmax, self.shops,self.shopmax)+ \
            "[{0:3} {1:4} {2:4}]".format(self.secu, self.defs, self.tech)
    
    def details2(self):
        return self.profiles2()+ \
            "[{0:4} /{1:4} {2:4} /{3:4}]".format( self.devs, self.devmax, self.shops,self.shopmax)+ \
            "[{0:3} {1:4} {2:4}]".format(self.secu, self.defs, self.tech)

    def __repr__(self):
        return self.profiles()
