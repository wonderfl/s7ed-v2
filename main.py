import sys
import re

import globals
from globals import ActionMenu

import commands.files

import commands.listup
import commands.search
import commands.game

import gui.gui as gui

def quit():
    exit(0)

def whoiam():
    gn = len(globals.generals)
    cn = len(globals.cities)
    print(f"장수 수: {gn}, 도시 수: {cn}")
    if gn == 0 or cn == 0:
        print("장수나 도시 데이터가 없습니다. 먼저 'load' 명령어로 데이터를 불러오세요.")
        return
    
    hero = globals.generals[globals._hero]
    if not hero:
        print("영웅을 찾을 수 없습니다.")
        return
    home = [city for city in cities if city.num == hero.city]
    if not home:
        print("영웅의 도시를 찾을 수 없습니다.")
        return

    print(f"{globals.generals[globals._hero]}")
    print(f"{home[0]}")

def help():
    print("도움말:")
    print("search - 조건으로 검색합니다.")
    print("load - 저장된 파일을 불러옵니다.")
    print("save - 데이터를 파일에 저장합니다.")
    print("play - 게임을 진행합니다.")
    print("who, 누구 - 주인공정보를 보여줍니다.")
    print("quit, exit, 종료 - 프로그램 종료")

def popup():
    gui.app()

# "command", "menu", "action", "help"
main_commands = {
    "H": ActionMenu("help", help, 0, "도움말을 보여줍니다."),
    "I": ActionMenu("whoi", whoiam, 0, "주인공 정보를 보여줍니다."),
    
    "1": ActionMenu("home", commands.files.files, 1, "파일을 관리합니다."),
    "2": ActionMenu("listup", commands.listup.listup, 3, "정보를 확인합니다."),
    "3": ActionMenu("search", commands.search.search, 3, "검색을 시작합니다."),

    "5": ActionMenu("popup", popup, 3, "검색을 시작합니다."),

    "8": ActionMenu("play", commands.game.game_play, 4, "게임을 시작합니다."),
    "0": ActionMenu("exit", quit, 9, "프로그램을 종료합니다."),}


args = sys.argv[1:]
if len(args) > 1:
    if args[0] == "--load" or args[0] == "-l":    
       _load = args[1]

menu = 0
filtered = [(key, value[0]) for key, value in main_commands.items() if value[2] != 0]

commands.files.load_file(True)

popup()
exit()

cmds = ": "+", ".join( f"{key}.{name}" for key, name in filtered)
while True:
    text = input("\n{0}\n\n? ".format(cmds))
    params = [p for p in re.split(r'[ .,]', text) if p]
    if( 0 >= len(params)):
        print(" . 명령어를 입력하세요..")
        continue

    #print("명령어:", params, len(params))
    command = main_commands.get(params[0])
    if not command:
        print(f" . '{params[0]}' 명령어를 찾을 수 없습니다.")
        continue
    if not command.action:
        print(f" . '{params[0]}' 명령어는 실행할 수 없습니다.")
        continue

    gn = len(globals.generals)
    cn = len(globals.cities)
    if gn == 0 or cn == 0:
        print("장수나 도시 데이터가 없습니다. 먼저 'load' 명령어로 데이터를 불러오세요.")
        continue

    args = params[1:]    
    command.action(*args)

    continue   
    

#for i, general in enumerate(generals):
#    print(f"{i:03}: {general}")

#generals_dict = {general.name: general for general in generals}
#ln = len(generals_dict)
#print(ln)

# print(generals_dict.keys())
# name = "강유"
# if name in generals_dict:
#     print(generals_dict[name])    