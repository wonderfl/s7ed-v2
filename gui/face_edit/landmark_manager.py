"""
랜드마크 상태 관리 클래스
모든 랜드마크 관련 상태를 중앙에서 관리
"""
from typing import List, Tuple, Optional, Dict, Any, Set


class LandmarkManager:
    """랜드마크 상태를 중앙에서 관리하는 클래스"""
    
    def __init__(self):
        """랜드마크 관리자 초기화"""
        # 원본 얼굴 랜드마크 (468개, 기본 얼굴 랜드마크만)
        self._original_face_landmarks: Optional[List[Tuple[float, float]]] = None
        
        # 원본 눈동자 랜드마크 (10개, 별도 관리)
        self._original_iris_landmarks: Optional[List[Tuple[float, float]]] = None
        
        # 하위 호환성: 기존 코드를 위해 유지 (deprecated)
        self._original_landmarks: Optional[List[Tuple[float, float]]] = None
        
        # 현재 편집된 랜드마크 (표시용)
        self._face_landmarks: Optional[List[Tuple[float, float]]] = None
        
        # 변형된 랜드마크 (사이즈 변경 등)
        self._transformed_landmarks: Optional[List[Tuple[float, float]]] = None
        
        # 사용자 수정 랜드마크 (드래그, 슬라이더 등)
        self._custom_landmarks: Optional[List[Tuple[float, float]]] = None
        
        # 사용자 수정 눈동자 중앙 포인트 (2개, Tesselation용)
        self._custom_iris_centers: Optional[List[Tuple[float, float]]] = None
        
        # 중앙 포인트 좌표 (하위 호환성 유지, 현재 편집된 값)
        self._left_iris_center_coord: Optional[Tuple[float, float]] = None
        self._right_iris_center_coord: Optional[Tuple[float, float]] = None
        
        # 원본 중앙 포인트 좌표 (처음 감지된 값, 드래그 전 원본)
        self._original_left_iris_center_coord: Optional[Tuple[float, float]] = None
        self._original_right_iris_center_coord: Optional[Tuple[float, float]] = None
        
        # 드래그로 변경된 포인트 인덱스 추적
        self._dragged_indices: Set[int] = set()
        
        # 원본 랜드마크 바운딩 박스 (이미지 로딩 시 한 번만 계산)
        self._original_bbox: Optional[Tuple[int, int, int, int]] = None  # (min_x, min_y, max_x, max_y)
        self._original_bbox_img_size: Optional[Tuple[int, int]] = None  # (img_width, img_height)
        
        # 변경 이력 (디버깅용, 선택사항)
        self._change_history: List[Dict[str, Any]] = []
    
    # ========== 원본 얼굴 랜드마크 (468개) ==========
    
    def set_original_face_landmarks(self, landmarks: List[Tuple[float, float]]):
        """원본 얼굴 랜드마크 설정 (468개, 직접 참조로 저장, 복사본 없음)"""
        if landmarks is not None:
            self._original_face_landmarks = landmarks
            self._log_change("set_original_face", len(landmarks))
        else:
            self._original_face_landmarks = None
    
    def get_original_face_landmarks(self) -> Optional[List[Tuple[float, float]]]:
        """원본 얼굴 랜드마크 반환 (468개, 직접 참조, 복사본 없음)"""
        return self._original_face_landmarks
    
    def has_original_face_landmarks(self) -> bool:
        """원본 얼굴 랜드마크 존재 여부"""
        return self._original_face_landmarks is not None
    
    # ========== 원본 눈동자 랜드마크 (10개) ==========
    
    def set_original_iris_landmarks(self, landmarks: Optional[List[Tuple[float, float]]]):
        """원본 눈동자 랜드마크 설정 (10개, 직접 참조로 저장, 복사본 없음)"""
        if landmarks is not None:
            self._original_iris_landmarks = landmarks
            self._log_change("set_original_iris", len(landmarks))
        else:
            self._original_iris_landmarks = None
    
    def get_original_iris_landmarks(self) -> Optional[List[Tuple[float, float]]]:
        """원본 눈동자 랜드마크 반환 (10개, 직접 참조, 복사본 없음)"""
        return self._original_iris_landmarks
    
    def has_original_iris_landmarks(self) -> bool:
        """원본 눈동자 랜드마크 존재 여부"""
        return self._original_iris_landmarks is not None
    
    # ========== 하위 호환성: 원본 랜드마크 (deprecated) ==========
    
    def set_original_landmarks(self, landmarks: List[Tuple[float, float]], img_width: Optional[int] = None, img_height: Optional[int] = None):
        """원본 랜드마크 설정 (하위 호환성, 478개 또는 468개)
        
        주의: 이 메서드는 하위 호환성을 위해 유지됩니다.
        새로운 코드는 set_original_face_landmarks와 set_original_iris_landmarks를 사용하세요.
        
        Args:
            landmarks: 랜드마크 리스트
            img_width: 이미지 너비 (바운딩 박스 계산용, 선택사항)
            img_height: 이미지 높이 (바운딩 박스 계산용, 선택사항)
        """
        if landmarks is not None:
            # 478개인 경우 얼굴(468개)과 눈동자(10개)로 분리
            if len(landmarks) == 478:
                try:
                    from utils.face_morphing.region_extraction import get_iris_indices
                    left_iris_indices, right_iris_indices = get_iris_indices()
                    iris_contour_indices = set(left_iris_indices + right_iris_indices)
                    iris_center_indices = {468, 473}
                    iris_indices = iris_contour_indices | iris_center_indices
                    
                    # 얼굴 랜드마크 (468개)
                    face_landmarks = [pt for i, pt in enumerate(landmarks) if i not in iris_indices]
                    # 눈동자 랜드마크 (10개)
                    iris_landmarks = [landmarks[i] for i in sorted(iris_indices) if i < len(landmarks)]
                    
                    self._original_face_landmarks = face_landmarks
                    self._original_iris_landmarks = iris_landmarks if iris_landmarks else None
                except Exception as e:
                    print(f"[LandmarkManager] 눈동자 분리 실패: {e}")
                    # 폴백: 전체를 얼굴로 저장 (슬라이싱은 새 리스트 생성, 직접 참조 불가)
                    self._original_face_landmarks = landmarks[:468] if len(landmarks) >= 468 else landmarks
                    self._original_iris_landmarks = landmarks[468:] if len(landmarks) > 468 else None
            elif len(landmarks) == 468:
                # 468개인 경우 얼굴로만 저장 (직접 참조)
                self._original_face_landmarks = landmarks
                # 기존 original_iris_landmarks가 있으면 유지 (초기화 시 보존)
                # None으로 덮어쓰지 않고 기존 값을 유지
                if self._original_iris_landmarks is None:
                    # 기존이 None이면 그대로 유지 (아무것도 하지 않음)
                    pass
                # else: 기존 값이 있으면 그대로 유지 (덮어쓰지 않음)
            else:
                # 기타: 그대로 저장 (하위 호환성, 직접 참조)
                self._original_face_landmarks = landmarks
                # 기존 original_iris_landmarks가 있으면 유지 (초기화 시 보존)
                if self._original_iris_landmarks is None:
                    # 기존이 None이면 그대로 유지 (아무것도 하지 않음)
                    pass
                # else: 기존 값이 있으면 그대로 유지 (덮어쓰지 않음)
            
            # 하위 호환성: 기존 필드도 유지 (직접 참조)
            self._original_landmarks = landmarks
            self._log_change("set_original", len(landmarks))
            
            # 원본 바운딩 박스 계산 및 캐싱 (이미지 크기가 제공된 경우)
            if img_width is not None and img_height is not None:
                try:
                    from utils.face_morphing.polygon_morphing.core import _calculate_landmark_bounding_box
                    # 바운딩 박스 계산 (복사본 생성 없이 인덱스로 필터링)
                    try:
                        from utils.face_morphing.region_extraction import get_iris_indices
                        left_iris_indices, right_iris_indices = get_iris_indices()
                        iris_contour_indices = set(left_iris_indices + right_iris_indices)
                        iris_center_indices = {468, 473}
                        iris_indices = iris_contour_indices | iris_center_indices
                    except:
                        # 폴백: 하드코딩된 인덱스 사용
                        iris_indices = {468, 469, 470, 471, 472, 473, 474, 475, 476, 477}
                    
                    # 바운딩 박스 계산: 모든 랜드마크를 사용하여 얼굴 전체 포함
                    # 눈동자 랜드마크는 제외하되, 얼굴 랜드마크 전체를 사용
                    # 경계 포인트는 이미지 경계 밖에 있어서 포함하면 전체 이미지가 되므로 제외
                    # 패딩을 50%로 늘려서 얼굴 전체(턱, 이마 등)를 포함하도록 함
                    landmarks_no_iris = [pt for i, pt in enumerate(landmarks) if i not in iris_indices]
                    bbox = _calculate_landmark_bounding_box(landmarks_no_iris, img_width, img_height, padding_ratio=0.5)
                    if bbox is not None:
                        self._original_bbox = bbox
                        self._original_bbox_img_size = (img_width, img_height)
                except Exception as e:
                    print(f"[LandmarkManager] 바운딩 박스 계산 실패: {e}")
                    self._original_bbox = None
                    self._original_bbox_img_size = None
            else:
                # 이미지 크기가 없으면 초기화만
                self._original_bbox = None
                self._original_bbox_img_size = None
        else:
            self._original_face_landmarks = None
            self._original_iris_landmarks = None
            self._original_landmarks = None
            self._original_bbox = None
            self._original_bbox_img_size = None
    
    def get_original_landmarks(self) -> Optional[List[Tuple[float, float]]]:
        """원본 랜드마크 반환 (하위 호환성, 468+10=478개 또는 468개)
        
        주의: 이 메서드는 하위 호환성을 위해 유지됩니다.
        새로운 코드는 get_original_landmarks_full()을 사용하세요.
        """
        return self.get_original_landmarks_full()
    
    def has_original_landmarks(self) -> bool:
        """원본 랜드마크 존재 여부 (하위 호환성)"""
        return self.has_original_face_landmarks()
    
    # ========== Face 랜드마크 ==========
    
    def set_face_landmarks(self, landmarks: Optional[List[Tuple[float, float]]]):
        """현재 편집된 랜드마크 설정 (직접 참조로 저장, 복사본 없음)
        
        Args:
            landmarks: 설정할 랜드마크 리스트 (직접 참조로 저장됨)
        """
        if landmarks is not None:
            # 항상 직접 참조로 저장 (복사본 생성 안 함)
            self._face_landmarks = landmarks
            self._log_change("set_face", len(landmarks))
        else:
            self._face_landmarks = None
    
    def get_face_landmarks(self) -> Optional[List[Tuple[float, float]]]:
        """현재 편집된 랜드마크 반환 (직접 참조, 복사본 없음)"""
        return self._face_landmarks
    
    # ========== 변형된 랜드마크 ==========
    
    def set_transformed_landmarks(self, landmarks: Optional[List[Tuple[float, float]]]):
        """변형된 랜드마크 설정 (직접 참조로 저장, 복사본 없음)
        
        Args:
            landmarks: 설정할 랜드마크 리스트 (직접 참조로 저장됨)
        """
        if landmarks is not None:
            # 항상 직접 참조로 저장 (복사본 생성 안 함)
            self._transformed_landmarks = landmarks
            self._log_change("set_transformed", len(landmarks))
        else:
            self._transformed_landmarks = None
    
    def get_transformed_landmarks(self) -> Optional[List[Tuple[float, float]]]:
        """변형된 랜드마크 반환 (직접 참조, 복사본 없음)"""
        return self._transformed_landmarks
    
    # ========== Custom 랜드마크 ==========
    
    def set_custom_landmarks(self, landmarks: Optional[List[Tuple[float, float]]], 
                             reason: str = "unknown"):
        """사용자 수정 랜드마크 설정 (468개 또는 470개, 직접 참조로 저장, 복사본 없음)
        
        Args:
            landmarks: 설정할 랜드마크 리스트 (직접 참조로 저장됨)
            reason: 설정 이유 (디버깅용)
        """
        if landmarks is not None:
            # 항상 직접 참조로 저장 (복사본 생성 안 함)
            self._custom_landmarks = landmarks
            self._log_change("set_custom", len(landmarks), reason)
        else:
            self._custom_landmarks = None
            self._log_change("set_custom", 0, reason)
    
    # ========== Custom 눈동자 중앙 포인트 (Tesselation용) ==========
    
    def set_custom_iris_centers(self, centers: Optional[List[Tuple[float, float]]]):
        """사용자 수정 눈동자 중앙 포인트 설정 (2개, Tesselation용)
        
        Args:
            centers: [left_center, right_center] 형태의 리스트 (2개)
        """
        if centers is not None and len(centers) == 2:
            self._custom_iris_centers = centers  # 직접 참조 (복사본 없음)
            # 하위 호환성: 기존 좌표도 업데이트
            self._left_iris_center_coord = centers[0]
            self._right_iris_center_coord = centers[1]
            self._log_change("set_custom_iris_centers", 2)
        else:
            self._custom_iris_centers = None
            self._log_change("set_custom_iris_centers", 0)
    
    def get_custom_iris_centers(self) -> Optional[List[Tuple[float, float]]]:
        """사용자 수정 눈동자 중앙 포인트 반환 (2개, Tesselation용, 직접 참조, 복사본 없음)"""
        return self._custom_iris_centers
    
    def has_custom_iris_centers(self) -> bool:
        """사용자 수정 눈동자 중앙 포인트 존재 여부"""
        return self._custom_iris_centers is not None
    
    def get_custom_landmarks(self) -> Optional[List[Tuple[float, float]]]:
        """사용자 수정 랜드마크 반환 (직접 참조, 복사본 없음)"""
        return self._custom_landmarks
    
    def has_custom_landmarks(self) -> bool:
        """사용자 수정 랜드마크 존재 여부"""
        return self._custom_landmarks is not None
    
    def update_custom_landmark(self, index: int, new_position: Tuple[float, float]):
        """특정 인덱스의 랜드마크 위치 업데이트 (드래그용)
        
        Args:
            index: 랜드마크 인덱스
            new_position: 새로운 위치 (x, y)
        """
        if self._custom_landmarks is not None and 0 <= index < len(self._custom_landmarks):
            self._custom_landmarks[index] = new_position
            # 드래그로 변경된 포인트로 표시
            self._dragged_indices.add(index)
            self._log_change("update_custom_point", index, f"pos={new_position}")
    
    def update_custom_landmarks(self, index: int, new_position: Tuple[float, float]):
        """하위 호환성: update_custom_landmark의 별칭"""
        self.update_custom_landmark(index, new_position)
    
    def apply_transform_to_custom(self, transform_func, *args, **kwargs):
        """변환 함수를 custom_landmarks에 적용"""
        if self._custom_landmarks is not None:
            result = transform_func(self._custom_landmarks, *args, **kwargs)
            if result is not None:
                self._custom_landmarks = result  # 직접 참조 (복사본 없음, transform_func가 새 리스트 반환할 수 있음)
                self._log_change("apply_transform", len(self._custom_landmarks), 
                               f"func={transform_func.__name__}")
    
    # ========== 중앙 포인트 좌표 ==========
    
    def set_iris_center_coords(self, left: Optional[Tuple[float, float]], 
                              right: Optional[Tuple[float, float]], 
                              is_original: bool = False):
        """눈동자 중앙 포인트 좌표 설정
        
        Args:
            left: 왼쪽 눈동자 중앙 포인트 좌표
            right: 오른쪽 눈동자 중앙 포인트 좌표
            is_original: True이면 원본 중앙 포인트로 저장 (처음 감지 시)
        """
        self._left_iris_center_coord = left
        self._right_iris_center_coord = right
        
        # 원본 중앙 포인트는 is_original=True일 때만 저장 (드래그 시 덮어쓰기 방지)
        if is_original:
            if left is not None:
                self._original_left_iris_center_coord = left
            if right is not None:
                self._original_right_iris_center_coord = right
        elif self._original_left_iris_center_coord is None and left is not None:
            # 원본이 없을 때만 자동으로 원본으로 저장 (초기화 시)
            self._original_left_iris_center_coord = left
        elif self._original_right_iris_center_coord is None and right is not None:
            # 원본이 없을 때만 자동으로 원본으로 저장 (초기화 시)
            self._original_right_iris_center_coord = right
            
        if left is not None or right is not None:
            self._log_change("set_iris_centers", 
                           f"left={left is not None}, right={right is not None}, is_original={is_original}")
    
    def get_original_left_iris_center_coord(self) -> Optional[Tuple[float, float]]:
        """원본 왼쪽 눈동자 중앙 포인트 좌표 반환"""
        return self._original_left_iris_center_coord
    
    def get_original_right_iris_center_coord(self) -> Optional[Tuple[float, float]]:
        """원본 오른쪽 눈동자 중앙 포인트 좌표 반환"""
        return self._original_right_iris_center_coord
    
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
    
    # ========== 드래그 추적 ==========
    
    def mark_as_dragged(self, index: int):
        """드래그로 변경된 포인트로 표시
        
        Args:
            index: 랜드마크 인덱스
        """
        self._dragged_indices.add(index)
        self._log_change("mark_as_dragged", index)
    
    def unmark_as_dragged(self, index: int):
        """드래그 표시 제거 (취소 시)
        
        Args:
            index: 랜드마크 인덱스
        """
        self._dragged_indices.discard(index)
        self._log_change("unmark_as_dragged", index)
    
    def get_dragged_indices(self) -> Set[int]:
        """드래그로 변경된 포인트 인덱스 반환
        
        Returns:
            드래그로 변경된 포인트 인덱스 집합 (복사본)
        """
        return set(self._dragged_indices)  # 복사본 반환
    
    def clear_dragged_indices(self):
        """드래그 표시 초기화"""
        self._dragged_indices.clear()
        self._log_change("clear_dragged_indices")
    
    def is_dragged(self, index: int) -> bool:
        """특정 인덱스가 드래그로 변경되었는지 확인
        
        Args:
            index: 랜드마크 인덱스
            
        Returns:
            드래그로 변경되었으면 True
        """
        return index in self._dragged_indices
    
    # ========== 상태 관리 ==========
    
    # ========== 원본 바운딩 박스 캐싱 ==========
    
    def set_original_bbox(self, bbox: Tuple[int, int, int, int], img_width: int, img_height: int):
        """원본 랜드마크 바운딩 박스 설정 (이미지 로딩 시 한 번만 계산)
        
        Args:
            bbox: (min_x, min_y, max_x, max_y) 바운딩 박스 좌표
            img_width: 이미지 너비
            img_height: 이미지 높이
        """
        self._original_bbox = bbox
        self._original_bbox_img_size = (img_width, img_height)
    
    def get_original_bbox(self, img_width: int, img_height: int) -> Optional[Tuple[int, int, int, int]]:
        """원본 랜드마크 바운딩 박스 반환 (캐시된 값 사용)
        
        Args:
            img_width: 현재 이미지 너비 (캐시 검증용)
            img_height: 현재 이미지 높이 (캐시 검증용)
        
        Returns:
            (min_x, min_y, max_x, max_y) 바운딩 박스 좌표 또는 None
        """
        # 이미지 크기가 변경되었으면 캐시 무효화
        if self._original_bbox_img_size is not None:
            cached_width, cached_height = self._original_bbox_img_size
            if cached_width != img_width or cached_height != img_height:
                self._original_bbox = None
                self._original_bbox_img_size = None
        return self._original_bbox
    
    def reset(self, keep_original: bool = True):
        """랜드마크 상태 초기화"""
        if keep_original:
            # 원본은 유지하고 나머지만 초기화
            self._face_landmarks = None
            self._transformed_landmarks = None
            self._custom_landmarks = None
            self._custom_iris_centers = None
            self._left_iris_center_coord = None
            self._right_iris_center_coord = None
            self._dragged_indices.clear()  # 드래그 표시도 초기화
            if self._original_face_landmarks is not None:
                # 원본 얼굴 랜드마크로 복원 (직접 참조, 복사본 없음)
                self._custom_landmarks = self._original_face_landmarks
        else:
            # 모두 초기화
            self._original_face_landmarks = None
            self._original_iris_landmarks = None
            self._original_landmarks = None
            self._face_landmarks = None
            self._transformed_landmarks = None
            self._custom_landmarks = None
            self._custom_iris_centers = None
            self._left_iris_center_coord = None
            self._right_iris_center_coord = None
            self._dragged_indices.clear()  # 드래그 표시도 초기화
        
        self._log_change("reset", keep_original=keep_original)
    
    def get_current_landmarks_for_display(self) -> Optional[List[Tuple[float, float]]]:
        """표시용 랜드마크 반환 (우선순위: custom > transformed > face > original, 직접 참조, 복사본 없음)"""
        if self._custom_landmarks is not None:
            return self._custom_landmarks
        elif self._transformed_landmarks is not None:
            return self._transformed_landmarks
        elif self._face_landmarks is not None:
            return self._face_landmarks
        elif self._original_landmarks is not None:
            return self._original_landmarks
        return None
    
    def get_landmarks_for_morphing(self) -> Tuple[Optional[List], Optional[List]]:
        """모핑용 랜드마크 반환 (원본, 변형, 직접 참조, 복사본 없음)
        
        주의: morph_face_by_polygons는 읽기만 하므로 직접 참조 반환 (복사본 없음)
        """
        original = self.get_original_landmarks_full()  # 직접 참조 (복사본 없음)
        transformed = self.get_custom_landmarks()  # 직접 참조 (복사본 없음)
        if transformed is None:
            transformed = self.get_transformed_landmarks()  # 직접 참조 (복사본 없음)
        return original, transformed
    
    # ========== 편의 메서드 ==========
    
    def get_original_landmarks_full(self) -> Optional[List[Tuple[float, float]]]:
        """원본 랜드마크 전체 반환 (직접 참조, 복사본 없음)
        
        주의: 눈동자가 있으면 얼굴 랜드마크만 반환 (468개)
        눈동자 포함 전체가 필요하면 get_copied_original_landmarks_full_with_iris() 사용
        
        Returns:
            468개 얼굴 랜드마크 (직접 참조)
        """
        return self._original_face_landmarks
    
    def get_copied_original_landmarks_full_with_iris(self) -> Optional[List[Tuple[float, float]]]:
        """원본 랜드마크 전체 반환 (눈동자 포함, 468+10=478개, 복사본 생성)
        
        주의: 구조 변경(눈동자 추가)을 위해 복사본 생성
        
        Returns:
            468개 얼굴 랜드마크 + 10개 눈동자 랜드마크 = 478개 (복사본)
        """
        if self._original_face_landmarks is not None:
            if self._original_iris_landmarks is not None:
                result = list(self._original_face_landmarks)  # 눈동자 추가를 위해 복사본 필요
                # 눈동자 랜드마크를 올바른 인덱스 위치에 삽입
                try:
                    from utils.face_morphing.region_extraction import get_iris_indices
                    left_iris_indices, right_iris_indices = get_iris_indices()
                    iris_contour_indices = set(left_iris_indices + right_iris_indices)
                    iris_center_indices = {468, 473}
                    iris_indices = sorted(iris_contour_indices | iris_center_indices)
                    
                    # 468개 위치에 눈동자 랜드마크 삽입
                    for i, idx in enumerate(iris_indices):
                        if i < len(self._original_iris_landmarks):
                            if idx < len(result):
                                result.insert(idx, self._original_iris_landmarks[i])
                            else:
                                result.append(self._original_iris_landmarks[i])
                except Exception as e:
                    print(f"[LandmarkManager] 눈동자 병합 실패: {e}")
                    # 폴백: 끝에 추가
                    result.extend(self._original_iris_landmarks)
                return result
            else:
                # 눈동자가 없으면 직접 참조 반환 (복사본 없음)
                return self._original_face_landmarks
        return None
    
    def get_landmarks_for_tesselation(self) -> Tuple[Optional[List[Tuple[float, float]]], Optional[List[Tuple[float, float]]]]:
        """Tesselation용 랜드마크 반환 (원본, 변형, 직접 참조, 복사본 없음)
        
        주의: 중앙 포인트가 없으면 468개만 반환
        중앙 포인트 포함이 필요하면 get_copied_landmarks_for_tesselation_with_centers() 사용
        
        Returns:
            (original_landmarks, transformed_landmarks)
            - original_landmarks: 468개 얼굴 (직접 참조, 복사본 없음)
            - transformed_landmarks: 468개 또는 470개 (직접 참조, 복사본 없음)
        """
        # 원본: 직접 참조 반환 (복사본 없음)
        original = self._original_face_landmarks
        
        # 변형: custom_landmarks 사용 (이미 470개 구조일 수 있음)
        transformed = self.get_custom_landmarks()
        if transformed is None:
            transformed = self.get_transformed_landmarks()
        
        return original, transformed
    
    def get_copied_landmarks_for_tesselation_with_centers(self) -> Tuple[Optional[List[Tuple[float, float]]], Optional[List[Tuple[float, float]]]]:
        """Tesselation용 랜드마크 반환 (중앙 포인트 포함, 복사본 생성)
        
        주의: 구조 변경(중앙 포인트 추가)을 위해 복사본 생성
        
        Returns:
            (original_landmarks, transformed_landmarks)
            - original_landmarks: 468개 얼굴 + 2개 중앙 포인트 = 470개 (복사본)
            - transformed_landmarks: 468개 또는 470개 (직접 참조, 복사본 없음)
        """
        # 원본: 얼굴 468개 + 중앙 포인트 2개
        original = None
        if self._original_face_landmarks is not None:
            # 중앙 포인트 추가 (우선순위: custom_iris_centers > 좌표 > 계산)
            left_center = None
            right_center = None
            
            if self._custom_iris_centers is not None and len(self._custom_iris_centers) >= 2:
                # custom_iris_centers 사용 (Tesselation용으로 이미 설정됨)
                left_center = self._custom_iris_centers[0]
                right_center = self._custom_iris_centers[1]
            elif self._left_iris_center_coord is not None and self._right_iris_center_coord is not None:
                # 기존 좌표 사용
                left_center = self._left_iris_center_coord
                right_center = self._right_iris_center_coord
            elif self._original_iris_landmarks is not None:
                # 원본 눈동자에서 중앙 포인트 계산
                try:
                    from utils.face_morphing.region_extraction import get_iris_indices
                    left_iris_indices, right_iris_indices = get_iris_indices()
                    # 왼쪽 눈동자 포인트 추출 (contour만)
                    left_points = []
                    for idx in left_iris_indices:
                        # original_iris_landmarks는 인덱스 순서대로 저장되어 있지 않을 수 있으므로
                        # 간단히 처음 4개를 왼쪽으로 가정
                        if len(left_points) < 4 and len(self._original_iris_landmarks) > len(left_points):
                            left_points.append(self._original_iris_landmarks[len(left_points)])
                    # 오른쪽 눈동자 포인트 추출
                    right_points = []
                    for idx in right_iris_indices:
                        if len(right_points) < 4 and len(self._original_iris_landmarks) > len(left_points) + len(right_points):
                            right_points.append(self._original_iris_landmarks[len(left_points) + len(right_points)])
                    
                    if left_points:
                        left_center = (sum(p[0] for p in left_points) / len(left_points),
                                      sum(p[1] for p in left_points) / len(left_points))
                    if right_points:
                        right_center = (sum(p[0] for p in right_points) / len(right_points),
                                       sum(p[1] for p in right_points) / len(right_points))
                except Exception as e:
                    print(f"[LandmarkManager] 중앙 포인트 계산 실패: {e}")
            
            # 중앙 포인트 추가 (morph_face_by_polygons 순서: MediaPipe LEFT_IRIS 먼저, MediaPipe RIGHT_IRIS 나중)
            if left_center is not None and right_center is not None:
                # 중앙 포인트 추가를 위해 새 리스트 생성 (구조 변경 필요)
                original = list(self._original_face_landmarks)  # 중앙 포인트 추가를 위해 복사본 필요
                original.append(left_center)   # MediaPipe LEFT_IRIS (사용자 왼쪽, len-2)
                original.append(right_center)  # MediaPipe RIGHT_IRIS (사용자 오른쪽, len-1)
            else:
                # 중앙 포인트가 없으면 직접 참조 반환 (복사본 없음)
                original = self._original_face_landmarks
        
        # 변형: custom_landmarks 사용 (이미 470개 구조일 수 있음)
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
            "has_original_face": self.has_original_face_landmarks(),
            "original_face_count": len(self._original_face_landmarks) if self._original_face_landmarks else 0,
            "has_original_iris": self.has_original_iris_landmarks(),
            "original_iris_count": len(self._original_iris_landmarks) if self._original_iris_landmarks else 0,
            "has_original": self.has_original_landmarks(),  # 하위 호환성
            "original_count": len(self._original_landmarks) if self._original_landmarks else 0,  # 하위 호환성
            "has_face": self._face_landmarks is not None,
            "face_count": len(self._face_landmarks) if self._face_landmarks else 0,
            "has_transformed": self._transformed_landmarks is not None,
            "transformed_count": len(self._transformed_landmarks) if self._transformed_landmarks else 0,
            "has_custom": self.has_custom_landmarks(),
            "custom_count": len(self._custom_landmarks) if self._custom_landmarks else 0,
            "has_custom_iris_centers": self.has_custom_iris_centers(),
            "custom_iris_centers_count": len(self._custom_iris_centers) if self._custom_iris_centers else 0,
            "has_iris_centers": self.has_iris_center_coords(),
            "history_count": len(self._change_history)
        }
