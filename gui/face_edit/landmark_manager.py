"""
랜드마크 상태 관리 클래스
모든 랜드마크 관련 상태를 중앙에서 관리
"""
from typing import List, Tuple, Optional, Dict, Any
import copy


class LandmarkManager:
    """랜드마크 상태를 중앙에서 관리하는 클래스"""
    
    def __init__(self):
        """랜드마크 관리자 초기화"""
        # 원본 랜드마크 (읽기 전용)
        self._original_landmarks: Optional[List[Tuple[float, float]]] = None
        
        # 현재 편집된 랜드마크 (표시용)
        self._face_landmarks: Optional[List[Tuple[float, float]]] = None
        
        # 변형된 랜드마크 (사이즈 변경 등)
        self._transformed_landmarks: Optional[List[Tuple[float, float]]] = None
        
        # 사용자 수정 랜드마크 (드래그, 슬라이더 등)
        self._custom_landmarks: Optional[List[Tuple[float, float]]] = None
        
        # 중앙 포인트 좌표
        self._left_iris_center_coord: Optional[Tuple[float, float]] = None
        self._right_iris_center_coord: Optional[Tuple[float, float]] = None
        
        # 변경 이력 (디버깅용, 선택사항)
        self._change_history: List[Dict[str, Any]] = []
    
    # ========== 원본 랜드마크 ==========
    
    def set_original_landmarks(self, landmarks: List[Tuple[float, float]]):
        """원본 랜드마크 설정 (읽기 전용)"""
        if landmarks is not None:
            self._original_landmarks = list(landmarks)
            self._log_change("set_original", len(landmarks))
        else:
            self._original_landmarks = None
    
    def get_original_landmarks(self) -> Optional[List[Tuple[float, float]]]:
        """원본 랜드마크 반환"""
        if self._original_landmarks is not None:
            return list(self._original_landmarks)  # 복사본 반환
        return None
    
    def has_original_landmarks(self) -> bool:
        """원본 랜드마크 존재 여부"""
        return self._original_landmarks is not None
    
    # ========== Face 랜드마크 ==========
    
    def set_face_landmarks(self, landmarks: Optional[List[Tuple[float, float]]]):
        """현재 편집된 랜드마크 설정"""
        if landmarks is not None:
            self._face_landmarks = list(landmarks)
            self._log_change("set_face", len(landmarks))
        else:
            self._face_landmarks = None
    
    def get_face_landmarks(self) -> Optional[List[Tuple[float, float]]]:
        """현재 편집된 랜드마크 반환"""
        if self._face_landmarks is not None:
            return list(self._face_landmarks)  # 복사본 반환
        return None
    
    # ========== 변형된 랜드마크 ==========
    
    def set_transformed_landmarks(self, landmarks: Optional[List[Tuple[float, float]]]):
        """변형된 랜드마크 설정"""
        if landmarks is not None:
            self._transformed_landmarks = list(landmarks)
            self._log_change("set_transformed", len(landmarks))
        else:
            self._transformed_landmarks = None
    
    def get_transformed_landmarks(self) -> Optional[List[Tuple[float, float]]]:
        """변형된 랜드마크 반환"""
        if self._transformed_landmarks is not None:
            return list(self._transformed_landmarks)  # 복사본 반환
        return None
    
    # ========== Custom 랜드마크 ==========
    
    def set_custom_landmarks(self, landmarks: Optional[List[Tuple[float, float]]], 
                             reason: str = "unknown"):
        """사용자 수정 랜드마크 설정"""
        if landmarks is not None:
            self._custom_landmarks = list(landmarks)
            self._log_change("set_custom", len(landmarks), reason)
        else:
            self._custom_landmarks = None
            self._log_change("set_custom", 0, reason)
    
    def get_custom_landmarks(self) -> Optional[List[Tuple[float, float]]]:
        """사용자 수정 랜드마크 반환"""
        if self._custom_landmarks is not None:
            return list(self._custom_landmarks)  # 복사본 반환
        return None
    
    def has_custom_landmarks(self) -> bool:
        """사용자 수정 랜드마크 존재 여부"""
        return self._custom_landmarks is not None
    
    def update_custom_landmarks(self, index: int, new_position: Tuple[float, float]):
        """특정 인덱스의 랜드마크 위치 업데이트 (드래그용)"""
        if self._custom_landmarks is not None and 0 <= index < len(self._custom_landmarks):
            self._custom_landmarks[index] = new_position
            self._log_change("update_custom_point", index, f"pos={new_position}")
    
    def apply_transform_to_custom(self, transform_func, *args, **kwargs):
        """변환 함수를 custom_landmarks에 적용"""
        if self._custom_landmarks is not None:
            result = transform_func(self._custom_landmarks, *args, **kwargs)
            if result is not None:
                self._custom_landmarks = list(result)
                self._log_change("apply_transform", len(self._custom_landmarks), 
                               f"func={transform_func.__name__}")
    
    # ========== 중앙 포인트 좌표 ==========
    
    def set_iris_center_coords(self, left: Optional[Tuple[float, float]], 
                              right: Optional[Tuple[float, float]]):
        """눈동자 중앙 포인트 좌표 설정"""
        self._left_iris_center_coord = left
        self._right_iris_center_coord = right
        if left is not None or right is not None:
            self._log_change("set_iris_centers", 
                           f"left={left is not None}, right={right is not None}")
    
    def get_left_iris_center_coord(self) -> Optional[Tuple[float, float]]:
        """왼쪽 눈동자 중앙 포인트 좌표 반환"""
        return self._left_iris_center_coord
    
    def get_right_iris_center_coord(self) -> Optional[Tuple[float, float]]:
        """오른쪽 눈동자 중앙 포인트 좌표 반환"""
        return self._right_iris_center_coord
    
    def has_iris_center_coords(self) -> bool:
        """중앙 포인트 좌표 존재 여부"""
        return (self._left_iris_center_coord is not None and 
                self._right_iris_center_coord is not None)
    
    # ========== 상태 관리 ==========
    
    def reset(self, keep_original: bool = True):
        """랜드마크 상태 초기화"""
        if keep_original:
            # 원본은 유지하고 나머지만 초기화
            self._face_landmarks = None
            self._transformed_landmarks = None
            self._custom_landmarks = None
            self._left_iris_center_coord = None
            self._right_iris_center_coord = None
            if self._original_landmarks is not None:
                # 원본으로 복원
                self._custom_landmarks = list(self._original_landmarks)
        else:
            # 모두 초기화
            self._original_landmarks = None
            self._face_landmarks = None
            self._transformed_landmarks = None
            self._custom_landmarks = None
            self._left_iris_center_coord = None
            self._right_iris_center_coord = None
        
        self._log_change("reset", keep_original=keep_original)
    
    def get_current_landmarks_for_display(self) -> Optional[List[Tuple[float, float]]]:
        """표시용 랜드마크 반환 (우선순위: custom > transformed > face > original)"""
        if self._custom_landmarks is not None:
            return list(self._custom_landmarks)
        elif self._transformed_landmarks is not None:
            return list(self._transformed_landmarks)
        elif self._face_landmarks is not None:
            return list(self._face_landmarks)
        elif self._original_landmarks is not None:
            return list(self._original_landmarks)
        return None
    
    def get_landmarks_for_morphing(self) -> Tuple[Optional[List], Optional[List]]:
        """모핑용 랜드마크 반환 (원본, 변형)"""
        original = self.get_original_landmarks()
        transformed = self.get_custom_landmarks()
        if transformed is None:
            transformed = self.get_transformed_landmarks()
        return original, transformed
    
    # ========== 변경 이력 ==========
    
    def _log_change(self, action: str, *args, **kwargs):
        """변경 이력 기록 (디버깅용)"""
        import time
        entry = {
            "time": time.time(),
            "action": action,
            "args": args,
            "kwargs": kwargs
        }
        self._change_history.append(entry)
        # 최근 100개만 유지
        if len(self._change_history) > 100:
            self._change_history = self._change_history[-100:]
    
    def get_change_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """최근 변경 이력 반환"""
        return self._change_history[-limit:]
    
    def clear_history(self):
        """변경 이력 초기화"""
        self._change_history.clear()
    
    # ========== 상태 확인 ==========
    
    def get_status(self) -> Dict[str, Any]:
        """현재 상태 정보 반환"""
        return {
            "has_original": self.has_original_landmarks(),
            "original_count": len(self._original_landmarks) if self._original_landmarks else 0,
            "has_face": self._face_landmarks is not None,
            "face_count": len(self._face_landmarks) if self._face_landmarks else 0,
            "has_transformed": self._transformed_landmarks is not None,
            "transformed_count": len(self._transformed_landmarks) if self._transformed_landmarks else 0,
            "has_custom": self.has_custom_landmarks(),
            "custom_count": len(self._custom_landmarks) if self._custom_landmarks else 0,
            "has_iris_centers": self.has_iris_center_coords(),
            "history_count": len(self._change_history)
        }
