import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
# sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'utils')))

from globals import generals, cities, generals_offset, cities_offset
from globals import __hero, __home, __load

def find_city():
    while True:
        name = input("\n도시이름? ")
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
            print("'{0}' 으로 찾은 도시: {1}".format( name, len(filtered)))    

def find_search():
    while True:
        name = input("\n찾는이름? ")
        if not name:
            break

        filtered = [person for person in generals if person.name.startswith(name)]
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
        name = input("\n장수이름? ")
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


def find_family():
    while True:
        name = input("\n장수이름? ")
        if not name:
            break
        founds = [found for found in generals if name == found.name]
        if not founds:
            print("'{}' 장수가 없습니다.".format(name))
            continue

        for i, found in enumerate(founds):
            if( 65535 == found.family):
                print("'{}' 의 가문[-] 정보가 없습니다.".format(name))
                continue
            
            founder = generals[found.family]
            print("\n'{0}' 의 가문: '{1}'".format( name, founder.name))
            filtered = [person for person in generals if found.family == person.family]
            if not filtered:
                print("'{}' 가문의 장수가 없습니다.".format(name))
                continue

            filtered.sort(key=lambda x: x.birthyear)
            for i, general in enumerate(filtered):
                print(f" . {general.num:03}: {general}")
            print("--------------------------------------------------------------------------------")                
            print("'{0}'의 가문'{1}' 장수: {2} 명".format( name, founder.name, len(filtered)))

def find_parent():
    while True:
        name = input("\n부모이름? ")
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

            for i, general in enumerate(filtered):
                print(f" . {general.num:03}: {general}")
            print("--------------------------------------------------------------------------------")
            print("'{0}' 의 자녀인 장수: {1} 명".format( name, len(filtered)))

def find_sibling():
    while True:
        name = input("\n장수이름? ")
        if not name:
            break
        founds = [found for found in generals if name == found.name]
        if not founds:
            print("'{}' 장수가 없습니다.".format(name))
            continue

        for i, found in enumerate(founds):
            if( 65535 == found.parent):
                print("'{}' 의 부모[-] 정보가 없습니다.".format(name))
                continue
            
            parents = [person for person in generals if found.parent == person.num] 
            parent_name = parents[0].name if parents else str(found.parent)

            filtered = [person for person in generals if found.parent == person.parent and found.num != person.num]
            if not filtered:
                print("'{0}[{1}]'와 형제인 장수가 없습니다.".format(name, parent_name))
                continue

            for i, general in enumerate(filtered):
                print(f" . {general.num:03}: {general}")
            print("--------------------------------------------------------------------------------")
            print("'{0}[{1}]' 의 형제 장수: {2} 명".format( name, parent_name, len(filtered)))            


searches = {
    "도시": find_city,
    "이름": find_search,
    "장수": find_people,
    "가문": find_family,
    "부모": find_parent,
    "형제": find_sibling,
}

def search():
    gn = len(generals)
    cn = len(cities)
    
    print(f"장수 수: {gn}, 도시 수: {cn}")
    if gn == 0 or cn == 0:
        print("장수나 도시 데이터가 없습니다. 먼저 'load' 명령어로 데이터를 불러오세요.")
        return
    
    commands = ", ".join(searches.keys())
    while True:
        command = input(f"{commands}\n찾을 명령어? ")
        if not command:
            break

        if command in searches:
            searches[command]()
            continue
        
        # 지원하지 않는 명령어 처리
        if command not in searches:        
          print(f"'{command}' 명령어는 지원하지 않습니다. 다음 명령어를 사용하세요: {', '.join(searches.keys())}")

        
