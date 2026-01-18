"""LandmarkManager 테스트"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from gui.face_edit.landmark_manager import LandmarkManager

def test_landmark_manager():
    """LandmarkManager 기본 기능 테스트"""
    lm = LandmarkManager()
    
    # 얼굴 랜드마크 설정 (468개)
    face_landmarks = [(float(i), float(i+1)) for i in range(468)]
    lm.set_original_face_landmarks(face_landmarks)
    assert len(lm.get_original_face_landmarks()) == 468, "Face landmarks 468"
    print("[OK] Face landmarks set: 468")
    
    # 눈동자 랜드마크 설정 (10개)
    iris_landmarks = [(float(i), float(i+1)) for i in range(10)]
    lm.set_original_iris_landmarks(iris_landmarks)
    assert len(lm.get_original_iris_landmarks()) == 10, "Iris landmarks 10"
    print("[OK] Iris landmarks set: 10")
    
    # 전체 랜드마크 가져오기 (478개)
    full = lm.get_original_landmarks_full()
    assert full is not None, "Full landmarks return"
    print(f"[OK] Full landmarks returned: {len(full)}")
    
    # 중앙 포인트 설정 (2개)
    centers = [(100.0, 200.0), (300.0, 400.0)]
    lm.set_custom_iris_centers(centers)
    assert lm.get_custom_iris_centers() == centers, "Iris centers set"
    print("[OK] Iris centers set: 2")
    
    # Tesselation용 랜드마크 가져오기 (470개)
    original_for_tess, transformed_for_tess = lm.get_landmarks_for_tesselation()
    assert original_for_tess is not None, "Tesselation original return"
    assert len(original_for_tess) == 470, f"Tesselation original 470 (actual: {len(original_for_tess)})"
    print(f"[OK] Tesselation landmarks returned: {len(original_for_tess)}")
    
    # 하위 호환성 테스트: set_original_landmarks (478개)
    full_landmarks = [(float(i), float(i+1)) for i in range(478)]
    lm2 = LandmarkManager()
    lm2.set_original_landmarks(full_landmarks)
    assert lm2.has_original_face_landmarks(), "Backward compatibility: auto split"
    print("[OK] Backward compatibility test: 478 auto split")
    
    print("\nAll tests passed!")

if __name__ == "__main__":
    test_landmark_manager()
