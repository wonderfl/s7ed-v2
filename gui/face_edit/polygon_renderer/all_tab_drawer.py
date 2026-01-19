"""
전체탭(all) 폴리곤 그리기 메서드
전체탭에 맞는 폴리곤 그리기 로직을 담당
"""
import math


class AllTabDrawerMixin:
    """전체탭 폴리곤 그리기 기능 Mixin"""
    
    def _draw_all_tab_polygons(self, canvas, image, landmarks, pos_x, pos_y, items_list, color, scale_x, scale_y, img_width, img_height, expansion_level, show_indices, bind_polygon_click_events, force_use_custom=False, iris_landmarks=None, iris_centers=None):
        """all 탭 폴리곤 그리기
        
        Args:
            iris_landmarks: 눈동자 랜드마크 (10개 또는 None)
            iris_centers: 눈동자 중앙 포인트 (2개 또는 None, Tesselation용)
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
            except AttributeError:
                # 구버전 MediaPipe에서는 지원하지 않을 수 있음
                LEFT_IRIS = []
                RIGHT_IRIS = []

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
                    iris_points = self._get_polygon_from_indices(
                        [], landmarks, img_width, img_height, scale_x, scale_y, pos_x, pos_y,
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
                if iris_centers is not None and len(iris_centers) == 2:
                    if iris_side == 'left':
                        center_pt = iris_centers[0]
                    else:
                        center_pt = iris_centers[1]
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
                    
                    center_radius = 8
                    center_id = canvas.create_oval(
                        canvas_x - center_radius,
                        canvas_y - center_radius,
                        canvas_x + center_radius,
                        canvas_y + center_radius,
                        fill="yellow",
                        outline="red",
                        width=2,
                        tags=("landmarks_polygon", f"iris_center_{iris_side}")
                    )
                    items_list.append(center_id)
                    
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
                            tags=("landmarks_polygon", f"iris_center_{iris_side}_text", f"iris_center_{iris_side}")
                        )
                        items_list.append(text_id)
                    
                    def on_iris_center_click(event):
                        print(f"[얼굴편집] {iris_side} 눈동자 중앙 포인트 클릭")
                        self.on_iris_center_drag_start(event, iris_side, canvas)
                        return "break"
                    
                    def on_iris_center_drag(event):
                        self.on_iris_center_drag(event, iris_side, canvas)
                        return "break"
                    
                    def on_iris_center_release(event):
                        self.on_iris_center_drag_end(event, iris_side, canvas)
                        return "break"
                    
                    canvas.tag_bind(center_id, "<Button-1>", on_iris_center_click)
                    canvas.tag_bind(center_id, "<B1-Motion>", on_iris_center_drag)
                    canvas.tag_bind(center_id, "<ButtonRelease-1>", on_iris_center_release)

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
                    iris_centers = landmarks[-2:]
            
            # 눈동자 체크박스가 선택되었을 때 중심점 그리기
            # iris_centers가 있으면 LEFT_IRIS/RIGHT_IRIS가 없어도 중심점을 그릴 수 있음
            if hasattr(self, 'show_left_iris') and self.show_left_iris.get():
                # Tesselation 모드가 아닐 때는 폴리곤도 그리지만, Tesselation 모드일 때는 중심점만 그리기
                # draw_iris 함수 호출
                draw_iris('left', LEFT_IRIS if LEFT_IRIS else [], '_left_iris_center_coord')
            
            if hasattr(self, 'show_right_iris') and self.show_right_iris.get():
                # Tesselation 모드가 아닐 때는 폴리곤도 그리지만, Tesselation 모드일 때는 중심점만 그리기
                # draw_iris 함수 호출
                draw_iris('right', RIGHT_IRIS if RIGHT_IRIS else [], '_right_iris_center_coord')
            
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
