import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
# sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'utils')))

import globals
from globals import ActionMenu

def find_city():
    while True:
        str = input("\n찾을 도시? ")
        if not str:
            break

        try:
            num = int(str)
            if( 0 <= num and num < len(globals.cities)):
                name = globals.cities[num].name
            else:
                print("해당 도시가 없습니다.")
                continue
        except:
            name = str

        
        filtered = [city for city in globals.cities if name in city.name]
        if not filtered:
            print("해당 이름의 도시가 없습니다.")
            continue

        for i, city in enumerate(filtered):
            print(f" . {city.num:03}: {city}")

        if 1 > len(filtered):
            print("--------------------------------------------------------------------------------")
            print("'{0}' 으로 찾은 도시: {1}".format( name, len(filtered)))

def find_general():
    while True:
        str = input("\n찾을 장수? ")
        if not str:
            break

        try:
            num = int(str)
            if( 0 <= num and num < len(globals.generals)):
                name = globals.generals[num].name
            else:
                print("해당 장수가 없습니다.")
                continue
        except:
            name = str

        filtered = [person for person in globals.generals if name in person.name]
        if not filtered:
            print("'{}' 이름을 가진 장수가 없습니다.".format(name))
            continue

        for i, general in enumerate(filtered):
            print(f" {general.num:03}: {general}")

        if 1 > len(filtered):
            print("--------------------------------------------------------------------------------")
            print("이름이 '{0}' 인 장수 : {1} 명".format( name, len(filtered)))


def find_family():
    while True:
        str = input("\n가문을 찾을 장수? ")
        if not str:
            break

        try:
            num = int(str)
            if( 0 <= num and num < len(globals.generals)):
                name = globals.generals[num].name
            else:
                print("해당 장수가 없습니다.")
                continue
        except:
            name = str

        founds = [found for found in globals.generals if name == found.name]
        if not founds:
            print("'{0}' 장수가 없습니다.".format(name))
            continue

        for i, found in enumerate(founds):
            if( 65535 == found.family):
                print("'{0}[{1}]'의 가문 정보가 없습니다.".format(name, found.num))
                continue
            
            founder = globals.generals[found.family]
            filtered = [person for person in globals.generals if found.family == person.family]
            if not filtered or 1 >= len(filtered):
                print("'{0}[{1}]' 가문의 장수가 없습니다.".format(founder.name, founder.num))
                continue

            filtered.sort(key=lambda x: x.birthyear)

            print("\n{0}[{1}]의 가문: '{2}'".format( name, found.num, founder.name, len(filtered)))
            print("--------------------------------------------------------------------------------")            
            for i, general in enumerate(filtered):
                print(f" {general.num:03}: {general}")
            print("--------------------------------------------------------------------------------")            
            print("'{0}[{1}]' 가문의 장수: {2} 명".format( founder.name, founder.num, len(filtered)))

def find_parent():
    while True:
        str = input("\n자녀를 찾을 장수? ")
        if not str:
            break

        try:
            num = int(str)
            if( 0 <= num and num < len(globals.generals)):
                name = globals.generals[num].name
            else:
                print("해당 장수가 없습니다.")
                continue
        except:
            name = str

        founds = [found for found in globals.generals if name == found.name]
        if not founds:
            print("'{}' 장수가 없습니다.".format(name))
            continue

        for i, found in enumerate(founds):
            filtered = [person for person in globals.generals if found.num == person.parent]
            if not filtered:
                print("'{}' 의 자녀인 장수가 없습니다.".format(name))
                continue

            print("--------------------------------------------------------------------------------")
            for i, general in enumerate(filtered):
                print(f" {general.num:03}: {general}")
            print("--------------------------------------------------------------------------------")
            print("'{0}[{1}]'의 자녀인 장수: {2} 명".format( name, found.num, len(filtered)))

def find_sibling():
    while True:
        str = input("\n형제를 찾을 장수? ")
        if not str:
            break

        try:
            num = int(str)
            if( 0 <= num and num < len(globals.generals)):
                name = globals.generals[num].name
            else:
                print("해당 장수가 없습니다.")
                continue
        except:
            name = str

        founds = [found for found in globals.generals if name == found.name]
        if not founds:
            print("'{}' 장수가 없습니다.".format(name))
            continue

        for i, found in enumerate(founds):
            if( 65535 == found.parent):
                print("'{0}[{1}]'의 부모 정보가 없습니다.".format( name, found.num ))
                continue
            
            parents = [person for person in globals.generals if found.parent == person.num] 
            
            parent_num = found.parent
            parent_name = parents[0].name if parents else "{}".format(found.parent)

            filtered = [person for person in globals.generals if found.parent == person.parent and found.num != person.num]
            if not filtered:
                print("'{0}[{1}]'의 형제인 장수가 없습니다.".format(name, found.num))
                continue

            print("\n'{0}[{1}]'의 부모: {2}[{3}] ".format( name, found.num, parent_name, parent_num))
            print("--------------------------------------------------------------------------------")
            for i, general in enumerate(filtered):
                print(f" {general.num:03}: {general}")
            print("--------------------------------------------------------------------------------")
            print("'{0}[{1}]'의 형제 장수: {2} 명".format( name, found.num, len(filtered)))


find_commands = {
    "1": ActionMenu("city", find_city, 2, "도시 검색."),
    "2": ActionMenu("general", find_general, 2, "장수 검색."),

    "3": ActionMenu("family", find_family, 4, "가문의 장수 검색."),
    "4": ActionMenu("child", find_parent, 4, "자녀 검색."),
    "5": ActionMenu("siblings", find_sibling, 4, "형제 검색."),
    "0": ActionMenu("return menu", None, 9, "이전 메뉴로."),
}

def search(*args):
    commands = [(key, value[0]) for key, value in find_commands.items() if value[2] != 0]
    cmds = "\n".join( f"  {key}. {name}" for key, name in commands)
    while True:
        print("\n[{0}년 {1}월]: search".format(globals._year, globals._month))
        params = input("\n{0}\n\n? ".format(cmds)).split()
        if( 0 >= len(params)):
            break
        
        if( "0" == params[0]):
            return
    
        command = find_commands.get(params[0])
        if not command:
            print(f" . '{params[0]}' 명령어를 찾을 수 없습니다.")
            continue
        if not command.action:
            print(f" . '{params[0]}' 명령어는 실행할 수 없습니다.")
            continue

        args = params[1:]
        command.action(*args)