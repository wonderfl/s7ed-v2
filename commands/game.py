import sys
import os
import re

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import globals
from globals import ActionMenu


def move_city():
    while True:
        name = input("\n이동할 도시이름? ")
        if not name:
            break

        filtered = [city for city in globals.cities if city.name.startswith(name)]
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

        filtered = [city for city in globals.cities if city.name.startswith(name)]
        if not filtered:
            print("해당 이름의 도시가 없습니다.")
            continue

        for i, city in enumerate(filtered):
            print(f" . {city.num:03}: {city}")

        if 1 > len(filtered):
            print("--------------------------------------------------------------------------------")
            print("'{0}' 으로 찾은 도시: {1} 개".format(name, len(filtered)))

def generals_city(id=None):
    num = globals._home if id is None else int(id)    
    city = globals.cities[num] if num is not None and 0 <= num < len(globals.cities) else None
    if not city:
        print(f" . 도시 번호 {num:03}에 해당하는 도시가 없습니다.")
        return
    
    print(f" . {city.num:03}: {city.details()}")

    filtered = [general for general in globals.generals if general.city==num and general.state < 5]
    if not filtered:
        print("해당 도시에 장수가 없습니다.")
        return
    print("--------------------------------------------------------------------------------")
    for i, general in enumerate(filtered):
        print(f" . {general.num:03}: {general.details()}")

    if 0 < len(filtered):
        print("--------------------------------------------------------------------------------")
        print("'{0}' 에 있는 장수: {1} 명".format(city.name, len(filtered)))


def generals_realm(id=None):

    if( id is None):
        num = globals.generals[globals._hero].realm
    else:
        try: 
            num = int(id)
        except:
            if( id == '-'):
                num = -1
            else:
                print("'{0}'세력 정보가 없습니다.".format(id))
                return

    founds = [realm for realm in globals.realms if -1 == num or (-1 !=num and realm.num == num) ]
    if not founds:
        print("'{}'세력 정보가 잆습니다.".format(num))
        return
    
    if( 1 >= len(founds) and 65535 == founds[0].ruler):
        print("'{}' 사라진 세력입니다.".format(num))
        return

    gn = len(globals.generals)
    for i, found in enumerate(founds):
        if 0 > found.ruler or found.ruler >= gn:
            #print("'{}'세력 정보가 잆습니다.".format(id))
            continue

        ruler = globals.generals[found.ruler]
        filtered = [general for general in globals.generals if general.realm==found.num]
        if not filtered:
            print("'{}'세력의 장수가 없습니다.".format(ruler.name))
            continue

        print(f"\n'{ruler.name}'의 세력")
        print("--------------------------------------------------------------------------------")
        for i, general in enumerate(filtered):
            print(f" . {general.num:03}: {general.details()}")

        if 0 < len(filtered):
            print("--------------------------------------------------------------------------------")
            print("'{0}'세력의 장수: {1} 명".format(ruler.name, len(filtered)))

game_commands = {
    "1": ActionMenu("generals city", generals_city, 1, "도시의 정보를 확인합니다."),    
    "2": ActionMenu("generals realm", generals_realm, 1, "세력의 장수 리스트업."),
    "4": ActionMenu("builds in ", builds_in, 1, "도시의 건물 리스트업."),
    "5": ActionMenu("move to ", move_city, 1, "도시를 이동합니다."),    
    "0": ActionMenu("return menu ", None, 1, "이전 메뉴로."),
}

def game_play():
    hero = globals.generals[globals._hero]
    if not hero:
        print("영웅을 찾을 수 없습니다.")
        return

    globals._home = hero.city
    if globals._home < 0 or globals._home >= len(globals.cities):
        print("영웅의 도시 정보가 잘못되었습니다.")
        return
    
    home = globals.cities[globals._home]
    if not home:
        print("영웅의 도시를 찾을 수 없습니다.")
        return
    
    commands = [(key, value[0]) for key, value in game_commands.items() if value[2] != 0]
    cmds = "\n".join( f" {key}. {name}" for key, name in commands)
    while True:
        print("\n[{0}년 {1}월]:\n\n. {2}: {3}".format(globals._year, globals._month, hero.name, home.details()))
        
        text = input("\n{0}\n\n? ".format(cmds))
        params = [p for p in re.split(r'[ .,]', text) if p]
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
