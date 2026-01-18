"""
LandmarkManager 테스트 스크립트
랜드마크 상태 관리가 제대로 작동하는지 확인
"""
import sys
import os

# 프로젝트 루트를 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from gui.face_edit.landmark_manager import LandmarkManager


def test_landmark_manager():
    """LandmarkManager 기본 기능 테스트"""
    print("=" * 60)
    print("LandmarkManager 테스트 시작")
    print("=" * 60)
    
    # 1. 인스턴스 생성
    print("\n[1] LandmarkManager 인스턴스 생성")
    manager = LandmarkManager()
    print("[OK] 인스턴스 생성 완료")
    
    # 2. original_landmarks 설정
    print("\n[2] original_landmarks 설정")
    test_landmarks = [(i * 10, i * 10) for i in range(478)]
    manager.set_original_landmarks(test_landmarks)
    original = manager.get_original_landmarks()
    assert original is not None, "original_landmarks가 None입니다"
    assert len(original) == 478, f"original_landmarks 길이가 잘못됨: {len(original)}"
    print(f"[OK] original_landmarks 설정 완료: {len(original)}개")
    
    # 3. face_landmarks 설정
    print("\n[3] face_landmarks 설정")
    face_landmarks = [(i * 10 + 1, i * 10 + 1) for i in range(478)]
    manager.set_face_landmarks(face_landmarks)
    face = manager.get_face_landmarks()
    assert face is not None, "face_landmarks가 None입니다"
    assert len(face) == 478, f"face_landmarks 길이가 잘못됨: {len(face)}"
    print(f"[OK] face_landmarks 설정 완료: {len(face)}개")
    
    # 4. custom_landmarks 설정
    print("\n[4] custom_landmarks 설정")
    custom_landmarks = [(i * 10 + 2, i * 10 + 2) for i in range(472)]  # 중앙 포인트 추가로 472개
    manager.set_custom_landmarks(custom_landmarks, reason="test")
    custom = manager.get_custom_landmarks()
    assert custom is not None, "custom_landmarks가 None입니다"
    assert len(custom) == 472, f"custom_landmarks 길이가 잘못됨: {len(custom)}"
    print(f"[OK] custom_landmarks 설정 완료: {len(custom)}개")
    
    # 5. transformed_landmarks 설정
    print("\n[5] transformed_landmarks 설정")
    transformed_landmarks = [(i * 10 + 3, i * 10 + 3) for i in range(478)]
    manager.set_transformed_landmarks(transformed_landmarks)
    transformed = manager.get_transformed_landmarks()
    assert transformed is not None, "transformed_landmarks가 None입니다"
    assert len(transformed) == 478, f"transformed_landmarks 길이가 잘못됨: {len(transformed)}"
    print(f"[OK] transformed_landmarks 설정 완료: {len(transformed)}개")
    
    # 6. 중앙 포인트 좌표 설정
    print("\n[6] 중앙 포인트 좌표 설정")
    left_center = (100.0, 200.0)
    right_center = (300.0, 200.0)
    manager.set_iris_center_coords(left_center, right_center)
    left = manager.get_left_iris_center_coord()
    right = manager.get_right_iris_center_coord()
    assert left == left_center, f"왼쪽 중앙 포인트가 잘못됨: {left}"
    assert right == right_center, f"오른쪽 중앙 포인트가 잘못됨: {right}"
    print(f"[OK] 중앙 포인트 좌표 설정 완료: 왼쪽={left}, 오른쪽={right}")
    
    # 7. 상태 확인 메서드
    print("\n[7] 상태 확인 메서드 테스트")
    assert manager.has_original_landmarks() == True, "has_original_landmarks가 False를 반환"
    assert manager.get_face_landmarks() is not None, "face_landmarks가 None입니다"
    assert manager.has_custom_landmarks() == True, "has_custom_landmarks가 False를 반환"
    assert manager.get_transformed_landmarks() is not None, "transformed_landmarks가 None입니다"
    print("[OK] 모든 상태 확인 메서드 정상 작동")
    
    # 8. reset 테스트
    print("\n[8] reset 테스트")
    # 먼저 다시 데이터 설정
    manager.set_face_landmarks(face_landmarks)
    manager.set_custom_landmarks(custom_landmarks, reason="test_reset")
    manager.set_transformed_landmarks(transformed_landmarks)
    manager.set_iris_center_coords(left_center, right_center)
    
    manager.reset(keep_original=True)
    assert manager.has_original_landmarks() == True, "reset 후 original_landmarks가 없어짐"
    assert manager.get_face_landmarks() is None, f"reset 후 face_landmarks가 남아있음: {manager.get_face_landmarks() is not None}"
    # reset(keep_original=True)는 custom_landmarks를 original_landmarks로 복원함
    custom_after = manager.get_custom_landmarks()
    assert custom_after is not None, "reset 후 custom_landmarks가 None입니다 (original로 복원되어야 함)"
    assert len(custom_after) == len(original), f"reset 후 custom_landmarks 길이가 잘못됨: {len(custom_after)} != {len(original)}"
    assert manager.get_transformed_landmarks() is None, "reset 후 transformed_landmarks가 남아있음"
    assert manager.get_left_iris_center_coord() is None, "reset 후 왼쪽 중앙 포인트가 남아있음"
    assert manager.get_right_iris_center_coord() is None, "reset 후 오른쪽 중앙 포인트가 남아있음"
    print("[OK] reset 정상 작동 (original_landmarks 유지, custom_landmarks는 original로 복원)")
    
    # 9. 완전 reset 테스트
    print("\n[9] 완전 reset 테스트")
    manager.reset(keep_original=False)
    assert manager.has_original_landmarks() == False, "완전 reset 후 original_landmarks가 남아있음"
    print("[OK] 완전 reset 정상 작동")
    
    # 10. 변경 이력 확인
    print("\n[10] 변경 이력 확인")
    history = manager.get_change_history()
    assert len(history) > 0, "변경 이력이 없음"
    print(f"[OK] 변경 이력 {len(history)}개 확인")
    for i, entry in enumerate(history[-3:], 1):  # 최근 3개만 출력
        # entry 구조 확인
        if isinstance(entry, dict):
            keys = list(entry.keys())
            print(f"  [{i}] {entry}")
        else:
            print(f"  [{i}] {entry}")
    
    print("\n" + "=" * 60)
    print("모든 테스트 통과!")
    print("=" * 60)
    return True


if __name__ == "__main__":
    try:
        test_landmark_manager()
        print("\n[SUCCESS] LandmarkManager 테스트 성공")
        sys.exit(0)
    except AssertionError as e:
        print(f"\n[FAIL] 테스트 실패: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] 예외 발생: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
