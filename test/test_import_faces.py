"""PNG 파일들을 Kaodata.s7에 반영하는 테스트"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from utils import kaodata_image
from PIL import Image

def test_import_faces():
    """PNG 파일들 반영 테스트"""
    print("=== PNG 파일들을 Kaodata.s7에 반영 테스트 ===")
    
    try:
        # 1. 테스트용 PNG 파일들 생성
        print("\n1. 테스트용 PNG 파일 생성...")
        test_dir = 'test/test_faces'
        os.makedirs(test_dir, exist_ok=True)
        
        # 몇 개의 테스트 이미지 생성
        test_faces = [0, 1, 7]
        for faceno in test_faces:
            # 원본 이미지 읽기
            original = kaodata_image.get_face_image(faceno)
            # 테스트용으로 약간 수정 (예: 밝기 조정)
            test_img = original.copy()
            # PNG로 저장
            test_path = os.path.join(test_dir, f'face{faceno:03d}.png')
            test_img.save(test_path)
            print(f"   생성: {test_path}")
        
        # 2. 백업: 원본 이미지들 백업
        print("\n2. 원본 이미지 백업...")
        backup_dir = 'test/backup_faces'
        os.makedirs(backup_dir, exist_ok=True)
        for faceno in test_faces:
            original = kaodata_image.get_face_image(faceno)
            backup_path = os.path.join(backup_dir, f'face{faceno:03d}_backup.png')
            original.save(backup_path)
        print(f"   백업 완료: {backup_dir}")
        
        # 3. PNG 파일들을 Kaodata.s7에 반영
        print("\n3. PNG 파일들을 Kaodata.s7에 반영...")
        results = kaodata_image.import_faces_from_png(
            png_dir=test_dir,
            pattern='face*.png',
            verbose=True
        )
        
        # 4. 반영된 이미지 확인
        print("\n4. 반영된 이미지 확인...")
        for faceno in test_faces:
            saved_img = kaodata_image.get_face_image(faceno)
            verify_path = os.path.join('test', f'face{faceno:03d}_imported.png')
            saved_img.save(verify_path)
            print(f"   확인: {verify_path}")
        
        # 5. 원본 복구
        print("\n5. 원본 이미지 복구...")
        for faceno in test_faces:
            backup_img = Image.open(os.path.join(backup_dir, f'face{faceno:03d}_backup.png'))
            kaodata_image.save_face_image(faceno, backup_img)
        print("   복구 완료")
        
        print("\n=== 테스트 완료 ===")
        print(f"결과: 성공 {results['success']}개, 실패 {results['failed']}개")
        
    except Exception as e:
        print(f"\n[에러] 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
    finally:
        kaodata_image.close_kaodata_file()

if __name__ == '__main__':
    test_import_faces()


