import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from globals import generals, cities
from globals import __hero, __home, __load

from globals import ActionMenu


def move_city():
    while True:
        name = input("\n이동할 도시이름? ")
        if not name:
            break

        filtered = [city for city in cities if city.name.startswith(name)]
        if not filtered:
            print("해당 이름의 도시가 없습니다.")
            continue

        for i, city in enumerate(filtered):
            print(f" . {city.num:03}: {city}")

        if 1 > len(filtered):
            print("--------------------------------------------------------------------------------")
            print("'{0}' 으로 찾은 도시: {1} 개".format(name, len(filtered)))

def builds_in():   
    while True:
        name = input("\n건축할 도시이름? ")
        if not name:
            break

        filtered = [city for city in cities if city.name.startswith(name)]
        if not filtered:
            print("해당 이름의 도시가 없습니다.")
            continue

        for i, city in enumerate(filtered):
            print(f" . {city.num:03}: {city}")

        if 1 > len(filtered):
            print("--------------------------------------------------------------------------------")
            print("'{0}' 으로 찾은 도시: {1} 개".format(name, len(filtered)))

def info_city(id=None):
    global __home

    print("\n도시 정보:{0}[{1}]".format(id, __home))

    num = __home if id is None else int(id)    
    city = cities[num] if num is not None and 0 <= num < len(cities) else None
    if not city:
        print(f" . 도시 번호 {num:03}에 해당하는 도시가 없습니다.")
        return
    print(f" . {city.num:03}: {city}")

def generals_city(id=None):
    global __home
    num = __home if id is None else int(id)
    city = cities[num] if num is not None and 0 <= num < len(cities) else None
    if not city:
        print(f" . 도시 번호 {num:03}에 해당하는 도시가 없습니다.")
        return    

    filtered = [general for general in generals if general.city==num]
    if not filtered:
        print("해당 이름의 장수가 없습니다.")
        return

    print(f"\n번호: {city.num:02}\n정보: {city}")    
    print("--------------------------------------------------------------------------------")
    for i, general in enumerate(filtered):
        print(f" . {general.num:03}: {general}")

    if 0 < len(filtered):
        print("--------------------------------------------------------------------------------")
        print("'{0}' 에 있는 장수: {1} 명".format(city.name, len(filtered)))

def generals_realm(id=None):
    
    global __hero
    
    num = __hero if id is None else int(id)
    hero = generals[num]
    if not hero:
        print("영웅을 찾을 수 없습니다.")
        return

    realm = hero.realm  
    if (255 == realm):
        print("{0}[{1},{2}] 장수의 세력이 없습니다.".format(hero.name, id, realm, ))
        return

    filtered = [general for general in generals if general.realm==realm]
    if not filtered:
        print("세력의 장수가 없습니다.")
        return

    print(f"\n'{hero.name}'의 세력: {realm:02}")
    print("--------------------------------------------------------------------------------")
    for i, general in enumerate(filtered):
        print(f" . {general.num:03}: {general}")

    if 0 < len(filtered):
        print("--------------------------------------------------------------------------------")
        print("'{0}'세력의 장수: {1} 명".format(realm, len(filtered)))           

game_commands = {
    "1": ActionMenu("info city", info_city, 1, "도시의 정보를 확인합니다."),    
    "2": ActionMenu("generals in city", generals_city, 1, "도시의 장수 리스트업."),
    "3": ActionMenu("generals in realm", generals_realm, 1, "세력의 장수 리스트업."),
    "4": ActionMenu("builds in ", builds_in, 1, "도시의 건물 리스트업."),
    "5": ActionMenu("move to ", move_city, 1, "도시를 이동합니다."),    
    "0": ActionMenu("return menu ", None, 1, "이전 메뉴로."),
}

def game_play():
    gn = len(generals)
    cn = len(cities)
    if gn == 0 or cn == 0:
        print("장수나 도시 데이터가 없습니다. 먼저 'load' 명령어로 데이터를 불러오세요.")
        return
    
    #print(f"장수 수: {gn}, 도시 수: {cn}")
    hero = generals[__hero]
    if not hero:
        print("영웅을 찾을 수 없습니다.")
        return
    
    global __home
    __home = hero.city
    if __home < 0 or __home >= len(cities):
        print("영웅의 도시 정보가 잘못되었습니다.")
        return
    
    home = cities[__home]
    if not home:
        print("영웅의 도시를 찾을 수 없습니다.")
        return
    
    commands = [(key, value[0]) for key, value in game_commands.items() if value[2] != 0]
    cmds = "\n".join( f" {key}. {name}" for key, name in commands)
    while True:
        print(f"\n: {hero.name}[ {hero.num:03} in {home.num}]\n: {home}")    

        params = input("\n{0}\n\n? ".format(cmds)).split()
        if( 0 >= len(params)):
            break
        
        if( "0" == params[0]):
            return

        command = game_commands.get(params[0])
        if not command:
            print(f" . '{params[0]}' 명령어를 찾을 수 없습니다.")
            continue

        args = params[1:]
        if not command.action:
            print(f" . '{params[0]}' 명령어는 실행할 수 없습니다.")
            continue

        command.action(*args)
