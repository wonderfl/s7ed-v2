from datas.city import CityState, CityStateStruct
from datas.general import General, GeneralStruct,CITY_NAMES

def xor_partial(data: bytes, offset: int, length: int, key: int) -> bytes:
    chunk = data[offset:offset+length]
    return bytes(b ^ key for b in chunk)


def xor_decrypt(data: bytes, key: int) -> bytes:
    return bytes(b ^ key for b in data)




generals_offset = 0x009C  # 장수 데이터 시작 위치 예시
generals = []

cities_offset = 0x000154C6  # 장수 데이터 시작 위치 예시
cities = []

# 장수 620명 기준 읽기 예시
with open("D_Save07dec.s7", "rb") as f:
    for i in range(620): # 620명 기준
        f.seek(generals_offset + i * GeneralStruct.size)
        chunk = f.read(GeneralStruct.size)
        general = General(chunk)
        generals.append(general)

    for i in range(54): # 54개 도시 기준
        f.seek(cities_offset + i * CityStateStruct.size)
        chunk = f.read(CityStateStruct.size)
        city = CityState(i, chunk)
        cities.append(city)

# 출력 예시
for i, general in enumerate(generals):
    cname = CITY_NAMES[general.city] if general.city < len(CITY_NAMES) else "Unknown"
    print(f"{i:03}: {general.name()}, {cname}")

for i, city in enumerate(cities):
    gov = generals[city.governor]
    gname = gov.name()
    cname = CITY_NAMES[city.num]
    print(f"{i:03}. {cname}[{gname}]{city}")