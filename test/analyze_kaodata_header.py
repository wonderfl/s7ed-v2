"""Kaodata.s7 헤더 분석 - 팔레트 찾기"""
import struct
import os
from PIL import Image

def analyze_header():
    filename = 'saves/Kaodata.s7'
    
    with open(filename, 'rb') as f:
        # 헤더 읽기 (더 많이 읽어서 분석)
        header = f.read(2000)
        
        print("=== Header Analysis ===")
        print("First 50 integers (little endian):")
        for i in range(0, 200, 4):
            val = struct.unpack('<I', header[i:i+4])[0]
            if val < 1000000:  # 너무 큰 값은 제외
                print(f"  Offset {i:04X}: {val:8d} (0x{val:08X})")
        
        # 팔레트는 보통 768 bytes (256색 * 3 RGB)
        # 또는 1024 bytes (256색 * 4 RGBA)
        palette_size_rgb = 256 * 3  # 768
        palette_size_rgba = 256 * 4  # 1024
        
        print(f"\n=== Palette Search ===")
        print(f"Looking for palette (RGB: {palette_size_rgb} bytes, RGBA: {palette_size_rgba} bytes)")
        
        # 헤더에서 팔레트 후보 위치 찾기
        # 일반적으로 팔레트는 헤더 앞부분에 있을 수 있음
        
        # 오프셋 200 이후부터 팔레트 데이터가 있을 수 있음
        # 256색 팔레트는 RGB로 768바이트
        
        # 여러 위치에서 팔레트 시도
        test_offsets = [0, 200, 400, 600, 800, 1000, 1200, 1400, 1600, 1800]
        
        for offset in test_offsets:
            if offset + palette_size_rgb > len(header):
                continue
            
            palette_data = header[offset:offset+palette_size_rgb]
            
            # RGB 팔레트인지 확인 (모든 값이 0-255 범위인지)
            is_valid = True
            for b in palette_data:
                if b > 255:
                    is_valid = False
                    break
            
            if is_valid:
                print(f"\n  Offset {offset:04X}: Possible RGB palette found")
                print(f"    First 10 colors:")
                for i in range(min(10, len(palette_data) // 3)):
                    r = palette_data[i*3]
                    g = palette_data[i*3+1]
                    b = palette_data[i*3+2]
                    print(f"      Color {i}: RGB({r:3d}, {g:3d}, {b:3d})")
                
                # 팔레트로 이미지 테스트
                try:
                    f.seek(200)  # 첫 번째 얼굴 데이터 위치
                    face_data = f.read(96 * 120)
                    if len(face_data) == 96 * 120:
                        img = Image.frombytes('P', (96, 120), face_data)
                        img.putpalette(palette_data)
                        test_path = f'test/palette_test_offset_{offset:04X}.png'
                        img.save(test_path)
                        print(f"    Test image saved: {test_path}")
                except Exception as e:
                    print(f"    Test failed: {e}")

if __name__ == '__main__':
    analyze_header()

