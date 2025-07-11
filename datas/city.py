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
        return self.name + "[ " + str(self.governor) + ","+ str(self.peoples) + "00,"+ str(self.golds) +","+ str(self.foods) +" ]" + \
            "[ " + str(self.devs)+"/"+ str(self.devmax) + ","+ str(self.shops) +"/"+ str(self.shopmax)+ " ]" + \
            "[ " + str(self.secu)+ ","+ str(self.tech)+ ","+ str(self.defs)+ " ]"