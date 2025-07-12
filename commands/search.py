import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
# sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'utils')))

from globals import generals, items, realms, cities
from globals import generals_offset, cities_offset
from globals import __hero, __home, __load
from globals import ActionMenu

def find_city():
    while True:
        name = input("\n도시이름에서 찾을 이름? ")
        if not name:
            break
        
        filtered = [city for city in cities if name in city.name]
        if not filtered:
            print("해당 이름의 도시가 없습니다.")
            continue

        for i, city in enumerate(filtered):
            print(f" . {city.num:03}: {city}")

        if 1 > len(filtered):
            print("--------------------------------------------------------------------------------")
            print("'{0}' 으로 찾은 도시: {1}".format( name, len(filtered)))    

def find_city_num():
    while True:
        str = input("\n찾을 도시번호? ")
        if not str:
            break

        num = int(str)
        if 0> num or num >= len(cities):
            print("'{}' 도시가 없습니다.".format(num))
            break

        found = cities[num]
        if not found:
            print("'{}' 도시를 찾지 못했습니다.".format(num))
            continue

        print(f" . {found.num:03}: {found}")

        
        print("--------------------------------------------------------------------------------")
        print("번호가 '{0}' 인 도시 : 1 명".format( num))            

def find_search():
    while True:
        name = input("\n장수이름에서 찾을 이름? ")
        if not name:
            break

        filtered = [person for person in generals if name in person.name]
        if not filtered:
            print("'{}' 으로 이름이 시작하는 장수가 없습니다.".format(name))
            continue

        for i, general in enumerate(filtered):
            print(f" . {general.num:03}: {general}")

        if 1 > len(filtered):
            print("--------------------------------------------------------------------------------")
            print("'{0}' 으로 이름이 시작하는 장수: {1} 명".format( name, len(filtered)))

def find_people():
    while True:
        name = input("\n찾을 장수이름? ")
        if not name:
            break

        filtered = [person for person in generals if name == person.name]
        if not filtered:
            print("'{}' 이름을 가진 장수가 없습니다.".format(name))
            continue

        for i, general in enumerate(filtered):
            print(f" . {general.num:03}: {general}")

        if 1 > len(filtered):
            print("--------------------------------------------------------------------------------")
            print("이름이 '{0}' 인 장수 : {1} 명".format( name, len(filtered)))        

def find_general():
    while True:
        str = input("\n찾을 장수번호? ")
        if not str:
            break

        num = int(str)
        if 0> num or num >= len(generals):
            print("'{}' 장수가 없습니다.".format(num))
            break

        found = generals[num]
        if not found:
            print("'{}' 장수를 찾지 못했습니다.".format(num))
            continue

        print(f" . {found.num:03}: {found}")

        
        print("--------------------------------------------------------------------------------")
        print("번호가 '{0}' 인 장수 : 1 명".format( num))


def find_family():
    while True:
        name = input("\n가문을 찾을 장수이름? ")
        if not name:
            break
        founds = [found for found in generals if name == found.name]
        if not founds:
            print("'{}' 장수가 없습니다.".format(name))
            continue

        for i, found in enumerate(founds):
            if( 65535 == found.family):
                print("'{}'의 가문[-] 정보가 없습니다.".format(name))
                continue
            
            founder = generals[found.family]
            print("\n'{0}'의 가문: '{1}'".format( name, founder.name))

            filtered = [person for person in generals if found.family == person.family]
            if not filtered:
                print("'{}' 가문의 장수가 없습니다.".format(founder.name))
                continue

            filtered.sort(key=lambda x: x.birthyear)
            
            print("--------------------------------------------------------------------------------")            
            for i, general in enumerate(filtered):
                print(f" . {general.num:03}: {general}")
            print("--------------------------------------------------------------------------------")
            print("'{0}' 가문의 장수: {1} 명".format( founder.name, len(filtered)))

def find_parent():
    while True:
        name = input("\n자녀를 찾을 장수이름? ")
        if not name:
            break
        founds = [found for found in generals if name == found.name]
        if not founds:
            print("'{}' 장수가 없습니다.".format(name))
            continue

        for i, found in enumerate(founds):
            filtered = [person for person in generals if found.num == person.parent]
            if not filtered:
                print("'{}' 의 자녀인 장수가 없습니다.".format(name))
                continue

            print("--------------------------------------------------------------------------------")
            for i, general in enumerate(filtered):
                print(f" . {general.num:03}: {general}")
            print("--------------------------------------------------------------------------------")
            print("'{0}'의 자녀인 장수: {1} 명".format( name, len(filtered)))

def find_sibling():
    while True:
        name = input("\n형제를 찾을 장수이름? ")
        if not name:
            break
        founds = [found for found in generals if name == found.name]
        if not founds:
            print("'{}' 장수가 없습니다.".format(name))
            continue

        for i, found in enumerate(founds):
            if( 65535 == found.parent):
                print("'{}'의 부모[-] 정보가 없습니다.".format(name))
                continue
            
            parents = [person for person in generals if found.parent == person.num] 
            parent_name = parents[0].name if parents else str(found.parent)

            filtered = [person for person in generals if found.parent == person.parent and found.num != person.num]
            if not filtered:
                print("'{0}[{1}]'와 형제인 장수가 없습니다.".format(name, parent_name))
                continue

            print("--------------------------------------------------------------------------------")
            for i, general in enumerate(filtered):
                print(f" . {general.num:03}: {general}")
            print("--------------------------------------------------------------------------------")
            print("'{0}[{1}]'의 형제 장수: {2} 명".format( name, parent_name, len(filtered)))            


find_commands = {
    "1": ActionMenu("find city", find_city, 2, "이름으로 도시 검색."),
    "2": ActionMenu("find city no", find_city_num, 2, "번호로 도시 검색."),
    "3": ActionMenu("find name", find_search, 2, "문자열로 장수 검색."),
    "4": ActionMenu("find general", find_people, 2, "이름으로 장수 검색."),
    "5": ActionMenu("find general no", find_general, 2, "번호로 장수 검색."),

    "6": ActionMenu("find with family", find_family, 4, "같은 가문의 다른 장수 검색."),
    "7": ActionMenu("find from parent", find_parent, 4, "부모로 자녀 검색."),
    "8": ActionMenu("find siblings", find_sibling, 4, "형제 장수 검색."),
    "0": ActionMenu("return menu", None, 9, "이전 메뉴로."),
}

def search():
    commands = [(key, value[0]) for key, value in find_commands.items() if value[2] != 0]
    cmds = "\n".join( f" {key}. {name}" for key, name in commands)
    while True:
        #print(f"\n도시이름: {home.name}[{home.num:03}]\n장수이름: {hero.name}[{hero.num:03}]")

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

        
