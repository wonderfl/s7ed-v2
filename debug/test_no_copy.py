"""랜드마크 복사본 생성 여부 테스트"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from gui.face_edit.landmark_manager import LandmarkManager

# 테스트 데이터 생성
test_landmarks = [(100.0, 200.0), (150.0, 250.0), (200.0, 300.0)]

# LandmarkManager 생성
lm = LandmarkManager()

# 1. set_custom_landmarks 테스트
print("=== 1. set_custom_landmarks 테스트 ===")
lm.set_custom_landmarks(test_landmarks, reason="test")
result = lm.get_custom_landmarks()
print(f"원본 리스트 id: {id(test_landmarks)}")
print(f"저장된 리스트 id: {id(lm._custom_landmarks)}")
print(f"get_custom_landmarks() 반환 id: {id(result)}")
print(f"같은 객체인가? {test_landmarks is lm._custom_landmarks}")
print(f"같은 객체인가? {test_landmarks is result}")
print()

# 2. Property를 통한 접근 테스트
print("=== 2. Property 접근 테스트 ===")
class TestPanel:
    def __init__(self):
        self.landmark_manager = LandmarkManager()
        self.landmark_manager.set_custom_landmarks(test_landmarks, reason="test")
    
    @property
    def custom_landmarks(self):
        if hasattr(self, 'landmark_manager'):
            return self.landmark_manager._custom_landmarks
        return None
    
    @custom_landmarks.setter
    def custom_landmarks(self, value):
        if hasattr(self, 'landmark_manager'):
            if value is self.landmark_manager._custom_landmarks:
                return
            self.landmark_manager.set_custom_landmarks(value, reason="legacy_setter")

panel = TestPanel()
prop_result = panel.custom_landmarks
print(f"원본 리스트 id: {id(test_landmarks)}")
print(f"Property 반환 id: {id(prop_result)}")
print(f"같은 객체인가? {test_landmarks is prop_result}")
print()

# 3. 수정 테스트 (직접 참조인지 확인)
print("=== 3. 수정 테스트 ===")
original_id = id(panel.custom_landmarks)
panel.custom_landmarks[0] = (999.0, 999.0)
after_id = id(panel.custom_landmarks)
print(f"수정 전 id: {original_id}")
print(f"수정 후 id: {after_id}")
print(f"같은 객체인가? {original_id == after_id}")
print(f"수정된 값: {panel.custom_landmarks[0]}")
print(f"원본도 변경되었는가? {test_landmarks[0]}")
print()

# 4. getter 직접 참조 테스트 (copy 파라미터 제거됨)
print("=== 4. getter 직접 참조 테스트 ===")
direct_ref = lm.get_custom_landmarks()  # 항상 직접 참조 반환 (복사본 없음)
copy_ref = list(lm.get_custom_landmarks()) if lm.get_custom_landmarks() else None  # 필요시 수동으로 복사본 생성
print(f"직접 참조 id: {id(direct_ref)}")
print(f"복사본 id: {id(copy_ref)}")
print(f"직접 참조 == 저장된 객체? {direct_ref is lm._custom_landmarks}")
print(f"복사본 == 저장된 객체? {copy_ref is lm._custom_landmarks}")
print()

print("=== 테스트 완료 ===")
