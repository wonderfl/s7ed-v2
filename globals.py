from collections import namedtuple

_hero = 493
_home = 0
_load = "saves/D_Save01.s7"
_year = 189
_month = 3

current_year_offset = 0x00000019

generals_offset = 0x0000009C  # 장수 데이터 시작 위치 예시
# 1 22A0 + 9c = 1 233C
generals_ends = 620 * 200 + 0x0000009C
generals = []

items_offset = 0x00012350  # 장수 데이터 시작 위치 예시
# B40 + 0x00012350 = 1 2E90
items_ends = 72 * 40  + 0x00012350
items = []

realm_offset =  0x00012FCC  # 세력 데이터 시작 위치 예시 168bytes
realm_ends = 620 * 200 + 0x0000009C
realms = []

cities_offset = 0x000154C6  # 장수 데이터 시작 위치 예시
# D80 + 0x000154C6 = 1 6246
cities_ends = 64 * 54  + 0x000154C6
cities = []

hero_gold_offset = 0x00016246
save_ends = 0x00019731

ActionMenu = namedtuple("ActionMenu", ["command", "action", "menu", "help"])