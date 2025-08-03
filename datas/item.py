import struct
import globals as gl
import utils.padstr as pads

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

#                              '< 8   16  6     10')  # 총 64 bytes
#                              '< OO0 OOO xOOOO xx')  # 총 64 bytes
#                              '< 012 3   456789 0')  # 총 64 bytes
ItemStateStruct = struct.Struct('<IHH 16s BBBBBB 5H')  # 총 40 bytes
class ItemState:
    def __init__(self, raw_data):
        self.unpack = ItemStateStruct.unpack(raw_data)
        self.unpacked = list(self.unpack)
      
        self.get_unpacked()

    def get_unpacked(self):

        u00 = self.unpacked[0]
        owner = self.unpacked[1]
        market = self.unpacked[2] # 3 은 마켓
        name0 = self.unpacked[3]

        item_type = self.unpacked[4]
        num = self.unpacked[5] # num
        price = self.unpacked[6] # x100 price
        stats = self.unpacked[7] # bonus value
        next = self.unpacked[8] # next item num

        self.u00 = u00
        self.propstr = ','.join([str for i, str in enumerate(gl._propNames_) if gl.bit32from(self.u00, i, 1) ])
        #self.propstr = ''.join([str if gl.bit32from(self.u00, i, 1) else '' for i, str in enumerate(gl._prop1Names_) ])

        self.num = num
        self.owner = owner
        self.name = name0.split(b'\x00')[0].decode("euc-kr", errors="ignore")
        self.fixed = pads.pad_string(self.name, 12,'center')
        
        self.market = market
        self.item_type = item_type
        self.stats = stats
        self.price = price*100
        self.next = next
    
    def __repr__(self):
        owner = None
        if( 0 <= self.owner and self.owner < len(gl.generals)):
            owner = gl.generals[self.owner]

        return "{0}[ {1:3} {2}][ {3} {4} {5} {6:4} {7}] {8}".format(
            self.fixed
            ,owner.num if owner is not None else '   '
            ,owner.fixed if owner is not None else '   -    '
            ,gl._itemTypes_[self.item_type]
            ,gl._itemStats_[self.item_type] if 0 < self.stats else ' -  '
            ,'+'+"{0:<2}".format(self.stats) if 0 < self.stats else '-  '
            ,self.price if 0<self.price else '   -'
            ,'$' if 3 == self.market else ' '
            ,self.propstr if 0<self.u00 else '  '
)
  