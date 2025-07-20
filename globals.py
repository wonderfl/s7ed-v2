from collections import namedtuple

def bit16from(value: int, start: int, length: int) -> int:
    """주어진 정수 값에서 특정 비트 구간 추출"""
    return (value >> (16 - start - length)) & ((1 << length) - 1)

def bit16from2(value: int, start: int, length: int) -> int:
    return (value >> (start+1 - length)) & ((1 << length) - 1)

def bit32from(value: int, start: int, length: int) -> int:
    return (value >> (start+1 - length)) & ((1 << length) - 1)

_cityNames_ = [
    '낙랑', '양평', '북평', ' 계 ', '남피', ' 업 ', '평원', '북해', '성양', '진양',
    '상당', '하비', '소패', '복양', '진류', '허창', ' 초 ', '여남', '하내', '낙양',
    '홍농', '장안', '천수', '안정', '무위', '서량', '무도', '한중', '자동', '성도',
    '강주', '영안', '건녕', '운남', '영창', ' 완 ', '신야', '양양', '강하', '상용',
    '강릉', '장사', '영릉', '무릉', '계양', '수춘', '여강', '건업', ' 오 ', '회계',
    '시상', '건안', '남해', '교지', '없음']

_stateNames_ = ['군주','태수','군사','일반','재야',' +  ',' -  ',' X  ','없음']
_stateNames2 = ['군주','태수','군사','일반','재야','미발견','대기','사망']

_rankNames_ = ["5품관","4품관","3품관","2품관","1품관",]

_itemTypes_=[ "명마","무구","지도","의학","기서","병법","경서","역사","논문","옥새","보물","성수" ]
_itemStats_=[ "","무력","","","지력","지력","지력","정치","정치","매력","","" ]

_healthStates_=[ "양호", "경상A","경상B","경상C","경상D", "중상A","중상B","중상C"]

_tendencies_=[ "능력","명성","의리","자기" ]
_strategies_=[ "무관심","내정","방어","수호전","군비","모략","사욕" ]

_propNames_=[ 
   "첩보","발명","조교","상재","응사","반계","수습","정찰",
   "무쌍","돌격","일기","강행","수복","수군","화시","난사",
   "선동","신산","허보","천문","수공","고무","욕설","혈공",
   "귀모","성흔","행동","수련","의술","점복","평가","부호",
  ]

_prop1Names_=[ 
   "첩","발","교","상","응","반","습","정",
   "무","돌","일","강","복","수","화","난",
   "선","산","허","천","공","고","욕","혈",
   "귀","흔","행","련","의","점","평","부",
  ]

_equipNames_=[ 
   "활","등갑","기마","마갑","철갑","노","연노","정란",
   "벽력거","화포","코끼리","목수","병선","누선",
  ]
_equip1Names_=[ 
   "활","등","기","마","철","노","연","정",
   "벽","포","코","목","병","누",
  ]

_hero = 493
_home = 0
_load = "saves/D_Save01.s7"
_year = 189
_month = 3

current_year_offset = 0x00000019

generals = []
generals_offset = 0x0000009C  # 장수 데이터 시작 위치 예시
# 1 22A0 + 9c = 1 233C
generals_ends = 620 * 200 + 0x0000009C


items = []
items_offset = 0x0001234C  # 장수 데이터 시작 위치 예시
# B40 + 0x0001234C = 1 2E8C
items_ends = 72 * 40  + 0x0001234C


realms = []
realm_offset =  0x00012FCC  # 세력 데이터 시작 위치 예시 168bytes
realm_ends = 620 * 200 + 0x0000009C


cities = []
cities_offset = 0x000154C6  # 장수 데이터 시작 위치 예시
# D80 + 0x000154C6 = 1 6246
cities_ends = 64 * 54  + 0x000154C6


hero_golds = 0
hero_golds_offset = 0x00016246

relations = [] # 주인공과 친밀도
hero_relations_offset = 0x00016266
hero_relations_ends = hero_relations_offset + 2*620 # 0x0001673E

sentiments = [] # 각 도시별 민심
hero_sentiments_offset = 0x0001673E
hero_sentiments_ends = hero_sentiments_offset + 1*54


save_ends = 0x00019731

ActionMenu = namedtuple("ActionMenu", ["command", "action", "menu", "help"])