import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from globals import generals, cities, generals_offset, cities_offset
from globals import __hero, __home, __load

from datas.general import General, GeneralStruct, CITY_NAMES
from datas.city import CityState, CityStateStruct

from utils.decode import __decrypt

def load_file():
    fname = input(f"'Load' 파일이름: {__load}")
    if not fname:
        fname = __load
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

                city = CityState(i, CITY_NAMES[i], decoded)
                cities.append(city)
    except FileNotFoundError:
        print("❌ 파일을 찾을 수 없습니다.")
        return None
    

def save_file():
    fname = input(f"'Save' 파일이름: {__load}")
    if not fname:
        fname = __load
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

                city = CityState(i, CITY_NAMES[i], decoded)
                cities.append(city)
    except FileNotFoundError:
        print("❌ 파일을 찾을 수 없습니다.")
        return None    