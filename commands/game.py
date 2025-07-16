import sys
import os
import re

import globals as gl

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

def move_city():
    while True:
        name = input("\n이동할 도시이름? ")
        if not name:
            break

        filtered = [city for city in gl.cities if city.name.startswith(name)]
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

        filtered = [city for city in gl.cities if city.name.startswith(name)]
        if not filtered:
            print("해당 이름의 도시가 없습니다.")
            continue

        for i, city in enumerate(filtered):
            print(f" . {city.num:03}: {city}")

        if 1 > len(filtered):
            print("--------------------------------------------------------------------------------")
            print("'{0}' 으로 찾은 도시: {1} 개".format(name, len(filtered)))

def generals_realm(id=None):

    if( id is None):
        num = gl.generals[gl._hero].realm
    else:
        try: 
            num = int(id)
        except:
            if( id == '-'):
                num = -1
            else:
                print("'{0}'세력 정보가 없습니다.".format(id))
                return

    founds = [realm for realm in gl.realms if -1 == num or (-1 !=num and realm.num == num) ]
    if not founds:
        print("'{}'세력 정보가 잆습니다.".format(num))
        return
    
    if( 1 >= len(founds) and 65535 == founds[0].ruler):
        print("'{}' 사라진 세력입니다.".format(num))
        return

    gn = len(gl.generals)
    for i, found in enumerate(founds):
        if 0 > found.ruler or found.ruler >= gn:
            #print("'{}'세력 정보가 잆습니다.".format(id))
            continue

        ruler = gl.generals[found.ruler]
        filtered = [general for general in gl.generals if general.realm==found.num]
        if not filtered:
            print("'{}'세력의 장수가 없습니다.".format(ruler.name))
            continue

        print(f"\n'{ruler.name}'의 세력")
        print("--------------------------------------------------------------------------------")
        for i, general in enumerate(filtered):
            print(f" {general.num:03}: {general.details()}")

        if 0 < len(filtered):
            print("--------------------------------------------------------------------------------")
            print("'{0}'세력의 장수: {1} 명".format(ruler.name, len(filtered)))

# 12345678901234567890123456789012345678901234567890123456789012345678901234567890
#################################################################################
# 도시 아이디를 가변인자로 받아 여러 도시에 장수를 한꺼번에 출력
# 디폴트는 주인공이 있는 도시
# 옵션: *:props, +:equips, -:trains?,items?, - 가변인자에서 값으로 받아 stats, props 출력
#
def generals_in_city(*args):
    city_set = set()
    city_ids = []
    city_ids.append(gl._home)

    exceptHome = False
    props = False
    abilities = False    
    equips = False

    maxCity = len(gl.cities)
    for arg in args:
        if False == arg.isdecimal():
            if "*" in arg: # props
                props = True                
            if "/" in arg: # equips
                abilities = True
            if "+" in arg: # equips
                equips = True
            if "-" in arg: # home 삭제
                exceptHome = True
            continue

        try:
            id = int(arg)
            if 0 > id or id >= maxCity:
                continue
            if id in city_set:
                continue
            city_set.add(id)
            city_ids.append(id)
        except:
            print("wrong id: ", arg)
            continue

    if True == exceptHome:
        city_ids.remove(gl._home)

    _cities = [gl.cities[id] for id in city_ids]
    for city in _cities:
        print(f"\n . {city.num:03}: {city.details()}")
        
        filtered = [general for general in gl.generals if general.city==city.num and general.state < 5]
        if not filtered:
            print("해당 도시에 장수가 없습니다.")
            continue

        print("--------------------------------------------------------------------------------")
        for i, general in enumerate(filtered):
            print(" {0:03}: {1}{2}{3}{4}".format(
                general.num, 
                general.profiles2() + general.stats(),
                general.abilities() if abilities else "", 
                general.properties() if props else "", 
                general.equipments() if equips else ""))

        # if 0 < len(filtered):
        #     print("--------------------------------------------------------------------------------")
        #     print("'{0}' 에 있는 장수: {1} 명".format(city.name, len(filtered)))

game_commands = {
    "1": gl.ActionMenu("generals in city", generals_in_city, 1, "도시내 장수의 수치를 확인합니다."),    
    "2": gl.ActionMenu("generals in realm", generals_realm, 1, "세력의 장수 리스트업."),
    
    "4": gl.ActionMenu("peoples", None, 1, "사람."),
    "5": gl.ActionMenu("operations", None, 1, "작전."),
    "6": gl.ActionMenu("developments", None, 1, "개발."),

    "8": gl.ActionMenu("actions", None, 1, "활동"),
    "9": gl.ActionMenu("next turn", None, 1, "다음 턴으로."),
    "0": gl.ActionMenu("return menu ", None, 1, "이전 메뉴로."),
}

def game_play(*args):
    hero = gl.generals[gl._hero]
    if not hero:
        print("영웅을 찾을 수 없습니다.")
        return

    gl._home = hero.city
    if gl._home < 0 or gl._home >= len(gl.cities):
        print("영웅의 도시 정보가 잘못되었습니다.")
        return
    
    home = gl.cities[gl._home]
    if not home:
        print("영웅의 도시를 찾을 수 없습니다.")
        return
    
    commands = [(key, value[0]) for key, value in game_commands.items() if value[2] != 0]
    cmds = "\n".join( f" {key}. {name}" for key, name in commands)
    while True:
        print("\n[{0}년 {1}월]: {2}[{3}] / {4}".format(gl._year, gl._month, hero.name, gl.hero_golds, home.details2()))
        
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

        if not command.action:
            print(f" . '{params[0]}' 명령어는 실행할 수 없습니다.")
            continue

        args = params[1:]
        command.action(*args)
