"""Kaodata.s7 이미지 저장 테스트"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from utils import kaodata_image
from PIL import Image

def test_save_face_image():
    """얼굴 이미지 저장 테스트"""
    print("=== Kaodata.s7 이미지 저장 테스트 ===")
    
    try:
        # 1. 기존 이미지 읽기
        print("\n1. 기존 이미지 읽기...")
        original_img = kaodata_image.get_face_image(0)
        print(f"   읽기 성공: {original_img.size}, 모드: {original_img.mode}")
        
        # 2. 테스트용 이미지 생성 (빨간색 사각형)
        print("\n2. 테스트 이미지 생성...")
        test_img = Image.new('RGB', (96, 120), color='red')
        # 팔레트 모드로 변환
        test_img_p = test_img.quantize()
        test_img_p.putpalette(kaodata_image.FACE_PALETTE)
        print(f"   생성 완료: {test_img_p.size}, 모드: {test_img_p.mode}")
        
        # 3. 백업: 원본 이미지를 PNG로 저장
        backup_path = 'test/face_000_backup.png'
        original_img.save(backup_path)
        print(f"\n3. 백업 저장: {backup_path}")
        
        # 4. 테스트 이미지 저장 (faceno 0에 저장)
        print("\n4. Kaodata.s7에 테스트 이미지 저장...")
        kaodata_image.save_face_image(0, test_img_p)
        print("   저장 완료!")
        
        # 5. 저장된 이미지 읽어서 확인
        print("\n5. 저장된 이미지 읽기 확인...")
        saved_img = kaodata_image.get_face_image(0)
        saved_path = 'test/face_000_saved.png'
        saved_img.save(saved_path)
        print(f"   확인 이미지 저장: {saved_path}")
        
        # 6. 원본 복구
        print("\n6. 원본 이미지 복구...")
        kaodata_image.save_face_image(0, original_img)
        restored_img = kaodata_image.get_face_image(0)
        restored_path = 'test/face_000_restored.png'
        restored_img.save(restored_path)
        print(f"   복구 완료: {restored_path}")
        
        print("\n=== 테스트 완료 ===")
        
    except Exception as e:
        print(f"\n[에러] 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
    finally:
        kaodata_image.close_kaodata_file()

if __name__ == '__main__':
    test_save_face_image()


