"""
2단계 테스트: 랜드마크 직접 변형 기능 테스트
사용법: python test\test_stage2_landmark_warping.py "이미지경로"
"""
import os
import sys

# 프로젝트 루트 경로 추가
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from PIL import Image
import numpy as np
import utils.face_landmarks as face_landmarks
import utils.face_morphing as face_morphing


def test_morph_face_by_landmarks(image_path):
    """morph_face_by_polygons() 함수 테스트"""
    print("=" * 60)
    print("테스트 1: morph_face_by_polygons() 함수")
    print("=" * 60)
    
    if not os.path.exists(image_path):
        print(f"이미지 파일을 찾을 수 없습니다: {image_path}")
        return False
    
    if not face_landmarks.is_available():
        print("경고: MediaPipe가 설치되지 않았습니다.")
        return False
    
    try:
        # scipy 확인
        try:
            from scipy.spatial import Delaunay
            print("[OK] scipy 설치 확인")
        except ImportError:
            print("[FAIL] scipy가 설치되지 않았습니다. 'pip install scipy'를 실행하세요.")
            return False
        
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
        
        print(f"랜드마크 감지 성공! ({len(landmarks)}개 포인트)")
        
        # 원본 랜드마크 저장
        original_landmarks = list(landmarks)
        
        # 간단한 변형: 눈 영역의 랜드마크를 약간 확대
        # 왼쪽 눈 중심 찾기
        key_landmarks = face_landmarks.get_key_landmarks(landmarks)
        if key_landmarks is None:
            print("주요 랜드마크를 추출할 수 없습니다.")
            return False
        
        left_eye_center = key_landmarks['left_eye']
        right_eye_center = key_landmarks['right_eye']
        
        # 눈 영역의 랜드마크 인덱스 가져오기
        from utils.face_landmarks import LEFT_EYE_INDICES, RIGHT_EYE_INDICES
        
        # 변형된 랜드마크 생성 (눈 영역 확대)
        transformed_landmarks = list(landmarks)
        scale_factor = 1.2  # 20% 확대
        
        # 왼쪽 눈 영역 확대
        for idx in LEFT_EYE_INDICES:
            if idx < len(landmarks):
                x, y = landmarks[idx]
                # 왼쪽 눈 중심 기준으로 확대
                dx = x - left_eye_center[0]
                dy = y - left_eye_center[1]
                transformed_landmarks[idx] = (
                    left_eye_center[0] + dx * scale_factor,
                    left_eye_center[1] + dy * scale_factor
                )
        
        # 오른쪽 눈 영역 확대
        for idx in RIGHT_EYE_INDICES:
            if idx < len(landmarks):
                x, y = landmarks[idx]
                # 오른쪽 눈 중심 기준으로 확대
                dx = x - right_eye_center[0]
                dy = y - right_eye_center[1]
                transformed_landmarks[idx] = (
                    right_eye_center[0] + dx * scale_factor,
                    right_eye_center[1] + dy * scale_factor
                )
        
        print(f"랜드마크 변형 완료 (눈 영역 {scale_factor}배 확대)")
        
        # Delaunay Triangulation 기반 변형 적용
        print("Delaunay Triangulation 기반 변형 적용 중...")
        result = face_morphing.morph_face_by_polygons(
            img, original_landmarks, transformed_landmarks
        )
        
        # 결과 저장
        base_name = os.path.splitext(image_path)[0]
        ext = os.path.splitext(image_path)[1]
        output_path = f"{base_name}_stage2_landmark_warping{ext}"
        result.save(output_path)
        print(f"[OK] 결과 저장: {output_path}")
        
        return True
        
    except Exception as e:
        print(f"[FAIL] 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_move_points(image_path):
    """move_points() 함수 테스트"""
    print("\n" + "=" * 60)
    print("테스트 2: move_points() 함수")
    print("=" * 60)
    
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
        
        print(f"랜드마크 감지 성공! ({len(landmarks)}개 포인트)")
        
        # 주요 랜드마크 가져오기
        key_landmarks = face_landmarks.get_key_landmarks(landmarks)
        if key_landmarks is None:
            print("주요 랜드마크를 추출할 수 없습니다.")
            return False
        
        # 왼쪽 눈 중심 포인트를 약간 위로 이동
        # 왼쪽 눈 중심에 가장 가까운 포인트 찾기
        left_eye_center = key_landmarks['left_eye']
        from utils.face_landmarks import LEFT_EYE_INDICES
        min_dist = float('inf')
        closest_idx = -1
        for idx in LEFT_EYE_INDICES:
            if idx < len(landmarks):
                x, y = landmarks[idx]
                dist = ((x - left_eye_center[0])**2 + (y - left_eye_center[1])**2)**0.5
                if dist < min_dist:
                    min_dist = dist
                    closest_idx = idx
        
        if closest_idx < 0:
            print("왼쪽 눈 포인트를 찾을 수 없습니다.")
            return False
        
        print(f"이동할 포인트 인덱스: {closest_idx}")
        print(f"원본 위치: {landmarks[closest_idx]}")
        
        # 포인트를 위로 10픽셀 이동
        move_offset = (0, -10)
        point_indices = [closest_idx]
        offsets = [move_offset]
        
        print(f"이동 오프셋: {move_offset}")
        
        # 랜드마크 포인트 이동
        transformed_landmarks = face_morphing.move_points(
            landmarks, point_indices, offsets, influence_radius=30.0
        )
        
        print(f"변형된 위치: {transformed_landmarks[closest_idx]}")
        print(f"주변 포인트 영향 반경: 30픽셀")
        
        # 원본 랜드마크와 변형된 랜드마크로 변형 적용
        try:
            from scipy.spatial import Delaunay
            print("\nDelaunay Triangulation 기반 변형 적용 중...")
            result = face_morphing.morph_face_by_polygons(
                img, landmarks, transformed_landmarks
            )
            
            # 결과 저장
            base_name = os.path.splitext(image_path)[0]
            ext = os.path.splitext(image_path)[1]
            output_path = f"{base_name}_stage2_move_points{ext}"
            result.save(output_path)
            print(f"[OK] 결과 저장: {output_path}")
            
        except ImportError:
            print("[SKIP] scipy가 설치되지 않아 변형 적용을 건너뜁니다.")
        
        return True
        
    except Exception as e:
        print(f"[FAIL] 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_apply_all_adjustments_with_warping(image_path):
    """apply_all_adjustments()의 use_landmark_warping 옵션 테스트"""
    print("\n" + "=" * 60)
    print("테스트 3: apply_all_adjustments() use_landmark_warping 옵션")
    print("=" * 60)
    
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
        
        print("\n[참고] 현재 use_landmark_warping=True일 때는 기본 구조만 완성되어 있습니다.")
        print("      실제 랜드마크 변형 로직은 향후 구현 예정입니다.")
        print("      이 테스트는 옵션이 제대로 전달되는지 확인합니다.\n")
        
        # 기존 방식 (use_landmark_warping=False)
        print("1. 기존 방식으로 눈 크기 조정 (1.3배)...")
        result1 = face_morphing.apply_all_adjustments(
            img, eye_size=1.3, use_landmark_warping=False
        )
        base_name = os.path.splitext(image_path)[0]
        ext = os.path.splitext(image_path)[1]
        output1 = f"{base_name}_stage2_normal_mode{ext}"
        result1.save(output1)
        print(f"   저장: {output1}")
        
        # 랜드마크 변형 방식 (use_landmark_warping=True)
        print("2. 랜드마크 변형 방식 (use_landmark_warping=True)...")
        result2 = face_morphing.apply_all_adjustments(
            img, eye_size=1.3, use_landmark_warping=True
        )
        output2 = f"{base_name}_stage2_warping_mode{ext}"
        result2.save(output2)
        print(f"   저장: {output2}")
        print("   [참고] 현재는 기본 구조만 완성되어 기존 방식으로 처리됩니다.")
        
        print("\n[OK] 옵션 전달 테스트 완료")
        return True
        
    except Exception as e:
        print(f"[FAIL] 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """메인 테스트 함수"""
    if len(sys.argv) < 2:
        print("사용법: python test\\test_stage2_landmark_warping.py \"이미지경로\"")
        print("예시: python test\\test_stage2_landmark_warping.py \"test\\test_image.png\"")
        sys.exit(1)
    
    image_path = sys.argv[1]
    
    print("=" * 60)
    print("2단계: 랜드마크 직접 변형 기능 테스트")
    print("=" * 60)
    print()
    
    results = []
    
    # 테스트 1: morph_face_by_polygons()
    results.append(("morph_face_by_polygons", test_morph_face_by_landmarks(image_path)))
    
    # 테스트 2: move_points()
    results.append(("move_points", test_move_points(image_path)))
    
    # 테스트 3: apply_all_adjustments() 옵션
    results.append(("apply_all_adjustments 옵션", test_apply_all_adjustments_with_warping(image_path)))
    
    # 결과 요약
    print("\n" + "=" * 60)
    print("테스트 결과 요약")
    print("=" * 60)
    for test_name, result in results:
        status = "[OK]" if result else "[FAIL]"
        print(f"{status} {test_name}")
    
    all_passed = all(result for _, result in results)
    if all_passed:
        print("\n모든 테스트를 통과했습니다!")
    else:
        print("\n일부 테스트가 실패했습니다. 위의 오류 메시지를 확인하세요.")


if __name__ == "__main__":
    main()
