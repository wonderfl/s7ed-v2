import sys
import os
import copy

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import globals

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