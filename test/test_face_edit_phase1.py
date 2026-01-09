"""
Phase 1 얼굴 편집 기능 테스트
"""
import os
import sys

# 프로젝트 루트 경로 추가
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from PIL import Image
import utils.face_landmarks as face_landmarks
import utils.face_morphing as face_morphing


def test_landmark_detection():
    """얼굴 랜드마크 감지 테스트"""
    print("=" * 50)
    print("테스트 1: 얼굴 랜드마크 감지")
    print("=" * 50)
    
    if not face_landmarks.is_available():
        print("경고: MediaPipe가 설치되지 않았습니다.")
        print("테스트를 실행하려면 'pip install mediapipe'를 실행하세요.")
        return False
    
    # 테스트 이미지 경로 (사용자가 제공해야 함)
    test_image_path = input("테스트할 이미지 경로를 입력하세요 (Enter로 건너뛰기): ").strip()
    if not test_image_path or not os.path.exists(test_image_path):
        print("이미지 경로가 제공되지 않았거나 파일이 없습니다. 테스트를 건너뜁니다.")
        return False
    
    try:
        img = Image.open(test_image_path)
        if img.mode != 'RGB':
            img = img.convert('RGB')
        
        print(f"이미지 로드: {test_image_path}")
        print(f"이미지 크기: {img.size}")
        
        # 랜드마크 감지
        landmarks, detected = face_landmarks.detect_face_landmarks(img)
        
        if detected:
            print(f"얼굴 감지 성공! 랜드마크 포인트 수: {len(landmarks)}")
            
            # 주요 랜드마크 추출
            key_landmarks = face_landmarks.get_key_landmarks(landmarks)
            if key_landmarks:
                print("주요 랜드마크:")
                print(f"  - 왼쪽 눈: {key_landmarks['left_eye']}")
                print(f"  - 오른쪽 눈: {key_landmarks['right_eye']}")
                print(f"  - 코: {key_landmarks['nose']}")
                print(f"  - 입: {key_landmarks['mouth']}")
                print(f"  - 얼굴 중심: {key_landmarks['face_center']}")
                return True
            else:
                print("경고: 주요 랜드마크를 추출할 수 없습니다.")
                return False
        else:
            print("얼굴을 감지하지 못했습니다.")
            return False
            
    except Exception as e:
        print(f"에러: {e}")
        return False


def test_face_alignment():
    """얼굴 정렬 테스트"""
    print("\n" + "=" * 50)
    print("테스트 2: 얼굴 정렬")
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
        
        # 얼굴 정렬
        aligned_img, angle = face_landmarks.align_face(img)
        
        print(f"정렬 완료! 회전 각도: {angle:.2f}도")
        
        # 결과 저장
        output_path = test_image_path.replace('.', '_aligned.')
        aligned_img.save(output_path)
        print(f"정렬된 이미지 저장: {output_path}")
        
        return True
        
    except Exception as e:
        print(f"에러: {e}")
        return False


def test_face_morphing():
    """얼굴 특징 보정 테스트"""
    print("\n" + "=" * 50)
    print("테스트 3: 얼굴 특징 보정")
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
        
        # 각 특징 보정 테스트
        print("\n1. 눈 크기 조정 (1.5배)...")
        eye_result = face_morphing.adjust_eye_size(img, eye_size_ratio=1.5)
        eye_output = test_image_path.replace('.', '_eye_1.5.')
        eye_result.save(eye_output)
        print(f"   저장: {eye_output}")
        
        print("2. 코 크기 조정 (0.8배)...")
        nose_result = face_morphing.adjust_nose_size(img, nose_size_ratio=0.8)
        nose_output = test_image_path.replace('.', '_nose_0.8.')
        nose_result.save(nose_output)
        print(f"   저장: {nose_output}")
        
        print("3. 턱선 조정 (+30)...")
        jaw_result = face_morphing.adjust_jaw(img, jaw_adjustment=30.0)
        jaw_output = test_image_path.replace('.', '_jaw_+30.')
        jaw_result.save(jaw_output)
        print(f"   저장: {jaw_output}")
        
        print("4. 얼굴 크기 조정 (너비 1.2배, 높이 1.1배)...")
        face_result = face_morphing.adjust_face_size(img, width_ratio=1.2, height_ratio=1.1)
        face_output = test_image_path.replace('.', '_face_1.2x1.1.')
        face_result.save(face_output)
        print(f"   저장: {face_output}")
        
        print("5. 모든 조정 한 번에 적용...")
        all_result = face_morphing.apply_all_adjustments(
            img,
            eye_size=1.2,
            nose_size=0.9,
            jaw_adjustment=20.0,
            face_width=1.1,
            face_height=1.05
        )
        all_output = test_image_path.replace('.', '_all_adjusted.')
        all_result.save(all_output)
        print(f"   저장: {all_output}")
        
        print("\n모든 특징 보정 테스트 완료!")
        return True
        
    except Exception as e:
        print(f"에러: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """메인 테스트 함수"""
    print("Phase 1 얼굴 편집 기능 테스트")
    print("=" * 50)
    
    results = []
    
    # 테스트 실행
    results.append(("랜드마크 감지", test_landmark_detection()))
    results.append(("얼굴 정렬", test_face_alignment()))
    results.append(("얼굴 특징 보정", test_face_morphing()))
    
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
