"""
폴리곤 그리기 관련 메서드
"""
import math
import tkinter as tk

# scipy import 확인
try:
    from scipy.spatial import Delaunay
    _scipy_available = True
except ImportError:
    _scipy_available = False
    Delaunay = None

from .all_tab_drawer import AllTabDrawerMixin
from .tab_drawers import TabDrawersMixin
from utils.logger import print_warning


class DrawingMixin(AllTabDrawerMixin, TabDrawersMixin):
    """폴리곤 그리기 기능 Mixin"""
    
    def _draw_landmark_polygons(self, canvas, image, face_landmarks, pos_x, pos_y, items_list, color, current_tab, iris_landmarks=None, iris_centers=None, force_use_custom=False):
        """랜드마크 폴리곤 그리기 (해당 부위의 모든 랜드마크 포인트를 찾아서 폴리곤으로 그리기)
        
        Args:
            face_landmarks: 얼굴 랜드마크 (468개)
            iris_landmarks: 눈동자 랜드마크 (10개 또는 None)
            iris_centers: 눈동자 중앙 포인트 (2개 또는 None, Tesselation용)
        """
        if image is None or pos_x is None or pos_y is None or face_landmarks is None:
            return
        
        # 하위 호환성: landmarks 파라미터가 전달된 경우 (기존 코드 호환)
        landmarks = face_landmarks
        if iris_landmarks is not None:
            # 478개 구조로 병합 (하위 호환성)
            try:
                from utils.face_morphing.region_extraction import get_iris_indices
                left_iris_indices, right_iris_indices = get_iris_indices()
                iris_contour_indices = set(left_iris_indices + right_iris_indices)
                iris_center_indices = {468, 473}
                iris_indices = sorted(iris_contour_indices | iris_center_indices)
                
                # 얼굴 랜드마크에 눈동자 랜드마크 삽입
                landmarks = list(face_landmarks)
                for i, idx in enumerate(iris_indices):
                    if i < len(iris_landmarks):
                        if idx < len(landmarks):
                            landmarks.insert(idx, iris_landmarks[i])
                        else:
                            landmarks.append(iris_landmarks[i])
            except Exception as e:
                print(f"[폴리곤렌더러] 눈동자 병합 실패: {e}")
                landmarks = face_landmarks
        try:
            import math
            img_width, img_height = image.size
            display_size = getattr(canvas, 'display_size', None)
            if display_size is None:
                return
            
            display_width, display_height = display_size
            scale_x = display_width / img_width
            scale_y = display_height / img_height
            
            # original_landmarks 보장 (중앙 포인트 계산 전에 필수) - LandmarkManager 사용
            if not self.landmark_manager.has_original_landmarks():
                if landmarks is not None:
                    # 이미지 크기와 함께 바운딩 박스 계산하여 캐싱
                    self.landmark_manager.set_original_landmarks(landmarks, img_width, img_height)
                    self.original_landmarks = self.landmark_manager.get_original_landmarks()
                    print(f"[폴리곤렌더러] original_landmarks 설정 - 길이: {len(self.original_landmarks)}")
            else:
                self.original_landmarks = self.landmark_manager.get_original_landmarks()
            
            # custom_landmarks가 없거나 468개인 경우 중앙 포인트 추가 - LandmarkManager 사용
            custom = self.landmark_manager.get_custom_landmarks()
            if custom is None or len(custom) == 468:
                # custom_landmarks가 없으면 landmarks 사용, 있으면 custom 사용
                base_landmarks = custom if custom is not None else landmarks
                if base_landmarks is not None:
                    # 중앙 포인트 좌표 초기화 (original_iris_landmarks에서 계산)
                    left_center = None
                    right_center = None
                    
                    # landmark_manager에서 저장된 중앙 포인트 먼저 확인
                    left_center = self.landmark_manager.get_left_iris_center_coord()
                    right_center = self.landmark_manager.get_right_iris_center_coord()
                    
                    # 없으면 original_iris_landmarks에서 계산
                    if left_center is None or right_center is None:
                        original_iris_landmarks = self.landmark_manager.get_original_iris_landmarks()
                        
                        # original_iris_landmarks가 없으면 landmarks에서 추출 시도
                        if original_iris_landmarks is None and landmarks is not None and len(landmarks) == 478:
                            # landmarks가 478개라면 눈동자 포인트가 포함되어 있음
                            try:
                                from utils.face_morphing.region_extraction import get_iris_indices
                                left_iris_indices, right_iris_indices = get_iris_indices()
                                iris_contour_indices = set(left_iris_indices + right_iris_indices)
                                iris_center_indices = {468, 473}
                                iris_indices = sorted(iris_contour_indices | iris_center_indices)
                                
                                # 눈동자 포인트 추출
                                iris_points = [landmarks[idx] for idx in iris_indices if idx < len(landmarks)]
                                if len(iris_points) == 10:
                                    original_iris_landmarks = iris_points
                                    print(f"[폴리곤렌더러] landmarks(478개)에서 눈동자 포인트 추출 성공")
                            except Exception as e:
                                print(f"[폴리곤렌더러] landmarks에서 눈동자 포인트 추출 실패: {e}")
                        
                        if original_iris_landmarks is not None and len(original_iris_landmarks) == 10:
                            # 눈동자 랜드마크: 왼쪽 5개 (0-4), 오른쪽 5개 (5-9)
                            left_iris_points = original_iris_landmarks[:5]  # 왼쪽 눈동자 (MediaPipe RIGHT_IRIS)
                            right_iris_points = original_iris_landmarks[5:]  # 오른쪽 눈동자 (MediaPipe LEFT_IRIS)
                            
                            # 중앙 포인트 계산
                            if left_iris_points:
                                left_center = (
                                    sum(p[0] for p in left_iris_points) / len(left_iris_points),
                                    sum(p[1] for p in left_iris_points) / len(left_iris_points)
                                )
                            if right_iris_points:
                                right_center = (
                                    sum(p[0] for p in right_iris_points) / len(right_iris_points),
                                    sum(p[1] for p in right_iris_points) / len(right_iris_points)
                                )
                            
                            # MediaPipe 관점: LEFT_IRIS = 이미지 오른쪽 (사용자 왼쪽)
                            # MediaPipe RIGHT_IRIS = 이미지 왼쪽 (사용자 오른쪽)
                            # 사용자 관점: 왼쪽 = MediaPipe RIGHT_IRIS, 오른쪽 = MediaPipe LEFT_IRIS
                            # 따라서: left_iris_points는 사용자 왼쪽, right_iris_points는 사용자 오른쪽
                            # landmark_manager에 저장할 때는 사용자 관점으로 저장
                            if left_center is not None and right_center is not None:
                                self.landmark_manager.set_iris_center_coords(left_center, right_center)
                                self._left_iris_center_coord = left_center
                                self._right_iris_center_coord = right_center
                                print(f"[폴리곤렌더러] 중앙 포인트 좌표 초기화 (iris_landmarks에서 계산): 왼쪽={left_center}, 오른쪽={right_center}")
                            else:
                                print_warning("폴리곤렌더러", "original_iris_landmarks에서 중앙 포인트 계산 실패")
                        else:
                            print_warning("폴리곤렌더러", f"original_iris_landmarks가 없거나 길이가 10이 아님: {len(original_iris_landmarks) if original_iris_landmarks is not None else None}, base_landmarks 길이: {len(base_landmarks) if base_landmarks is not None else None}")
                    
                    # custom_landmarks 생성: 눈동자 포인트 제거 + 중앙 포인트 추가
                    try:
                        from utils.face_morphing.region_extraction import get_iris_indices
                        
                        # 눈동자 인덱스 가져오기 (나중에 _calculate_iris_center에서 사용하기 위해 항상 정의)
                        left_iris_indices, right_iris_indices = get_iris_indices()
                        
                        # base_landmarks가 468개인 경우 이미 눈동자 포인트가 제거된 상태
                        if len(base_landmarks) == 468:
                            # 눈동자 포인트 제거 불필요, 중앙 포인트만 추가
                            custom_landmarks_no_iris = list(base_landmarks)
                        else:
                            # 눈동자 포인트 제거
                            iris_contour_indices = set(left_iris_indices + right_iris_indices)
                            iris_center_indices = {468, 473}
                            iris_indices = iris_contour_indices | iris_center_indices
                            custom_landmarks_no_iris = [pt for i, pt in enumerate(base_landmarks) if i not in iris_indices]
                        
                        # 중앙 포인트 추가 (저장된 좌표 사용 또는 계산)
                        # morph_face_by_polygons와 동일한 순서로 추가해야 함
                        # morph_face_by_polygons: left_iris_center_orig 먼저 (len-2), right_iris_center_orig 나중 (len-1)
                        # MediaPipe 관점: LEFT_IRIS = 이미지 오른쪽 (사용자 왼쪽), RIGHT_IRIS = 이미지 왼쪽 (사용자 오른쪽)
                        
                        # landmark_manager에서 저장된 중앙 포인트 가져오기
                        if left_center is None:
                            left_center = self.landmark_manager.get_left_iris_center_coord()
                        if right_center is None:
                            right_center = self.landmark_manager.get_right_iris_center_coord()
                        
                        # 여전히 None이면 계산 시도
                        if (left_center is None or right_center is None) and hasattr(self, '_calculate_iris_center'):
                            original = self.landmark_manager.get_original_landmarks()
                            if original is not None:
                                # 사용자 관점: 왼쪽 = MediaPipe RIGHT_IRIS, 오른쪽 = MediaPipe LEFT_IRIS
                                if left_center is None:
                                    left_center = self._calculate_iris_center(original, right_iris_indices, img_width, img_height)
                                if right_center is None:
                                    right_center = self._calculate_iris_center(original, left_iris_indices, img_width, img_height)
                                
                                # 계산 성공 시 landmark_manager에 저장
                                if left_center is not None and right_center is not None:
                                    self.landmark_manager.set_iris_center_coords(left_center, right_center)
                        
                        # 중앙 포인트 추가
                        if left_center is not None and right_center is not None:
                            # morph_face_by_polygons 순서: MediaPipe LEFT_IRIS 먼저 (len-2), MediaPipe RIGHT_IRIS 나중 (len-1)
                            # MediaPipe LEFT_IRIS = 이미지 오른쪽 (사용자 왼쪽)
                            # MediaPipe RIGHT_IRIS = 이미지 왼쪽 (사용자 오른쪽)
                            # 따라서: 사용자 왼쪽 먼저 추가 (len-2), 사용자 오른쪽 나중 추가 (len-1)
                            custom_landmarks_no_iris.append(left_center)   # 사용자 왼쪽 = MediaPipe LEFT_IRIS (len-2)
                            custom_landmarks_no_iris.append(right_center)  # 사용자 오른쪽 = MediaPipe RIGHT_IRIS (len-1)
                            print(f"[폴리곤렌더러] 중앙 포인트 추가 완료: 왼쪽={left_center}, 오른쪽={right_center}")
                        else:
                            print_warning("폴리곤렌더러", "중앙 포인트 계산 실패, custom_landmarks에 추가하지 않음")
                        
                        self.landmark_manager.set_custom_landmarks(custom_landmarks_no_iris, reason="polygon_renderer_init_with_iris_centers")
                        # property가 자동으로 처리하므로 동기화 코드 불필요
                        print(f"[폴리곤렌더러] custom_landmarks 생성 (눈동자 제거 + 중앙 포인트 추가) - 길이: {len(self.custom_landmarks)}")
                    except Exception as e:
                        print(f"[폴리곤렌더러] custom_landmarks 변환 실패: {e}")
                        import traceback
                        traceback.print_exc()
                        # 폴백: 원본 그대로 사용
                        self.landmark_manager.set_custom_landmarks(base_landmarks, reason="polygon_renderer_init_fallback")
                        # property가 자동으로 처리하므로 동기화 코드 불필요
                        print(f"[폴리곤렌더러] custom_landmarks 생성 (폴백) - 길이: {len(self.custom_landmarks)}")
                    # custom_landmarks 사용
                    landmarks = self.landmark_manager.get_custom_landmarks()
            else:
                landmarks = self.landmark_manager.get_custom_landmarks()
            
            # iris_centers 파라미터가 전달된 경우 (Tesselation용)
            # 주의: iris_centers는 _draw_all_tab_polygons에 전달하기 위해 보존해야 함
            if iris_centers is not None and len(iris_centers) == 2:
                # Tesselation 모드: face_landmarks(468개) + iris_centers(2개) = 470개 구조
                # custom_landmarks에 저장
                # face_landmarks + iris_centers를 합쳐서 custom_landmarks로 저장
                custom_landmarks_with_centers = list(face_landmarks)
                custom_landmarks_with_centers.extend(iris_centers)  # +2개 = 470개
                self.landmark_manager.set_custom_landmarks(custom_landmarks_with_centers, reason="tesselation_with_iris_centers")
                self.landmark_manager.set_custom_iris_centers(iris_centers)
                landmarks = self.landmark_manager.get_custom_landmarks()
                # iris_centers는 그대로 유지 (draw_iris 함수에서 사용)
                print(f"[폴리곤렌더러] Tesselation 모드 - iris_centers 사용, 길이: {len(landmarks)}, 탭: {current_tab}")
            # iris_centers가 없고 custom_landmarks가 있는 경우
            else:
                custom = self.landmark_manager.get_custom_landmarks()
                if custom is not None and len(custom) == len(landmarks):
                    landmarks = custom
            
            # 중앙 포인트 좌표 초기화 (iris_centers가 없을 때만)
            if iris_centers is None and hasattr(self, '_get_iris_indices') and hasattr(self, '_calculate_iris_center'):
                # original_landmarks 가져오기 (LandmarkManager 사용)
                original = self.landmark_manager.get_original_landmarks()
                left_center = self.landmark_manager.get_left_iris_center_coord()
                right_center = self.landmark_manager.get_right_iris_center_coord()
                
                # 왼쪽 중앙 포인트 계산
                if left_center is None and original is not None:
                    left_iris_indices, right_iris_indices = self._get_iris_indices()
                    # 사용자 관점: 왼쪽 = MediaPipe RIGHT_IRIS
                    left_center = self._calculate_iris_center(original, right_iris_indices, img_width, img_height)
                
                # 오른쪽 중앙 포인트 계산
                if right_center is None and original is not None:
                    left_iris_indices, right_iris_indices = self._get_iris_indices()
                    # 사용자 관점: 오른쪽 = MediaPipe LEFT_IRIS
                    right_center = self._calculate_iris_center(original, left_iris_indices, img_width, img_height)
                
                # 좌표를 저장
                if left_center is not None or right_center is not None:
                    self.landmark_manager.set_iris_center_coords(left_center, right_center)
                    self._left_iris_center_coord = self.landmark_manager.get_left_iris_center_coord()
                    self._right_iris_center_coord = self.landmark_manager.get_right_iris_center_coord()
            
            # 인덱스 표시 여부 확인
            show_indices = getattr(self, 'show_landmark_indices', None)
            show_indices = show_indices.get() if show_indices and hasattr(show_indices, 'get') else False
            
            # 폴리곤을 다시 그리기 전에 polygon_point_map 초기화
            # 폴리곤이 추가/변경/삭제될 때마다 갱신되도록
            canvas_type = 'original' if canvas == self.canvas_original else 'edited'
            point_map = self.polygon_point_map_original if canvas_type == 'original' else self.polygon_point_map_edited
            point_map.clear()
            
            # 확장 레벨 가져오기
            expansion_level = getattr(self, 'polygon_expansion_level', tk.IntVar(value=1)).get() if hasattr(self, 'polygon_expansion_level') else 1
            
            # 인덱스 표시 여부 확인
            show_indices = getattr(self, 'show_landmark_indices', None)
            show_indices = show_indices.get() if show_indices and hasattr(show_indices, 'get') else False
            
            # 폴리곤 클릭 시 가장 가까운 포인트 찾기 함수
            def find_nearest_landmark(event, target_indices=None):
                """클릭한 위치에서 가장 가까운 랜드마크 포인트 찾기"""
                if landmarks is None:
                    return None
                
                # 캔버스 좌표를 이미지 좌표로 변환
                rel_x = (event.x - pos_x) / scale_x
                rel_y = (event.y - pos_y) / scale_y
                click_img_x = img_width / 2 + rel_x
                click_img_y = img_height / 2 + rel_y
                
                min_distance = float('inf')
                nearest_idx = None
                
                for idx, landmark in enumerate(landmarks):
                    # 현재 탭에 해당하는 랜드마크만 확인
                    if target_indices is not None and idx not in target_indices:
                        continue
                    
                    # 랜드마크 좌표
                    if isinstance(landmark, tuple):
                        lm_x, lm_y = landmark
                    else:
                        lm_x = landmark.x * img_width
                        lm_y = landmark.y * img_height
                    
                    # 거리 계산
                    distance = math.sqrt((click_img_x - lm_x)**2 + (click_img_y - lm_y)**2)
                    
                    # 최소 거리 업데이트 (20픽셀 이내만 선택)
                    if distance < min_distance and distance < 20:
                        min_distance = distance
                        nearest_idx = idx
                
                return nearest_idx
            
            # 폴리곤 클릭 이벤트 핸들러
            def on_polygon_click(event, target_indices=None):
                """폴리곤 클릭 시 가장 가까운 포인트를 찾아서 드래그 시작"""
                # 포인트를 찾지 못하면 이벤트 전파 (이미지 드래그 허용)
                nearest_idx = find_nearest_landmark(event, target_indices)
                if nearest_idx is None:
                    # 포인트를 찾지 못하면 이벤트를 전파하지 않음
                    # add="+"를 사용했으므로 캔버스 레벨 이벤트가 실행되어야 함
                    # 하지만 실제로는 tag_bind가 이벤트를 소비할 수 있으므로,
                    # 포인트를 찾지 못한 경우 명시적으로 이벤트를 전파하지 않음
                    # None을 반환하면 이벤트가 전파되지 않지만,
                    # add="+"를 사용했으므로 캔버스 레벨 이벤트가 실행되어야 함
                    return None
                # 가장 가까운 포인트 드래그 시작
                # 이제 폴리곤에서만 포인트를 찾아서 드래그하므로 on_polygon_drag_start 사용
                result = self.on_polygon_drag_start(event, nearest_idx, canvas)
                # 이벤트 전파 중단 (포인트 드래그 시작)
                return "break"
            
            def on_polygon_drag(event, target_indices=None):
                """폴리곤 드래그 중 (사용 안 함 - 캔버스 레벨에서 처리)"""
                # 이제 폴리곤 클릭 이벤트를 사용하지 않으므로 이 함수는 사용 안 함
                return None
            
            def on_polygon_release(event, target_indices=None):
                """폴리곤 드래그 종료 (사용 안 함 - 캔버스 레벨에서 처리)"""
                # 이제 폴리곤 클릭 이벤트를 사용하지 않으므로 이 함수는 사용 안 함
                return None
                return None
            
            # 폴리곤 그리기 헬퍼 함수 (클릭 이벤트 제거)
            def bind_polygon_click_events(polygon_id, target_indices):
                """폴리곤에 클릭 이벤트 바인딩하지 않음 (이미지 드래그를 방해하지 않도록)"""
                # 폴리곤 클릭 이벤트를 제거하여 이미지 드래그가 작동하도록 함
                # 대신 포인트 클릭 영역을 크게 만들어서 포인트를 직접 클릭할 수 있도록 함
                # 또는 캔버스 레벨 이벤트 핸들러에서 포인트를 찾도록 함
                pass
            
            # 현재 탭에 따라 해당 부위의 모든 랜드마크 인덱스 수집
            target_indices = []
            
            if current_tab == '전체':
                # 눈동자 이동 범위 제한 파라미터 가져오기
                clamping_enabled = getattr(self, 'iris_clamping_enabled', None)
                margin_ratio = getattr(self, 'iris_clamping_margin_ratio', None)
                clamping_enabled_val = clamping_enabled.get() if clamping_enabled is not None else True
                margin_ratio_val = margin_ratio.get() if margin_ratio is not None else 0.3
                
                self._draw_all_tab_polygons(
                    canvas, image, landmarks, pos_x, pos_y, items_list, color,
                    scale_x, scale_y, img_width, img_height, expansion_level, show_indices,
                    bind_polygon_click_events, force_use_custom, iris_landmarks, iris_centers,
                    clamping_enabled=clamping_enabled_val, margin_ratio=margin_ratio_val
                )
            elif current_tab == '눈':
                self._draw_eye_tab_polygons(
                    canvas, image, landmarks, pos_x, pos_y, items_list, color,
                    scale_x, scale_y, img_width, img_height, expansion_level, show_indices,
                    bind_polygon_click_events, force_use_custom
                )
            elif current_tab == '눈동자':
                # 눈동자 이동 범위 제한 파라미터 가져오기
                clamping_enabled = getattr(self, 'iris_clamping_enabled', None)
                margin_ratio = getattr(self, 'iris_clamping_margin_ratio', None)
                clamping_enabled_val = clamping_enabled.get() if clamping_enabled is not None else True
                margin_ratio_val = margin_ratio.get() if margin_ratio is not None else 0.3
                
                self._draw_iris_tab_polygons(
                    canvas, image, landmarks, pos_x, pos_y, items_list, color,
                    scale_x, scale_y, img_width, img_height, expansion_level, show_indices,
                    bind_polygon_click_events, force_use_custom, iris_centers,
                    clamping_enabled=clamping_enabled_val, margin_ratio=margin_ratio_val
                )
            elif current_tab == '코':
                self._draw_nose_tab_polygons(
                    canvas, image, landmarks, pos_x, pos_y, items_list, color,
                    scale_x, scale_y, img_width, img_height, expansion_level, show_indices,
                    bind_polygon_click_events, force_use_custom
                )
            elif current_tab == '입':
                self._draw_mouth_tab_polygons(
                    canvas, image, landmarks, pos_x, pos_y, items_list, color,
                    scale_x, scale_y, img_width, img_height, expansion_level, show_indices,
                    bind_polygon_click_events, force_use_custom
                )
            elif current_tab == '눈썹':
                self._draw_eyebrow_tab_polygons(
                    canvas, image, landmarks, pos_x, pos_y, items_list, color,
                    scale_x, scale_y, img_width, img_height, expansion_level, show_indices,
                    bind_polygon_click_events, force_use_custom
                )
            elif current_tab == '턱선':
                self._draw_jaw_tab_polygons(
                    canvas, image, landmarks, pos_x, pos_y, items_list, color,
                    scale_x, scale_y, img_width, img_height, expansion_level, show_indices,
                    bind_polygon_click_events, force_use_custom
                )
            elif current_tab == '윤곽':
                self._draw_contour_tab_polygons(
                    canvas, image, landmarks, pos_x, pos_y, items_list, color,
                    scale_x, scale_y, img_width, img_height, expansion_level, show_indices,
                    bind_polygon_click_events, force_use_custom
                )
        
        except Exception as e:
            from utils.logger import get_logger
            logger = get_logger('얼굴편집')
            logger.error(f"폴리곤 그리기 실패: {e}", exc_info=True)
            import traceback
            traceback.print_exc()
    


    def _fill_polygon_area(self, canvas, image, landmarks, pos_x, pos_y, items_list, color, current_tab):
        """폴리곤 영역을 채워서 표시"""
        if image is None or pos_x is None or pos_y is None or landmarks is None:
            return
        
        try:
            import math
            img_width, img_height = image.size
            display_size = getattr(canvas, 'display_size', None)
            if display_size is None:
                return
            
            display_width, display_height = display_size
            scale_x = display_width / img_width
            scale_y = display_height / img_height
            
            # MediaPipe 연결 정보 가져오기
            try:
                import mediapipe as mp
                mp_face_mesh = mp.solutions.face_mesh
                FACE_OVAL = mp_face_mesh.FACEMESH_FACE_OVAL
                LEFT_EYE = mp_face_mesh.FACEMESH_LEFT_EYE
                RIGHT_EYE = mp_face_mesh.FACEMESH_RIGHT_EYE
                LEFT_EYEBROW = mp_face_mesh.FACEMESH_LEFT_EYEBROW
                RIGHT_EYEBROW = mp_face_mesh.FACEMESH_RIGHT_EYEBROW
                NOSE = mp_face_mesh.FACEMESH_NOSE
                LIPS = mp_face_mesh.FACEMESH_LIPS
            except ImportError:
                return
            
            # 현재 탭에 따라 표시할 연결선 결정
            connections_by_group = {}
            if current_tab == '전체':
                # 전체 탭: 모든 연결선 표시
                connections_by_group['left_eye'] = list(LEFT_EYE)
                connections_by_group['right_eye'] = list(RIGHT_EYE)
                connections_by_group['left_eyebrow'] = list(LEFT_EYEBROW)
                connections_by_group['right_eyebrow'] = list(RIGHT_EYEBROW)
                connections_by_group['nose'] = list(NOSE)
                connections_by_group['lips'] = list(LIPS)
                connections_by_group['face_oval'] = list(FACE_OVAL)
            elif current_tab == '눈':
                # 눈 편집 시: 눈 외곽선 + 눈썹 연결선 모두 표시
                connections_by_group['left_eye'] = list(LEFT_EYE)
                connections_by_group['right_eye'] = list(RIGHT_EYE)
                connections_by_group['left_eyebrow'] = list(LEFT_EYEBROW)
                connections_by_group['right_eyebrow'] = list(RIGHT_EYEBROW)
            elif current_tab == '눈썹':
                # 눈썹 편집 시: 눈썹 연결선만 표시
                connections_by_group['left_eyebrow'] = list(LEFT_EYEBROW)
                connections_by_group['right_eyebrow'] = list(RIGHT_EYEBROW)
            elif current_tab == '코':
                connections_by_group['nose'] = list(NOSE)
            elif current_tab == '입':
                connections_by_group['lips'] = list(LIPS)
            elif current_tab == '턱선':
                # 턱선 편집 시: 얼굴 외곽선 연결선 표시
                connections_by_group['face_oval'] = list(FACE_OVAL)
            else:
                connections_by_group['face_oval'] = list(FACE_OVAL)
                connections_by_group['left_eye'] = list(LEFT_EYE)
                connections_by_group['right_eye'] = list(RIGHT_EYE)
                connections_by_group['nose'] = list(NOSE)
                connections_by_group['lips'] = list(LIPS)
            
            # 각 그룹의 폴리곤 그리기
            for group, connections in connections_by_group.items():
                if len(connections) == 0:
                    continue
                
                # 연결선으로부터 포인트 수집
                point_indices = set()
                for idx1, idx2 in connections:
                    if idx1 < len(landmarks) and idx2 < len(landmarks):
                        point_indices.add(idx1)
                        point_indices.add(idx2)
                
                if len(point_indices) < 3:
                    continue
                
                # 포인트 좌표 수집 및 중심점 계산
                point_coords = []
                center_x, center_y = 0, 0
                for idx in point_indices:
                    if idx < len(landmarks):
                        pt = landmarks[idx]
                        if isinstance(pt, tuple):
                            img_x, img_y = pt
                        else:
                            img_x = pt.x * img_width
                            img_y = pt.y * img_height
                        point_coords.append((idx, img_x, img_y))
                        center_x += img_x
                        center_y += img_y
                
                if len(point_coords) < 3:
                    continue
                
                center_x /= len(point_coords)
                center_y /= len(point_coords)
                
                # 중심점 기준으로 각도 순 정렬
                def get_angle(x, y):
                    dx = x - center_x
                    dy = y - center_y
                    return math.atan2(dy, dx)
                
                point_coords.sort(key=lambda p: get_angle(p[1], p[2]))
                
                # 캔버스 좌표로 변환하여 폴리곤 경로 생성
                polygon_points = []
                for idx, img_x, img_y in point_coords:
                    rel_x = (img_x - img_width / 2) * scale_x
                    rel_y = (img_y - img_height / 2) * scale_y
                    canvas_x = pos_x + rel_x
                    canvas_y = pos_y + rel_y
                    polygon_points.append((canvas_x, canvas_y))
                
                if len(polygon_points) >= 3:
                    # 폴리곤 그리기 (더 잘 보이도록 진하게)
                    print(f"[얼굴편집] 폴리곤 그리기: 그룹={group}, 포인트 수={len(polygon_points)}")
                    
                    # 폴리곤 색상 결정 (랜드마크 색상과 동일하되 더 진하게)
                    # 원본 이미지는 녹색, 편집 이미지는 노란색
                    if canvas == self.canvas_original:
                        fill_color = "#00FF00"  # 밝은 녹색
                        outline_color = "#00AA00"  # 진한 녹색
                    else:
                        fill_color = "#FFFF00"  # 밝은 노란색
                        outline_color = "#FFAA00"  # 진한 노란색
                    
                    # 폴리곤을 채우지 않고 outline만 그리기
                    polygon_id = canvas.create_polygon(
                        polygon_points,
                        fill="",  # 채우지 않음
                        outline=outline_color, 
                        width=2,
                        tags=("landmarks_polygon_fill", f"polygon_{group}")
                    )
                    items_list.append(polygon_id)
                    
                    # 폴리곤 아이템 저장
                    canvas_type = 'original' if canvas == self.canvas_original else 'edited'
                    self.landmark_polygon_items[canvas_type].append(polygon_id)
                    
                    # 폴리곤을 이미지 위에 배치하여 잘 보이도록
                    # 이미지 아이템을 찾아서 폴리곤을 이미지 위로 올림
                    try:
                        # 이미지 아이템 찾기
                        if canvas == self.canvas_original:
                            image_item = getattr(self, 'image_created_original', None)
                        else:
                            image_item = getattr(self, 'image_created_edited', None)
                        
                        if image_item:
                            # 폴리곤을 이미지 위에 배치
                            canvas.tag_raise(polygon_id, image_item)
                        else:
                            # 이미지가 없으면 연결선 위에 배치
                            canvas.tag_raise(polygon_id, "landmarks_polygon")
                    except Exception:
                        # 실패하면 그냥 raise
                        canvas.tag_raise(polygon_id)
                    print(f"[얼굴편집] 폴리곤 그리기 완료: 그룹={group}, 아이템 ID={polygon_id}")
                else:
                    print(f"[얼굴편집] 폴리곤 포인트 부족: 그룹={group}, 포인트 수={len(polygon_points)}")
            
            # 뒤집힌 삼각형 감지 및 표시 (원본 랜드마크와 변형된 랜드마크가 모두 있을 때만)
            # custom_landmarks를 사용하여 실제 변형된 랜드마크와 비교
            if (canvas == self.canvas_original and 
                hasattr(self, 'original_landmarks') and self.original_landmarks is not None and
                hasattr(self, 'custom_landmarks') and self.custom_landmarks is not None and
                _scipy_available and len(self.custom_landmarks) == len(self.original_landmarks)):
                try:
                    self._draw_flipped_triangles(
                        canvas, image, self.original_landmarks, self.custom_landmarks, 
                        pos_x, pos_y, items_list, img_width, img_height, 
                        scale_x, scale_y
                    )
                except Exception as e:
                    print(f"[얼굴편집] 뒤집힌 삼각형 표시 실패: {e}")
                    import traceback
                    traceback.print_exc()
        
        except Exception as e:
            print(f"[얼굴편집] 폴리곤 영역 채우기 실패: {e}")
            import traceback
            traceback.print_exc()
