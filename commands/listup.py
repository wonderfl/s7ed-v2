import sys
import os
import re

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
# sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'utils')))

import globals as gl
import datas.general as data

def listup_items(str="-1"):    
    num = int(str)
    name = "전체"
    if( 0 <= num and num < len(gl.generals)):
        name = gl.generals[num].name
    elif ( 65535 == num ):
        name = "주인 없는"

    filtered = [item for item in gl.items if -1 == num or ( -1 != num and item.owner == num) ]
    print("--------------------------------------------------------------------------------")            
    for i, item in enumerate(filtered):
        print(f" . {item.num:03}: {item}")
    print("--------------------------------------------------------------------------------")
    print("'{2}' 아이템: {3} 개".format( gl._year, gl._month, name, len(filtered)))

def listup_owners(str="-1"):
    
    num = int(str)    
    owners = {}
    for i, item in enumerate(gl.items):
        if item.owner!=65535 and item.owner not in owners:        
            owners[item.owner]=[]
    owners[65535]=[]            

    filtered = [item for item in gl.items if -1 == num or ( -1 != num and item.owner == num) ]
    for id, item in enumerate(filtered):
        value = owners.get(item.owner)
        if value is None:
            continue
        value.append(item)

    for id, value in owners.items():
        if( -1 != num and id != num):
            continue

        name = "주인없음"
        if( 0 <= id and id < len(gl.generals)):
            name = gl.generals[id].name
    
        print("")
        #print(f"'{name}'의 아이템: {len(value)}")        
        #print("--------------------------------------------------------------------------------")    
        for i, item in enumerate(value):
            print(f" . {item.num:03}: {item}")            

def listup_realms():
    filtered = [realm for realm in gl.realms if realm.ruler != 65535]
    if not filtered:
        print("세력 정보가 없습니다.".format('realm'))
        return

    print("--------------------------------------------------------------------------------")            
    for i, realm in enumerate(filtered):
        print(f" . {realm.num:03}: {realm}")
    print("--------------------------------------------------------------------------------")
    print("[{0}년 {1}월] 세력: {2}".format( gl._year, gl._month, len(filtered)))

def listup_cities():
    print("--------------------------------------------------------------------------------")            
    for i, city in enumerate(gl.cities):
        print(f" . {city.num:03}: {city}")
    print("--------------------------------------------------------------------------------")
    print("도시: {2}".format( gl._year, gl._month, len(gl.cities)))


# 12345678901234567890123456789012345678901234567890123456789012345678901234567890
#################################################################################
# 장수 신분을 가변인자로 받아 장수를 필터링
# 디폴트는 주인공이 있는 도시
# 옵션: /:ablities, *:props, +:equips, - 가변인자에서 값으로 받아 stats, props 출력
#

def listup_generals(*args):

    props = False
    abilities = False    
    equips = False
    
    states = set()
    max_state = len(gl._rankStates_)
    for arg in args:
        if False == arg.isdecimal():
            if "*" in arg: # props
                props = True                
            if "/" in arg: # equips
                abilities = True
            if "+" in arg: # equips
                equips = True
        try:
            if -1 in states:
                state = -1
                continue
            
            if("?" == arg):
                state = 5
            elif("-" == arg):
                state = 6
            else:
                if False == arg.isdigit():
                    continue

                state = int(arg)
                if -1 == state:
                    states.clear()
                    states.add(state)
                    continue

            if 0 > state or state >= max_state:
                continue
            if state in states:
                continue

            states.add(state)
        except:
            print("wrong state: ", arg)
            continue

    if 0 >= len(states):
        state = -1
        states.add(state)

    for state in sorted(states):            
        statestr = "전체"
        if 0 <= state and state < max_state:
            statestr = gl._rankStates_[state]

        filtered = [general for general in gl.generals if -1 == state or ( -1 != state and general.state == state)]
        print("")
        for i, general in enumerate(filtered):
            #print(f" .{general.num:03}:{general}")
            print(" {0:03}: {1}{2}{3}{4}".format(
                general.num, general.profiles() + general.stats(), 
                general.abilities() if abilities else "", 
                general.properties()if props else "", 
                general.equipments() if equips else ""))
        print("--------------------------------------------------------------------------------")
        print("'{2}': {3} 명".format( gl._year, gl._month, statestr, len(filtered)))    

listup_commands = {
    "1": gl.ActionMenu("generals", listup_generals, 2, "장수 리스트업."),
    "2": gl.ActionMenu("items", listup_items, 2, "아이템 리스트업."),
    "3": gl.ActionMenu("owner's items", listup_owners, 2, "아이템 리스트업."),
    "4": gl.ActionMenu("realm", listup_realms, 2, "세력 리스트업."),
    "5": gl.ActionMenu("cities", listup_cities, 2, "도시 리스트업."),
    "0": gl.ActionMenu("return menu", None, 9, "이전 메뉴로."),
}

def listup(*args):
    
    commands = [(key, value[0]) for key, value in listup_commands.items() if value[2] != 0]
    cmds = "\n".join( f"  {key}. {name}" for key, name in commands)
    while True:
        print("\n[{0}년 {1}월]: listup".format(gl._year, gl._month))

        text = input("\n{0}\n\n? ".format(cmds))
        params = [p for p in re.split(r'[ .,]', text) if p]
        if( 0 >= len(params)):
            break
        
        if( "0" == params[0]):
            return
    
        command = listup_commands.get(params[0])
        if not command:
            print(f" . '{params[0]}' 명령어를 찾을 수 없습니다.")
            continue

        if not command.action:
            print(f" . '{params[0]}' 명령어는 실행할 수 없습니다.")
            continue

        args = params[1:]
        command.action(*args)

        
