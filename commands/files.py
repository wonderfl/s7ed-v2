import sys
import os
import copy

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import globals
from globals import ActionMenu

from datas.general import General, GeneralStruct, _CITY_
from datas.city import CityState, CityStateStruct
from datas.item import ItemState, ItemStateStruct
from datas.realm import RealmState, RealmStateStruct

from utils.decode import __decrypt

def load_file(needs=True):
    if needs == False:
        fname = globals._load
    else:
        fname = input(f"'Load' 파일이름: ")

    if( 0 >= len(fname) ):
        print("파일이름이 없습니다.")
        return
    
    _generals=[]
    _items=[]
    _realms=[]
    _cities=[]
    
    try:
        # 장수 620명 기준 읽기 예시
        #with open(filename, 'r', encoding='utf-8') as f:
        with open(fname, "rb") as f:
            f.seek(globals.current_year_offset )
            val0 = f.read(2)
            val1 = f.read(2)
            globals._month = int.from_bytes(val0)
            globals._year = int.from_bytes(val1)

            for i in range(620): # 620명 기준
                f.seek(globals.generals_offset + i * GeneralStruct.size)
                chunk = f.read(GeneralStruct.size)
                decoded = __decrypt(chunk)

                general = General(i,decoded)
                _generals.append(general)

            for i in range(72): # 72개 아이템 기준
                f.seek(globals.items_offset + i * ItemStateStruct.size)
                chunk = f.read(ItemStateStruct.size)
                decoded = __decrypt(chunk)

                item = ItemState(i, decoded)
                _items.append(item)

            for i in range(54): # 54개 도시 기준
                f.seek(globals.realm_offset + i * RealmStateStruct.size)
                chunk = f.read(RealmStateStruct.size)
                decoded = __decrypt(chunk)

                realm = RealmState(i, decoded)
                _realms.append(realm)

            for i in range(54): # 54개 도시 기준
                f.seek(globals.cities_offset + i * CityStateStruct.size)
                chunk = f.read(CityStateStruct.size)
                decoded = __decrypt(chunk)

                city = CityState(i, _CITY_[i], decoded)
                _cities.append(city)        

        globals.generals.clear()
        globals.generals.extend(copy.deepcopy(_generals))

        globals.items.clear()
        globals.items.extend(copy.deepcopy(_items))

        globals.realms.clear()
        globals.realms.extend(copy.deepcopy(_realms))

        globals.cities.clear()
        globals.cities.extend(copy.deepcopy(_cities))

        hero = globals.generals[globals._hero]
        globals._home = hero.city

        print(f":'{fname}' 파일을 성공적으로 불러왔습니다. {globals._year}년{globals._month}월:{hero.name}[{globals._home}]")

    except FileNotFoundError:
        print(f": `{fname}`파일을 찾을 수 없습니다.")
        return None
    

def save_file():
    fname = input(f"'Save' 파일이름: {globals._load}")
    if not fname:
        fname = globals._load
    return

    try:
        # 장수 620명 기준 읽기 예시
        #with open(filename, 'r', encoding='utf-8') as f:
        with open(fname, "rb") as f:
            for i in range(620): # 620명 기준
                f.seek(generals_offset + i * GeneralStruct.size)
                chunk = f.read(GeneralStruct.size)
                decoded = __decrypt(chunk)

                general = General(i,decoded)
                generals.append(general)

            for i in range(54): # 54개 도시 기준
                f.seek(cities_offset + i * CityStateStruct.size)
                chunk = f.read(CityStateStruct.size)
                decoded = __decrypt(chunk)

                city = CityState(i, _CITY_[i], decoded)
                cities.append(city)
    except FileNotFoundError:
        print("❌ 파일을 찾을 수 없습니다.")
        return None    
    
find_commands = {
    "1": ActionMenu("load game", load_file, 2, "게임 데이터 로드."),
    "2": ActionMenu("save game", save_file, 2, "게임 데이터 저장."),

    #"3": ActionMenu("load scenario", load_scene, 2, "시나리오 로드."),
    #"4": ActionMenu("save scenario", save_scene, 2, "시나리오 저장."),    
    
    #"5": ActionMenu("load new 100", load_100, 2, "새로운 장수 로드."),
    #"6": ActionMenu("save new 100", save_100, 2, "새로운 장수 저장."),
    "0": ActionMenu("return menu", None, 9, "이전 메뉴로."),
}

def files():
    commands = [(key, value[0]) for key, value in find_commands.items() if value[2] != 0]
    cmds = "\n".join( f"  {key}. {name}" for key, name in commands)
    while True:
        print("\n: files".format(globals._year, globals._month))
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