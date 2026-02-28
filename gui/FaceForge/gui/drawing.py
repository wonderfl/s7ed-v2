import math
import tkinter as tk
from .guide import GuideLinesManager

from utils.logger import debug, info, warning, error, log
from gui.FaceForge.utils.debugs import DEBUG_RENDER_POLYGONS, DEBUG_REGION_PIVOTS, DEBUG_GUIDE_LINES_UPDATE, DEBUG_DRAWING_CURRENT

class DrawingsMixin:

    def __init__(self, *args, **kwargs):
        """초기화"""
        super().__init__(*args, **kwargs)

    def _draw_polygons(self, 
        canvas, image, landmarks, pos_x, pos_y, items_list, color, scale_x, scale_y, 
        img_width, img_height, expansion_level, show_indices, bind_polygon_click_events, force_use_custom=False, 
        iris_landmarks=None, iris_centers=None, clamping_enabled=True, margin_ratio=0.3 ):
        """all 탭 폴리곤 그리기
        
        Args:
            iris_landmarks: 눈동자 랜드마크 (10개 또는 None)
            iris_centers: 눈동자 중앙 포인트 (2개 또는 None, Tesselation용)
            clamping_enabled: 눈동자 이동 범위 제한 활성화 여부
            margin_ratio: 눈동자 이동 범위 제한 마진 비율 (0.0 ~ 1.0)
        """
        if DEBUG_RENDER_POLYGONS:
            print(
                f"{'='*80}"
                f"\n[_draw_polygons] "
                f"canvas: {canvas.display_size}, image: {image.size}, landmarks: {None if landmarks is None else len(landmarks)}, "
                f"pos( {pos_x:.2f}, {pos_y:.2f} ), expansion: {expansion_level}, color: {color}\n"
                f"scale( {scale_x:.3f}, {scale_y:.3f} ), items_list: {items_list}, "
                f"show_indices: {show_indices}, polygon_click: {True if bind_polygon_click_events else None}, "
                f"force_use: {force_use_custom}, clamping: {clamping_enabled}")
        # 현재 탭에 따라 해당 부위의 모든 랜드마크 인덱스 수집
        target_indices = []

        # 전체 탭: 선택된 부위가 있으면 선택된 부위만, 없으면 모든 부위의 폴리곤 그리기
        try:
            # 선택된 부위 확인            
            selected_regions = self._get_selected_regions()
            
            # 선택된 부위의 인덱스 수집
            for region_name, indices in selected_regions:
                target_indices.extend(indices)
            
            # 모든 부위의 폴리곤 그리기 함수
            def draw_polygon_mesh(connections, tag_name, part_name, target_indices=None):
                """연결 정보를 사용해서 폴리곤 메쉬 그리기"""
                # 연결 정보에서 모든 포인트 인덱스 수집
                polygon_indices_set = set()
                for idx1, idx2 in connections:
                    if idx1 < len(landmarks) and idx2 < len(landmarks):
                        polygon_indices_set.add(idx1)
                        polygon_indices_set.add(idx2)

                if DEBUG_RENDER_POLYGONS:
                    debug("draw_polygon_mesh", f": {part_name}, expansion={expansion_level}, connections={len(connections)}, polygons={len(polygon_indices_set)}")
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
                        error("draw_polygon_mesh", "MediaPipe가 설치되지 않았습니다. MediaPipe를 설치한 후 다시 시도해주세요.")
                        pass
                # 폴리곤에 포함된 포인트 인덱스를 polygon_point_map에 저장
                polygon_indices = list(polygon_indices_set)
                canvas_type = 'original' if canvas == self.canvas_original else 'edited'
                if DEBUG_RENDER_POLYGONS:
                    debug("draw_polygon_mesh", f"polygon_indices: ( {len(polygon_indices_set)}, {len(polygon_indices)} ), canvas_type: {canvas_type}")

                point_map = self.polygon_point_map_original if canvas_type == 'original' else self.polygon_point_map_edited
                for idx in polygon_indices:
                    if idx < len(landmarks):
                        point_map.add(idx)

                # 확장 레벨 0일 때는 연결선으로 그리기 (폴리곤 대신)
                if expansion_level > 0:
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
                else:
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
                                fill=color, width=1, tags=("landmarks_polygon", tag_name)
                            )
                            items_list.append(line_id)

                            # 연결선에도 클릭 이벤트 바인딩 (폴리곤과 동일하게)
                            bind_polygon_click_events(line_id, target_indices)

            # 선택된 부위만 폴리곤 그리기
            if len(selected_regions) > 0:
                # print("selected_regions: ", selected_regions)
                # 선택된 부위만 그리기
                for region_name, region_indices in selected_regions:
                    draw_polygon_mesh(region_indices, "polygon_"+f"{region_name}", region_name, None)
                            
        except Exception as e:
            error("_draw_polygons", f"MediaPipe Face Mesh 상수 로드 실패: {e}")
            import traceback
            traceback.print_exc()            
            return


    def _draw_pivots(self, canvas, image, landmarks, pos_x, pos_y, items_list):
        """선택된 부위의 중심점을 캔버스에 그리기"""
        if DEBUG_REGION_PIVOTS:
            print("[_draw_region_pivots]", f"canvas: {canvas.display_size}, image: {image.size}, landmarks: {None if landmarks is None else len(landmarks)}, pos( {pos_x:.2f}, {pos_y:.2f} ), items_list: {items_list}")
        if image is None or pos_x is None or pos_y is None or landmarks is None:
            return
        
        # 선택된 부위 목록 가져오기
        selected_regions = []
        if hasattr(self, 'show_face_oval') and self.show_face_oval.get():
            selected_regions.append('face_oval')
        if hasattr(self, 'show_left_eye') and self.show_left_eye.get():
            selected_regions.append('left_eye')
        if hasattr(self, 'show_right_eye') and self.show_right_eye.get():
            selected_regions.append('right_eye')
        if hasattr(self, 'show_left_eyebrow') and self.show_left_eyebrow.get():
            selected_regions.append('left_eyebrow')
        if hasattr(self, 'show_right_eyebrow') and self.show_right_eyebrow.get():
            selected_regions.append('right_eyebrow')
        if hasattr(self, 'show_nose') and self.show_nose.get():
            selected_regions.append('nose')
        if hasattr(self, 'show_lips') and self.show_lips.get():
            selected_regions.append('lips')
        if hasattr(self, 'show_left_iris') and self.show_left_iris.get():
            selected_regions.append('left_iris')
        if hasattr(self, 'show_right_iris') and self.show_right_iris.get():
            selected_regions.append('right_iris')
        if hasattr(self, 'show_contours') and self.show_contours.get():
            selected_regions.append('contours')
        if hasattr(self, 'show_tesselation') and self.show_tesselation.get():
            selected_regions.append('tesselation')
        
        if DEBUG_REGION_PIVOTS:
            print("[_draw_region_pivots]", f"selected_regions: {len(selected_regions)}")
        if not selected_regions:
            return
        
        try:
            from gui.FaceForge.utils.morphing.region import _get_region_pivot
            
            img_width, img_height = image.size
            display_size = getattr(canvas, 'display_size', None)
            if DEBUG_REGION_PIVOTS:
                print("[_draw_region_pivots]", f"display_size: {display_size}")
            if display_size is None:
                return
            
            display_width, display_height = display_size
            scale_x = display_width / img_width
            scale_y = display_height / img_height
            
            # 공통 슬라이더 값 가져오기
            region_pivot_x = self.region_pivot_x.get() if hasattr(self, 'region_pivot_x') else 0.0
            region_pivot_y = self.region_pivot_y.get() if hasattr(self, 'region_pivot_y') else 0.0
            
            # 각 선택된 부위의 중심점 그리기
            for region_name in selected_regions:
                pivot = _get_region_pivot(region_name, landmarks, region_pivot_x, region_pivot_y)
                if pivot is None:
                    continue
                
                pivot_x, pivot_y = pivot
                
                # 캔버스 좌표로 변환
                rel_x = (pivot_x - img_width / 2) * scale_x
                rel_y = (pivot_y - img_height / 2) * scale_y
                canvas_x = pos_x + rel_x
                canvas_y = pos_y + rel_y
                
                # 중심점을 십자가 모양으로 그리기 (크기: 10픽셀)
                size = 5
                # 가로선
                line1 = canvas.create_line(
                    canvas_x - size, canvas_y,
                    canvas_x + size, canvas_y,
                    fill="yellow",
                    width=2,
                    tags=("region_pivot", f"pivot_{region_name}")
                )
                items_list.append(line1)
                
                # 세로선
                line2 = canvas.create_line(
                    canvas_x, canvas_y - size,
                    canvas_x, canvas_y + size,
                    fill="yellow",
                    width=2,
                    tags=("region_pivot", f"pivot_{region_name}")
                )
                items_list.append(line2)
                
                # 중심점을 원으로도 그리기 (반지름 3픽셀)
                circle = canvas.create_oval(
                    canvas_x - 3, canvas_y - 3,
                    canvas_x + 3, canvas_y + 3,
                    outline="yellow",
                    width=2,
                    fill="",
                    tags=("region_pivot", f"pivot_{region_name}")
                )
                items_list.append(circle)

            if DEBUG_REGION_PIVOTS:
                print("[_draw_region_pivots]", f"items_list: {len(items_list)}")
        
        except Exception as e:
            import traceback
            traceback.print_exc()

    def _draw_guides(self):
        """지시선 업데이트 (확대/축소 시 호출)"""

        has_guide_manager = hasattr(self, 'guide_lines_manager')
        attr_show_lines = getattr(self, 'show_guide_lines', None)
        is_zooming = getattr(self, '_is_zooming', False)
        has_current_image = self.current_image is not None
        landmarks = self.landmark_manager.get_original_landmarks_full()

        if DEBUG_GUIDE_LINES_UPDATE:
            debug("_draw_guides", 
                f"show_lines: {attr_show_lines}, manager: {has_guide_manager}, "
                f"zooming: {is_zooming}, current_image: {has_current_image}, "
                f"landmarks: {None if landmarks is None else len(landmarks)}")

        if not has_guide_manager or attr_show_lines is None:
            return
                
        # 체크박스 상태에 따라 지시선 설정 업데이트
        for key in self.guide_lines_manager.guide_line_settings:
            if key.endswith('_line'):
                self.guide_lines_manager.guide_line_settings[key] = attr_show_lines.get()
        
        # 미리보기 업데이트
        # 확대/축소 중에는 전체 리렌더 없이 지시선만 갱신
        if has_guide_manager and not is_zooming:
            if landmarks:
                if has_current_image:
                    img_width, img_height = self.current_image.size
                    display_size = getattr(self.canvas_original, 'display_size', None)
                    if display_size is None:
                        zoom_scale = getattr(self, 'zoom_scale_original', 1.0)
                        display_width = int(img_width * zoom_scale)
                        display_height = int(img_height * zoom_scale)
                    else:
                        display_width, display_height = display_size
                    if img_width and img_height:
                        scale_x = display_width / img_width
                        scale_y = display_height / img_height
                    else:
                        scale_x = scale_y = getattr(self, 'zoom_scale_original', 1.0)
                    pos_x = self.canvas_original_pos_x if self.canvas_original_pos_x is not None else (getattr(self, 'preview_width', 800) // 2)
                    pos_y = self.canvas_original_pos_y if self.canvas_original_pos_y is not None else (getattr(self, 'preview_height', 1000) // 2)

                    self.guide_lines_manager.draw_guide_lines(
                        self.canvas_original,
                        landmarks,
                        img_width,
                        img_height,
                        scale_x,
                        scale_y,
                        pos_x,
                        pos_y,
                        'original'
                    )

    def clear_bbox_display(self):
        """바운딩 박스 표시 제거"""
        # 원본 이미지의 바운딩 박스 제거
        if self.bbox_rect_original is not None:
            try:
                self.canvas_original.delete(self.bbox_back_original)
                self.canvas_original.delete(self.bbox_rect_original)
            except Exception as e:
                print(f"[바운딩 박스 표시 제거] 오류 발생: {e}")
                pass
        self.bbox_back_original = None
        self.bbox_rect_original = None
    
    def _draw_bbox(self):
        """바운딩 박스 표시 업데이트"""

        has_current_image = self.current_image is not None
        has_landmark_manager = hasattr(self, 'landmark_manager')
        if DEBUG_GUIDE_LINES_UPDATE:
            debug("_draw_bbox",f": image: {has_current_image}, landmark: {has_landmark_manager}")

        if not has_current_image:
            return

        if not has_landmark_manager:
            return

        img_width, img_height = self.current_image.size
        try:
            # 기존 바운딩 박스 제거
            self.clear_bbox_display()

            # 바운딩 박스 가져오기
            bbox = self.landmark_manager.get_original_bbox(img_width, img_height)

            # 바운딩 박스가 None이면 계산 시도
            if bbox is None:
                # 랜드마크를 사용하여 바운딩 박스 계산
                landmarks = self.landmark_manager.get_face_landmarks()
                if landmarks is not None:
                    from gui.FaceForge.utils.morphing.polygon.core import _calculate_landmark_bounding_box
                    try:
                        from gui.FaceForge.utils.morphing.region import get_iris_indices
                        left_iris_indices, right_iris_indices = get_iris_indices()
                        iris_contour_indices = set(left_iris_indices + right_iris_indices)
                        iris_center_indices = {468, 473}
                        iris_indices = iris_contour_indices | iris_center_indices
                    except:
                        iris_indices = {468, 469, 470, 471, 472, 473, 474, 475, 476, 477}
                    
                    landmarks_no_iris = [pt for i, pt in enumerate(landmarks) if i not in iris_indices]
                    bbox = _calculate_landmark_bounding_box(landmarks_no_iris, img_width, img_height, padding_ratio=0.5)
                    
                    if bbox is not None:
                        # 계산된 바운딩 박스를 캐시에 저장
                        self.landmark_manager.set_original_bbox(bbox, img_width, img_height)
            
            if DEBUG_GUIDE_LINES_UPDATE:
                info("_draw_bbox",f"bbox: {bbox}, image({img_width}x{img_height})")
                            
            if bbox is None:
                return
            
            min_x, min_y, max_x, max_y = bbox
            
            # 원본 이미지에 바운딩 박스 표시
            if self.canvas_original_pos_x is None or self.canvas_original_pos_y is None:
                return
            
            display_size = getattr(self.canvas_original, 'display_size', None)
            if display_size is None:
                return
            
            pos_x = self.canvas_original_pos_x
            pos_y = self.canvas_original_pos_y
            display_width, display_height = display_size
            
            # 이미지 스케일 계산
            scale_x = display_width / img_width
            scale_y = display_height / img_height
            
            # 바운딩 박스 좌표를 캔버스 좌표로 변환
            rel_x1 = (min_x - img_width / 2) * scale_x
            rel_y1 = (min_y - img_height / 2) * scale_y
            rel_x2 = (max_x - img_width / 2) * scale_x
            rel_y2 = (max_y - img_height / 2) * scale_y
            
            canvas_x1 = pos_x + rel_x1
            canvas_y1 = pos_y + rel_y1
            canvas_x2 = pos_x + rel_x2
            canvas_y2 = pos_y + rel_y2

            self.bbox_back_original = self.canvas_original.create_rectangle(
                canvas_x1+1, canvas_y1+1, canvas_x2+1, canvas_y2+1,
                outline="grey", width=1, tags="bbox"
            )                        
            
            # 바운딩 박스 사각형 그리기 (빨간색, 두꺼운 선)
            self.bbox_rect_original = self.canvas_original.create_rectangle(
                canvas_x1, canvas_y1, canvas_x2, canvas_y2,
                outline="white", width=1, tags="bbox"
            )

            
        except Exception as e:
            import traceback
            traceback.print_exc()


    def draw_polygons_current(self):
        """폴리곤만 간단하게 그리기"""
        has_current_image = self.current_image is not None
        has_landmark_manager = hasattr(self, 'landmark_manager')
        if DEBUG_DRAWING_CURRENT:
            info("draw_polygons_current",f":image: {has_current_image}, landmark: {has_landmark_manager}")        

        if not has_current_image or not has_landmark_manager:
            return
        
        landmarks = self.landmark_manager.get_current_landmarks()
        # 랜드마크 3개 출력으로 변화 확인 (입술)
        if DEBUG_DRAWING_CURRENT:
            lip_top = landmarks[13]     # 입술 중앙 상단
            lip_left = landmarks[61]    # 입술 왼쪽 끝
            lip_right = landmarks[291]  # 입술 오른쪽 끝
            lip_down = landmarks[292]   # 입술 중앙 하단
            info("draw_polygons_current", f"입술 상단: {lip_top}, 입술 왼쪽: {lip_left}, 입술 오른쪽: {lip_right}, 입술 하단: {lip_down}")

        if not landmarks:
            return
        
        # 필요한 값들 계산
        img_width, img_height = self.current_image.size
        display_size = getattr(self.canvas_original, 'display_size', (img_width, img_height))
        scale_x = display_size[0] / img_width
        scale_y = display_size[1] / img_height

        expansion_level = getattr(self, 'region_expansion_level', tk.IntVar(value=1)).get() if hasattr(self, 'region_expansion_level') else 1

        def bind_polygon_click_events(polygon_id, target_indices):
            """폴리곤에 클릭 이벤트 바인딩하지 않음 (이미지 드래그를 방해하지 않도록)"""
            pass        
        
        self._draw_polygons(
            self.canvas_original,
            self.current_image,
            landmarks,
            self.canvas_original_pos_x,
            self.canvas_original_pos_y,
            self.landmark_polygon_items['original'],
            self.show_polygon_color.get(), #"green",
            scale_x, scale_y,
            img_width, img_height,
            expansion_level,  # expansion_level
            False,  # show_indices
            bind_polygon_click_events, # 클릭 이벤트 함수
            False,  # force_use_custom
            None, None,  # iris_landmarks, iris_centers
            True,  # clamping_enabled
            0.3   # margin_ratio
        )

    def draw_pivots_current(self):
        """pivot만 간단하게 그리기"""
        has_current_image = self.current_image is not None
        has_landmark_manager = hasattr(self, 'landmark_manager')        
        if DEBUG_DRAWING_CURRENT:
            info("draw_current_pivots",f":image: {has_current_image}, landmark: {has_landmark_manager}")

        if not has_current_image or not has_landmark_manager:
            return
        
        landmarks = self.landmark_manager.get_current_landmarks()
        if not landmarks:
            return
        
        self._draw_pivots(
            self.canvas_original,
            self.current_image,
            landmarks,
            self.canvas_original_pos_x,
            self.canvas_original_pos_y,
            self.landmarks_items_original
        )

    def clear_overlays_current(self):
        """폴리곤과 pivot 모두 지우기"""
        if DEBUG_DRAWING_CURRENT:
            log("clear_overlays_current",f":")
        # ✅ 무조건 폴리곤 지우기!
        if hasattr(self, 'landmark_polygon_items') and 'original' in self.landmark_polygon_items:
            for item_id in list(self.landmark_polygon_items['original']):
                try:
                    self.canvas_original.delete(item_id)
                except Exception:
                    pass
            self.landmark_polygon_items['original'].clear()
            if hasattr(self, 'polygon_point_map_original'):
                self.polygon_point_map_original.clear()

        # ✅ 무조건 pivot 지우기!
        if hasattr(self, 'landmarks_items_original'):
            for item_id in list(self.landmarks_items_original):
                try:
                    self.canvas_original.delete(item_id)
                except Exception:
                    pass
            self.landmarks_items_original.clear()
        
        if hasattr(self, 'landmarks_items_transformed'):
            for item_id in list(self.landmarks_items_transformed):
                try:
                    self.canvas_original.delete(item_id)
                except Exception:
                    pass
            self.landmarks_items_transformed.clear()

    def draw_overlays_current(self):
        if DEBUG_DRAWING_CURRENT:
            log("draw_overlays_current",f":")

        self.clear_overlays_current()
        try:
            if self._is_polygon_display_enabled():
                self.draw_polygons_current()
            if self._is_pivot_display_enabled():
                self.draw_pivots_current()
            if self._is_guides_display_enabled():
                self._draw_guides()
            if self._is_bbox_frame_display_enabled():
                self._draw_bbox()
        except Exception as e:
            import traceback
            traceback.print_exc()