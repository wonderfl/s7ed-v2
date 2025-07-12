import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
# sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'utils')))

from globals import generals, items, realms, cities
from globals import __hero, __home, __load
from globals import ActionMenu

def listup_generals():
  print("--------------------------------------------------------------------------------")            
  for i, general in enumerate(generals):
      print(f" . {general.num:03}: {general}")
  print("--------------------------------------------------------------------------------")
  print("장수: {1} 명".format( 0, len(generals)))

def listup_items():
  print("--------------------------------------------------------------------------------")            
  for i, item in enumerate(items):
      print(f" . {item.num:03}: {item}")
  print("--------------------------------------------------------------------------------")
  print("아이템: {1} 개".format( 0, len(items)))

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
    "3": ActionMenu("listup realm", listup_realms, 2, "세력 리스트업."),
    "4": ActionMenu("listup cities", listup_cities, 2, "도시 리스트업."),
    "0": ActionMenu("return menu", None, 9, "이전 메뉴로."),
}

def listup():
    
    gn = len(generals)
    cn = len(cities)
    
    print(f"장수 수: {gn}, 도시 수: {cn}")
    if gn == 0 or cn == 0:
        print("장수나 도시 데이터가 없습니다. 먼저 'load' 명령어로 데이터를 불러오세요.")
        return
    
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

        
