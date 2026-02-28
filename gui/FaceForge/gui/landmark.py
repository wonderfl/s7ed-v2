"""
랜드마크 상태 관리 클래스
모든 랜드마크 관련 상태를 중앙에서 관리
"""
from typing import List, Tuple, Optional, Dict, Any, Set

from utils.logger import debug, info, error, log
from gui.FaceForge.utils.debugs import DEBUG_GUIDE_LINES, DEBUG_CURRENT_LANDMARKS

class StateKeys:
    # landmark_state 섹션 키
    SECTION_ORIGINAL = 'original'
    SECTION_CURRENT = 'current'
    SECTION_TRANSFORMED = 'transformed'
    SECTION_WARP = 'warp'
    SECTION_CONTEXT = 'context'

    # landmark_state 데이터 키
    KEY_FACE_LANDMARKS = 'face_landmarks'
    KEY_IRIS_LANDMARKS = 'iris_landmarks'
    KEY_DRAGGED_INDICES = 'dragged_indices'
    KEY_TRANSFORMED_INDICES = 'transformed_indices'
    KEY_SOURCE_LANDMARKS = 'source_landmarks'
    KEY_TARGET_LANDMARKS = 'target_landmarks'
    KEY_SELECTED_INDICES = 'selected_indices'
    KEY_IMAGE_SIZE = 'image_size'
    KEY_SELECTED_REGIONS = 'selected_regions'
    KEY_SLIDER_PARAMS = 'slider_params'


