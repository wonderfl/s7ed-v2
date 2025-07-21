import sys
import os
import re
import copy
import struct

import tkinter as tk

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import globals as gl

from globals import ActionMenu

from datas.general import General, GeneralStruct
from datas.city import CityState, CityStateStruct
from datas.item import ItemState, ItemStateStruct
from datas.realm import RealmState, RealmStateStruct

from utils.encode import _encrypt_data 
from utils.decode import _decrypt_data

from gui.gui import GeneralEditorApp, _app, _root
import gui._popup as _popup

# 1. 폴더 경로 설정
#_saves = "./saves"
_saves = "E:/05.game/Sam7pk"
_start = "D_Save"

# 정규식 패턴 정의 (예: data_숫자4자리.csv)
#pattern = re.compile(r"^data_\d{4}\.csv$")
pattern = re.compile(r"^D_Save\d{2}\.s7$")

def listup_file(ext='.s7', **args):

    # 2. 파일 목록 필터링 (.txt 또는 .csv)
    files = [f for f in os.listdir(_saves) 
             if os.path.isfile(os.path.join(_saves, f)) and pattern.match(f)]
    
    # 3. 목록 출력
    if not files:
        print(f"해당 폴더에 {ext} 파일이 없습니다.")
        return ""

    print("\n  {0}\n".format(_saves))
    for idx, filename in enumerate(files):
        print(f"  {idx+1}. {filename}")
    print("")

    # 4. 사용자로부터 파일 선택
    try:
        selected_index = int(input("Load File: "))
        selected_file = files[selected_index-1]
        return _saves+ '/' + selected_file
    except (ValueError, IndexError):
        print("잘못된 입력입니다.")
        return ""


def open_file(fname):

    _generals=[]
    _items=[]
    _realms=[]
    _cities=[]
    _relations=[]
    _sentiments=[]
    
    try:
        # 장수 620명 기준 읽기 예시
        #with open(filename, 'r', encoding='utf-8') as f:
        with open(fname, "rb") as f:
            f.seek(gl.current_year_offset )
            val0 = f.read(2)
            val1 = f.read(2)
            gl._month = int.from_bytes(val0, 'big')
            gl._year = int.from_bytes(val1,'big')

            for i in range(620): # 620명 기준
                f.seek(gl.generals_offset + i * GeneralStruct.size)
                chunk = f.read(GeneralStruct.size)
                decoded = _decrypt_data(chunk)

                general = General(i,decoded)
                _generals.append(general)

            for i in range(72): # 72개 아이템 기준
                f.seek(gl.items_offset + i * ItemStateStruct.size)
                chunk = f.read(ItemStateStruct.size)
                decoded = _decrypt_data(chunk)

                item = ItemState(decoded)
                _items.append(item)

            for i in range(54): # 54개 도시 기준
                f.seek(gl.realm_offset + i * RealmStateStruct.size)
                chunk = f.read(RealmStateStruct.size)
                decoded = _decrypt_data(chunk)

                realm = RealmState(i, decoded)
                _realms.append(realm)

            for i in range(54): # 54개 도시 기준
                #print('읽을도시:{0}'.format(i))
                f.seek(gl.cities_offset + i * CityStateStruct.size)
                chunk = f.read(CityStateStruct.size)
                decoded = _decrypt_data(chunk)

                city = CityState(i, gl._cityNames_[i], decoded)
                _cities.append(city)

            f.seek(gl.hero_golds_offset)
            chunk = f.read(2)
            decoded = _decrypt_data(chunk)
            gl.hero_golds = struct.unpack('<H', decoded)[0]

            for i in range(620): # 620명 기준
                f.seek(gl.hero_relations_offset + i * 2)
                chunk = f.read(2)
                decoded = _decrypt_data(chunk)

                _closeness = struct.unpack('<H', decoded)[0]
                _relations.append(_closeness)

            for i in range(54): # 54 도시 민심
                f.seek(gl.hero_sentiments_offset + i)
                chunk = f.read(1)
                decoded = _decrypt_data(chunk)
                
                _sentiment = struct.unpack('<B', decoded)[0]
                _sentiments.append(_sentiment)

        gl.generals.clear()
        gl.generals.extend(copy.deepcopy(_generals))

        gl.items.clear()
        gl.items.extend(copy.deepcopy(_items))

        gl.realms.clear()
        gl.realms.extend(copy.deepcopy(_realms))

        gl.cities.clear()
        gl.cities.extend(copy.deepcopy(_cities))

        gl.relations.clear()
        gl.relations.extend(copy.deepcopy(_relations))

        gl.sentiments.clear()
        gl.sentiments.extend(copy.deepcopy(_sentiments))


        gn = len(gl.generals)
        rn = len(gl.realms)
        cn = len(gl.cities)
        hero = gl.generals[gl._hero]
        gl._home = hero.city
        home = gl.cities[gl._home]

        print(f"\nLoad '{fname}' Completed.. {rn}:{cn}:{gn}")
        print("{0}년 {1}월: {2} / {3}".format( gl._year,gl._month, hero.name, home.details2()))

    except FileNotFoundError:
        print(f": `{fname}`파일을 찾을 수 없습니다.")
        return None
        

