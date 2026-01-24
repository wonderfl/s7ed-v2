"""
전체탭(all) 폴리곤 그리기 메서드
전체탭에 맞는 폴리곤 그리기 로직을 담당
"""
import math
import time
from typing import List, Tuple, Optional, Dict, Any

# 눈꺼풀 랜드마크 인덱스 정의 (MediaPipe Face Mesh)
LEFT_EYELID_INDICES = [33, 7, 163, 144, 145, 153, 154, 155, 133, 173, 157, 158, 159, 160, 161, 246]
RIGHT_EYELID_INDICES = [362, 398, 384, 385, 386, 387, 388, 466, 263, 249, 390, 373, 374, 380, 381, 382]

# 상안견/하안견 분리 (위쪽 눈꺼풀)
LEFT_UPPER_EYELID_INDICES = [33, 7, 163, 144, 145, 153, 154, 155]
LEFT_LOWER_EYELID_INDICES = [133, 173, 157, 158, 159, 160, 161, 246]
RIGHT_UPPER_EYELID_INDICES = [362, 398, 384, 385, 386, 387, 388]
RIGHT_LOWER_EYELID_INDICES = [263, 249, 390, 373, 374, 380, 381, 382]

class AllTabDrawerMixin:
    """전체 탭 폴리곤 그리기 믹스인"""
    
    def __init__(self):
        # 눈동자 윤곽 재계산 캐시
        self._iris_contour_cache = {}
        self._cache_max_size = 100
        
        # 성능 측정
        self._performance_stats = {
            'cache_hits': 0,
            'cache_misses': 0,
            'total_calls': 0,
            'total_time': 0.0
        }
    
    def calculate_iris_contour(self, iris_center: Tuple[float, float], 
                           eye_landmarks: List[Tuple[float, float]], 
                           original_iris_landmarks: List[Tuple[float, float]], 
                           img_width: int, img_height: int,
                           face_landmarks: Optional[List[Tuple[float, float]]] = None) -> List[Tuple[float, float]]:
        """눈동자 윤곽 재계산 (눈꺼풀 상호작용 포함)
        
        Args:
            iris_center: 이동된 눈동자 중심점 (x, y)
            eye_landmarks: 눈꺼풀 랜드마크 리스트 [(x, y), ...]
            original_iris_landmarks: 원본 눈동자 윤곽 랜드마크 리스트
            img_width: 이미지 너비
            img_height: 이미지 높이
            face_landmarks: 전체 얼굴 랜드마크 (눈꺼풀 상호작용용)
            
        Returns:
            list: 재계산된 눈동자 윤곽 랜드마크 리스트
        """
        # 성능 측정 시작
        start_time = time.time()
        
        # 성능 통계 속성이 없으면 초기화 (안전장치)
        if not hasattr(self, '_performance_stats'):
            self._performance_stats = {
                'cache_hits': 0,
                'cache_misses': 0,
                'total_calls': 0,
                'total_time': 0.0
            }
            self._iris_contour_cache = {}
            self._cache_max_size = 100
        
        self._performance_stats['total_calls'] += 1
        
        if not iris_center or not eye_landmarks or not original_iris_landmarks:
            return original_iris_landmarks
        
        # 눈동자-눈꺼풀 상호작용 파라미터 가져오기
        interaction_enabled = getattr(self, 'iris_eyelid_interaction', None)
        interaction_enabled_val = interaction_enabled.get() if interaction_enabled is not None else True
        adjustment_intensity = getattr(self, 'eyelid_adjustment_intensity', None)
        adjustment_intensity_val = adjustment_intensity.get() if adjustment_intensity is not None else 0.5
        detection_sensitivity = getattr(self, 'eyelid_detection_sensitivity', None)
        detection_sensitivity_val = detection_sensitivity.get() if detection_sensitivity is not None else 8.0
        
        # 캐시 키 생성 (입력값 기반 + 눈꺼풀 상호작용 파라미터)
        cache_key = (
            round(iris_center[0], 1), round(iris_center[1], 1),
            len(eye_landmarks), len(original_iris_landmarks),
            round(img_width, 0), round(img_height, 0),
            # 눈꺼풀 랜드마크 일부를 포함하여 더 정밀한 캐싱
            round(eye_landmarks[0][0] if eye_landmarks else 0, 1),
            round(eye_landmarks[0][1] if eye_landmarks else 0, 1),
            # 눈꺼풀 상호작용 파라미터 포함
            interaction_enabled_val,
            round(adjustment_intensity_val, 2),
            round(detection_sensitivity_val, 1)
        )
        
        # 캐시 확인
        if cache_key in self._iris_contour_cache:
            self._performance_stats['cache_hits'] += 1
            return self._iris_contour_cache[cache_key]
        
        self._performance_stats['cache_misses'] += 1
        
        # 캐시 크기 관리
        if len(self._iris_contour_cache) >= self._cache_max_size:
            # 가장 오래된 항목 제거 (간단한 LRU)
            oldest_key = next(iter(self._iris_contour_cache))
            del self._iris_contour_cache[oldest_key]
            
        # 원본 눈동자 중심점 계산
        original_center_x = sum(pt[0] if isinstance(pt, tuple) else pt.x * img_width for pt in original_iris_landmarks) / len(original_iris_landmarks)
        original_center_y = sum(pt[1] if isinstance(pt, tuple) else pt.y * img_height for pt in original_iris_landmarks) / len(original_iris_landmarks)
        
        # 이동량 계산
        offset_x = iris_center[0] - original_center_x
        offset_y = iris_center[1] - original_center_y
        
        # 이동량이 거의 없으면 원본 반환 (불필요한 재계산 방지)
        if abs(offset_x) < 0.1 and abs(offset_y) < 0.1:
            return original_iris_landmarks
        
        # 눈동자-눈꺼풀 상호작용 처리
        enhanced_iris_center = iris_center
        if interaction_enabled_val and face_landmarks:
            # 경계 근접 감지
            proximity_info = self.detect_eyelid_boundary_proximity(
                iris_center, face_landmarks, detection_sensitivity_val
            )
            
            if proximity_info['is_near_boundary']:
                # 눈동자 위치를 눈꺼풀 방향으로 더 확장
                direction = proximity_info['direction']
                distance = proximity_info['distance']
                closest_point = proximity_info['closest_point']
                
                # 조정량 계산 (거리가 가까울수록 더 많이 조정)
                adjustment_factor = max(0, 1 - (distance / detection_sensitivity_val))
                adjustment_factor *= adjustment_intensity_val * 0.6  # 최대 60%까지 조정 (극대화)
                
                # 방향별 눈동자 위치 확장
                if direction == 'up':
                    # 위쪽으로 더 이동
                    enhanced_iris_center = (
                        iris_center[0],
                        iris_center[1] - adjustment_factor * detection_sensitivity_val * 0.7
                    )
                elif direction == 'down':
                    # 아래쪽으로 더 이동
                    enhanced_iris_center = (
                        iris_center[0],
                        iris_center[1] + adjustment_factor * detection_sensitivity_val * 0.7
                    )
                elif direction == 'left':
                    # 왼쪽으로 더 이동
                    enhanced_iris_center = (
                        iris_center[0] - adjustment_factor * detection_sensitivity_val * 0.5,
                        iris_center[1]
                    )
                elif direction == 'right':
                    # 오른쪽으로 더 이동
                    enhanced_iris_center = (
                        iris_center[0] + adjustment_factor * detection_sensitivity_val * 0.5,
                        iris_center[1]
                    )
                
                # 새로운 중심점으로 이동량 재계산
                offset_x = enhanced_iris_center[0] - original_center_x
                offset_y = enhanced_iris_center[1] - original_center_y
        
        # 눈꺼풀 경계 계산
        eye_x_coords = [pt[0] if isinstance(pt, tuple) else pt.x * img_width for pt in eye_landmarks]
        eye_y_coords = [pt[1] if isinstance(pt, tuple) else pt.y * img_height for pt in eye_landmarks]
        
        if not eye_x_coords or not eye_y_coords:
            return original_iris_landmarks
            
        eye_min_x, eye_max_x = min(eye_x_coords), max(eye_x_coords)
        eye_min_y, eye_max_y = min(eye_y_coords), max(eye_y_coords)
        eye_center_x = (eye_min_x + eye_max_x) / 2
        eye_center_y = (eye_min_y + eye_max_y) / 2
        eye_width = eye_max_x - eye_min_x
        eye_height = eye_max_y - eye_min_y
        
        # 재계산된 눈동자 윤곽
        adjusted_landmarks = []
        
        for pt in original_iris_landmarks:
            if isinstance(pt, tuple):
                original_x, original_y = pt[0], pt[1]
            else:
                original_x = pt.x * img_width
                original_y = pt.y * img_height
                
            # 기본 이동 적용
            new_x = original_x + offset_x
            new_y = original_y + offset_y
            
            # 눈동자 형태 완전 유지 (상대적 위치 그대로 이동)
            # 원본 중심점으로부터의 상대적 위치를 그대로 유지
            rel_x = original_x - original_center_x
            rel_y = original_y - original_center_y
            
            # 새로운 중심점에 상대적 위치를 그대로 적용
            new_x = iris_center[0] + rel_x
            new_y = iris_center[1] + rel_y
            
            # 최종 좌표를 이미지 상대 좌표로 변환
            final_x = new_x / img_width
            final_y = new_y / img_height
            
            # 원본 포인트 타입 유지
            if isinstance(pt, tuple):
                adjusted_landmarks.append((final_x, final_y))
            else:
                adjusted_landmarks.append(type(pt)(x=final_x, y=final_y, z=pt.z, visibility=pt.visibility))
        
        # 결과를 캐시에 저장
        self._iris_contour_cache[cache_key] = adjusted_landmarks
        
        # 성능 측정 종료
        end_time = time.time()
        self._performance_stats['total_time'] += (end_time - start_time)
        
        return adjusted_landmarks
    
    def get_performance_stats(self):
        """성능 통계 정보 반환
        
        Returns:
            dict: 성능 통계 정보
        """
        stats = self._performance_stats.copy()
        if stats['total_calls'] > 0:
            stats['cache_hit_rate'] = stats['cache_hits'] / stats['total_calls'] * 100
            stats['avg_time_ms'] = (stats['total_time'] / stats['total_calls']) * 1000
        else:
            stats['cache_hit_rate'] = 0.0
            stats['avg_time_ms'] = 0.0
        return stats
    
    def clear_performance_stats(self):
        """성능 통계 초기화"""
        self._performance_stats = {
            'cache_hits': 0,
            'cache_misses': 0,
            'total_calls': 0,
            'total_time': 0.0
        }
    
    def calculate_iris_eyelid_distance(self, iris_center: Tuple[float, float], 
                                     eyelid_landmarks: List[Tuple[float, float]]) -> Tuple[float, Tuple[float, float]]:
        """눈동자 중심점과 눈꺼풀 랜드마크 간의 최소 거리 계산
        
        Args:
            iris_center: 눈동자 중심점 (x, y)
            eyelid_landmarks: 눈꺼풀 랜드마크 리스트 [(x, y), ...]
            
        Returns:
            tuple: (최소 거리, 가장 가까운 눈꺼풀 포인트)
        """
        if not iris_center or not eyelid_landmarks:
            return float('inf'), (0, 0)
        
        min_distance = float('inf')
        closest_point = (0, 0)
        
        for point in eyelid_landmarks:
            if point:
                distance = math.sqrt((iris_center[0] - point[0])**2 + (iris_center[1] - point[1])**2)
                if distance < min_distance:
                    min_distance = distance
                    closest_point = point
        
        return min_distance, closest_point
    
    def detect_eyelid_boundary_proximity(self, iris_center: Tuple[float, float],
                                      face_landmarks: List[Tuple[float, float]],
                                      sensitivity: float = 8.0) -> Dict[str, Any]:
        """눈동자가 눈꺼풀 경계에 근접했는지 감지 (상하좌우 전체 방향)
        
        Args:
            iris_center: 눈동자 중심점 (x, y)
            face_landmarks: 얼굴 랜드마크 (468개)
            sensitivity: 감지 민감도 (픽셀)
            
        Returns:
            dict: 감지 결과 정보
        """
        if not iris_center or not face_landmarks:
            return {
                'is_near_boundary': False,
                'direction': None,
                'distance': float('inf'),
                'closest_point': (0, 0),
                'eyelid_type': None,
                'is_left_eye': True
            }
        
        # 눈동자 x좌표로 왼쪽/오른쪽 눈 판단
        iris_x = iris_center[0]
        is_left_eye = iris_x < face_landmarks[0][0] if face_landmarks else True
        
        # 해당 눈의 눈꺼풀 랜드마크 선택
        if is_left_eye:
            upper_indices = LEFT_UPPER_EYELID_INDICES
            lower_indices = LEFT_LOWER_EYELID_INDICES
            # 좌우 눈꺼풀 인덱스 (왼쪽 눈 기준)
            left_indices = [33, 7, 163, 144]  # 왼쪽 눈꺼풀 (코 쪽)
            right_indices = [173, 157, 158, 159]  # 오른쪽 눈꺼풀 (귀 쪽)
        else:
            upper_indices = RIGHT_UPPER_EYELID_INDICES
            lower_indices = RIGHT_LOWER_EYELID_INDICES
            # 좌우 눈꺼풀 인덱스 (오른쪽 눈 기준)
            left_indices = [362, 398, 384, 385]  # 왼쪽 눈꺼풀 (코 쪽)
            right_indices = [263, 249, 390, 373]  # 오른쪽 눈꺼풀 (귀 쪽)
        
        # 상하좌우 눈꺼풀 거리 계산
        upper_landmarks = [face_landmarks[i] for i in upper_indices if i < len(face_landmarks)]
        lower_landmarks = [face_landmarks[i] for i in lower_indices if i < len(face_landmarks)]
        left_landmarks = [face_landmarks[i] for i in left_indices if i < len(face_landmarks)]
        right_landmarks = [face_landmarks[i] for i in right_indices if i < len(face_landmarks)]
        
        upper_dist, upper_point = self.calculate_iris_eyelid_distance(iris_center, upper_landmarks)
        lower_dist, lower_point = self.calculate_iris_eyelid_distance(iris_center, lower_landmarks)
        left_dist, left_point = self.calculate_iris_eyelid_distance(iris_center, left_landmarks)
        right_dist, right_point = self.calculate_iris_eyelid_distance(iris_center, right_landmarks)
        
        # 가장 가까운 방향 결정
        distances = [
            ('up', upper_dist, upper_point, 'upper'),
            ('down', lower_dist, lower_point, 'lower'),
            ('left', left_dist, left_point, 'left'),
            ('right', right_dist, right_point, 'right')
        ]
        
        min_distance = float('inf')
        closest_point = (0, 0)
        direction = None
        eyelid_type = None
        
        for dir_name, dist, point, eyelid in distances:
            if dist < min_distance:
                min_distance = dist
                closest_point = point
                direction = dir_name
                eyelid_type = eyelid
        
        # 경계 근접 여부 판단
        is_near_boundary = min_distance < sensitivity
        
        return {
            'is_near_boundary': is_near_boundary,
            'direction': direction,
            'distance': min_distance,
            'closest_point': closest_point,
            'eyelid_type': eyelid_type,
            'is_left_eye': is_left_eye
        }
    
    def adjust_eyelid_landmarks(self, face_landmarks: List[Tuple[float, float]], 
                               proximity_info: Dict[str, Any], 
                               intensity: float = 0.5) -> List[Tuple[float, float]]:
        """눈꺼풀 랜드마크를 실시간으로 직접 변형
        
        Args:
            face_landmarks: 원본 얼굴 랜드마크 (468개)
            proximity_info: 경계 근접 정보
            intensity: 조정 강도
            
        Returns:
            list: 변형된 얼굴 랜드마크
        """
        if not proximity_info['is_near_boundary'] or not face_landmarks:
            return face_landmarks
        
        # 랜드마크 복사본 생성
        adjusted_landmarks = list(face_landmarks)
        
        direction = proximity_info['direction']
        is_left_eye = proximity_info['is_left_eye']
        distance = proximity_info['distance']
        
        # 조정량 계산
        adjustment_factor = max(0, 1 - (distance / 8.0))  # 기본 민감도 8.0
        adjustment_factor *= intensity * 0.3  # 최대 30%까지 랜드마크 변형
        
        # 방향별 눈꺼풀 랜드마크 선택 및 변형
        if direction == 'up':
            # 상안견을 위로 미세하게 당기기
            indices = LEFT_UPPER_EYELID_INDICES if is_left_eye else RIGHT_UPPER_EYELID_INDICES
            for idx in indices:
                if idx < len(adjusted_landmarks):
                    x, y = adjusted_landmarks[idx]
                    adjusted_landmarks[idx] = (x, y - adjustment_factor * 2.0)
                    
        elif direction == 'down':
            # 하안견을 아래로 미세하게 당기기
            indices = LEFT_LOWER_EYELID_INDICES if is_left_eye else RIGHT_LOWER_EYELID_INDICES
            for idx in indices:
                if idx < len(adjusted_landmarks):
                    x, y = adjusted_landmarks[idx]
                    adjusted_landmarks[idx] = (x, y + adjustment_factor * 2.0)
                    
        elif direction == 'left':
            # 왼쪽 눈꺼풀을 왼쪽으로 미세하게 당기기
            if is_left_eye:
                indices = [33, 7, 163, 144]  # 왼쪽 눈의 왼쪽
            else:
                indices = [362, 398, 384, 385]  # 오른쪽 눈의 왼쪽
            for idx in indices:
                if idx < len(adjusted_landmarks):
                    x, y = adjusted_landmarks[idx]
                    adjusted_landmarks[idx] = (x - adjustment_factor * 1.5, y)
                    
        elif direction == 'right':
            # 오른쪽 눈꺼풀을 오른쪽으로 미세하게 당기기
            if is_left_eye:
                indices = [173, 157, 158, 159]  # 왼쪽 눈의 오른쪽
            else:
                indices = [263, 249, 390, 373]  # 오른쪽 눈의 오른쪽
            for idx in indices:
                if idx < len(adjusted_landmarks):
                    x, y = adjusted_landmarks[idx]
                    adjusted_landmarks[idx] = (x + adjustment_factor * 1.5, y)
        
        return adjusted_landmarks
    
    def _draw_iris_connection_polygons(self, canvas, iris_side: str, center_x: float, center_y: float,
                                     iris_coords: List[Tuple[float, float]], img_width: int, img_height: int,
                                     scale_x: float, scale_y: float, pos_x: float, pos_y: float, items_list: List):
        """눈동자 중심점과 연결된 폴리곤 그리기
        
        Args:
            canvas: 캔버스 객체
            iris_side: 'left' 또는 'right'
            center_x, center_y: 눈동자 중심점 좌표
            iris_coords: 눈동자 윤곽 좌표 리스트
            img_width, img_height: 이미지 크기
            scale_x, scale_y: 스케일
            pos_x, pos_y: 위치
            items_list: 아이템 리스트
        """
        if not iris_coords:
            return
        
        # 중심점 캔버스 좌표 계산
        center_rel_x = (center_x - img_width / 2) * scale_x
        center_rel_y = (center_y - img_height / 2) * scale_y
        center_canvas_x = pos_x + center_rel_x
        center_canvas_y = pos_y + center_rel_y
        
        # 연결선 스타일 설정
        connection_color = "#FF6B6B" if iris_side == 'left' else "#4ECDC4"
        connection_width = 2
        
        # 눈동자 윤곽점과 중심점 연결
        for i, (iris_x, iris_y) in enumerate(iris_coords):
            # 눈동자 윤곽점 캔버스 좌표 계산
            iris_rel_x = (iris_x - img_width / 2) * scale_x
            iris_rel_y = (iris_y - img_height / 2) * scale_y
            iris_canvas_x = pos_x + iris_rel_x
            iris_canvas_y = pos_y + iris_rel_y
            
            # 연결선 그리기
            line_id = canvas.create_line(
                center_canvas_x, center_canvas_y,
                iris_canvas_x, iris_canvas_y,
                fill=connection_color,
                width=connection_width,
                dash=(5, 3),  # 점선 스타일
                tags=("iris_connections", f"iris_connection_{iris_side}_{i}")
            )
            items_list.append(line_id)
        
        # 외곽선 4개 점을 연결하는 선만 그리기
        if len(iris_coords) >= 4:
            import math
            
            # 중심점 찾기 (가장 중앙에 있는 점)
            center_x_avg = sum(coord[0] for coord in iris_coords) / len(iris_coords)
            center_y_avg = sum(coord[1] for coord in iris_coords) / len(iris_coords)
            
            # 중심점에서 가장 가까운 점을 중심점으로 간주하고 제외
            def distance_from_center(coord):
                return math.sqrt((coord[0] - center_x_avg)**2 + (coord[1] - center_y_avg)**2)
            
            # 거리순으로 정렬하여 가장 가까운 점(중심점)을 찾음
            sorted_by_distance = sorted(iris_coords, key=distance_from_center)
            center_point = sorted_by_distance[0]  # 중심점
            
            # 중심점을 제외한 외곽선 점들
            outer_points = [coord for coord in iris_coords if coord != center_point]
            
            # 외곽점을 각도순으로 정렬
            def angle_from_point(coord):
                return -math.atan2(coord[1] - center_y, coord[0] - center_x)  # 시계 반대 방향
            
            sorted_outer_points = sorted(outer_points, key=angle_from_point)
            
            # 외곽선 4개 점을 연결하는 선 그리기
            canvas_points = []
            for coord in sorted_outer_points[:4]:  # 외곽선 4개 점만 사용
                rel_x = (coord[0] - img_width / 2) * scale_x
                rel_y = (coord[1] - img_height / 2) * scale_y
                canvas_pt = (pos_x + rel_x, pos_y + rel_y)
                canvas_points.extend(canvas_pt)
            
            # 색상 설정 (왼쪽: 붉은색 계열, 오른쪽: 청록색 계열)
            line_color = "#FF6B6B" if iris_side == 'left' else "#4ECDC4"  # 더 진한 색상
            
            # 외곽선 4개 점을 순서대로 연결하는 선들 그리기
            for i in range(len(canvas_points) // 2):
                start_idx = i * 2
                end_idx = ((i + 1) * 2) % len(canvas_points)
                
                line_id = canvas.create_line(
                    canvas_points[start_idx], canvas_points[start_idx + 1],
                    canvas_points[end_idx], canvas_points[end_idx + 1],
                    fill=line_color,
                    width=3,
                    tags=("iris_connections", f"iris_outline_{iris_side}")
                )
                items_list.append(line_id)
            
            print(f"Drawn {len(canvas_points)//2} outer points with connecting lines for {iris_side}")
        else:
            print(f"Not enough iris coords for {iris_side}: {len(iris_coords)} < 4")
    
    def _draw_all_tab_polygons(self, canvas, image, landmarks, pos_x, pos_y, items_list, color, scale_x, scale_y, img_width, img_height, expansion_level, show_indices, bind_polygon_click_events, force_use_custom=False, iris_landmarks=None, iris_centers=None, clamping_enabled=True, margin_ratio=0.3):
        """all 탭 폴리곤 그리기
        
        Args:
            iris_landmarks: 눈동자 랜드마크 (10개 또는 None)
            iris_centers: 눈동자 중앙 포인트 (2개 또는 None, Tesselation용)
            clamping_enabled: 눈동자 이동 범위 제한 활성화 여부
            margin_ratio: 눈동자 이동 범위 제한 마진 비율 (0.0 ~ 1.0)
        """
        # 현재 탭에 따라 해당 부위의 모든 랜드마크 인덱스 수집
        target_indices = []

        # 전체 탭: 선택된 부위가 있으면 선택된 부위만, 없으면 모든 부위의 폴리곤 그리기
        try:
            import mediapipe as mp
            mp_face_mesh = mp.solutions.face_mesh
            LEFT_EYE = list(mp_face_mesh.FACEMESH_LEFT_EYE)
            RIGHT_EYE = list(mp_face_mesh.FACEMESH_RIGHT_EYE)
            LEFT_EYEBROW = list(mp_face_mesh.FACEMESH_LEFT_EYEBROW)
            RIGHT_EYEBROW = list(mp_face_mesh.FACEMESH_RIGHT_EYEBROW)
            NOSE = list(mp_face_mesh.FACEMESH_NOSE)
            LIPS = list(mp_face_mesh.FACEMESH_LIPS)
            FACE_OVAL = list(mp_face_mesh.FACEMESH_FACE_OVAL)
            CONTOURS = list(mp_face_mesh.FACEMESH_CONTOURS)
            TESSELATION = list(mp_face_mesh.FACEMESH_TESSELATION)

            # 선택된 부위 확인
            selected_regions = []
            if hasattr(self, 'show_face_oval') and self.show_face_oval.get():
                selected_regions.append(('face_oval', FACE_OVAL))
            if hasattr(self, 'show_left_eye') and self.show_left_eye.get():
                selected_regions.append(('left_eye', LEFT_EYE))
            if hasattr(self, 'show_right_eye') and self.show_right_eye.get():
                selected_regions.append(('right_eye', RIGHT_EYE))
            if hasattr(self, 'show_left_eyebrow') and self.show_left_eyebrow.get():
                selected_regions.append(('left_eyebrow', LEFT_EYEBROW))
            if hasattr(self, 'show_right_eyebrow') and self.show_right_eyebrow.get():
                selected_regions.append(('right_eyebrow', RIGHT_EYEBROW))
            if hasattr(self, 'show_nose') and self.show_nose.get():
                selected_regions.append(('nose', NOSE))
            # Lips를 하나로 통합
            if hasattr(self, 'show_lips') and self.show_lips.get():
                selected_regions.append(('lips', LIPS))
            if hasattr(self, 'show_contours') and self.show_contours.get():
                selected_regions.append(('contours', CONTOURS))
            if hasattr(self, 'show_tesselation') and self.show_tesselation.get():
                selected_regions.append(('tesselation', TESSELATION))
            # 눈동자 연결 정보 (refine_landmarks=True일 때 사용 가능)
            try:
                LEFT_IRIS = list(mp_face_mesh.FACEMESH_LEFT_IRIS)
                RIGHT_IRIS = list(mp_face_mesh.FACEMESH_RIGHT_IRIS)
                print(f"MediaPipe LEFT_IRIS: {len(LEFT_IRIS)} connections")
                print(f"MediaPipe RIGHT_IRIS: {len(RIGHT_IRIS)} connections")
            except AttributeError:
                # 구버전 MediaPipe에서는 지원하지 않을 수 있음
                print("MediaPipe LEFT_IRIS/RIGHT_IRIS not available, using fallback")
                # 수동으로 눈동자 연결 정의 (사각형)
                LEFT_IRIS = [(0,1), (1,2), (2,3), (3,0)]
                RIGHT_IRIS = [(0,1), (1,2), (2,3), (3,0)]

            # 모든 부위의 폴리곤 그리기 함수
            def draw_polygon_mesh(connections, tag_name, part_name, target_indices=None):
                """연결 정보를 사용해서 폴리곤 메쉬 그리기"""
                # 연결 정보에서 모든 포인트 인덱스 수집
                polygon_indices_set = set()
                for idx1, idx2 in connections:
                    if idx1 < len(landmarks) and idx2 < len(landmarks):
                        polygon_indices_set.add(idx1)
                        polygon_indices_set.add(idx2)

                # 확장 레벨에 따라 주변 포인트 추가
                if expansion_level > 0:
                    try:
                        import mediapipe as mp
                        mp_face_mesh = mp.solutions.face_mesh
                        tesselation = list(mp_face_mesh.FACEMESH_TESSELATION)

                        # TESSELATION 그래프 구성
                        tesselation_graph = {}
                        for idx1, idx2 in tesselation:
                            if idx1 < len(landmarks) and idx2 < len(landmarks):
                                if idx1 not in tesselation_graph:
                                    tesselation_graph[idx1] = []
                                if idx2 not in tesselation_graph:
                                    tesselation_graph[idx2] = []
                                tesselation_graph[idx1].append(idx2)
                                tesselation_graph[idx2].append(idx1)

                        # 확장 레벨만큼 이웃 포인트 추가
                        current_indices = polygon_indices_set.copy()
                        for level in range(expansion_level):
                            next_level_indices = set()
                            for idx in current_indices:
                                if idx in tesselation_graph:
                                    for neighbor in tesselation_graph[idx]:
                                        if neighbor < len(landmarks):
                                            next_level_indices.add(neighbor)
                            polygon_indices_set.update(next_level_indices)
                            current_indices = next_level_indices
                    except ImportError:
                        pass

                # 폴리곤에 포함된 포인트 인덱스를 polygon_point_map에 저장
                polygon_indices = list(polygon_indices_set)
                canvas_type = 'original' if canvas == self.canvas_original else 'edited'
                point_map = self.polygon_point_map_original if canvas_type == 'original' else self.polygon_point_map_edited
                for idx in polygon_indices:
                    if idx < len(landmarks):
                        point_map.add(idx)

                # 인덱스 표시 (폴리곤에 포함된 포인트들)
                if show_indices:
                    for idx in polygon_indices:
                        if idx < len(landmarks):
                            # 랜드마크 좌표 가져오기
                            pt = landmarks[idx]
                            if isinstance(pt, tuple):
                                img_x, img_y = pt
                            else:
                                img_x = pt.x * img_width
                                img_y = pt.y * img_height

                            # 캔버스 좌표로 변환
                            rel_x = (img_x - img_width / 2) * scale_x
                            rel_y = (img_y - img_height / 2) * scale_y
                            canvas_x = pos_x + rel_x
                            canvas_y = pos_y + rel_y

                            # 인덱스 번호 표시
                            text_offset = 10  # 포인트에서 약간 떨어진 위치
                            text_id = canvas.create_text(
                                canvas_x + text_offset,
                                canvas_y - text_offset,
                                text=str(idx),
                                fill=color,
                                font=("Arial", 12, "bold"),  # 글자 크기 8 -> 12로 증가
                                tags=("landmarks_polygon", f"landmark_text_{idx}", tag_name)
                            )
                            items_list.append(text_id)
                            # 텍스트를 최상위로 올림
                            try:
                                canvas.tag_raise(text_id, "landmarks_polygon")
                                canvas.tag_raise(text_id)
                            except Exception:
                                pass

                # 확장 레벨 0일 때는 연결선으로 그리기 (폴리곤 대신)
                if expansion_level == 0:
                    # 연결선 그리기
                    for idx1, idx2 in connections:
                        if idx1 < len(landmarks) and idx2 < len(landmarks):
                            # 랜드마크 좌표 가져오기
                            pt1 = landmarks[idx1]
                            pt2 = landmarks[idx2]

                            if isinstance(pt1, tuple):
                                img_x1, img_y1 = pt1
                            else:
                                img_x1 = pt1.x * img_width
                                img_y1 = pt1.y * img_height

                            if isinstance(pt2, tuple):
                                img_x2, img_y2 = pt2
                            else:
                                img_x2 = pt2.x * img_width
                                img_y2 = pt2.y * img_height

                            # 캔버스 좌표로 변환
                            rel_x1 = (img_x1 - img_width / 2) * scale_x
                            rel_y1 = (img_y1 - img_height / 2) * scale_y
                            rel_x2 = (img_x2 - img_width / 2) * scale_x
                            rel_y2 = (img_y2 - img_height / 2) * scale_y

                            canvas_x1 = pos_x + rel_x1
                            canvas_y1 = pos_y + rel_y1
                            canvas_x2 = pos_x + rel_x2
                            canvas_y2 = pos_y + rel_y2

                            line_id = canvas.create_line(
                                canvas_x1, canvas_y1, canvas_x2, canvas_y2,
                                fill=color, width=2, tags=("landmarks_polygon", tag_name)
                            )
                            items_list.append(line_id)
                            # 연결선에도 클릭 이벤트 바인딩 (폴리곤과 동일하게)
                            bind_polygon_click_events(line_id, target_indices)
                else:
                    # 확장 레벨 > 0일 때는 폴리곤으로 그리기
                    points = self._get_polygon_from_indices(
                        [], landmarks, img_width, img_height, scale_x, scale_y, pos_x, pos_y,
                        use_mediapipe_connections=True, connections=connections, expansion_level=expansion_level
                    )
                    if points and len(points) >= 3:
                        if len(points) % 4 == 0:
                            # 삼각형 메쉬
                            triangle_count = 0
                            for i in range(0, len(points), 4):
                                if i + 4 <= len(points):
                                    triangle_points = points[i:i+4]
                                    polygon_id = canvas.create_polygon(
                                        triangle_points,
                                        fill="",
                                        outline=color,
                                        width=1,
                                        tags=("landmarks_polygon", tag_name)
                                    )
                                    items_list.append(polygon_id)
                                    # 폴리곤 클릭 이벤트 바인딩
                                    bind_polygon_click_events(polygon_id, target_indices)
                                    triangle_count += 1
                        else:
                            # 단일 폴리곤 (폴백)
                            polygon_id = canvas.create_polygon(
                                points,
                                fill="",
                                outline=color,
                                width=2,
                                tags=("landmarks_polygon", tag_name)
                            )
                            items_list.append(polygon_id)
                            # 폴리곤 클릭 이벤트 바인딩
                            bind_polygon_click_events(polygon_id, target_indices)

            # 각 부위의 랜드마크 인덱스 수집
            left_eye_indices = set()
            right_eye_indices = set()
            left_eyebrow_indices = set()
            right_eyebrow_indices = set()
            nose_indices = set()
            lips_indices = set()
            face_oval_indices = set()

            for idx1, idx2 in LEFT_EYE:
                left_eye_indices.add(idx1)
                left_eye_indices.add(idx2)
            for idx1, idx2 in RIGHT_EYE:
                right_eye_indices.add(idx1)
                right_eye_indices.add(idx2)
            for idx1, idx2 in LEFT_EYEBROW:
                left_eyebrow_indices.add(idx1)
                left_eyebrow_indices.add(idx2)
            for idx1, idx2 in RIGHT_EYEBROW:
                right_eyebrow_indices.add(idx1)
                right_eyebrow_indices.add(idx2)
            for idx1, idx2 in NOSE:
                nose_indices.add(idx1)
                nose_indices.add(idx2)
            for idx1, idx2 in LIPS:
                lips_indices.add(idx1)
                lips_indices.add(idx2)
            for idx1, idx2 in FACE_OVAL:
                face_oval_indices.add(idx1)
                face_oval_indices.add(idx2)

            # 눈동자 그리기 함수 정의
            def draw_iris(iris_side, iris_connections, iris_center_coord_attr):
                """눈동자 그리기 (왼쪽 또는 오른쪽)
                
                Args:
                    iris_side: 'left' 또는 'right'
                    iris_connections: 눈동자 연결 정보
                    iris_center_coord_attr: 중앙 포인트 좌표 속성명
                """
                # iris_landmarks 또는 iris_centers 파라미터로 명확히 구분
                has_iris_landmarks = (iris_landmarks is not None and len(iris_landmarks) > 0)
                has_iris_centers = (iris_centers is not None and len(iris_centers) == 2)
                
                # Tesselation 모드에서는 iris_connections가 없어도 중심점은 그려야 함
                # iris_centers가 있으면 iris_connections가 없어도 중심점을 그릴 수 있음
                if not iris_connections and not has_iris_centers and not has_iris_landmarks:
                    # iris_connections도 없고, iris_centers도 없고, iris_landmarks도 없으면 그릴 수 없음
                    return
                
                # MediaPipe의 실제 인덱스 추출 (iris_landmarks가 있는 경우)
                iris_indices_set = set()
                if has_iris_landmarks:
                    for idx1, idx2 in iris_connections:
                        # iris_landmarks는 별도로 관리되므로 인덱스는 0부터 시작
                        if idx1 < len(iris_landmarks) and idx2 < len(iris_landmarks):
                            iris_indices_set.add(idx1)
                            iris_indices_set.add(idx2)
                
                # 폴리곤 그리기 (iris_landmarks가 있을 때만)
                if has_iris_landmarks:
                    # 눈동자 중심점 가져오기
                    current_iris_center_coord = None
                    if iris_centers is not None and len(iris_centers) == 2: # iris_centers는 UI 기준 (왼쪽이 [1], 오른쪽이 [0])
                        if iris_side == 'left':
                            current_iris_center_coord = iris_centers[1]
                        else:
                            current_iris_center_coord = iris_centers[0]
                    elif hasattr(self, f'_{iris_side}_iris_center_coord'):
                        current_iris_center_coord = getattr(self, f'_{iris_side}_iris_center_coord')

                    # 눈꺼풀 랜드마크 가져오기
                    eye_landmarks = None
                    if iris_side == 'left':
                        # FACEMESH_LEFT_EYE는 [(idx1, idx2), ...] 형태이므로 평탄화
                        left_eye_indices = set()
                        for idx1, idx2 in LEFT_EYE:
                            left_eye_indices.add(idx1)
                            left_eye_indices.add(idx2)
                        eye_landmarks = [landmarks[i] for i in left_eye_indices if i < len(landmarks)]
                    else:
                        # FACEMESH_RIGHT_EYE는 [(idx1, idx2), ...] 형태이므로 평탄화
                        right_eye_indices = set()
                        for idx1, idx2 in RIGHT_EYE:
                            right_eye_indices.add(idx1)
                            right_eye_indices.add(idx2)
                        eye_landmarks = [landmarks[i] for i in right_eye_indices if i < len(landmarks)]

                    # 원본 눈동자 윤곽 랜드마크 추출
                    original_iris_landmarks = []
                    iris_connections_indices = set()
                    for idx1, idx2 in iris_connections:
                        iris_connections_indices.add(idx1)
                        iris_connections_indices.add(idx2)
                    
                    for idx in sorted(iris_connections_indices):
                        if idx < len(landmarks):
                            original_iris_landmarks.append(landmarks[idx])

                    # 눈동자 윤곽 재계산
                    if current_iris_center_coord and eye_landmarks and original_iris_landmarks:
                        adjusted_landmarks_iris = self.calculate_iris_contour(
                            current_iris_center_coord, eye_landmarks, original_iris_landmarks, img_width, img_height, landmarks
                        )
                    else:
                        adjusted_landmarks_iris = landmarks

                    iris_points = self._get_polygon_from_indices(
                        [], adjusted_landmarks_iris, img_width, img_height, scale_x, scale_y, pos_x, pos_y,
                        use_mediapipe_connections=True, connections=iris_connections, expansion_level=0
                    )
                    if iris_points and len(iris_points) >= 3:
                        polygon_id = canvas.create_polygon(
                            iris_points,
                            fill="",
                            outline=color,
                            width=2,
                            tags=("landmarks_polygon", f"polygon_{iris_side}_iris")
                        )
                        items_list.append(polygon_id)
                        bind_polygon_click_events(polygon_id, None)
                
                # 중앙 포인트 표시
                iris_indices_list = list(iris_indices_set)
                iris_coords = []
                for idx in iris_indices_list:
                    if idx < len(landmarks):
                        pt = landmarks[idx]
                        if isinstance(pt, tuple):
                            img_x, img_y = pt
                        else:
                            img_x = pt.x * img_width
                            img_y = pt.y * img_height
                        iris_coords.append((img_x, img_y))
                
                # 중앙 포인트 좌표 계산
                center_x = None
                center_y = None
                
                if iris_side == 'left':
                    center_idx_offset = 2  # len-2
                else:
                    center_idx_offset = 1  # len-1

                len_landmarks = len(landmarks)
                # iris_centers 파라미터가 전달된 경우 우선 사용
                # UI 라벨 "Left"/"Right"와 실제 눈 매핑
                if iris_centers is not None and len(iris_centers) == 2:
                    if iris_side == 'left':
                        center_pt = iris_centers[1]  # UI Left → landmarks[469]
                    else:
                        center_pt = iris_centers[0]  # UI Right → landmarks[468]
                    if isinstance(center_pt, tuple):
                        center_x, center_y = center_pt
                    else:
                        center_x = center_pt.x * img_width
                        center_y = center_pt.y * img_height
                    
                    setattr(self, iris_center_coord_attr, (center_x, center_y))
                # Tesselation 모드: custom_landmarks에서 중앙 포인트 추출 (470개 구조만)
                elif len_landmarks == 470:
                    center_idx = len_landmarks - center_idx_offset
                    if center_idx >= 0 and center_idx < len_landmarks:
                        center_pt = landmarks[center_idx]
                        if isinstance(center_pt, tuple):
                            center_x, center_y = center_pt
                        else:
                            center_x = center_pt.x * img_width
                            center_y = center_pt.y * img_height
                        setattr(self, iris_center_coord_attr, (center_x, center_y))
                # 468개는 얼굴 랜드마크만 있으므로 저장된 좌표 사용
                elif hasattr(self, iris_center_coord_attr) and getattr(self, iris_center_coord_attr) is not None:
                    center_x, center_y = getattr(self, iris_center_coord_attr)
                elif hasattr(self, '_get_iris_indices') and hasattr(self, '_calculate_iris_center'):
                    original = self.landmark_manager.get_original_landmarks()
                    
                    if original is not None:
                        left_iris_indices, right_iris_indices = self._get_iris_indices()
                        if iris_side == 'left':
                            center = self._calculate_iris_center(original, left_iris_indices, img_width, img_height)
                        else:
                            center = self._calculate_iris_center(original, right_iris_indices, img_width, img_height)
                        if center is not None:
                            center_x, center_y = center
                            setattr(self, iris_center_coord_attr, center)
                else:
                    if iris_coords:
                        center_x = sum(c[0] for c in iris_coords) / len(iris_coords)
                        center_y = sum(c[1] for c in iris_coords) / len(iris_coords)
                
                if center_x is not None and center_y is not None:
                    rel_x = (center_x - img_width / 2) * scale_x
                    rel_y = (center_y - img_height / 2) * scale_y
                    canvas_x = pos_x + rel_x
                    canvas_y = pos_y + rel_y

                    scale_factor = 1.0 # default
                    scale_factor = math.sqrt(scale_x*scale_y)/3
                                        
                    center_radius = 8 * scale_factor
                    
                    # 고유한 ID 생성
                    unique_id = f"{iris_side}_{int(time.time() * 1000)}"
                    
                    # 중심점 생성
                    center_id = canvas.create_oval(
                        canvas_x - center_radius,
                        canvas_y - center_radius,
                        canvas_x + center_radius,
                        canvas_y + center_radius,
                        fill="yellow",
                        outline="red",
                        width=2,
                        tags=("landmarks_polygon", f"iris_center_{unique_id}")
                    )
                    items_list.append(center_id)
                    
                    print(f"Created center point for {iris_side} with ID: {center_id}")
                    
                    if show_indices:
                        text_offset = center_radius + 5
                        if len(landmarks) >= 2:
                            center_idx = len(landmarks) - center_idx_offset
                            index_text = str(center_idx)
                        else:
                            index_text = f"C-{'L' if iris_side == 'left' else 'R'}"
                        text_id = canvas.create_text(
                            canvas_x + text_offset,
                            canvas_y - text_offset,
                            text=index_text,
                            fill="red",
                            font=("Arial", 12, "bold"),
                            tags=("landmarks_polygon", f"iris_center_{unique_id}_text", f"iris_center_{unique_id}")
                        )
                        items_list.append(text_id)
                    
                    def on_iris_center_click(event):
                        print(f"Clicked {iris_side} iris center!")
                        self.on_iris_center_drag_start(event, iris_side, canvas)
                        return "break"
                    
                    def on_iris_center_drag(event):
                        self.on_iris_center_drag(event, iris_side, canvas)
                        return "break"
                    
                    def on_iris_center_release(event):
                        self.on_iris_center_drag_end(event, iris_side, canvas)
                        return "break"
                    
                    # 기존 바인딩 제거 후 새로 바인딩
                    canvas.tag_unbind(center_id, "<Button-1>")
                    canvas.tag_unbind(center_id, "<B1-Motion>")
                    canvas.tag_unbind(center_id, "<ButtonRelease-1>")
                    
                    canvas.tag_bind(center_id, "<Button-1>", on_iris_center_click)
                    canvas.tag_bind(center_id, "<B1-Motion>", on_iris_center_drag)
                    canvas.tag_bind(center_id, "<ButtonRelease-1>", on_iris_center_release)
                    
                    print(f"Bound events to {iris_side} center point (ID: {center_id})")
                    
                    # 눈동자 중심점과 연결된 폴리곤 그리기
                    if hasattr(self, 'show_iris_connections') and self.show_iris_connections.get():
                        print(f"Checking iris connections for {iris_side}")
                        print(f"has_iris_landmarks: {has_iris_landmarks}")
                        print(f"iris_landmarks: {iris_landmarks}")
                        print(f"current iris_coords length: {len(iris_coords)}")
                        
                        # 눈동자 윤곽 좌표가 없으면 현재 랜드마크에서 추출
                        if not iris_coords and has_iris_landmarks:
                            print(f"Extracting iris coords from landmarks for {iris_side}")
                            print(f"iris_connections: {iris_connections}")
                            print(f"landmarks length: {len(landmarks)}")
                            
                            # iris_landmarks에서 직접 윤곽점 추출 (landmarks 배열이 아님)
                            # iris_landmarks는 별도의 10개 좌표 배열
                            if iris_landmarks:
                                # 눈동자 좌표 구조 확인
                                print(f"iris_landmarks structure: {iris_landmarks}")
                                
                                # 고정 분리: 처음 5개 = 오른쪽, 마지막 5개 = 왼쪽
                                # MediaPipe 순서가 [오른쪽 눈동자 5개, 왼쪽 눈동자 5개]인 것으로 보임
                                left_coords = iris_landmarks[5:]  # 마지막 5개 = 왼쪽
                                right_coords = iris_landmarks[:5]  # 처음 5개 = 오른쪽
                                
                                print(f"Index-based split - Left coords ({len(left_coords)}): {left_coords}")
                                print(f"Index-based split - Right coords ({len(right_coords)}): {right_coords}")
                                
                                # 해당 눈의 좌표 선택
                                if iris_side == 'left':
                                    iris_coords = left_coords
                                else:
                                    iris_coords = right_coords
                                
                                print(f"Final selected {len(iris_coords)} coords for {iris_side}: {iris_coords}")
                            else:
                                print("No iris_landmarks available")
                        
                        # 디버깅 출력
                        print(f"Final iris_coords for {iris_side}: {len(iris_coords)} points")
                        if iris_coords:
                            print(f"First few coords: {iris_coords[:3]}")
                            # 중심점을 먼저 그린 후 연결 폴리곤을 그리면 중심점이 위로 올라감
                            # 따라서 연결 폴리곤을 먼저 그리고 중심점을 나중에 그려야 함
                            # 하지만 이미 중심점을 그렸으므로, 태그 순서를 조정하여 중심점이 위로 오게 함
                            self._draw_iris_connection_polygons(canvas, iris_side, center_x, center_y, 
                                                              iris_coords, img_width, img_height, 
                                                              scale_x, scale_y, pos_x, pos_y, items_list)
                            
                            # 중심점을 최상위로 올리기
                            canvas.tag_raise(center_id)
                            if show_indices:
                                canvas.tag_raise(f"iris_center_{unique_id}_text")
                        else:
                            print(f"No iris coordinates found for {iris_side}")

            # 선택된 부위만 폴리곤 그리기
            if len(selected_regions) > 0:
                # 선택된 부위만 그리기
                for region_name, connections in selected_regions:
                    if region_name == 'left_eye':
                        draw_polygon_mesh(LEFT_EYE, "polygon_left_eye", "왼쪽 눈", None)
                    elif region_name == 'right_eye':
                        draw_polygon_mesh(RIGHT_EYE, "polygon_right_eye", "오른쪽 눈", None)
                    elif region_name == 'left_eyebrow':
                        draw_polygon_mesh(LEFT_EYEBROW, "polygon_left_eyebrow", "왼쪽 눈썹", None)
                    elif region_name == 'right_eyebrow':
                        draw_polygon_mesh(RIGHT_EYEBROW, "polygon_right_eyebrow", "오른쪽 눈썹", None)
                    elif region_name == 'nose':
                        draw_polygon_mesh(NOSE, "polygon_nose", "코", None)
                    elif region_name == 'lips':
                        draw_polygon_mesh(LIPS, "polygon_lips", "Lips", None)
                    elif region_name == 'face_oval':
                        draw_polygon_mesh(FACE_OVAL, "polygon_face_oval", "Face Oval", None)
                    elif region_name == 'contours':
                        draw_polygon_mesh(CONTOURS, "polygon_contours", "Contours", None)
                    elif region_name == 'tesselation':
                        draw_polygon_mesh(TESSELATION, "polygon_tesselation", "Tesselation", None)
                        # Tesselation 선택 시 눈동자 중심점 항상 그리기
                        # iris_centers가 없으면 LandmarkManager나 custom_landmarks에서 가져오기
                        iris_centers_for_draw = iris_centers
                        if iris_centers_for_draw is None:
                            iris_centers_for_draw = self.landmark_manager.get_custom_iris_centers()
                            if iris_centers_for_draw is None and len(landmarks) == 470:
                                # custom_landmarks에서 중앙 포인트 추출 (마지막 2개)
                                iris_centers_for_draw = landmarks[-2:]
                        
                        # iris_centers 변수 업데이트 (draw_iris 함수에서 사용)
                        if iris_centers_for_draw is not None:
                            iris_centers = iris_centers_for_draw
                        
                        # Tesselation 모드에서는 항상 눈동자 중심점 그리기
                        # iris_centers가 있으면 LEFT_IRIS/RIGHT_IRIS가 없어도 중심점을 그릴 수 있음
                        draw_iris('left', LEFT_IRIS if LEFT_IRIS else [], '_left_iris_center_coord')
                        draw_iris('right', RIGHT_IRIS if RIGHT_IRIS else [], '_right_iris_center_coord')
            
            # 눈동자 체크박스가 선택되었을 때 그리기
            # Tesselation 모드에서도 iris 체크박스 선택 시 중심점을 그려야 함
            # iris_centers가 없으면 다시 계산
            if iris_centers is None:
                iris_centers = self.landmark_manager.get_custom_iris_centers()
                if iris_centers is None and len(landmarks) == 470:
                    # custom_landmarks에서 중앙 포인트 추출 (마지막 2개)
                    # landmarks[468] = LEFT_EYE_INDICES에서 계산된 중심
                    # landmarks[469] = RIGHT_EYE_INDICES에서 계산된 중심
                    pt468 = landmarks[468]
                    pt469 = landmarks[469]
                    
                    # 좌표 추출 (로그용)
                    if isinstance(pt468, tuple):
                        coord468 = pt468
                    else:
                        coord468 = (pt468.x * img_width, pt468.y * img_height)
                    
                    if isinstance(pt469, tuple):
                        coord469 = pt469
                    else:
                        coord469 = (pt469.x * img_width, pt469.y * img_height)
                    
                    iris_centers = [landmarks[468], landmarks[469]]
            
            # 눈동자 체크박스가 선택되었을 때 중심점 그리기
            # iris_centers가 있으면 LEFT_IRIS/RIGHT_IRIS가 없어도 중심점을 그릴 수 있음
            print(f"Checkbox states - Left iris: {hasattr(self, 'show_left_iris') and self.show_left_iris.get()}, Right iris: {hasattr(self, 'show_right_iris') and self.show_right_iris.get()}")
            
            if hasattr(self, 'show_left_iris') and self.show_left_iris.get():
                print("Drawing left iris center")
                # Tesselation 모드가 아닐 때는 폴리곤도 그리지만, Tesselation 모드일 때는 중심점만 그리기
                # draw_iris 함수 호출
                draw_iris('left', LEFT_IRIS if LEFT_IRIS else [], '_left_iris_center_coord')
            
            if hasattr(self, 'show_right_iris') and self.show_right_iris.get():
                print("Drawing right iris center")
                # Tesselation 모드가 아닐 때는 폴리곤도 그리지만, Tesselation 모드일 때는 중심점만 그리기
                # draw_iris 함수 호출
                draw_iris('right', RIGHT_IRIS if RIGHT_IRIS else [], '_right_iris_center_coord')
            else:
                print("Right iris checkbox not checked")
            
            # 선택된 부위가 없으면 아무것도 그리지 않음

        except ImportError:
            # MediaPipe가 없으면 인덱스 기반으로 폴백
            LEFT_EYE_INDICES = [33, 7, 163, 144, 145, 153, 154, 155, 133, 173, 157, 158, 159, 160, 161, 246]
            RIGHT_EYE_INDICES = [362, 382, 381, 380, 374, 373, 390, 249, 263, 466, 388, 387, 386, 385, 384, 398]
            LEFT_EYEBROW_INDICES = [70, 63, 105, 66, 107, 55, 65, 52, 53, 46]
            RIGHT_EYEBROW_INDICES = [300, 293, 334, 296, 336, 285, 295, 282, 283, 276]
            NOSE_INDICES = [8, 240, 98, 164, 327, 460, 4]
            OUTER_LIP_INDICES = [61, 185, 40, 39, 37, 0, 267, 269, 270, 409, 291, 375, 321, 405, 314, 17, 84, 181, 91, 146]
            INNER_LIP_INDICES = [78, 191, 80, 81, 82, 13, 312, 311, 310, 415, 308, 324, 318, 402, 317, 14, 87, 178, 88, 95]
            MOUTH_ALL_INDICES = list(set(OUTER_LIP_INDICES + INNER_LIP_INDICES))

            # 전체 탭: 모든 부위 폴리곤 그리기
            for indices, tag_name, part_name in [
                (LEFT_EYE_INDICES, "polygon_left_eye", "왼쪽 눈"),
                (RIGHT_EYE_INDICES, "polygon_right_eye", "오른쪽 눈"),
                (LEFT_EYEBROW_INDICES, "polygon_left_eyebrow", "왼쪽 눈썹"),
                (RIGHT_EYEBROW_INDICES, "polygon_right_eyebrow", "오른쪽 눈썹"),
                (NOSE_INDICES, "polygon_nose", "코"),
                (MOUTH_ALL_INDICES, "polygon_lips", "입")
            ]:
                    # 폴리곤에 포함된 포인트 인덱스를 polygon_point_map에 저장
                    if canvas == self.canvas_original:
                        for idx in indices:
                            if idx < len(landmarks):
                                self.polygon_point_map_original.add(idx)
                    elif canvas == self.canvas_edited:
                        for idx in indices:
                            if idx < len(landmarks):
                                self.polygon_point_map_edited.add(idx)

                    points = self._get_polygon_from_indices(indices, landmarks, img_width, img_height, scale_x, scale_y, pos_x, pos_y)
                    if points and len(points) >= 3:
                        polygon_id = canvas.create_polygon(
                            points,
                            fill="",
                            outline=color,
                            width=2,
                            tags=("landmarks_polygon", tag_name)
                        )
                        items_list.append(polygon_id)
                        # 폴리곤 클릭 이벤트 바인딩 (전체 탭이므로 None)
                        bind_polygon_click_events(polygon_id, None)
                        from utils.logger import get_logger
                        logger = get_logger('얼굴편집')
                        logger.debug(f"{part_name} 폴리곤 그리기 (폴백): {len(points)}개 포인트")
