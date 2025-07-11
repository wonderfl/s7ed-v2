import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from globals import generals, cities

def game_play():
    while True:
        name = input("\n이동할 도시이름: ")
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
        
        num = int(input("이동할 도시번호? "))
        if num < 0 or num >= len(cities):
            print("잘못된 도시번호입니다.")
            continue

        # 이동 로직 구현
        print(f"도시 '{filtered[0].name}' 에서 '{cities[num].name}' 으로 이동합니다.")