class LandmarkManager:
    """랜드마크 상태를 중앙에서 관리하는 클래스"""

    section_keys_map = {
        StateKeys.SECTION_ORIGINAL: [
            StateKeys.KEY_FACE_LANDMARKS,
            StateKeys.KEY_IRIS_LANDMARKS
        ],
        StateKeys.SECTION_CURRENT:[
            StateKeys.KEY_FACE_LANDMARKS,
            StateKeys.KEY_DRAGGED_INDICES
        ],
        StateKeys.SECTION_TRANSFORMED:[
            StateKeys.KEY_FACE_LANDMARKS,
            StateKeys.KEY_TRANSFORMED_INDICES
        ],
        StateKeys.SECTION_WARP:[
            StateKeys.KEY_SOURCE_LANDMARKS, 
            StateKeys.KEY_TARGET_LANDMARKS, 
            StateKeys.KEY_SELECTED_INDICES
        ],
        StateKeys.SECTION_CONTEXT:[
            StateKeys.KEY_IMAGE_SIZE, 
            StateKeys.KEY_SELECTED_REGIONS, 
            StateKeys.KEY_SLIDER_PARAMS
        ],
    }    
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.landmark_state = None  # 새로 추가

        """랜드마크 관리자 초기화"""
        # 원본 얼굴 랜드마크 (468개, 기본 얼굴 랜드마크만)
        self._original_face_landmarks: Optional[List[Tuple[float, float]]] = None
        
        # 원본 눈동자 랜드마크 (10개, 별도 관리)
        self._original_iris_landmarks: Optional[List[Tuple[float, float]]] = None

        # 현재 편집된 랜드마크
        self._current_face_landmarks: Optional[List[Tuple[float, float]]] = None


        # 현재 편집된 랜드마크 (표시용)
        self._face_landmarks: Optional[List[Tuple[float, float]]] = None
        
        # 변형된 랜드마크 (사이즈 변경 등)
        self._transformed_landmarks: Optional[List[Tuple[float, float]]] = None
        
        # 사용자 수정 랜드마크 (드래그, 슬라이더 등)
        self._custom_landmarks: Optional[List[Tuple[float, float]]] = None
        self._custom_landmarks_signature: Optional[Tuple[int, Tuple[float, ...]]] = None
        
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

        self.create_landmark_state()
    
    # ========== 원본 얼굴 랜드마크 (468개) ==========
    
    def set_original_face_landmarks(self, landmarks: List[Tuple[float, float]]):
        """원본 얼굴 랜드마크 설정 (468개, 직접 참조로 저장, 복사본 없음)"""
        self._original_face_landmarks = None
        if landmarks is not None:
            self._original_face_landmarks = landmarks
            self._log_change("set_original_face", len(landmarks))
    
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
        if DEBUG_GUIDE_LINES:
            debug("set_original_landmarks",f"landmarks: {len(landmarks) if landmarks else -1}, image({img_width}x{img_height})")

        if landmarks is not None:
            # 478개인 경우 얼굴(468개)과 눈동자(10개)로 분리
            if len(landmarks) == 478:
                try:
                    from gui.FaceForge.utils.morphing.region import get_iris_indices
                    left_iris_indices, right_iris_indices = get_iris_indices()
                    iris_contour_indices = set(left_iris_indices + right_iris_indices)
                    iris_center_indices = {468, 473}
                    iris_indices = iris_contour_indices | iris_center_indices
                    
                    # 얼굴 랜드마크 (468개)
                    face_landmarks = [pt for i, pt in enumerate(landmarks) if i not in iris_indices]
                    # 눈동자 랜드마크 (10개)
                    iris_landmarks = [landmarks[i] for i in sorted(iris_indices) if i < len(landmarks)]
                    
                    self.set_original_face_landmarks(face_landmarks)
                    self._original_iris_landmarks = iris_landmarks if iris_landmarks else None
                except Exception as e:
                    print(f"[LandmarkManager] 눈동자 분리 실패: {e}")
                    # 폴백: 전체를 얼굴로 저장 (슬라이싱은 새 리스트 생성, 직접 참조 불가)
                    self.set_original_face_landmarks(landmarks[:468] if len(landmarks) >= 468 else landmarks)
                    self._original_iris_landmarks = landmarks[468:] if len(landmarks) > 468 else None
            elif len(landmarks) == 468:
                # 468개인 경우 얼굴로만 저장 (직접 참조)
                self.set_original_face_landmarks(landmarks)
            else:
                # 기타: 그대로 저장 (하위 호환성, 직접 참조)
                self.set_original_face_landmarks(landmarks)

            # 원본 바운딩 박스 계산 및 캐싱 (이미지 크기가 제공된 경우)
            if img_width is not None and img_height is not None:
                try:
                    from gui.FaceForge.utils.morphing.polygon.core import _calculate_landmark_bounding_box
                    # 바운딩 박스 계산 (복사본 생성 없이 인덱스로 필터링)
                    try:
                        from gui.FaceForge.utils.morphing.region import get_iris_indices
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

                    if DEBUG_GUIDE_LINES:
                        debug("set_original_landmarks",
                            f"landmarks_no_iris: {len(landmarks_no_iris)}, bbox: {bbox}, "
                            f"original_bbox[ {self._original_bbox}, {self._original_bbox_img_size} ]"
                        )
                except Exception as e:
                    print(f"[LandmarkManager] 바운딩 박스 계산 실패: {e}")
                    self._original_bbox = None
                    self._original_bbox_img_size = None
            else:
                if DEBUG_GUIDE_LINES:
                    debug("set_original_landmarks",
                        f"no image[ {img_width} x {img_height} ]"
                    )

                # 이미지 크기가 없으면 초기화만                
                self._original_bbox = None
                self._original_bbox_img_size = None
        else:
            self._original_face_landmarks = None
            self._original_iris_landmarks = None
            self._original_bbox = None
            self._original_bbox_img_size = None
    
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
            new_signature = self._compute_landmark_signature(landmarks)
            if (self._custom_landmarks is not None and
                    self._custom_landmarks_signature == new_signature):
                # 동일한 내용이면 중복 갱신을 피한다
                return

            # 항상 직접 참조로 저장 (복사본 생성 안 함)
            self._custom_landmarks = landmarks
            self._custom_landmarks_signature = new_signature
            self._log_change("set_custom", len(landmarks), reason)
        else:
            self._custom_landmarks = None
            self._custom_landmarks_signature = None
            self._log_change("set_custom", 0, reason)

    def get_custom_landmarks_signature(self):
        """최근 custom 랜드마크 시그니처 반환 (중복 갱신 여부 확인용)"""
        return self._custom_landmarks_signature

    
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
            left: 왼쪽 눈동자 중앙 포인트 좌표 (MediaPipe LEFT_EYE 기준)
            right: 오른쪽 눈동자 중앙 포인트 좌표 (MediaPipe RIGHT_EYE 기준)
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

    # ========== 내부 유틸리티 ==========

    def _compute_landmark_signature(self, landmarks: Optional[List[Tuple[float, float]]]):
        if not landmarks:
            return None

        length = len(landmarks)
        if length == 0:
            return None

        sample_indices = [0, length // 2, length - 1]
        samples: List[float] = []
        for idx in sample_indices:
            if idx < 0 or idx >= length:
                continue
            point = landmarks[idx]
            if isinstance(point, (tuple, list)) and len(point) >= 2:
                x, y = point[:2]
            else:
                x = getattr(point, 'x', 0.0)
                y = getattr(point, 'y', 0.0)
            try:
                samples.append(round(float(x), 3))
                samples.append(round(float(y), 3))
            except (TypeError, ValueError):
                samples.extend([0.0, 0.0])

        return (length, tuple(samples))
                        

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

        if DEBUG_GUIDE_LINES:
            print("[get_original_bbox]",
                f": image({img_width},{img_height}), size: {self._original_bbox_img_size}, "
                f"bbox: {self._original_bbox}, "
                f"cache_valid: {self._original_bbox_img_size == (img_width, img_height)}")
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

            self._face_landmarks = None
            self._transformed_landmarks = None
            self._custom_landmarks = None
            self._custom_iris_centers = None
            self._left_iris_center_coord = None
            self._right_iris_center_coord = None
            self._original_left_iris_center_coord = None
            self._original_right_iris_center_coord = None
            self._dragged_indices.clear()  # 드래그 표시도 초기화

        # landmark_state 초기화
        self.create_landmark_state()
        
        self._log_change("reset", keep_original=keep_original)

    # ========== 편의 메서드 ==========
    
    def get_original_landmarks_full(self) -> Optional[List[Tuple[float, float]]]:
        """원본 랜드마크 전체 반환 (직접 참조, 복사본 없음)
        
        주의: 눈동자가 있으면 얼굴 랜드마크만 반환 (468개)
        눈동자 포함 전체가 필요하면 get_copied_original_landmarks_full_with_iris() 사용
        
        Returns:
            468개 얼굴 랜드마크 (직접 참조)
        """
        return self._original_face_landmarks                                


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



    # ========== 현재 편집 랜드마크 ==========
    
    def get_current_landmarks(self, reason: Optional[str] = None):
        # ✅ 편집본이 없으면 원본으로 초기화하고 항상 편집본 반환
        # landmark_state에서 최신 랜드마크 가져오기
        state = self.get_landmark_state()
        landmarks = state.get(StateKeys.SECTION_CURRENT, {}).get(StateKeys.KEY_FACE_LANDMARKS)
        if DEBUG_CURRENT_LANDMARKS:
            log("get_current_landmarks", f"SECTION_CURRENT landmarks: {landmarks is not None}, reason: {reason}")
            if landmarks:
                debug("get_current_landmarks", 
                    f"SECTION_CURRENT lips: 상단 ({landmarks[13][0]:.3f},{landmarks[13][1]:.3f}), "
                    f"왼쪽: ({landmarks[61][0]:.3f},{landmarks[61][1]:.3f}), "
                    f"오른쪽: ({landmarks[291][0]:.3f},{landmarks[291][1]:.3f}), "
                    f"하단: ({landmarks[292][0]:.3f},{landmarks[292][1]:.3f})"
                )


        if landmarks is None:
            # 편집본이 없으면 원본으로 초기화하고 항상 편집본 반환
            if self._current_face_landmarks is None:
                self._current_face_landmarks = self._original_face_landmarks.copy() if self._original_face_landmarks else None
            landmarks = self._current_face_landmarks

        # _current_face_landmarks도 업데이트
        self._current_face_landmarks = landmarks
        
        return landmarks
    
    def set_current_landmarks(self, landmarks: Optional[List[Tuple[float, float]]],
                              reason: Optional[str] = None):
        """현재 편집 중인 랜드마크 설정"""

        if DEBUG_CURRENT_LANDMARKS:
            log("set_current_landmarks", f"SECTION_CURRENT landmarks: {landmarks is not None}, reason: {reason}")
            if landmarks:
                debug("set_current_landmarks", 
                    f"SECTION_CURRENT lips: 상단 ({landmarks[13][0]:.3f},{landmarks[13][1]:.3f}), "
                    f"왼쪽: ({landmarks[61][0]:.3f},{landmarks[61][1]:.3f}), "
                    f"오른쪽: ({landmarks[291][0]:.3f},{landmarks[291][1]:.3f}), "
                    f"하단: ({landmarks[292][0]:.3f},{landmarks[292][1]:.3f})"
                )

        self._current_face_landmarks = landmarks
        self._log_change("set_current", len(landmarks) if landmarks else 0, reason=reason)
    
    def has_current_landmarks(self) -> bool:
        """현재 편집 중인 랜드마크 존재 여부"""
        return self._current_face_landmarks is not None
    
    def reset_current_landmarks(self):
        """현재 편집 랜드마크 초기화 (원본으로 되돌림)"""
        self._current_face_landmarks = None
        self._log_change("reset_current", 0)

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

    def create_landmark_state(self):
        """landmark_state dict 생성
        Returns:
        dict: 랜드마크 상태를 관리하는 구조체
            - original: 원본 랜드마크 데이터 (변경 불가)
            - current: 현재 랜드마크 데이터 (드래그 반영)
            - transformed: 변형된 랜드마크 데이터 (슬라이더 반영)
            - warp: 워프용 데이터 (morph_face_by_polygons 전용)
            - context: 기타 메타데이터 (이미지 정보, 파라미터 등)
        """
        
        self.landmark_state = {
            # 원본 데이터: 절대 변경되지 않는 기준점
            StateKeys.SECTION_ORIGINAL: {
                StateKeys.KEY_FACE_LANDMARKS: self._original_face_landmarks,  # 468개 얼굴 랜드마크
                StateKeys.KEY_IRIS_LANDMARKS: self._original_iris_landmarks,  # 10개 홍채 랜드마크
            },
            # 현재 상태: 드래그된 랜드마크
            StateKeys.SECTION_CURRENT: {
                StateKeys.KEY_FACE_LANDMARKS: self._current_face_landmarks,   # 드래그 반영된 현재 상태
                StateKeys.KEY_DRAGGED_INDICES: self.get_dragged_indices(),    # 드래그된 포인트 인덱스
            },
            
            # 변형 상태: 슬라이더 적용된 결과
            StateKeys.SECTION_TRANSFORMED: {
                StateKeys.KEY_FACE_LANDMARKS: None,                           # 슬라이더 적용 후 최종 상태
                StateKeys.KEY_TRANSFORMED_INDICES: set(),                     # 실제 변형된 포인트 인덱스
            },
            
            # 워프 데이터: morph_face_by_polygons 함수용
            StateKeys.SECTION_WARP: {
                StateKeys.KEY_SOURCE_LANDMARKS: None,                         # 워프 전 랜드마크
                StateKeys.KEY_TARGET_LANDMARKS: None,                         # 워프 후 랜드마크
                StateKeys.KEY_SELECTED_INDICES: None,                         # 워프 대상 포인트 인덱스
            },
            
            # 컨텍스트: 기타 필요 정보
            StateKeys.SECTION_CONTEXT: {
                StateKeys.KEY_IMAGE_SIZE: None,                               # 이미지 크기 (width, height)
                StateKeys.KEY_SELECTED_REGIONS: None,                         # 선택된 영역 목록
                StateKeys.KEY_SLIDER_PARAMS: {},                              # 슬라이더 파라미터
            }
        }
        return self.landmark_state
    
    def update_landmark_state(self, action, data):
        """landmark_state 업데이트"""
        if self.landmark_state is None:
            return
        
        if action == 'apply_drag':
            # 드래그 적용
            pass
        elif action == 'apply_sliders':
            # 슬라이더 적용
            pass
        elif action == 'prepare_warp':
            # 워프 데이터 준비
            pass

    def get_landmark_state(self):
        """landmark_state 반환"""
        return self.landmark_state        

    def get_state_section(self, section):
        """섹션 전체 조회"""
        if self.landmark_state is None:
            raise ValueError("landmark_state is None")
        
        if section not in self.landmark_state:
            raise ValueError(f"wrong section: {section}")
        
        return self.landmark_state[section]

    def _get_valid_keys_for_section(self, section):
        """
        섹션별 유효한 키 목록 반환
        
        Args:
            section (str): 섹션 키 (예: StateKeys.SECTION_ORIGINAL)
            
        Returns:
            list: 해당 섹션에서 사용 가능한 키 목록
                유효하지 않은 섹션이면 빈 리스트 반환
        """

        return self.section_keys_map.get(section, [])

    def _validate_section_data(self, section, data):
        """
        섹션 데이터의 타입 유효성 검사
        
        Args:
            section (str): 섹션 키 (예: StateKeys.SECTION_WARP)
            data (dict): 검사할 데이터 딕셔너리
            
        Raises:
            TypeError: 데이터 타입이 올바르지 않을 경우
            
        Note:
            - face_landmarks, iris_landmarks: list 또는 None 허용
            - dragged_indices, transformed_indices, selected_indices: set, list 또는 None 허용  
            - image_size: tuple 또는 None 허용
        """

        for key, value in data.items():
            if key == StateKeys.KEY_FACE_LANDMARKS or key == StateKeys.KEY_IRIS_LANDMARKS:
                if value is not None and not isinstance(value, list):
                    raise TypeError(f"{key} must be list or None, got {type(value)}")
            elif key in [StateKeys.KEY_DRAGGED_INDICES, StateKeys.KEY_TRANSFORMED_INDICES, StateKeys.KEY_SELECTED_INDICES]:
                if value is not None and not isinstance(value, (set, list)):
                    raise TypeError(f"{key} must be set or list or None, got {type(value)}")
            elif key == StateKeys.KEY_IMAGE_SIZE:
                if value is not None and not isinstance(value, tuple):
                    raise TypeError(f"{key} must be tuple or None, got {type(value)}")                    



    def set_state_section(self, section, data):
        """섹션 전체 업데이트"""
        if self.landmark_state is None:
            raise ValueError("landmark_state is None")
        
        if section not in self.landmark_state:
            raise ValueError(f"wrong section: {section}")

        # 키 유효성 검사
        valid_keys = self._get_valid_keys_for_section(section)
        for key in data.keys():
            if key in valid_keys:
                continue
            raise ValueError(f"invalid key '{key}' for section '{section}'. Valid keys: {valid_keys}")
    
        # 값 type 유효성 검사
        self._validate_section_data(section, data)            
        
        self.landmark_state[section].update(data)


    def get_state_value(self, section, key):
        """특정 키값 조회"""
        if self.landmark_state is None:
            raise ValueError("landmark_state is None")
        
        if section not in self.landmark_state:
            raise ValueError(f"wrong section: {section}")
        
        if key not in self.landmark_state[section]:
            raise ValueError(f"wrong key: {key} in {section}")
        
        return self.landmark_state[section][key]

    
    def set_state_value(self, section, key, value):
        """특정 키값 업데이트"""
        if self.landmark_state is None:
            raise ValueError("landmark_state is None")
        
        if section not in self.landmark_state:
            raise ValueError(f"wrong section: {section}")
        
        if key not in self.landmark_state[section]:
            raise ValueError(f"wrong key: {key} in {section}")
        
        self.landmark_state[section][key] = value