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

# -*- coding: utf-8 -*-          4 8    6   4  10    2 12     18     12  1 2  8        2  4    1 4    1   3 18
#                             '< O OOOO OOO OO xxxxx O xxxxOx OOOOOO xxx x OO OOOOOOOO OO OOxO B OOOO O OOO xxx')  # 총 120bytes
GeneralStruct = struct.Struct('< I HHHH HHH HH HHHHH H HHHHHH 6s6s6s 12s B BB BBBBBBBB BB BBBB B BBBB B BBB 18s')  # 총 120bytes
                               # 0 1234 567 89 01234 5 678901  2 3 4   5 6 78 90123456 78 9012 3 4567 8 901 234567890123456789012345678901234567890123456789
class General:
    def __init__(self, num, raw_data):
        self.unpack = GeneralStruct.unpack(raw_data)
        self.unpacked = list(self.unpack)
        
        self.get_unpacked(num)        

    def get_unpacked(self, num):
        properties  = self.unpacked[0]
        faceno  = self.unpacked[1]
        appearance = self.unpacked[2]        
        birthyear = self.unpacked[3]
        years = gl._year- birthyear
        employment = self.unpacked[4]

        achieve = self.unpacked[5]
        fame = self.unpacked[6]
        soldiers = self.unpacked[7]
        
        family = self.unpacked[8]
        parent = self.unpacked[9]
        
        value0 = self.unpacked[10]
        #.야망: 0123 1100
        #.의리: 4567 1111
        #.성별: 89 00
        #.용맹: ABC 101
        #.냉정: DEF 101
        self.ambition = gl.bit16from(value0, 8, 4)
        self.fidelity = gl.bit16from(value0,12, 4)
        self.gender   = gl.bit16from(value0, 0, 1)
        self.valour   = gl.bit16from(value0, 2, 3)
        self.composed = gl.bit16from(value0, 5, 3)

        value1 = self.unpacked[11]
        #.특성: 0123 0011 3 매력, 
        #.건강: 4567 0000
        #.성장: 89AB 0010 
        #.수명: CDEF 0111
        self.job      = gl.bit16from(value1, 8, 4)
        self.injury   = gl.bit16from(value1,12, 4)
        self.growth   = gl.bit16from(value1, 0, 4)
        self.lifespan = gl.bit16from(value1, 4, 4)

        value2 = self.unpacked[12]
        #.인물: 0123 0000
        #.전략: 4567 0011
        #.행동: 89AB 0000
        #.???: CDEF 0000
        self.tendency   = gl.bit16from(value2, 8, 4) # 인물경향
        self.strategy   = gl.bit16from(value2,12, 4) # 전략경향
        self.turned     = gl.bit16from(value2, 0, 1)
        self.opposite   = gl.bit16from(value2, 4, 4)

        value3 = self.unpacked[13]
        value4 = self.unpacked[14]

        colleague = self.unpacked[15]
        equips = self.unpacked[16]

        actions = self.unpacked[20]


        name0 = self.unpacked[22]
        name1 = self.unpacked[23]
        name2 = self.unpacked[24]
        
        state = self.unpacked[26]
        realm = self.unpacked[27]
        city = self.unpacked[28]

        str0 = self.unpacked[29]
        int0 = self.unpacked[30]
        pol0 = self.unpacked[31]
        chr0 = self.unpacked[32]

        str1 = self.unpacked[33]
        int1 = self.unpacked[34]
        pol1 = self.unpacked[35]
        chr1 = self.unpacked[36]

        loyalty = self.unpacked[37]
        title = self.unpacked[38]
        rank = self.unpacked[39]
        
        salary = self.unpacked[40] # 봉록
        training = self.unpacked[41] # 훈련
        relation = self.unpacked[43] # 상성

        item = self.unpacked[48] # 아이템        
        
        capture_ruler = self.unpacked[21] # 포획 군주

        ambush_cnt = self.unpacked[44] # 매복 횟수        
        ambush_realm = self.unpacked[45] # 매복 세력
        operate_cnt = self.unpacked[46] # 작전 횟수
        operate_realm = self.unpacked[47] # 작전 세력
        capture_cnt = self.unpacked[49] # 포획 횟수

        wins1 = self.unpacked[50] # 무술대회 우승
        wins2 = self.unpacked[51] # 한시대회 우승

        self.name0 = name0.split(b'\x00')[0].decode("euc-kr", errors="ignore")
        self.name1 = name1.split(b'\x00')[0].decode("euc-kr", errors="ignore")
        self.name2 = name2.split(b'\x00')[0].decode("euc-kr", errors="ignore")
        
        self.num = num
        self.name = self.name0 + self.name1.strip()
        
        #self.fixed = self.name if 4 <= len(self.name) else ' '+self.name+' ' if 3 <= len(self.name) else '  '+self.name+'  '
        self.fixed = pads.pad_string(self.name,8,'center')
        self.props = properties
        
        names = [ name for i, name in enumerate(gl._prop1Names_) if gl.bit32from(self.props, i, 1)]
        self.propstr = ''.join(name + (' ' if (i + 1) % 4 == 0 and i != len(names) - 1 else '') for i, name in enumerate(names))
        
        fixed = [
            name if gl.bit32from(self.props, i, 1) else '  '
            for i, name in enumerate(gl._prop1Names_)
        ]
        self.propfixed = ''.join(name for i, name in enumerate(fixed))

        self.faceno = faceno
        self.birthyear = birthyear
        self.years = years
        self.appearance = appearance 
        self.employment = employment 

        self.fame = fame
        self.achieve = achieve
        self.soldier = soldiers

        self.family = family
        self.parent = parent
        self.colleague = colleague
        self.equips = equips

        self.equipstr = ' '.join([str for i, str in enumerate(gl._equipNames_) if gl.bit16from2(self.equips, i, 1)])
        self.equipfixed = ''.join( [ str if gl.bit16from2(self.equips, i, 1) else '  ' for i, str in enumerate(gl._equip1Names_) ])

        self.actions = actions

        self.state = state
        self.realm = realm
        self.city = city
        self.rank = rank

        self.str = str0
        self.int = int0
        self.pol = pol0
        self.chr = chr0

        self.str1 = str1
        self.int1 = int1
        self.pol1 = pol1
        self.chr1 = chr1        

        self.loyalty = loyalty 
        self.item = item
        self.salary = salary
        self.training = training
        self.relation = relation

        #-----------------------------------------
        self.capture_ruler = capture_ruler # 포획 군주
        self.ambush_realm = ambush_realm # 매복 세력
        self.operate_realm = operate_realm # 작전 세력

        self.capture_cnt = capture_cnt # 포획 횟수
        self.ambush_cnt = ambush_cnt # 매복 횟수
        self.operate_cnt = operate_cnt # 작전 횟수
        
        self.wins1 = wins1
        self.wins2 = wins2               

    def get_turns(self):
        value = gl.get_bits(self.unpacked[12], 15, 1)
        return value
    
    def set_turns(self, value):
        data = self.unpacked[12]
        self.unpacked[12] = gl.set_bits(data, value, 15, 1)
        return self.unpacked[12]

    def to_bytes(self):
        values = []
        for key, val in vars(self).items():
            values.append(val)
        return struct.pack( GeneralStruct, *values)
    
    def to_keys(self):
        keys = []
        for key, val in vars(self).items():
            keys.append(key)
        return keys
    
    def to_values(self):
        values = []
        for key, val in vars(self).items():
            values.append(val)
        return values    
    
    def properties(self):
        #return "[{0}]".format(format(self.props, '032b'))
        return "[{0}]".format(self.propstr)
        #return "[{0}]".format(self.propfixed)
    
    def equipments(self):
        #return "[{0}]".format(format(self.equips, '016b'))
        return "[{0}]".format(self.equipstr)    
    
    def states(self):
        closeness = gl.relations[self.num]
        return "{0:>4}".format( self.fixed ) + \
            "[{0}{1:2} {2} {3} {4:3} ]".format( 
                " " if 0 == self.turned else "!", self.opposite, 
                gl._cityNames_[ self.city if self.city != 255 else 54 ],  
                gl._stateNames_[self.state], 
                closeness if 100 >= closeness else 100) 
    
    def states_detail(self):
        closeness = gl.relations[self.num]
        return "{0:>4}".format( self.fixed ) + \
            "[{0}{1:3} {2} {3} {4:3} ".format( 
                " " if 0 == self.turned else "!", self.opposite, 
                gl._cityNames_[ self.city if self.city != 255 else 54 ], 
                gl._stateNames_[self.state],
                closeness if 100 >= closeness else 100 ) +\
            "{0:3}:{1:3} {2} {3:3} ]".format( 
                self.years if 0<self.years else "  -", self.birthyear, 
                '남' if 0 == self.gender else '여', 
                self.family if self.family != self.num else "   " )
            
    
    def loyalties(self):        
        return "[{0:2} {1:3} {2:3} {3:3} ]".format( self.realm if self.realm != 255 else '  ', self.actions, self.salary, self.loyalty)
    
    def abilities(self):
        return "[ {0} {1} {2} {3} {4:2} {5:2} {6:3} ]".format( self.lifespan, self.growth, self.valour, self.composed, self.ambition, self.fidelity, self.relation )
    
    def stats(self):
        return "[ {0:3} {1:3} {2:3} {3:3} ]".format( self.str,self.int,self.pol,self.chr)
    
    def soldiers(self):
        return "[{0:>5}:{1:<3}]".format( self.soldier, self.training)
    
    def profiles(self):
        return self.states() + self.loyalties() + self.soldiers()
    
    def profiles2(self):
        return self.states_detail() + self.loyalties() + self.soldiers()    
    
    def details(self):
        return self.states_detail() + self.loyalties() + self.soldiers() + self.stats() + self.abilities()
    
    def details2(self):
        return self.states_detail() + self.loyalties() + self.soldiers() + self.properties() + self.equipments()    

    def __repr__(self):
        return self.profiles()
    



