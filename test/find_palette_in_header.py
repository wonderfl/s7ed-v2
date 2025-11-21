"""Kaodata.s7 헤더에서 팔레트 찾기"""
import struct
import os
from PIL import Image

def find_palette():
    filename = 'saves/Kaodata.s7'
    HEADER_SIZE = 10372
    palette_size = 256 * 3  # 768 bytes
    
    with open(filename, 'rb') as f:
        # 헤더 전체 읽기
        header = f.read(HEADER_SIZE)
        
        print(f"=== Header Size: {HEADER_SIZE} bytes ===")
        print(f"Looking for palette (768 bytes) in header...\n")
        
        # 헤더 끝 부분부터 역순으로 검색 (팔레트는 보통 헤더 끝에 있음)
        # 또는 특정 오프셋에서 검색
        
        # 일반적인 팔레트 위치 후보들
        # 1. 헤더 시작 부분
        # 2. 헤더 끝 부분 (HEADER_SIZE - 768)
        # 3. 특정 오프셋
        
        test_offsets = [
            0,                    # 시작
            200,                  # 이전 분석에서 발견
            1000,                 # 중간
            2000,                 # 중간
            5000,                 # 중간
            HEADER_SIZE - 768,   # 헤더 끝
            HEADER_SIZE - 1024,  # 헤더 끝 (RGBA 가능성)
        ]
        
        # 기존 PNG의 팔레트와 비교
        ref_img = Image.open('gui/png/face000.png')
        ref_palette = ref_img.palette.palette
        
        print("Reference palette (from PNG) first 10 colors:")
        for i in range(10):
            r = ref_palette[i*3]
            g = ref_palette[i*3+1]
            b = ref_palette[i*3+2]
            print(f"  Color {i}: RGB({r:3d}, {g:3d}, {b:3d})")
        
        print("\n=== Testing offsets ===")
        
        best_match = None
        best_score = 0
        
        for offset in test_offsets:
            if offset + palette_size > len(header):
                continue
            
            palette_data = header[offset:offset+palette_size]
            
            # 유효성 검사: 모든 값이 0-255 범위
            is_valid = True
            for b in palette_data:
                if b > 255:
                    is_valid = False
                    break
            
            if not is_valid:
                continue
            
            # 기존 팔레트와 비교
            match_count = 0
            for i in range(min(50, len(palette_data) // 3)):  # 처음 50개 색상 비교
                r1 = ref_palette[i*3]
                g1 = ref_palette[i*3+1]
                b1 = ref_palette[i*3+2]
                
                r2 = palette_data[i*3]
                g2 = palette_data[i*3+1]
                b2 = palette_data[i*3+2]
                
                if r1 == r2 and g1 == g2 and b1 == b2:
                    match_count += 1
            
            score = match_count
            
            print(f"\nOffset {offset:05X} ({offset:5d}):")
            print(f"  First 10 colors: RGB({palette_data[0]:3d},{palette_data[1]:3d},{palette_data[2]:3d}), "
                  f"RGB({palette_data[3]:3d},{palette_data[4]:3d},{palette_data[5]:3d}), "
                  f"RGB({palette_data[6]:3d},{palette_data[7]:3d},{palette_data[8]:3d}), "
                  f"RGB({palette_data[9]:3d},{palette_data[10]:3d},{palette_data[11]:3d})")
            print(f"  Match score: {score}/50")
            
            # 테스트 이미지 생성
            try:
                f.seek(HEADER_SIZE)  # 첫 번째 얼굴 데이터
                face_data = f.read(96 * 120)
                if len(face_data) == 96 * 120:
                    img = Image.frombytes('P', (96, 120), face_data)
                    img.putpalette(palette_data)
                    test_path = f'test/palette_header_{offset:05X}.png'
                    img.save(test_path)
                    print(f"  Test image: {test_path}")
            except Exception as e:
                print(f"  Test failed: {e}")
            
            if score > best_score:
                best_score = score
                best_match = (offset, palette_data)
        
        if best_match:
            offset, palette_data = best_match
            print(f"\n=== Best Match ===")
            print(f"Offset: {offset:05X} ({offset})")
            print(f"Match score: {best_score}/50")
            return offset, palette_data
        else:
            print("\n=== No good match found in header ===")
            return None, None

if __name__ == '__main__':
    find_palette()

