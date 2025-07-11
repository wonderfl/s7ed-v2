import sys

from globals import generals, cities
from globals import __hero, __home, __load

from commands.search import search
from commands.load import load_file, save_file
from commands.game import game_play


from collections import namedtuple

#for i, general in enumerate(generals):
#    print(f"{i:03}: {general}")

#generals_dict = {general.name: general for general in generals}
#ln = len(generals_dict)
#print(ln)

# print(generals_dict.keys())
# name = "강유"
# if name in generals_dict:
#     print(generals_dict[name])

def quit():
    exit(0)

def whoiam():
    gn = len(generals)
    cn = len(cities)
    print(f"장수 수: {gn}, 도시 수: {cn}")
    if gn == 0 or cn == 0:
        print("장수나 도시 데이터가 없습니다. 먼저 'load' 명령어로 데이터를 불러오세요.")
        return
    
    hero = generals[__hero]
    if not hero:
        print("영웅을 찾을 수 없습니다.")
        return
    home = [city for city in cities if city.num == hero.city]
    if not home:
        print("영웅의 도시를 찾을 수 없습니다.")
        return

    print(f"{generals[__hero]}")
    print(f"{home[0]}")

def help():
    print("도움말:")
    print("search - 조건으로 검색합니다.")
    print("load - 저장된 파일을 불러옵니다.")
    print("save - 데이터를 파일에 저장합니다.")
    print("play - 게임을 진행합니다.")
    print("who, 누구 - 주인공정보를 보여줍니다.")
    print("quit, exit, 종료 - 프로그램 종료")


ActionMenu = namedtuple("ActionMenu", ["action", "menu", "help"])
commands = {
    "exit": ActionMenu(quit, 0, "프로그램을 종료합니다."),
    "help": ActionMenu(help, 0, "도움말을 보여줍니다."),
    "who": ActionMenu(whoiam, 0, "주인공 정보를 보여줍니다."),
    "play": ActionMenu(game_play, 2, "게임을 시작합니다."),
    "find": ActionMenu(search, 2, "검색을 시작합니다."),
    "load": ActionMenu(load_file, 2, "파일을 불러옵니다."),
    "save": ActionMenu(save_file, 2, "파일에 저장합니다."),
}

menu = 0
filtered = [key for key, value in commands.items() if value[1] != 0]


cmds = ", ".join(filtered)
while True:
    params = input(f"{cmds}\명령? ").split()
    if( 0 >= len(params)):
        print(" . 명령어를 입력하세요..")
        continue

    #print("명령어:", params, len(params))
    command = commands.get(params[0])
    if not command:
        print(f" . '{params[0]}' 명령어를 찾을 수 없습니다.")
        continue
    
    args = params[1:]
    if not command.action:
        print(f" . '{params[0]}' 명령어는 실행할 수 없습니다.")
        continue
    command.action(*args)
    continue
    
    