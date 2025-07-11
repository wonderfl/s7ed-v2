import struct

_CITY_ = [
    '낙랑', '양평', '북평', '  계', '남피', '  업', '평원', '북해', '성양', '진양',
    '상당', '하비', '소패', '복양', '진류', '허창', '  초', '여남', '하내', '낙양',
    '홍농', '장안', '천수', '안정', '무위', '서량', '무도', '한중', '자동', '성도',
    '강주', '영안', '건녕', '운남', '영창', '  완', '신야', '양양', '강하', '상용',
    '강릉', '장사', '영릉', '무릉', '계양', '수춘', '여강', '건업', '  오', '회계',
    '시상', '건안', '남해', '교지', '없음'
]

_STATE_ = [
    '군주','태수','군사','일반','재야',' -  ','대기','사망',
]

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


# -*- coding: utf-8 -*-           4   8   6  4   10   2   12     18   12  1 2  8        2  4    1 2  2  1 21
#                             '< OO OOOO OOO OO xxxxx O xxxxOx OOOOOO xxx x OO OOOOOOOO OO OOxO B BB BB B xxx')  # 총 120bytes
GeneralStruct = struct.Struct('< 4s HHHH HHH HH HHHHH H HHHHHH 6s6s6s 12s B BB BBBBBBBB BB BBBB B BB BB B 21s')  # 총 120bytes
class General:
    def __init__(self, num, raw_data):
        unpacked = GeneralStruct.unpack(raw_data)
        

        properties  = unpacked[0]

        faceno  = unpacked[1]
        appearance = unpacked[2]        
        birthyear = unpacked[3]
        employment = unpacked[4]

        achieve = unpacked[5]
        fame = unpacked[6]
        soldiers = unpacked[7]
        
        family = unpacked[8]
        parent = unpacked[9]
        colleague = unpacked[15]

        actions = unpacked[20]
        capture_ruler = unpacked[21]

        name0 = unpacked[22]
        name1 = unpacked[23]
        name2 = unpacked[24]
        
        state = unpacked[26]
        realm = unpacked[27]
        city = unpacked[28]

        str0 = unpacked[29]
        int0 = unpacked[30]
        pol0 = unpacked[31]
        chr0 = unpacked[32]

        str1 = unpacked[33]
        int1 = unpacked[34]
        pol1 = unpacked[35]
        chr1 = unpacked[36]

        loyalty = unpacked[37]
        title = unpacked[38]
        rank = unpacked[39]
        
        salary = unpacked[40] # 봉록
        training = unpacked[41] # 훈련
        relation = unpacked[43] # 상성
        
        item = unpacked[48] # 아이템

        self.name0 = name0.split(b'\x00')[0].decode("euc-kr", errors="ignore")
        self.name1 = name1.split(b'\x00')[0].decode("euc-kr", errors="ignore")
        self.name2 = name2.split(b'\x00')[0].decode("euc-kr", errors="ignore")
        
        self.num = num        
        self.name = self.name0 + self.name1
        self.props = properties
        self.faceno = faceno
        self.birthyear = birthyear
        self.appearance = appearance 
        self.employment = employment 

        self.fame = fame
        self.achieve = achieve
        self.soldier = soldiers

        self.family = family
        self.parent = parent
        self.colleague = colleague

        self.state = state
        self.realm = realm
        self.city = city

        self.str = str0
        self.int = int0
        self.pol = pol0
        self.chr = chr0
        self.loyaty = loyalty 
        self.item = item
        self.salary = salary
        self.training = training
        self.relation = relation
        self.actions = actions
    
    def properties(self):
        return "[ " + format(self.props[0], '08b')+","+ format(self.props[1], '08b') + ","+ format(self.props[2], '08b') +","+ format(self.props[3], '08b') + " ]"
    
    def states(self):
        return "{0:>3}".format(self.name if len(self.name) > 2 else '  '+self.name) + "[ "+ _CITY_[ self.city if self.city != 255 else 54 ]+":"+ _STATE_[self.state]+", " +str(self.birthyear)+'년' + " ]"
    
    def states2(self):
        return "[ " + "{0:>3}:{1:<3}".format(str(self.faceno),str(self.family)) +" ]"
    
    def loyalties(self):
        return "[ " +"{0},{1:>3}:{2},{3}".format( self.realm if self.realm != 255 else '-', self.salary, self.loyaty, self.actions)+" ]"    
    
    def relations(self):
        return "[ " + str(self.relation) +" ]"
    
    def stats(self):
        return "[ " + str(self.str) +","+ str(self.int)+ ","+str(self.pol)+","+str(self.chr)+" ]"
    
    def soldiers(self):
        return "[ " + str(self.soldier)+","+ str(self.training)+" ]"

    def __repr__(self):
        return self.states() + self.states2() + self.loyalties() + self.stats() + self.soldiers() 



