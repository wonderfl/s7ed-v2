import sys
import os
import re
import copy
import struct
import time

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
            f.seek(gl.game_year_offset )
            val0 = f.read(2)
            gl._year = int.from_bytes(val0,'little')

            f.seek(gl.game_month_offset )
            val1 = f.read(1)
            gl._month = int.from_bytes(val1, 'little')
            
            f.seek(gl.player_name_offset)
            _name = f.read(8)
            _name = _name.decode('euc-kr')
            _name = _name.rstrip('\x00')            
            gl._name = _name
            print(gl._name)

            f.seek(gl.scene_num_offset)
            _num = f.read(1)
            gl._scene = int.from_bytes(_num, 'little')

            s4 = (gl._scene - 1) % 4
            for i in range(620): # 620명 기준
                f.seek(gl.generals_offset + i * GeneralStruct.size)
                chunk = f.read(GeneralStruct.size)
                decoded = _decrypt_data(s4, chunk)

                general = General(i,decoded)
                _generals.append(general)

            for i in range(72): # 72개 아이템 기준
                f.seek(gl.items_offset + i * ItemStateStruct.size)
                chunk = f.read(ItemStateStruct.size)
                decoded = _decrypt_data(s4, chunk)

                item = ItemState(decoded)
                _items.append(item)

            for i in range(54): # 54개 도시 기준
                f.seek(gl.realm_offset + i * RealmStateStruct.size)
                chunk = f.read(RealmStateStruct.size)
                decoded = _decrypt_data(s4, chunk)

                realm = RealmState(i, decoded)
                _realms.append(realm)

            for i in range(54): # 54개 도시 기준
                #print('읽을도시:{0}'.format(i))
                f.seek(gl.cities_offset + i * CityStateStruct.size)
                chunk = f.read(CityStateStruct.size)
                decoded = _decrypt_data(s4, chunk)

                city = CityState(i, gl._cityNames_[i], decoded)
                _cities.append(city)

            f.seek(gl.hero_golds_offset)
            chunk = f.read(2)
            decoded = _decrypt_data(s4, chunk)
            gl.hero_golds = struct.unpack('<H', decoded)[0]

            chunk = f.read(2) # ??
            chunk = f.read(2)
            decoded = _decrypt_data(s4, chunk)

            _num = struct.unpack('<H', decoded)[0] # general player
            if 0 > _num or _num >= len(_generals):
                print("save data error: wrong player num.. \nnum: {0}, gn:{1}".format( _num, len(_generals)))
                return
            general = _generals[_num]
            if general.name != gl._name:
                print("save data error: wrong player name.\n [{0}!={1}]".format( gl._name, general.name))
                return
            
            gl._player_num = _num
            gl._player_name = _name            

            for i in range(620): # 620명 기준
                f.seek(gl.hero_relations_offset + i * 2)
                chunk = f.read(2)
                decoded = _decrypt_data(s4, chunk)

                _closeness = struct.unpack('<H', decoded)[0]
                _relations.append(_closeness)

            for i in range(54): # 54 도시 민심
                f.seek(gl.hero_sentiments_offset + i)
                chunk = f.read(1)
                decoded = _decrypt_data(s4, chunk)
                
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

        #hero = gl.generals[gl._hero]
        #gl._home = hero.city
        #home = gl.cities[gl._home]

        print(f"\nLoad '{fname}' Completed.. {rn}:{cn}:{gn}")
        #print("{0}년 {1}월: {2} / {3}".format( gl._year,gl._month, hero.name, home.details2()))
        
        # 파일의 수정 시간 저장
        try:
            gl._file_mtime = os.path.getmtime(fname)
        except Exception as e:
            print(f"[파일체크] mtime 저장 실패: {e}")
            gl._file_mtime = None
        
        # 저장 파일과 같은 디렉토리에 있는 Kaodata.s7 파일 자동 감지
        try:
            file_dir = os.path.dirname(fname)
            
            import utils.kaodata_image as kaodata_image
            kaodata_dir = kaodata_image.get_face_file_path()            
            
            print(f"[파일체크] 저장 파일: {fname}, 얼굴 파일: {kaodata_dir}")

            # kaodata_path = os.path.join(kaodata_dir, "Kaodata.s7")
            # if os.path.exists(kaodata_path):
            #     import utils.kaodata_image as kaodata_image
            #     import utils.config as config
            #     kaodata_image.set_face_file_path(kaodata_path)
            #     config.save_config()  # 설정 파일에 저장
            #     print(f"[파일체크] 얼굴 파일 경로 자동 설정: {kaodata_path}")
        except Exception as e:
            print(f"[파일체크] 얼굴 파일 경로 자동 설정 실패: {e}")

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

