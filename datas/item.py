import struct
import globals as gl

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
ItemStateStruct = struct.Struct('<IHH 16s BBBBH 5H')  # 총 40 bytes
class ItemState:
  def __init__(self, raw_data):
    unpacked = ItemStateStruct.unpack(raw_data)

    u00 = unpacked[0]
    owner = unpacked[1]
    market = unpacked[2] # 3 은 마켓
    name0 = unpacked[3]

    item_type = unpacked[4]
    num = unpacked[5] # num
    price = unpacked[6] # x100 price
    stats = unpacked[7] # bonus value
    value4 = unpacked[8]

    self.u00 = u00
    self.propstr = ','.join([str for i, str in enumerate(gl._propNames_) if gl.bit32from(self.u00, i, 1)])

    self.owner = owner
    self.market = market
    self.name = name0.split(b'\x00')[0].decode("euc-kr", errors="ignore")

    self.item_type = item_type
    self.num = num
    self.price = price*100
    self.stats = stats
    self.v4 = value4
    
  def __repr__(self):
      owner = None
      if( 0 <= self.owner and self.owner < len(gl.generals)):
          owner = gl.generals[self.owner]

      return "[{0}][ {2} {3} {4}  {5} {6:4} {7}] {1:8}".format(owner.fixed if owner is not None else "   -    ", \
          self.name, gl._itemTypes_[self.item_type], gl._itemStats_[self.item_type] if 0 < self.stats else ' -  ', \
          '+'+"{0:<2}".format(self.stats) if 0 < self.stats else '-  ', self.propstr if 0<self.u00 else '    ', \
          self.price if 0<self.price else '   -', '$' if 3 == self.market else ' ' )