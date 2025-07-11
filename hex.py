import sys

__str = \
"41 5C 19 E3 F0 3C EE 43 76 FE F1 A7 45 D9 C8 2A \
 CB C9 DC 8E 1B 59 5D 18 A1 08 82 F6 23 6B DB A6 \
 FD 1E 51 12 F3 4F EF E7 A5 E8 4B D6 7C 68 FF 56 \
 6C 86 17 F5 A3 95 AD 8F 83 0E EB 07 36 A0 39 AC \
 4C 74 49 11 8C D5 3F E2 42 5A EA 67 96 85 91 26 \
 9A C2 2F EC 97 24 46 32 64 20 65 B7 53 7F 40 E5 \
 2E DA CF 2D 4E ED FB 90 81 E9 B1 9D 80 77 F7 7E \
 A4 6A 57 09 62 35 55 BD 5F 9B 6D A8 16 C3 4D 75 \
 22 1C 03 0B 54 48 1D 3A 78 93 30 BA 92 9F 0A 02 \
 2C AF 50 6E 44 B3 FC 4A C5 79 31 FA 69 9C C0 CC \
 13 F8 1A 34 D8 B0 B4 14 72 84 BB E4 8A C4 AB E1 \
 B5 8D D0 0C 37 CA D1 47 CE 15 0D 0F 27 99 01 89 \
 58 61 A9 D3 C1 28 AE 00 70 21 5B 05 04 F2 B9 3B \
 5E 98 BC 06 AA 94 A2 F9 3E B8 29 7D F4 E0 B6 66 \
 63 73 C7 D2 38 8B 6F 52 33 88 3D 1F C6 10 7A 2B \
 D4 87 25 E6 9E DF B2 D7 DE 71 BF 7B 60 DD BE CD"

__list = __str.split()
__exch = bytes(int(h, 16) for h in __list)



from utils.city import CityState, CityStateStruct
from utils.general import General, GeneralStruct,CITY_NAMES

def __decrypt(data: bytes ) -> bytes:
    return bytes( __exch[b] for b in data)

ln = len(sys.argv)
if ln < 2:
    print("사용법: python hex.py <파일명>")
    exit(1)

fname = sys.argv[1]
if not fname.endswith(".s7"):
    print("파일명은 .s7 확장자를 가져야 합니다.")
    exit(2)

generals_offset = 0x009C  # 장수 데이터 시작 위치 예시
generals = []

cities_offset = 0x000154C6  # 장수 데이터 시작 위치 예시
cities = []

# 장수 620명 기준 읽기 예시
with open(fname, "rb") as f:
    for i in range(620): # 620명 기준
        f.seek(generals_offset + i * GeneralStruct.size)
        chunk = f.read(GeneralStruct.size)
        decoded = __decrypt(chunk)

        general = General(i,decoded)
        generals.append(general)

    for i in range(54): # 54개 도시 기준
        f.seek(cities_offset + i * CityStateStruct.size)
        chunk = f.read(CityStateStruct.size)
        decoded = __decrypt(chunk)

        city = CityState(i, CITY_NAMES[i], decoded)
        cities.append(city)

#for i, general in enumerate(generals):
#    print(f"{i:03}: {general}")

#generals_dict = {general.name: general for general in generals}
#ln = len(generals_dict)
#print(ln)

# print(generals_dict.keys())
# name = "강유"
# if name in generals_dict:
#     print(generals_dict[name])

def quit():
    exit(0)

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
            print("\n'{0}' 의 가문: '{1}'".format( name, generals[found.family].name))
            filtered = [person for person in generals if found.family == person.family]
            if not filtered:
                print("'{}' 가문의 장수가 없습니다.".format(name))
                continue

            filtered.sort(key=lambda x: x.birthyear)
            for i, general in enumerate(filtered):
                print(f" . {general.num:03}: {general}")
            print("--------------------------------------------------------------------------------")                
            print("'{0}' 가문의 장수: {1} 명".format( generals[found.family].name, len(filtered)))

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
    

commands = {
    "도시": find_city,
    "이름": find_search,
    "장수": find_people,
    "가문": find_family,
    "부모": find_parent,
    "quit": quit,
    "exit": quit
}

menu = 0
while True:
    cmd = input(": ")
    action = commands.get(cmd, lambda: quit())
    action()