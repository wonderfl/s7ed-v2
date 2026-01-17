"""
빠른 테스트: 이미지 경로를 인자로 받아서 테스트
사용법: python test\test_quick.py "이미지경로"
"""
import os
import sys

# 프로젝트 루트 경로 추가
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from PIL import Image
import utils.face_landmarks as face_landmarks
import utils.face_morphing as face_morphing


def quick_test(image_path):
    """빠른 테스트 실행"""
    if not os.path.exists(image_path):
        print(f"이미지 파일을 찾을 수 없습니다: {image_path}")
        return False
    
    if not face_landmarks.is_available():
        print("경고: MediaPipe가 설치되지 않았습니다.")
        return False
    
    try:
        print(f"이미지 로드: {image_path}")
        img = Image.open(image_path)
        if img.mode != 'RGB':
            img = img.convert('RGB')
        
        # 랜드마크 감지
        print("랜드마크 감지 중...")
        landmarks, detected = face_landmarks.detect_face_landmarks(img)
        if not detected:
            print("랜드마크를 감지할 수 없습니다.")
            return False
        
        print("랜드마크 감지 성공!")
        
        # 각 편집 기능 테스트
        base_name = os.path.splitext(image_path)[0]
        ext = os.path.splitext(image_path)[1]
        
        print("\n1. 눈 크기 조정 (1.3배)...")
        eye_result = face_morphing.adjust_eye_size(img, eye_size_ratio=1.3, landmarks=landmarks)
        eye_output = f"{base_name}_test_eye_1.3{ext}"
        eye_result.save(eye_output)
        print(f"   저장: {eye_output}")
        
        print("2. 코 크기 조정 (0.9배)...")
        nose_result = face_morphing.adjust_nose_size(img, nose_size_ratio=0.9, landmarks=landmarks)
        nose_output = f"{base_name}_test_nose_0.9{ext}"
        nose_result.save(nose_output)
        print(f"   저장: {nose_output}")
        
        print("3. 입 크기 조정 (1.2배)...")
        mouth_result = face_morphing.adjust_mouth_size(img, mouth_size_ratio=1.2, mouth_width_ratio=1.2, landmarks=landmarks)
        mouth_output = f"{base_name}_test_mouth_1.2{ext}"
        mouth_result.save(mouth_output)
        print(f"   저장: {mouth_output}")
        
        print("\n테스트 완료! 결과 이미지를 확인하세요.")
        print("개선된 블렌딩이 적용되었는지 확인하세요.")
        
        return True
        
    except Exception as e:
        print(f"테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("사용법: python test\\test_quick.py \"이미지경로\"")
        print("예시: python test\\test_quick.py \"test\\test_image.png\"")
        sys.exit(1)
    
    image_path = sys.argv[1]
    quick_test(image_path)