def test_save_generals(fname):
    s4 = (gl._scene - 1) % 4
    for i, general in enumerate (gl.generals): # 620명 기준
        values = general.unpacked
        packed = GeneralStruct.pack(*values)
        encoded = _encrypt_data(s4, packed)

        decoded = _decrypt_data(s4, encoded)
        _general = General(i,decoded)
        print(_general)

def test_save_items(fname):
    s4 = (gl._scene - 1) % 4
    for i, item in enumerate (gl.items): # 620명 기준
        values = item.unpacked
        packed = ItemStateStruct.pack(*values)
        encoded = _encrypt_data(s4, packed)

        decoded = _decrypt_data(s4, encoded)
        _item = ItemState(decoded)
        print(_item)

def test_save_general_selected(fname, count, general, save=False):
    if general is None:
        print("error: general None..")
        return False
    
    s4 = (gl._scene - 1) % 4
    
    values = general.unpacked
    packed = GeneralStruct.pack(*values)
    encoded = _encrypt_data(s4, packed)
    
    decoded = _decrypt_data(s4, encoded)
    _general = General(general.num, decoded)
    if general.name != _general.name:
        print("error: not match decode..")
        return False    

    print("{0:3}. {1}".format(count, general))
    if False == save:
        return False
    
    gl._is_saving = True
    with open(fname, "r+b") as f:
        f.seek(gl.generals_offset + general.num * GeneralStruct.size)
        values = general.unpacked
        packed = GeneralStruct.pack(*values)
        encoded = _encrypt_data(s4, packed)
        saved = f.write(encoded)

        #print("{0},{1}".format(general.num, gl.relations[general.num]))
        values = struct.pack('<H', gl.relations[general.num])
        encoded = _encrypt_data(s4, values)
        f.seek(gl.hero_relations_offset + 2 * general.num)
        saved = f.write(encoded)        

    return True        

def test_save_item_selected(fname, item, save=False):
    if item is None:
        print("error: item None..")
        return False    
    s4 = (gl._scene - 1) % 4
    
    values = item.unpacked
    packed = ItemStateStruct.pack(*values)
    encoded = _encrypt_data(s4, packed)
    
    decoded = _decrypt_data(s4, encoded)
    _item = ItemState(decoded)

    if item.name != _item.name:
        print("error: not match decode..")
        return False
    
    print("save: {0}".format(fname))
    print(item)
    if False == save:
        return False
    gl._is_saving = True
    with open(fname, "r+b") as f:
        f.seek(gl.items_offset + item.num * ItemStateStruct.size)
        values = item.unpacked
        packed = ItemStateStruct.pack(*values)
        encoded = _encrypt_data(s4, packed)
        saved = f.write(encoded)

    return True

def test_save_city_selected(fname, city, save=False):
    if city is None:
        print("error: city None..")
        return False
    
    values = city.unpacked
    packed = CityStateStruct.pack(*values)

    s4 = (gl._scene - 1) % 4
    encoded = _encrypt_data(s4, packed)    
    decoded = _decrypt_data(s4, encoded)
    _city = CityState(city.num, city.name, decoded)

    if city.peoples != _city.peoples:
        print("error: not match decode..")
        return False
    
    print(city)
    if False == save:
        return False
    gl._is_saving = True
    with open(fname, "r+b") as f:
        f.seek(gl.cities_offset + city.num * CityStateStruct.size)
        values = city.unpacked
        packed = CityStateStruct.pack(*values)
        encoded = _encrypt_data(s4, packed)
        saved = f.write(encoded)

        values = struct.pack('<B', gl.sentiments[city.num])
        encoded = _encrypt_data(s4, values)
        f.seek(gl.hero_sentiments_offset + city.num)
        saved = f.write(encoded)

    print("save: {0}, {1}".format(fname, gl.sentiments[city.num]))

