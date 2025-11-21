"""기존 PNG 파일에서 팔레트 추출"""
from PIL import Image
import pickle

def extract_palette():
    """기존 PNG 파일에서 팔레트 추출"""
    # 기존 PNG 파일 열기
    img = Image.open('gui/png/face000.png')
    
    print(f"Image mode: {img.mode}")
    print(f"Has palette: {img.palette is not None}")
    
    if img.palette:
        print(f"Palette mode: {img.palette.mode}")
        palette_data = img.palette.palette
        print(f"Palette size: {len(palette_data)} bytes")
        print(f"Palette colors: {len(palette_data) // 3}")
        
        # 팔레트 저장
        with open('test/face_palette.pkl', 'wb') as f:
            pickle.dump(palette_data, f)
        print("Palette saved to test/face_palette.pkl")
        
        # 팔레트 색상 일부 출력
        print("\nFirst 10 colors:")
        for i in range(min(10, len(palette_data) // 3)):
            r = palette_data[i*3]
            g = palette_data[i*3+1]
            b = palette_data[i*3+2]
            print(f"  Color {i}: RGB({r}, {g}, {b})")
    else:
        print("No palette found!")

if __name__ == '__main__':
    extract_palette()

