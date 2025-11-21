"""팔레트를 바이트 배열로 추출"""
from PIL import Image
import os

def get_palette_bytes():
    """기존 PNG 파일에서 팔레트를 바이트 배열로 추출"""
    img = Image.open('gui/png/face000.png')
    
    if img.palette:
        palette_data = img.palette.palette
        print("Palette bytes (Python list format):")
        print("FACE_PALETTE = [")
        for i in range(0, len(palette_data), 16):
            chunk = palette_data[i:i+16]
            values = ', '.join(f'{b:3d}' for b in chunk)
            print(f"    {values},")
        print("]")
        
        # 파일로 저장
        with open('test/palette_bytes.txt', 'w') as f:
            f.write("FACE_PALETTE = [\n")
            for i in range(0, len(palette_data), 16):
                chunk = palette_data[i:i+16]
                values = ', '.join(f'{b:3d}' for b in chunk)
                f.write(f"    {values},\n")
            f.write("]\n")
        print("\nSaved to test/palette_bytes.txt")

if __name__ == '__main__':
    get_palette_bytes()

