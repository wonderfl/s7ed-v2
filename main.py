import sys
import re
import os

# MediaPipe 경고 메시지 억제 (가장 먼저 설정)
os.environ['GLOG_minloglevel'] = '3'  # FATAL만 표시 (0=INFO, 1=WARNING, 2=ERROR, 3=FATAL)
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'  # TensorFlow 로그 완전 억제

# absl.logging 억제 (MediaPipe가 import되기 전에 설정)
try:
    import absl.logging
    absl.logging.set_verbosity(absl.logging.ERROR)
    # absl.logging 핸들러 비활성화
    import logging
    logging.getLogger('absl').setLevel(logging.ERROR)
except ImportError as e:
    # absl.logging이 없어도 동작해야 하므로 DEBUG 레벨로 로그 출력 (선택적)
    pass  # ImportError는 정상적인 경우이므로 로그 출력 생략

# warnings 억제
import warnings
warnings.filterwarnings('ignore')

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
    home = [city for city in globals.cities if city.num == hero.city]
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
# 주석: --load 옵션은 현재 사용하지 않음 (향후 사용 가능)

menu = 0
filtered = [(key, value[0]) for key, value in main_commands.items() if value[2] != 0]


#commands.files.load_file(False)
popup()
exit()    