import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
# sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'utils')))

import globals
from globals import ActionMenu

import datas.general

def listup_generals(str="-1"):
  
    state = -1
    statestr = "전체"
    if("?" == str or "5" == str):
        state = 5
        statestr = "미발견"
    elif("-" == str or "6" == str):
        state = 6
        statestr = "대기"
    else:
        try:        
            num = int(str)
            if( 0 <= num and num <= 7):
                state = num
        except (ValueError, TypeError):
            state = -1

    statestr = datas.general._STATE_[state] if state != 5 and state != 6 and state != -1 else statestr

    filtered = [general for general in globals.generals if -1 == state or ( -1 != state and general.state == state)]
    print("--------------------------------------------------------------------------------")            
    for i, general in enumerate(filtered):
        print(f" .{general.num:03}:{general}")
    print("--------------------------------------------------------------------------------")
    print("'{2}': {3} 명".format( globals._year, globals._month, statestr, len(filtered)))

def listup_items(str="-1"):    
    num = int(str)
    name = "전체"
    if( 0 <= num and num < len(globals.generals)):
        name = globals.generals[num].name
    elif ( 65535 == num ):
        name = "주인 없는"

    filtered = [item for item in globals.items if -1 == num or ( -1 != num and item.owner == num) ]
    print("--------------------------------------------------------------------------------")            
    for i, item in enumerate(filtered):
        print(f" . {item.num:03}: {item}")
    print("--------------------------------------------------------------------------------")
    print("'{2}' 아이템: {3} 개".format( globals._year, globals._month, name, len(filtered)))

def listup_owners(str="-1"):
    
    num = int(str)    
    owners = {}
    for i, item in enumerate(globals.items):
        if item.owner!=65535 and item.owner not in owners:        
            owners[item.owner]=[]
    owners[65535]=[]            

    filtered = [item for item in globals.items if -1 == num or ( -1 != num and item.owner == num) ]
    for id, item in enumerate(filtered):
        value = owners.get(item.owner)
        if value is None:
            continue
        value.append(item)

    for id, value in owners.items():
        if( -1 != num and id != num):
            continue

        name = "주인없음"
        if( 0 <= id and id < len(globals.generals)):
            name = globals.generals[id].name
    
        print("")
        #print(f"'{name}'의 아이템: {len(value)}")        
        #print("--------------------------------------------------------------------------------")    
        for i, item in enumerate(value):
            print(f" . {item.num:03}: {item}")            

def listup_realms():
    filtered = [realm for realm in globals.realms if realm.ruler != 65535]
    if not filtered:
        print("세력 정보가 없습니다.".format('realm'))
        return

    print("--------------------------------------------------------------------------------")            
    for i, realm in enumerate(filtered):
        print(f" . {realm.num:03}: {realm}")
    print("--------------------------------------------------------------------------------")
    print("[{0}년 {1}월] 세력: {2}".format( globals._year, globals._month, len(filtered)))

def listup_cities():
    print("--------------------------------------------------------------------------------")            
    for i, city in enumerate(globals.cities):
        print(f" . {city.num:03}: {city}")
    print("--------------------------------------------------------------------------------")
    print("도시: {2}".format( globals._year, globals._month, len(globals.cities)))

listup_commands = {
    "1": ActionMenu("generals", listup_generals, 2, "장수 리스트업."),
    "2": ActionMenu("items", listup_items, 2, "아이템 리스트업."),
    "3": ActionMenu("owner's items", listup_owners, 2, "아이템 리스트업."),
    "4": ActionMenu("realm", listup_realms, 2, "세력 리스트업."),
    "5": ActionMenu("cities", listup_cities, 2, "도시 리스트업."),
    "0": ActionMenu("return menu", None, 9, "이전 메뉴로."),
}

def listup():
    
    commands = [(key, value[0]) for key, value in listup_commands.items() if value[2] != 0]
    cmds = "\n".join( f"  {key}. {name}" for key, name in commands)
    while True:
        print("\n[{0}년 {1}월]: listup".format(globals._year, globals._month))
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

        
