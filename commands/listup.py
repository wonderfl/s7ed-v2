import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
# sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'utils')))

from globals import generals, items, realms, cities
from globals import __hero, __home, __load
from globals import ActionMenu

def listup_generals(str="-1"):
  
    state = -1
    if("+" == str):
        state = 5        
    elif("?" == str):
        state = 6
    else:
        try:        
            num = int(str)
            if( 0 <= num and num <= 7):
                state = num
        except (ValueError, TypeError):
            state = -1

    filtered = [general for general in generals if -1 == state or ( -1 != state and general.state == state)]
    print("--------------------------------------------------------------------------------")            
    for i, general in enumerate(filtered):
        print(f" .{general.num:03}:{general}")
    print("--------------------------------------------------------------------------------")
    print("장수: {1} 명".format( 0, len(filtered)))

def listup_items(str="-1"):    
    num = int(str)
    name = "전체"
    if( 0 <= num and num < len(generals)):
        name = generals[num].name
    elif ( 65535 == num ):
        name = "주인 없는"

    filtered = [item for item in items if -1 == num or ( -1 != num and item.owner == num) ]
    print("--------------------------------------------------------------------------------")            
    for i, item in enumerate(filtered):
        print(f" . {item.num:03}: {item}")
    print("--------------------------------------------------------------------------------")
    print("'{0}' 아이템: {1} 개".format( name, len(filtered)))

def listup_owners(str="-1"):
    
    num = int(str)    
    owners = {}
    for i, item in enumerate(items):
        if item.owner not in owners:        
            owners[item.owner]=[]

    filtered = [item for item in items if -1 == num or ( -1 != num and item.owner == num) ]
    for id, item in enumerate(filtered):
        value = owners.get(item.owner)
        if value is None:
            continue
        value.append(item)

    for id, value in owners.items():
        if( -1 != num and id != num):
            continue

        name = "주인없음"
        if( 0 <= id and id < len(generals)):
            name = generals[id].states()
    
        print("")
        print(f"'{name}'의 아이템: {len(value)}")        
        print("--------------------------------------------------------------------------------")    
        for i, item in enumerate(value):
            print(f" . {item.num:03}: {item}")            

def listup_realms():
    filtered = [realm for realm in realms if realm.ruler != 65535]
    if not filtered:
        print("세력 정보가 없습니다.".format('realm'))
        return

    print("--------------------------------------------------------------------------------")            
    for i, realm in enumerate(filtered):
        print(f" . {realm.num:03}: {realm}")
    print("--------------------------------------------------------------------------------")
    print("세력: {1}".format( 0, len(filtered)))

def listup_cities():
    print("--------------------------------------------------------------------------------")            
    for i, city in enumerate(cities):
        print(f" . {city.num:03}: {city}")
    print("--------------------------------------------------------------------------------")
    print("장수: {1} 명".format( 0, len(cities)))

listup_commands = {
    "1": ActionMenu("listup generals", listup_generals, 2, "장수 리스트업."),
    "2": ActionMenu("listup items", listup_items, 2, "아이템 리스트업."),
    "3": ActionMenu("listup owner's items", listup_owners, 2, "아이템 리스트업."),
    "4": ActionMenu("listup realm", listup_realms, 2, "세력 리스트업."),
    "5": ActionMenu("listup cities", listup_cities, 2, "도시 리스트업."),
    "0": ActionMenu("return menu", None, 9, "이전 메뉴로."),
}

def listup():
    
    commands = [(key, value[0]) for key, value in listup_commands.items() if value[2] != 0]
    cmds = "\n".join( f" {key}. {name}" for key, name in commands)
    while True:
        #print(f"\n도시이름: {home.name}[{home.num:03}]\n장수이름: {hero.name}[{hero.num:03}]")

        params = input("\n{0}\n\n? ".format(cmds)).split()
        if( 0 >= len(params)):
            break
        
        if( "0" == params[0]):
            return
    
        command = listup_commands.get(params[0])
        if not command:
            print(f" . '{params[0]}' 명령어를 찾을 수 없습니다.")
            continue

        args = params[1:]
        if not command.action:
            print(f" . '{params[0]}' 명령어는 실행할 수 없습니다.")
            continue

        command.action(*args)

        
