import struct
import os
from PIL import Image

def analyze_kaodata():
    filename = 'saves/Kaodata.s7'
    
    file_size = os.path.getsize(filename)
    print(f"File size: {file_size} bytes ({file_size/1024:.2f} KB)")
    
    with open(filename, 'rb') as f:
        # 헤더 읽기
        header = f.read(200)
        
        print("\n=== Header Analysis ===")
        print("First 20 integers (little endian):")
        for i in range(0, 80, 4):
            val = struct.unpack('<I', header[i:i+4])[0]
            print(f"  Offset {i:02X}: {val:8d} (0x{val:08X})")
        
        # 얼굴 이미지 크기: 96x120 = 11520 픽셀
        # 팔레트 모드면 1바이트/픽셀 = 11520 바이트
        # RGBA면 4바이트/픽셀 = 46080 바이트
        face_size_palette = 96 * 120  # 11520 bytes
        face_size_rgba = 96 * 120 * 4  # 46080 bytes
        
        print(f"\n=== Face Image Size ===")
        print(f"Palette mode (1 byte/pixel): {face_size_palette} bytes")
        print(f"RGBA mode (4 bytes/pixel): {face_size_rgba} bytes")
        
        # 파일 크기로 얼굴 개수 추정
        # 헤더 제외한 데이터 크기
        estimated_faces_palette = (file_size - 200) // face_size_palette
        estimated_faces_rgba = (file_size - 200) // face_size_rgba
        
        print(f"\n=== Estimated Face Count ===")
        print(f"Palette mode: ~{estimated_faces_palette} faces")
        print(f"RGBA mode: ~{estimated_faces_rgba} faces")
        
        # 첫 번째 얼굴 데이터 시도
        print(f"\n=== Testing Image Extraction ===")
        
        # 헤더 다음부터 읽기
        f.seek(200)
        
        # 팔레트 모드 시도
        try:
            face_data = f.read(face_size_palette)
            if len(face_data) == face_size_palette:
                # 팔레트 이미지 생성 시도
                img = Image.frombytes('P', (96, 120), face_data)
                print(f"Palette image created: {img.size}, mode: {img.mode}")
                # 팔레트가 없으면 기본 팔레트 사용
                img.save('test/face_test_palette.png')
                print("Saved: test/face_test_palette.png")
        except Exception as e:
            print(f"Palette mode failed: {e}")
        
        # RGBA 모드 시도
        f.seek(200)
        try:
            face_data = f.read(face_size_rgba)
            if len(face_data) == face_size_rgba:
                img = Image.frombytes('RGBA', (96, 120), face_data)
                print(f"RGBA image created: {img.size}, mode: {img.mode}")
                img.save('test/face_test_rgba.png')
                print("Saved: test/face_test_rgba.png")
        except Exception as e:
            print(f"RGBA mode failed: {e}")

if __name__ == '__main__':
    analyze_kaodata()

