import math
import tkinter as tk
from utils.logger import debug
from gui.FaceForge.utils.debugs import DEBUG_RENDER_POLYGONS

class RenderManagerMixin:

    def __init__(self, *args, **kwargs):
        """초기화"""
        super().__init__(*args, **kwargs)

    def _draw_landmark_polygons(self, canvas, image, face_landmarks, pos_x, pos_y, items_list, color, current_tab, iris_landmarks=None, iris_centers=None, force_use_custom=False, highlight_indices=None):
        """랜드마크 폴리곤 그리기 (해당 부위의 모든 랜드마크 포인트를 찾아서 폴리곤으로 그리기)
        
        Args:
            face_landmarks: 얼굴 랜드마크 (468개)
            iris_landmarks: 눈동자 랜드마크 (10개 또는 None)
            iris_centers: 눈동자 중앙 포인트 (2개 또는 None, Tesselation용)
        """

        if DEBUG_RENDER_POLYGONS:
            # 실제 이미지 위치 확인 (canvas.coords로 이미지 실제 위치 가져오기)
            try:
                actual_coords = None
                image_items = canvas.find_withtag("image")
                if image_items:
                    coord_x, coord_y = canvas.coords(image_items[0])

                debug("_draw_landmark_polygons", 
                    f": coords=({coord_x:.2f} {coord_y:.2f}), pos( {pos_x:.2f}, {pos_y:.2f} ), display: {getattr(canvas, 'display_size', None)}, image={image.size}, face={len(face_landmarks)}, \n"
                    f"items_list={len(items_list)}, color={color}, current={current_tab}, "
                    f"iris_landmarks={iris_landmarks}, iris_centers={iris_centers}, "
                    f"force_use={force_use_custom}, highlights={highlight_indices}")
            except:
                error("_draw_landmark_polygons", "이미지 좌표, 파라미터 출력 실패")
                pass                

        if image is None or pos_x is None or pos_y is None or face_landmarks is None:
            return
        
        # 하위 호환성: landmarks 파라미터가 전달된 경우 (기존 코드 호환)
        target_landmarks = face_landmarks
        landmarks = face_landmarks
        # if iris_landmarks is not None:
        #     # 478개 구조로 병합 (하위 호환성)
        #     try:
        #         from utils.morphing.region import get_iris_indices
        #         left_iris_indices, right_iris_indices = get_iris_indices()
        #         iris_contour_indices = set(left_iris_indices + right_iris_indices)
        #         iris_center_indices = {468, 473}
        #         iris_indices = sorted(iris_contour_indices | iris_center_indices)
                
        #         # 얼굴 랜드마크에 눈동자 랜드마크 삽입
        #         landmarks = list(face_landmarks)
        #         for i, idx in enumerate(iris_indices):
        #             if i < len(iris_landmarks):
        #                 if idx < len(landmarks):
        #                     landmarks.insert(idx, iris_landmarks[i])
        #                 else:
        #                     landmarks.append(iris_landmarks[i])
        #     except Exception as e:
        #         if DEBUG_POLYGON_RENDERER:
        #             print(f"[폴리곤렌더러] 눈동자 병합 실패: {e}")
        #         landmarks = face_landmarks
        try:
            import math
            img_width, img_height = image.size
            display_size = getattr(canvas, 'display_size', None)
            if display_size is None:
                return
            
            display_width, display_height = display_size
            scale_x = display_width / img_width
            scale_y = display_height / img_height

            landmarks = self.landmark_manager.get_custom_landmarks()
            
            # 인덱스 표시 여부 확인
            show_indices = getattr(self, 'show_landmark_indices', None)
            show_indices = show_indices.get() if show_indices and hasattr(show_indices, 'get') else False
            
            # 폴리곤을 다시 그리기 전에 polygon_point_map 초기화
            # 폴리곤이 추가/변경/삭제될 때마다 갱신되도록
            canvas_type = 'original' if canvas == self.canvas_original else 'edited'
            point_map = self.polygon_point_map_original if canvas_type == 'original' else self.polygon_point_map_edited
            point_map.clear()
            
            # 확장 레벨 가져오기
            expansion_level = getattr(self, 'region_expansion_level', tk.IntVar(value=1)).get() if hasattr(self, 'region_expansion_level') else 1
            
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

            
            # 폴리곤 그리기 헬퍼 함수 (클릭 이벤트 제거)
            def bind_polygon_click_events(polygon_id, target_indices):
                """폴리곤에 클릭 이벤트 바인딩하지 않음 (이미지 드래그를 방해하지 않도록)"""
                # 폴리곤 클릭 이벤트를 제거하여 이미지 드래그가 작동하도록 함
                # 대신 포인트 클릭 영역을 크게 만들어서 포인트를 직접 클릭할 수 있도록 함
                # 또는 캔버스 레벨 이벤트 핸들러에서 포인트를 찾도록 함
                pass
            
            # 현재 탭에 따라 해당 부위의 모든 랜드마크 인덱스 수집
            target_indices = []            
            highlight_indices_set = set(highlight_indices) if highlight_indices else None

            # 눈동자 이동 범위 제한 파라미터 가져오기
            clamping_enabled = getattr(self, 'iris_clamping_enabled', None)
            margin_ratio = getattr(self, 'iris_clamping_margin_ratio', None)
            clamping_enabled_val = clamping_enabled.get() if clamping_enabled is not None else True
            margin_ratio_val = margin_ratio.get() if margin_ratio is not None else 0.3

            self._draw_polygons(
                canvas, image, target_landmarks, pos_x, pos_y, items_list, color,
                scale_x, scale_y, img_width, img_height, expansion_level, show_indices,
                bind_polygon_click_events, force_use_custom, iris_landmarks, iris_centers,
                clamping_enabled=clamping_enabled_val, margin_ratio=margin_ratio_val
            )
        except Exception as e:
            from utils.logger import get_logger
            logger = get_logger('얼굴편집')
            logger.error(f"폴리곤 그리기 실패: {e}", exc_info=True)
            import traceback
            traceback.print_exc()


