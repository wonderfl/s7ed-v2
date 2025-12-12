"""PNG 파일 하나를 원하는 위치에 저장하는 테스트"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from utils import kaodata_image
from PIL import Image

def test_save_face_from_png():
    """PNG 파일을 원하는 위치에 저장하는 테스트"""
    print("=== PNG 파일을 원하는 위치에 저장 테스트 ===")
    
    try:
        # 1. 테스트용 PNG 파일 생성
        print("\n1. 테스트용 PNG 파일 생성...")
        test_png = 'test/test_face.png'
        
        # 얼굴 번호 0의 이미지를 읽어서 테스트 파일로 저장
        original_img = kaodata_image.get_face_image(0)
        original_img.save(test_png)
        print(f"   생성: {test_png}")
        
        # 2. 백업: 저장할 위치의 원본 이미지 백업
        print("\n2. 원본 이미지 백업...")
        target_faceno = 10  # 테스트할 얼굴 번호
        backup_img = kaodata_image.get_face_image(target_faceno)
        backup_path = f'test/face_{target_faceno:03d}_backup.png'
        backup_img.save(backup_path)
        print(f"   백업: {backup_path}")
        
        # 3. PNG 파일을 원하는 위치에 저장
        print(f"\n3. {test_png} 파일을 얼굴 번호 {target_faceno}에 저장...")
        kaodata_image.save_face_from_png(test_png, target_faceno)
        print("   저장 완료!")
        
        # 4. 저장된 이미지 확인
        print(f"\n4. 저장된 이미지 확인 (얼굴 번호 {target_faceno})...")
        saved_img = kaodata_image.get_face_image(target_faceno)
        verify_path = f'test/face_{target_faceno:03d}_saved.png'
        saved_img.save(verify_path)
        print(f"   확인: {verify_path}")
        
        # 5. 원본 복구
        print(f"\n5. 원본 이미지 복구 (얼굴 번호 {target_faceno})...")
        kaodata_image.save_face_image(target_faceno, backup_img)
        restored_img = kaodata_image.get_face_image(target_faceno)
        restored_path = f'test/face_{target_faceno:03d}_restored.png'
        restored_img.save(restored_path)
        print(f"   복구 완료: {restored_path}")
        
        # 6. 다른 예시: 얼굴 번호 0의 이미지를 얼굴 번호 20에 복사
        print(f"\n6. 추가 테스트: 얼굴 번호 0 -> 얼굴 번호 20 복사...")
        source_png = 'gui/png/face000.png'
        if os.path.exists(source_png):
            kaodata_image.save_face_from_png(source_png, 20)
            copied_img = kaodata_image.get_face_image(20)
            copied_path = 'test/face_020_copied.png'
            copied_img.save(copied_path)
            print(f"   복사 완료: {copied_path}")
        else:
            print(f"   건너뜀: {source_png} 파일이 없습니다.")
        
        print("\n=== 테스트 완료 ===")
        
    except Exception as e:
        print(f"\n[에러] 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
    finally:
        kaodata_image.close_kaodata_file()

if __name__ == '__main__':
    test_save_face_from_png()


