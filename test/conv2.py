import re

def is_hex(s):
    return bool(re.fullmatch(r'[0-9a-fA-F]+', s)) and len(s) % 2 == 0

def text2hex():
  while True:
    str = input("\n(euc-kr): ").strip()
    if not str:
        break
    try:
        # 한글을 hex로
        text = str.encode("euc-kr")
    except:
        print("wrong data", str)
        continue
    
    print("  '{0}' => '{1}'".format(str, text.hex().upper()))

def hex2text():
    while True:
        str = input("\nHexCode: ").strip()
        if not str:
          break
        str = str.replace(" ", "")

        if True != is_hex(str): # 16진수 판별
            continue

        try:
            code = bytes.fromhex(str)
            # hex를 한글로
            text = code.decode("euc-kr")
        except:
            print("wrong data", str)
            continue
        
        print("  '{0}' => '{1}'".format(str, text))


def help():
  print("     Enter :   exit")  
  print("'k' or '*' : euc-kr => hex")
  print("'h' or '-' :    hex => euc-kr")

help()
while True:
    cmd = input("? ")
    if not cmd:
        break
    
    if '*'== cmd or 'k' == cmd:
        text2hex()
    elif '-' == cmd or 'h' == cmd:
        hex2text()
    else:
        help()
    
