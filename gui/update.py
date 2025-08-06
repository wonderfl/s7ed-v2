import globals as gl

def refill_general_actions( count, selected):
    data0 = selected.get_turns() # 행동유무
    data1 = selected.unpacked[20] # 행동력
    
    value0 = 0
    value1 = 200
                
    selected.set_turns(value0)
    selected.turned = value0

    selected.unpacked[20] = value1
    selected.actions = value1    

    print("{0:3}. {1}[{2:3}][ {3},{4:3} => {5},{6:3} ]".format(count, selected.fixed, selected.num, data0, data1, value0, value1))

def refill_general_captures( count, selected):
    data0 = selected.unpacked[21] # 포획 군주
    data1 = selected.unpacked[49] # 포획 횟수

    value0 = 65535
    value1 = 0

    selected.unpacked[21] = value0
    selected.capture_ruler = value0
    selected.unpacked[49] = value1
    selected.capture_cnt = value1

    print("{0:3}. {1}[{2:3}][ {3},{4:3} => {5},{6:3} ]".format(count, selected.fixed, selected.num, data0, data1, value0, value1))    


def refill_soldiers_training( count, selected):
    data0 = selected.unpacked[7] #병사
    data1 = selected.unpacked[41] #훈련
    if 0 >= data0: # 병사가 없으면
        return False
    value1 = 100
    selected.unpacked[41] = value1
    selected.training = value1

    print("{0:3}. {1}[{2:3}][ {3:6}, {4:3} => {5:3} ]".format(count, selected.fixed, selected.num, data0, data1, value1))
    return True

def refill_general_soldiers( count, selected):
    data0 = selected.unpacked[7]    # 병사
    data1 = selected.unpacked[41]   # 훈련
    
    state = selected.unpacked[26]   # 신분
    
    rank = selected.unpacked[39]   # rank
    if 0 > rank or rank >= 5:
        return False
    
    rank_soldier=[10000, 12000, 14000, 17000, 20000]
    max_soldier = rank_soldier[rank]
    if 0 == state: # 군주이면
        max_soldier = rank_soldier[4 ]

    value0 = data0 + 500
    value0 = int(value0/500)*500
    if value0 > max_soldier: # 병사가 없으면
        value0 = max_soldier

    selected.unpacked[7] = value0
    selected.soldier = value0
    
    value1 = 100 # 훈련
    selected.unpacked[41] = value1
    selected.training = value1

    print("{0:3}. {1}[{2:3}][ {3:6},{4:3} => {5:6},{6:3} ]".format(count, selected.fixed, selected.num, data0, data1, value0, value1))
    return True

def refill_general_loyalty( count, selected):
    data0 = selected.unpacked[37] # 충성
    value0 = data0 + 5
    if 94 <= data0:
        value0 = data0
    elif 94 <= value0:
        value0 = 94
    selected.unpacked[37] = value0
    selected.loyalty = value0

    if data0 == value0:
        return False
    
    print("{0:3}. {1}[{2:3}][ {3:3} ]".format(count, selected.fixed, selected.num, value0))
    return True



def refill_general_relation( count, selected):
    data0 = gl.relations[selected.num]
    value0 = data0 + 10
    if 100 <= value0:
        value0 = data0
    gl.relations[selected.num] = value0

    if data0 == value0:
        return False
    
    print("{0:3}. {1}[{2:3}][ {3:3} ]".format(count, selected.fixed, selected.num, value0,))
    return True