def load_file(needs=True, **args):
    if needs == False:
        fname = gl._load
    else:
        #fname = input(f"'Load' 파일이름: ")
        fname = listup_file(".s7")

    if( 0 >= len(fname) ):
        print("파일이름이 없습니다.")
        return
    open_file(fname)    
    _app.generalTab.listup_generals()

def save_data(**args):
    fname = input(f"'Save' 파일이름: {gl._load}")
    if not fname:
        fname = gl._load    

def test_save_file(fname):
    general = gl.generals[0]
    #print(general.to_keys(), )    

    #values = []
    #for value in general.unpacked:
    #    values.append(value)

    for i, general in enumerate (gl.generals): # 620명 기준
        
        values = general.unpacked

        packed = GeneralStruct.pack(*values)
        encoded = _encrypt_data(packed)

        decoded = _decrypt_data(encoded)
        general = General(i,decoded)

        print(general)            

def save_file(fname):

    try:
        # 장수 620명 기준 읽기 예시
        #with open(filename, 'r', encoding='utf-8') as f:
        with open(fname, "r+b") as f:
            for i, general in enumerate (gl.generals): # 620명 기준
                f.seek(gl.generals_offset + i * GeneralStruct.size)
                values = general.unpacked
                packed = GeneralStruct.pack(*values)
                encoded = _encrypt_data(packed)
                saved = f.write(encoded)

    except FileNotFoundError:
        print("❌ 파일을 찾을 수 없습니다.")
        return None    
    
find_commands = {
    "1": gl.ActionMenu("load game", load_file, 2, "게임 데이터 로드."),
    "2": gl.ActionMenu("save game", save_file, 2, "게임 데이터 저장."),

    #"3": gl.ActionMenu("load scenario", load_scene, 2, "시나리오 로드."),
    #"4": gl.ActionMenu("save scenario", save_scene, 2, "시나리오 저장."),    
    
    #"5": gl.ActionMenu("load new 100", load_100, 2, "새로운 장수 로드."),
    #"6": gl.ActionMenu("save new 100", save_100, 2, "새로운 장수 저장."),
    "0": gl.ActionMenu("return menu", None, 9, "이전 메뉴로."),
}

def files(*args):
    commands = [(key, value[0]) for key, value in find_commands.items() if value[2] != 0]
    cmds = "\n".join( f"  {key}. {name}" for key, name in commands)
    while True:
        print("\n: files".format(gl._year, gl._month))
        params = input("\n{0}\n\n? ".format(cmds)).split()
        if( 0 >= len(params)):
            break
        
        if( "0" == params[0]):
            return
    
        command = find_commands.get(params[0])
        if not command:
            print(f" . '{params[0]}' 명령어를 찾을 수 없습니다.")
            continue

        args = params[1:]
        if not command.action:
            print(f" . '{params[0]}' 명령어는 실행할 수 없습니다.")
            continue

        command.action(*args)