def test_save_cities(fname):    
    s4 = (gl._scene - 1) % 4
    for i, city in enumerate (gl.cities): # 620명 기준
        values = city.unpacked
        packed = CityStateStruct.pack(*values)
        encoded = _encrypt_data(s4, packed)

        decoded = _decrypt_data(s4, encoded)
        _city = CityState(i, gl._cityNames_[i], decoded)
        print(_city)   

def save_player_gold(fname):
    try:
        print("save_player_gold: {0}, {1}, {2}".format(gl._year, gl._month, gl.hero_golds))
        s4 = (gl._scene - 1) % 4    
        gl._is_saving = True
        with open(fname, "r+b") as f:
            values = struct.pack('<H', gl.hero_golds)
            encoded = _encrypt_data(s4, values)

            f.seek(gl.hero_golds_offset)
            saved = f.write(encoded)


            # values = struct.pack('<H', gl._year)
            # encoded = _encrypt_data(s4, values)
            # f.seek(gl.game_year_offset )
            # saved = f.write(encoded)

            # values = struct.pack('<B', gl._month)
            # encoded = _encrypt_data(s4, values)
            # f.seek(gl.game_month_offset )
            # saved = f.write(encoded)


    except FileNotFoundError:
        print("{0} 파일을 찾을 수 없습니다.".format(fname))
        return None         


def save_file(fname):

    try:
        # 저장 중 플래그 설정
        gl._is_saving = True
        
        # 장수 620명 기준 읽기 예시
        #with open(filename, 'r', encoding='utf-8') as f:
        s4 = (gl._scene - 1) % 4
        with open(fname, "r+b") as f:
            for i, general in enumerate (gl.generals): # 620명 기준
                f.seek(gl.generals_offset + i * GeneralStruct.size)
                values = general.unpacked
                packed = GeneralStruct.pack(*values)
                encoded = _encrypt_data(s4, packed)
                saved = f.write(encoded)

            for i, item in enumerate (gl.items): # 620명 기준
                f.seek(gl.items_offset + i * ItemStateStruct.size)
                values = item.unpacked
                packed = ItemStateStruct.pack(*values)
                encoded = _encrypt_data(s4, packed)
                saved = f.write(encoded)

            for i, city in enumerate (gl.cities): # 620명 기준
                f.seek(gl.cities_offset + i * CityStateStruct.size)
                values = city.unpacked
                packed = CityStateStruct.pack(*values)
                encoded = _encrypt_data(s4, packed)
                saved = f.write(encoded)
            
            values = struct.pack('<H', gl.hero_golds)
            encoded = _encrypt_data(s4, values)

            f.seek(gl.hero_golds_offset)
            saved = f.write(encoded)
            
            # 파일을 명시적으로 flush하여 디스크에 완전히 쓰기
            f.flush()
            os.fsync(f.fileno())

        print(f"\nSave '{fname}' Completed.. {s4}")

    except FileNotFoundError:
        print("❌ 파일을 찾을 수 없습니다.")
        gl._is_saving = False
        return None
    except Exception as e:
        print(f"[파일저장] 저장 중 오류 발생: {e}")
        gl._is_saving = False
        return None    


def check_file_changed():
    """파일이 외부에서 변경되었는지 확인"""

    if not gl._loading_file or len(gl._loading_file) == 0:
        return False
    
    if gl._file_mtime is None:
        return False
    
    try:
        if not os.path.exists(gl._loading_file):
            return False
        
        current_mtime = os.path.getmtime(gl._loading_file)
        if current_mtime != gl._file_mtime:
            print(f"[파일체크] 파일 변경 감지: 저장된 mtime={gl._file_mtime}, 현재 mtime={current_mtime}")
            return True
        return False
    except Exception as e:
        print(f"[파일체크] 파일 변경 확인 실패: {e}")
        return False


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