"""Kaodata.s7 이미지 읽기 테스트"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from utils import kaodata_image
from PIL import Image

def test_get_face_image():
    """얼굴 이미지 읽기 테스트"""
    print("=== Kaodata.s7 이미지 읽기 테스트 ===")
    
    # 테스트할 얼굴 번호들
    test_faces = [0, 1, 7, 100, 647]
    
    for faceno in test_faces:
        try:
            print(f"\n얼굴 번호 {faceno} 읽기 시도...")
            img = kaodata_image.get_face_image(faceno)
            print(f"  성공: {img.size}, 모드: {img.mode}")
            
            # 테스트 이미지 저장
            output_path = f'test/face_{faceno:03d}_from_kaodata.png'
            img.save(output_path)
            print(f"  저장: {output_path}")
            
        except Exception as e:
            print(f"  실패: {e}")
    
    # 파일 닫기
    kaodata_image.close_kaodata_file()
    print("\n=== 테스트 완료 ===")

if __name__ == '__main__':
    test_get_face_image()

