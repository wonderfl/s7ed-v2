"""
1단계 개선 작업 테스트: 랜드마크 기반 얼굴 변형 기능 개선
"""
import os
import sys

# 프로젝트 루트 경로 추가
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from PIL import Image
import utils.face_landmarks as face_landmarks
import utils.face_morphing as face_morphing


def test_new_functions():
    """새로 추가된 함수들이 제대로 정의되어 있는지 테스트"""
    print("=" * 50)
    print("테스트 1: 새로 추가된 함수 확인")
    print("=" * 50)
    
    # 함수 존재 확인
    functions_to_check = [
        '_sigmoid_blend_mask',
        '_create_blend_mask',
        '_get_mouth_region',
        '_get_nose_region'
    ]
    
    all_exist = True
    for func_name in functions_to_check:
        if hasattr(face_morphing, func_name):
            print(f"[OK] {func_name} 함수 존재")
        else:
            print(f"[FAIL] {func_name} 함수 없음")
            all_exist = False
    
    return all_exist


def test_improved_eye_region():
    """개선된 _get_eye_region 함수 테스트"""
    print("\n" + "=" * 50)
    print("테스트 2: 개선된 눈 영역 계산 함수")
    print("=" * 50)
    
    if not face_landmarks.is_available():
        print("경고: MediaPipe가 설치되지 않았습니다. 테스트를 건너뜁니다.")
        return False
    
    test_image_path = input("테스트할 이미지 경로를 입력하세요 (Enter로 건너뛰기): ").strip()
    if not test_image_path or not os.path.exists(test_image_path):
        print("이미지 경로가 제공되지 않았거나 파일이 없습니다. 테스트를 건너뜁니다.")
        return False
    
    try:
        img = Image.open(test_image_path)
        if img.mode != 'RGB':
            img = img.convert('RGB')
        
        print(f"이미지 로드: {test_image_path}")
        
        # 랜드마크 감지
        landmarks, detected = face_landmarks.detect_face_landmarks(img)
        if not detected:
            print("랜드마크를 감지할 수 없습니다.")
            return False
        
        key_landmarks = face_landmarks.get_key_landmarks(landmarks)
        if key_landmarks is None:
            print("주요 랜드마크를 추출할 수 없습니다.")
            return False
        
        # 눈 영역 계산 테스트
        img_width, img_height = img.size
        eye_region, eye_center = face_morphing._get_eye_region(
            key_landmarks, img_width, img_height, 'left', landmarks
        )
        x1, y1, x2, y2 = eye_region
        print(f"왼쪽 눈 영역: ({x1}, {y1}) ~ ({x2}, {y2})")
        print(f"왼쪽 눈 중심: {eye_center}")
        
        eye_region, eye_center = face_morphing._get_eye_region(
            key_landmarks, img_width, img_height, 'right', landmarks
        )
        x1, y1, x2, y2 = eye_region
        print(f"오른쪽 눈 영역: ({x1}, {y1}) ~ ({x2}, {y2})")
        print(f"오른쪽 눈 중심: {eye_center}")
        
        return True
        
    except Exception as e:
        print(f"테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_improved_mouth_region():
    """새로 추가된 _get_mouth_region 함수 테스트"""
    print("\n" + "=" * 50)
    print("테스트 3: 입 영역 계산 함수")
    print("=" * 50)
    
    if not face_landmarks.is_available():
        print("경고: MediaPipe가 설치되지 않았습니다. 테스트를 건너뜁니다.")
        return False
    
    test_image_path = input("테스트할 이미지 경로를 입력하세요 (Enter로 건너뛰기): ").strip()
    if not test_image_path or not os.path.exists(test_image_path):
        print("이미지 경로가 제공되지 않았거나 파일이 없습니다. 테스트를 건너뜁니다.")
        return False
    
    try:
        img = Image.open(test_image_path)
        if img.mode != 'RGB':
            img = img.convert('RGB')
        
        print(f"이미지 로드: {test_image_path}")
        
        # 랜드마크 감지
        landmarks, detected = face_landmarks.detect_face_landmarks(img)
        if not detected:
            print("랜드마크를 감지할 수 없습니다.")
            return False
        
        key_landmarks = face_landmarks.get_key_landmarks(landmarks)
        if key_landmarks is None:
            print("주요 랜드마크를 추출할 수 없습니다.")
            return False
        
        # 입 영역 계산 테스트
        img_width, img_height = img.size
        mouth_region, mouth_center = face_morphing._get_mouth_region(
            key_landmarks, img_width, img_height, landmarks
        )
        x1, y1, x2, y2 = mouth_region
        print(f"입 영역: ({x1}, {y1}) ~ ({x2}, {y2})")
        print(f"입 중심: {mouth_center}")
        
        return True
        
    except Exception as e:
        print(f"테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_improved_nose_region():
    """새로 추가된 _get_nose_region 함수 테스트"""
    print("\n" + "=" * 50)
    print("테스트 4: 코 영역 계산 함수")
    print("=" * 50)
    
    if not face_landmarks.is_available():
        print("경고: MediaPipe가 설치되지 않았습니다. 테스트를 건너뜁니다.")
        return False
    
    test_image_path = input("테스트할 이미지 경로를 입력하세요 (Enter로 건너뛰기): ").strip()
    if not test_image_path or not os.path.exists(test_image_path):
        print("이미지 경로가 제공되지 않았거나 파일이 없습니다. 테스트를 건너뜁니다.")
        return False
    
    try:
        img = Image.open(test_image_path)
        if img.mode != 'RGB':
            img = img.convert('RGB')
        
        print(f"이미지 로드: {test_image_path}")
        
        # 랜드마크 감지
        landmarks, detected = face_landmarks.detect_face_landmarks(img)
        if not detected:
            print("랜드마크를 감지할 수 없습니다.")
            return False
        
        key_landmarks = face_landmarks.get_key_landmarks(landmarks)
        if key_landmarks is None:
            print("주요 랜드마크를 추출할 수 없습니다.")
            return False
        
        # 코 영역 계산 테스트
        img_width, img_height = img.size
        nose_region, nose_center = face_morphing._get_nose_region(
            key_landmarks, img_width, img_height, landmarks
        )
        x1, y1, x2, y2 = nose_region
        print(f"코 영역: ({x1}, {y1}) ~ ({x2}, {y2})")
        print(f"코 중심: {nose_center}")
        
        return True
        
    except Exception as e:
        print(f"테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_improved_blending():
    """개선된 블렌딩 함수 테스트"""
    print("\n" + "=" * 50)
    print("테스트 5: 개선된 블렌딩 함수")
    print("=" * 50)
    
    if not face_landmarks.is_available():
        print("경고: MediaPipe가 설치되지 않았습니다. 테스트를 건너뜁니다.")
        return False
    
    test_image_path = input("테스트할 이미지 경로를 입력하세요 (Enter로 건너뛰기): ").strip()
    if not test_image_path or not os.path.exists(test_image_path):
        print("이미지 경로가 제공되지 않았거나 파일이 없습니다. 테스트를 건너뜁니다.")
        return False
    
    try:
        img = Image.open(test_image_path)
        if img.mode != 'RGB':
            img = img.convert('RGB')
        
        print(f"이미지 로드: {test_image_path}")
        
        # 개선된 블렌딩이 적용된 얼굴 편집 테스트
        print("\n1. 눈 크기 조정 (1.3배, 개선된 블렌딩 적용)...")
        eye_result = face_morphing.adjust_eye_size(img, eye_size_ratio=1.3)
        eye_output = test_image_path.replace('.', '_improved_eye_1.3.')
        eye_result.save(eye_output)
        print(f"   저장: {eye_output}")
        
        print("2. 코 크기 조정 (0.9배, 개선된 블렌딩 적용)...")
        nose_result = face_morphing.adjust_nose_size(img, nose_size_ratio=0.9)
        nose_output = test_image_path.replace('.', '_improved_nose_0.9.')
        nose_result.save(nose_output)
        print(f"   저장: {nose_output}")
        
        print("3. 입 크기 조정 (1.2배, 개선된 블렌딩 적용)...")
        mouth_result = face_morphing.adjust_mouth_size(img, mouth_size_ratio=1.2, mouth_width_ratio=1.2)
        mouth_output = test_image_path.replace('.', '_improved_mouth_1.2.')
        mouth_result.save(mouth_output)
        print(f"   저장: {mouth_output}")
        
        print("\n개선된 블렌딩이 적용된 결과를 확인하세요.")
        print("기존 결과와 비교하여 블렌딩이 더 부드러운지 확인하세요.")
        
        return True
        
    except Exception as e:
        print(f"테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """메인 테스트 함수"""
    print("1단계 개선 작업 테스트: 랜드마크 기반 얼굴 변형 기능 개선")
    print("=" * 50)
    
    results = []
    
    # 테스트 실행
    results.append(("새 함수 확인", test_new_functions()))
    results.append(("개선된 눈 영역 계산", test_improved_eye_region()))
    results.append(("입 영역 계산", test_improved_mouth_region()))
    results.append(("코 영역 계산", test_improved_nose_region()))
    results.append(("개선된 블렌딩", test_improved_blending()))
    
    # 결과 요약
    print("\n" + "=" * 50)
    print("테스트 결과 요약")
    print("=" * 50)
    for name, result in results:
        status = "통과" if result else "실패/건너뜀"
        print(f"{name}: {status}")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    print(f"\n통과: {passed}/{total}")


if __name__ == "__main__":
    main()
