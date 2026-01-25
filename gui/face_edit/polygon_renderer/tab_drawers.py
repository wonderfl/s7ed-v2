"""
탭별 폴리곤 그리기 메서드
각 탭에 맞는 폴리곤 그리기 로직을 담당 (전체탭 제외)
"""
import math

# 눈동자 렌더러 import
try:
    from ..iris_renderer import IrisRenderer
except ImportError:
    # 상대 import 실패 시 절대 import 시도
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from iris_renderer import IrisRenderer


class TabDrawersMixin:
    """탭별 폴리곤 그리기 기능 Mixin (전체탭 제외)"""
    
    def _draw_iris_center_fallback(self, canvas, iris_side, center_x, center_y, pos_x, pos_y, scale_x, scale_y, img_width, img_height, show_indices, items_list):
        """IrisRenderer 실패 시 fallback 중심점 그리기"""
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
            index_text = f"C-{iris_side[0].upper()}"
            text_id = canvas.create_text(
                canvas_x + text_offset,
                canvas_y - text_offset,
                text=index_text,
                fill="red",
                font=("Arial", 12, "bold"),
                tags=("landmarks_polygon", f"iris_center_{iris_side}_text", f"iris_center_{iris_side}")
            )
            items_list.append(text_id)
        
        # 이벤트 바인딩
        def on_iris_center_click(event):
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
    
    def _draw_eye_tab_polygons(self, canvas, image, landmarks, pos_x, pos_y, items_list, color, scale_x, scale_y, img_width, img_height, expansion_level, show_indices, bind_polygon_click_events, force_use_custom=False):
        """eye 탭 폴리곤 그리기"""
        # 눈 편집 시: MediaPipe 연결 정보를 사용해서 눈과 눈썹을 각각 별도 폴리곤으로 그리기
        try:
            import mediapipe as mp
            mp_face_mesh = mp.solutions.face_mesh
            LEFT_EYE = list(mp_face_mesh.FACEMESH_LEFT_EYE)
            RIGHT_EYE = list(mp_face_mesh.FACEMESH_RIGHT_EYE)
            LEFT_EYEBROW = list(mp_face_mesh.FACEMESH_LEFT_EYEBROW)
            RIGHT_EYEBROW = list(mp_face_mesh.FACEMESH_RIGHT_EYEBROW)

            # 눈 탭의 랜드마크 인덱스 수집 (눈과 눈동자만, 눈썹 제외)
            eye_indices = set()
            # 눈만 포함 (눈썹 제외)
            for idx1, idx2 in LEFT_EYE + RIGHT_EYE:
                eye_indices.add(idx1)
                eye_indices.add(idx2)

            # 눈동자 연결 정보 가져오기
            try:
                LEFT_IRIS = list(mp_face_mesh.FACEMESH_LEFT_IRIS)
                RIGHT_IRIS = list(mp_face_mesh.FACEMESH_RIGHT_IRIS)
            except AttributeError:
                LEFT_IRIS = []
                RIGHT_IRIS = []

            # 눈동자 연결 정보 추가 (중심점은 연결 정보에 포함되지 않음)
            # LandmarkManager를 통해 얼굴/눈동자 분리 확인
            iris_landmarks = self.landmark_manager.get_original_iris_landmarks()
            has_iris_landmarks = (iris_landmarks is not None and len(iris_landmarks) > 0)
            
            if LEFT_IRIS and RIGHT_IRIS and has_iris_landmarks:
                for idx1, idx2 in LEFT_IRIS + RIGHT_IRIS:
                    if idx1 < len(landmarks) and idx2 < len(landmarks):
                        eye_indices.add(idx1)
                        eye_indices.add(idx2)
                # 눈동자 중심점도 인덱스에 추가 (선택 가능하도록)
                eye_indices.add(468)  # 왼쪽 눈동자 중심
                eye_indices.add(473)  # 오른쪽 눈동자 중심

            # 폴리곤 그리기 헬퍼 함수
            def draw_polygon_with_click(points, tag_name, part_name, ti, polygon_indices=None):
                """폴리곤을 그리면서 클릭 이벤트 바인딩"""
                # 폴리곤에 포함된 포인트 인덱스를 polygon_point_map에 저장
                if polygon_indices is not None:
                    if canvas == self.canvas_original:
                        for idx in polygon_indices:
                            if idx < len(landmarks):
                                self.polygon_point_map_original.add(idx)
                    elif canvas == self.canvas_edited:
                        for idx in polygon_indices:
                            if idx < len(landmarks):
                                self.polygon_point_map_edited.add(idx)

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
                                bind_polygon_click_events(polygon_id, ti)
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
                        bind_polygon_click_events(polygon_id, ti)

            # 왼쪽 눈: 눈 자체 폴리곤 (삼각형 메쉬)
            left_eye_indices_set = set()
            for idx1, idx2 in LEFT_EYE:
                left_eye_indices_set.add(idx1)
                left_eye_indices_set.add(idx2)
            # 확장 레벨에 따라 주변 포인트 추가
            if expansion_level > 0:
                try:
                    import mediapipe as mp
                    mp_face_mesh = mp.solutions.face_mesh
                    tesselation = list(mp_face_mesh.FACEMESH_TESSELATION)
                    tesselation_graph = {}
                    for idx1, idx2 in tesselation:
                        if idx1 < len(landmarks) and idx2 < len(landmarks):
                            if idx1 not in tesselation_graph:
                                tesselation_graph[idx1] = []
                            if idx2 not in tesselation_graph:
                                tesselation_graph[idx2] = []
                            tesselation_graph[idx1].append(idx2)
                            tesselation_graph[idx2].append(idx1)
                    current_indices = left_eye_indices_set.copy()
                    for level in range(expansion_level):
                        next_level_indices = set()
                        for idx in current_indices:
                            if idx in tesselation_graph:
                                for neighbor in tesselation_graph[idx]:
                                    if neighbor < len(landmarks):
                                        next_level_indices.add(neighbor)
                        left_eye_indices_set.update(next_level_indices)
                        current_indices = next_level_indices
                except ImportError:
                    pass
            left_eye_points = self._get_polygon_from_indices(
                [], landmarks, img_width, img_height, scale_x, scale_y, pos_x, pos_y,
                use_mediapipe_connections=True, connections=LEFT_EYE, expansion_level=expansion_level
            )
            # draw_polygon_with_click 함수 내부에서 polygon_indices를 받아서 polygon_point_map에 저장함
            draw_polygon_with_click(left_eye_points, "polygon_left_eye", "왼쪽 눈", eye_indices, list(left_eye_indices_set))

            # 왼쪽 눈동자: 눈동자 폴리곤 (순환 경로)
            try:
                LEFT_IRIS = list(mp_face_mesh.FACEMESH_LEFT_IRIS)
            except AttributeError:
                LEFT_IRIS = []

            # LandmarkManager를 통해 얼굴/눈동자 분리 확인
            iris_landmarks = self.landmark_manager.get_original_iris_landmarks()
            has_iris_landmarks_left = (iris_landmarks is not None and len(iris_landmarks) > 0)
            
            if LEFT_IRIS and has_iris_landmarks_left:
                left_iris_indices_set = set()
                for idx1, idx2 in LEFT_IRIS:
                    if idx1 < len(landmarks) and idx2 < len(landmarks):
                        left_iris_indices_set.add(idx1)
                        left_iris_indices_set.add(idx2)
                # 눈동자 중심점(468)도 인덱스에 추가 (선택 가능하도록)
                if 468 < len(landmarks):
                    left_iris_indices_set.add(468)

                left_iris_points = self._get_polygon_from_indices(
                    [], landmarks, img_width, img_height, scale_x, scale_y, pos_x, pos_y,
                    use_mediapipe_connections=True, connections=LEFT_IRIS, expansion_level=0
                )
                draw_polygon_with_click(left_iris_points, "polygon_left_iris", "왼쪽 눈동자", eye_indices, list(left_iris_indices_set))

            # 오른쪽 눈: 눈 자체 폴리곤 (삼각형 메쉬)
            right_eye_indices_set = set()
            for idx1, idx2 in RIGHT_EYE:
                right_eye_indices_set.add(idx1)
                right_eye_indices_set.add(idx2)
            # 확장 레벨에 따라 주변 포인트 추가
            if expansion_level > 0:
                try:
                    import mediapipe as mp
                    mp_face_mesh = mp.solutions.face_mesh
                    tesselation = list(mp_face_mesh.FACEMESH_TESSELATION)
                    tesselation_graph = {}
                    for idx1, idx2 in tesselation:
                        if idx1 < len(landmarks) and idx2 < len(landmarks):
                            if idx1 not in tesselation_graph:
                                tesselation_graph[idx1] = []
                            if idx2 not in tesselation_graph:
                                tesselation_graph[idx2] = []
                            tesselation_graph[idx1].append(idx2)
                            tesselation_graph[idx2].append(idx1)
                    current_indices = right_eye_indices_set.copy()
                    for level in range(expansion_level):
                        next_level_indices = set()
                        for idx in current_indices:
                            if idx in tesselation_graph:
                                for neighbor in tesselation_graph[idx]:
                                    if neighbor < len(landmarks):
                                        next_level_indices.add(neighbor)
                        right_eye_indices_set.update(next_level_indices)
                        current_indices = next_level_indices
                except ImportError:
                    pass
            right_eye_points = self._get_polygon_from_indices(
                [], landmarks, img_width, img_height, scale_x, scale_y, pos_x, pos_y,
                use_mediapipe_connections=True, connections=RIGHT_EYE, expansion_level=expansion_level
            )
            # draw_polygon_with_click 함수 내부에서 polygon_indices를 받아서 polygon_point_map에 저장함
            draw_polygon_with_click(right_eye_points, "polygon_right_eye", "오른쪽 눈", eye_indices, list(right_eye_indices_set))

            # 오른쪽 눈동자: 눈동자 폴리곤 (순환 경로, 확장 레벨 없음)
            try:
                RIGHT_IRIS = list(mp_face_mesh.FACEMESH_RIGHT_IRIS)
            except AttributeError:
                RIGHT_IRIS = []

            # LandmarkManager를 통해 얼굴/눈동자 분리 확인
            iris_landmarks = self.landmark_manager.get_original_iris_landmarks()
            has_iris_landmarks = (iris_landmarks is not None and len(iris_landmarks) > 0)
            
            if RIGHT_IRIS and has_iris_landmarks:
                right_iris_indices_set = set()
                for idx1, idx2 in RIGHT_IRIS:
                    if idx1 < len(landmarks) and idx2 < len(landmarks):
                        right_iris_indices_set.add(idx1)
                        right_iris_indices_set.add(idx2)
                # 눈동자 중심점(473)도 인덱스에 추가 (선택 가능하도록)
                if 473 < len(landmarks):
                    right_iris_indices_set.add(473)

                right_iris_points = self._get_polygon_from_indices(
                    [], landmarks, img_width, img_height, scale_x, scale_y, pos_x, pos_y,
                    use_mediapipe_connections=True, connections=RIGHT_IRIS, expansion_level=0
                )
                draw_polygon_with_click(right_iris_points, "polygon_right_iris", "오른쪽 눈동자", eye_indices, list(right_iris_indices_set))

        except ImportError:
            # MediaPipe가 없으면 인덱스 기반으로 폴백
            LEFT_EYE_INDICES = [33, 7, 163, 144, 145, 153, 154, 155, 133, 173, 157, 158, 159, 160, 161, 246]
            RIGHT_EYE_INDICES = [362, 382, 381, 380, 374, 373, 390, 249, 263, 466, 388, 387, 386, 385, 384, 398]
            # 눈 탭: 눈과 눈동자만 (눈썹 제외)
            eye_indices_set = set(LEFT_EYE_INDICES + RIGHT_EYE_INDICES)
            # 눈동자 인덱스 추가 (MediaPipe 정의 사용)
            try:
                from utils.face_morphing.region_extraction import get_iris_indices
                left_iris_indices, right_iris_indices = get_iris_indices()
                iris_indices = left_iris_indices + right_iris_indices
                min_iris_index = min(iris_indices) if iris_indices else 468
            except ImportError:
                # 폴백: 하드코딩된 인덱스 사용 (실제 MediaPipe 정의: LEFT_IRIS=[474,475,476,477], RIGHT_IRIS=[469,470,471,472])
                iris_indices = [469, 470, 471, 472, 474, 475, 476, 477]
                min_iris_index = 469
            if len(landmarks) > min_iris_index:
                for idx in iris_indices:
                    if idx < len(landmarks):
                        eye_indices_set.add(idx)

            # 왼쪽 눈 폴리곤
            left_eye_points = self._get_polygon_from_indices(LEFT_EYE_INDICES, landmarks, img_width, img_height, scale_x, scale_y, pos_x, pos_y)
            if left_eye_points and len(left_eye_points) >= 3:
                polygon_id = canvas.create_polygon(
                    left_eye_points,
                    fill="",
                    outline=color,
                    width=2,
                    tags=("landmarks_polygon", "polygon_left_eye")
                )
                items_list.append(polygon_id)
                bind_polygon_click_events(polygon_id, eye_indices_set)

            # 오른쪽 눈 폴리곤
            right_eye_points = self._get_polygon_from_indices(RIGHT_EYE_INDICES, landmarks, img_width, img_height, scale_x, scale_y, pos_x, pos_y)
            if right_eye_points and len(right_eye_points) >= 3:
                polygon_id = canvas.create_polygon(
                    right_eye_points,
                    fill="",
                    outline=color,
                    width=2,
                    tags=("landmarks_polygon", "polygon_right_eye")
                )
                items_list.append(polygon_id)
                bind_polygon_click_events(polygon_id, eye_indices_set)


    def _draw_nose_tab_polygons(self, canvas, image, landmarks, pos_x, pos_y, items_list, color, scale_x, scale_y, img_width, img_height, expansion_level, show_indices, bind_polygon_click_events, force_use_custom=False):
        """nose 탭 폴리곤 그리기"""
        # 코 영역: MediaPipe 연결 정보 사용
        try:
            import mediapipe as mp
            mp_face_mesh = mp.solutions.face_mesh
            NOSE = list(mp_face_mesh.FACEMESH_NOSE)
            # 코 탭의 랜드마크 인덱스 수집
            nose_indices_set = set()
            for idx1, idx2 in NOSE:
                nose_indices_set.add(idx1)
                nose_indices_set.add(idx2)

            # 확장 레벨에 따라 주변 포인트 추가
            if expansion_level > 0:
                try:
                    import mediapipe as mp
                    mp_face_mesh = mp.solutions.face_mesh
                    tesselation = list(mp_face_mesh.FACEMESH_TESSELATION)
                    tesselation_graph = {}
                    for idx1, idx2 in tesselation:
                        if idx1 < len(landmarks) and idx2 < len(landmarks):
                            if idx1 not in tesselation_graph:
                                tesselation_graph[idx1] = []
                            if idx2 not in tesselation_graph:
                                tesselation_graph[idx2] = []
                            tesselation_graph[idx1].append(idx2)
                            tesselation_graph[idx2].append(idx1)
                    current_indices = nose_indices_set.copy()
                    for level in range(expansion_level):
                        next_level_indices = set()
                        for idx in current_indices:
                            if idx in tesselation_graph:
                                for neighbor in tesselation_graph[idx]:
                                    if neighbor < len(landmarks):
                                        next_level_indices.add(neighbor)
                        nose_indices_set.update(next_level_indices)
                        current_indices = next_level_indices
                except ImportError:
                    pass

            # 폴리곤에 포함된 포인트 인덱스를 polygon_point_map에 저장
            if canvas == self.canvas_original:
                for idx in nose_indices_set:
                    if idx < len(landmarks):
                        self.polygon_point_map_original.add(idx)
            elif canvas == self.canvas_edited:
                for idx in nose_indices_set:
                    if idx < len(landmarks):
                        self.polygon_point_map_edited.add(idx)

            nose_points = self._get_polygon_from_indices(
                [], landmarks, img_width, img_height, scale_x, scale_y, pos_x, pos_y,
                use_mediapipe_connections=True, connections=NOSE, expansion_level=expansion_level
            )
            if nose_points and len(nose_points) >= 3:
                # 삼각형 메쉬인지 확인 (4의 배수면 삼각형 메쉬)
                if len(nose_points) % 4 == 0:
                    # 삼각형 메쉬: 4개씩 나눠서 각 삼각형을 개별 폴리곤으로 그리기
                    triangle_count = 0
                    for i in range(0, len(nose_points), 4):
                        if i + 4 <= len(nose_points):
                            triangle_points = nose_points[i:i+4]
                            polygon_id = canvas.create_polygon(
                                triangle_points,
                                fill="",
                                outline=color,
                                width=1,
                                tags=("landmarks_polygon", "polygon_nose")
                            )
                            items_list.append(polygon_id)
                            bind_polygon_click_events(polygon_id, nose_indices_set)
                            triangle_count += 1
                else:
                    # 단일 폴리곤 (폴백)
                    polygon_id = canvas.create_polygon(
                        nose_points,
                        fill="",
                        outline=color,
                        width=2,
                        tags=("landmarks_polygon", "polygon_nose")
                    )
                    items_list.append(polygon_id)
                    bind_polygon_click_events(polygon_id, nose_indices_set)
        except ImportError:
            # 폴백: 인덱스 기반
            NOSE_INDICES = [8, 240, 98, 164, 327, 460, 4, 19, 20, 94, 102, 115, 131, 134, 141, 220, 235, 236, 281, 305, 358, 360, 363]
            nose_indices_set = set(NOSE_INDICES)
            # 폴리곤에 포함된 포인트 인덱스를 polygon_point_map에 저장
            if canvas == self.canvas_original:
                for idx in nose_indices_set:
                    if idx < len(landmarks):
                        self.polygon_point_map_original.add(idx)
            elif canvas == self.canvas_edited:
                for idx in nose_indices_set:
                    if idx < len(landmarks):
                        self.polygon_point_map_edited.add(idx)
            nose_points = self._get_polygon_from_indices(NOSE_INDICES, landmarks, img_width, img_height, scale_x, scale_y, pos_x, pos_y)
            if nose_points and len(nose_points) >= 3:
                polygon_id = canvas.create_polygon(
                    nose_points,
                    fill="",
                    outline=color,
                    width=2,
                    tags=("landmarks_polygon", "polygon_nose")
                )
                items_list.append(polygon_id)
                bind_polygon_click_events(polygon_id, nose_indices_set)


    def _draw_mouth_tab_polygons(self, canvas, image, landmarks, pos_x, pos_y, items_list, color, scale_x, scale_y, img_width, img_height, expansion_level, show_indices, bind_polygon_click_events, force_use_custom=False):
        """mouth 탭 폴리곤 그리기"""
        # 입 영역: MediaPipe 연결 정보 사용
        try:
            import mediapipe as mp
            mp_face_mesh = mp.solutions.face_mesh
            LIPS = list(mp_face_mesh.FACEMESH_LIPS)
            # 입 탭의 랜드마크 인덱스 수집
            lips_indices_set = set()
            for idx1, idx2 in LIPS:
                lips_indices_set.add(idx1)
                lips_indices_set.add(idx2)

            # 확장 레벨에 따라 주변 포인트 추가
            if expansion_level > 0:
                try:
                    import mediapipe as mp
                    mp_face_mesh = mp.solutions.face_mesh
                    tesselation = list(mp_face_mesh.FACEMESH_TESSELATION)
                    tesselation_graph = {}
                    for idx1, idx2 in tesselation:
                        if idx1 < len(landmarks) and idx2 < len(landmarks):
                            if idx1 not in tesselation_graph:
                                tesselation_graph[idx1] = []
                            if idx2 not in tesselation_graph:
                                tesselation_graph[idx2] = []
                            tesselation_graph[idx1].append(idx2)
                            tesselation_graph[idx2].append(idx1)
                    current_indices = lips_indices_set.copy()
                    for level in range(expansion_level):
                        next_level_indices = set()
                        for idx in current_indices:
                            if idx in tesselation_graph:
                                for neighbor in tesselation_graph[idx]:
                                    if neighbor < len(landmarks):
                                        next_level_indices.add(neighbor)
                        lips_indices_set.update(next_level_indices)
                        current_indices = next_level_indices
                except ImportError:
                    pass

            # 폴리곤에 포함된 포인트 인덱스를 polygon_point_map에 저장
            if canvas == self.canvas_original:
                for idx in lips_indices_set:
                    if idx < len(landmarks):
                        self.polygon_point_map_original.add(idx)
            elif canvas == self.canvas_edited:
                for idx in lips_indices_set:
                    if idx < len(landmarks):
                        self.polygon_point_map_edited.add(idx)

            lips_points = self._get_polygon_from_indices(
                [], landmarks, img_width, img_height, scale_x, scale_y, pos_x, pos_y,
                use_mediapipe_connections=True, connections=LIPS, expansion_level=expansion_level
            )
            if lips_points and len(lips_points) >= 3:
                # 삼각형 메쉬인지 확인 (4의 배수면 삼각형 메쉬)
                if len(lips_points) % 4 == 0:
                    # 삼각형 메쉬: 4개씩 나눠서 각 삼각형을 개별 폴리곤으로 그리기
                    triangle_count = 0
                    for i in range(0, len(lips_points), 4):
                        if i + 4 <= len(lips_points):
                            triangle_points = lips_points[i:i+4]
                            polygon_id = canvas.create_polygon(
                                triangle_points,
                                fill="",
                                outline=color,
                                width=1,
                                tags=("landmarks_polygon", "polygon_lips")
                            )
                            items_list.append(polygon_id)
                            bind_polygon_click_events(polygon_id, lips_indices_set)
                            triangle_count += 1
                    from utils.logger import get_logger
                    logger = get_logger('얼굴편집')
                    logger.debug(f"입 삼각형 메쉬 그리기: {triangle_count}개 삼각형")
                else:
                    # 단일 폴리곤 (폴백)
                    polygon_id = canvas.create_polygon(
                        lips_points,
                        fill="",
                        outline=color,
                        width=2,
                        tags=("landmarks_polygon", "polygon_lips")
                    )
                    items_list.append(polygon_id)
                    bind_polygon_click_events(polygon_id, lips_indices_set)
        except ImportError:
            # 폴백: 인덱스 기반
            OUTER_LIP_INDICES = [61, 185, 40, 39, 37, 0, 267, 269, 270, 409, 291, 375, 321, 405, 314, 17, 84, 181, 91, 146]
            INNER_LIP_INDICES = [78, 191, 80, 81, 82, 13, 312, 311, 310, 415, 308, 324, 318, 402, 317, 14, 87, 178, 88, 95]
            MOUTH_ALL_INDICES = list(set(OUTER_LIP_INDICES + INNER_LIP_INDICES))
            lips_indices_set = set(MOUTH_ALL_INDICES)
            # 폴리곤에 포함된 포인트 인덱스를 polygon_point_map에 저장
            if canvas == self.canvas_original:
                for idx in lips_indices_set:
                    if idx < len(landmarks):
                        self.polygon_point_map_original.add(idx)
            elif canvas == self.canvas_edited:
                for idx in lips_indices_set:
                    if idx < len(landmarks):
                        self.polygon_point_map_edited.add(idx)
            lips_points = self._get_polygon_from_indices(MOUTH_ALL_INDICES, landmarks, img_width, img_height, scale_x, scale_y, pos_x, pos_y)
            if lips_points and len(lips_points) >= 3:
                polygon_id = canvas.create_polygon(
                    lips_points,
                    fill="",
                    outline=color,
                    width=2,
                    tags=("landmarks_polygon", "polygon_lips")
                )
                items_list.append(polygon_id)
                bind_polygon_click_events(polygon_id, lips_indices_set)


    def _draw_eyebrow_tab_polygons(self, canvas, image, landmarks, pos_x, pos_y, items_list, color, scale_x, scale_y, img_width, img_height, expansion_level, show_indices, bind_polygon_click_events, force_use_custom=False):
        """eyebrow 탭 폴리곤 그리기"""
        # 눈썹 영역: MediaPipe 연결 정보 사용
        try:
            import mediapipe as mp
            mp_face_mesh = mp.solutions.face_mesh
            LEFT_EYEBROW = list(mp_face_mesh.FACEMESH_LEFT_EYEBROW)
            RIGHT_EYEBROW = list(mp_face_mesh.FACEMESH_RIGHT_EYEBROW)

            # 눈썹 탭의 랜드마크 인덱스 수집
            eyebrow_indices_set = set()
            for idx1, idx2 in LEFT_EYEBROW + RIGHT_EYEBROW:
                eyebrow_indices_set.add(idx1)
                eyebrow_indices_set.add(idx2)

            # 확장 레벨에 따라 주변 포인트 추가
            if expansion_level > 0:
                try:
                    import mediapipe as mp
                    mp_face_mesh = mp.solutions.face_mesh
                    tesselation = list(mp_face_mesh.FACEMESH_TESSELATION)
                    tesselation_graph = {}
                    for idx1, idx2 in tesselation:
                        if idx1 < len(landmarks) and idx2 < len(landmarks):
                            if idx1 not in tesselation_graph:
                                tesselation_graph[idx1] = []
                            if idx2 not in tesselation_graph:
                                tesselation_graph[idx2] = []
                            tesselation_graph[idx1].append(idx2)
                            tesselation_graph[idx2].append(idx1)
                    current_indices = eyebrow_indices_set.copy()
                    for level in range(expansion_level):
                        next_level_indices = set()
                        for idx in current_indices:
                            if idx in tesselation_graph:
                                for neighbor in tesselation_graph[idx]:
                                    if neighbor < len(landmarks):
                                        next_level_indices.add(neighbor)
                        eyebrow_indices_set.update(next_level_indices)
                        current_indices = next_level_indices
                except ImportError:
                    pass

            # 폴리곤에 포함된 포인트 인덱스를 polygon_point_map에 저장
            if canvas == self.canvas_original:
                for idx in eyebrow_indices_set:
                    if idx < len(landmarks):
                        self.polygon_point_map_original.add(idx)
            elif canvas == self.canvas_edited:
                for idx in eyebrow_indices_set:
                    if idx < len(landmarks):
                        self.polygon_point_map_edited.add(idx)

            # 왼쪽 눈썹: 눈썹 폴리곤 (삼각형 메쉬)
            left_eyebrow_points = self._get_polygon_from_indices(
                [], landmarks, img_width, img_height, scale_x, scale_y, pos_x, pos_y,
                use_mediapipe_connections=True, connections=LEFT_EYEBROW, expansion_level=expansion_level
            )
            if left_eyebrow_points and len(left_eyebrow_points) >= 3:
                # 삼각형 메쉬인지 확인 (4의 배수면 삼각형 메쉬)
                if len(left_eyebrow_points) % 4 == 0:
                    # 삼각형 메쉬: 4개씩 나눠서 각 삼각형을 개별 폴리곤으로 그리기
                    triangle_count = 0
                    for i in range(0, len(left_eyebrow_points), 4):
                        if i + 4 <= len(left_eyebrow_points):
                            triangle_points = left_eyebrow_points[i:i+4]
                            polygon_id = canvas.create_polygon(
                                triangle_points,
                                fill="",
                                outline=color,
                                width=1,
                                tags=("landmarks_polygon", "polygon_left_eyebrow")
                            )
                            items_list.append(polygon_id)
                            bind_polygon_click_events(polygon_id, eyebrow_indices_set)
                            triangle_count += 1
                else:
                    # 단일 폴리곤 (폴백)
                    polygon_id = canvas.create_polygon(
                        left_eyebrow_points,
                        fill="",
                        outline=color,
                        width=2,
                        tags=("landmarks_polygon", "polygon_left_eyebrow")
                    )
                    items_list.append(polygon_id)
                    bind_polygon_click_events(polygon_id, eyebrow_indices_set)

            # 오른쪽 눈썹: 눈썹 폴리곤 (삼각형 메쉬)
            right_eyebrow_points = self._get_polygon_from_indices(
                [], landmarks, img_width, img_height, scale_x, scale_y, pos_x, pos_y,
                use_mediapipe_connections=True, connections=RIGHT_EYEBROW, expansion_level=expansion_level
            )
            if right_eyebrow_points and len(right_eyebrow_points) >= 3:
                # 삼각형 메쉬인지 확인 (4의 배수면 삼각형 메쉬)
                if len(right_eyebrow_points) % 4 == 0:
                    # 삼각형 메쉬: 4개씩 나눠서 각 삼각형을 개별 폴리곤으로 그리기
                    triangle_count = 0
                    for i in range(0, len(right_eyebrow_points), 4):
                        if i + 4 <= len(right_eyebrow_points):
                            triangle_points = right_eyebrow_points[i:i+4]
                            polygon_id = canvas.create_polygon(
                                triangle_points,
                                fill="",
                                outline=color,
                                width=1,
                                tags=("landmarks_polygon", "polygon_right_eyebrow")
                            )
                            items_list.append(polygon_id)
                            bind_polygon_click_events(polygon_id, eyebrow_indices_set)
                            triangle_count += 1
                else:
                    # 단일 폴리곤 (폴백)
                    polygon_id = canvas.create_polygon(
                        right_eyebrow_points,
                        fill="",
                        outline=color,
                        width=2,
                        tags=("landmarks_polygon", "polygon_right_eyebrow")
                    )
                    items_list.append(polygon_id)
                    bind_polygon_click_events(polygon_id, eyebrow_indices_set)

        except ImportError:
            # MediaPipe가 없으면 인덱스 기반으로 폴백
            LEFT_EYEBROW_INDICES = [70, 63, 105, 66, 107, 55, 65, 52, 53, 46]
            RIGHT_EYEBROW_INDICES = [300, 293, 334, 296, 336, 285, 295, 282, 283, 276]
            eyebrow_indices_set = set(LEFT_EYEBROW_INDICES + RIGHT_EYEBROW_INDICES)
            # 폴리곤에 포함된 포인트 인덱스를 polygon_point_map에 저장
            if canvas == self.canvas_original:
                for idx in eyebrow_indices_set:
                    if idx < len(landmarks):
                        self.polygon_point_map_original.add(idx)
            elif canvas == self.canvas_edited:
                for idx in eyebrow_indices_set:
                    if idx < len(landmarks):
                        self.polygon_point_map_edited.add(idx)

            # 왼쪽 눈썹 폴리곤
            left_eyebrow_points = self._get_polygon_from_indices(LEFT_EYEBROW_INDICES, landmarks, img_width, img_height, scale_x, scale_y, pos_x, pos_y)
            if left_eyebrow_points and len(left_eyebrow_points) >= 3:
                polygon_id = canvas.create_polygon(
                    left_eyebrow_points,
                    fill="",
                    outline=color,
                    width=2,
                    tags=("landmarks_polygon", "polygon_left_eyebrow")
                )
                items_list.append(polygon_id)
                bind_polygon_click_events(polygon_id, eyebrow_indices_set)

            # 오른쪽 눈썹 폴리곤
            right_eyebrow_points = self._get_polygon_from_indices(RIGHT_EYEBROW_INDICES, landmarks, img_width, img_height, scale_x, scale_y, pos_x, pos_y)
            if right_eyebrow_points and len(right_eyebrow_points) >= 3:
                polygon_id = canvas.create_polygon(
                    right_eyebrow_points,
                    fill="",
                    outline=color,
                    width=2,
                    tags=("landmarks_polygon", "polygon_right_eyebrow")
                )
                items_list.append(polygon_id)
                bind_polygon_click_events(polygon_id, eyebrow_indices_set)
                from utils.logger import get_logger
                logger = get_logger('얼굴편집')
                logger.debug(f"오른쪽 눈썹 폴리곤 그리기 (폴백): {len(right_eyebrow_points)}개 포인트")


    def _draw_jaw_tab_polygons(self, canvas, image, landmarks, pos_x, pos_y, items_list, color, scale_x, scale_y, img_width, img_height, expansion_level, show_indices, bind_polygon_click_events, force_use_custom=False):
        """jaw 탭 폴리곤 그리기"""
        # 턱선 영역: FACE_OVAL에서 턱선 부분만 필터링
        try:
            import mediapipe as mp
            mp_face_mesh = mp.solutions.face_mesh
            FACE_OVAL = list(mp_face_mesh.FACEMESH_FACE_OVAL)

            # 턱선 필터링: 눈 중심을 기준으로 아래쪽 부분만 사용 (귀까지 포함)
            if landmarks and len(landmarks) > 4:
                # 눈 중심의 y 좌표를 기준으로 사용 (귀까지 포함하기 위해)
                left_eye_indices = [33, 7, 163, 144, 145, 153, 154, 155, 133, 173, 157, 158, 159, 160, 161, 246]
                right_eye_indices = [362, 382, 381, 380, 374, 373, 390, 249, 263, 466, 388, 387, 386, 385, 384, 398]

                eye_y_values = []
                for idx in left_eye_indices + right_eye_indices:
                    if idx < len(landmarks):
                        if isinstance(landmarks[idx], tuple):
                            eye_y_values.append(landmarks[idx][1])
                        else:
                            eye_y_values.append(landmarks[idx].y * img_height)

                # 기준 y 좌표: 눈 중심의 y 좌표 (귀까지 포함하기 위해 눈 중심을 기준으로)
                if eye_y_values:
                    # 눈의 평균 y 좌표를 기준으로 사용
                    reference_y = sum(eye_y_values) / len(eye_y_values)
                else:
                    # 눈 인덱스를 찾을 수 없으면 코 끝을 기준으로
                    nose_tip_idx = 4
                    if isinstance(landmarks[nose_tip_idx], tuple):
                        reference_y = landmarks[nose_tip_idx][1]
                    else:
                        reference_y = landmarks[nose_tip_idx].y * img_height

                # FACE_OVAL 연결 중에서 기준 y 좌표보다 아래쪽에 있는 연결만 필터링
                jaw_connections = []
                jaw_indices_set = set()

                for idx1, idx2 in FACE_OVAL:
                    if idx1 < len(landmarks) and idx2 < len(landmarks):
                        # 각 포인트의 y 좌표 확인
                        if isinstance(landmarks[idx1], tuple):
                            y1 = landmarks[idx1][1]
                            y2 = landmarks[idx2][1]
                        else:
                            y1 = landmarks[idx1].y * img_height
                            y2 = landmarks[idx2].y * img_height

                        # 두 포인트 중 하나라도 기준 y 좌표보다 아래쪽이면 턱선으로 간주
                        # (귀까지 포함하기 위해 약간의 여유를 둠)
                        if y1 >= reference_y - (img_height * 0.02) or y2 >= reference_y - (img_height * 0.02):
                            jaw_connections.append((idx1, idx2))
                            jaw_indices_set.add(idx1)
                            jaw_indices_set.add(idx2)
            else:
                # 랜드마크가 없으면 전체 FACE_OVAL 사용
                jaw_connections = FACE_OVAL
                jaw_indices_set = set()
                for idx1, idx2 in FACE_OVAL:
                    jaw_indices_set.add(idx1)
                    jaw_indices_set.add(idx2)

            # 확장 레벨에 따라 주변 포인트 추가
            if expansion_level > 0:
                try:
                    import mediapipe as mp
                    mp_face_mesh = mp.solutions.face_mesh
                    tesselation = list(mp_face_mesh.FACEMESH_TESSELATION)
                    tesselation_graph = {}
                    for idx1, idx2 in tesselation:
                        if idx1 < len(landmarks) and idx2 < len(landmarks):
                            if idx1 not in tesselation_graph:
                                tesselation_graph[idx1] = []
                            if idx2 not in tesselation_graph:
                                tesselation_graph[idx2] = []
                            tesselation_graph[idx1].append(idx2)
                            tesselation_graph[idx2].append(idx1)
                    current_indices = jaw_indices_set.copy()
                    for level in range(expansion_level):
                        next_level_indices = set()
                        for idx in current_indices:
                            if idx in tesselation_graph:
                                for neighbor in tesselation_graph[idx]:
                                    if neighbor < len(landmarks):
                                        next_level_indices.add(neighbor)
                        jaw_indices_set.update(next_level_indices)
                        current_indices = next_level_indices
                except ImportError:
                    pass

            # 폴리곤에 포함된 포인트 인덱스를 polygon_point_map에 저장
            if canvas == self.canvas_original:
                for idx in jaw_indices_set:
                    if idx < len(landmarks):
                        self.polygon_point_map_original.add(idx)
            elif canvas == self.canvas_edited:
                for idx in jaw_indices_set:
                    if idx < len(landmarks):
                        self.polygon_point_map_edited.add(idx)

            jaw_points = self._get_polygon_from_indices(
                [], landmarks, img_width, img_height, scale_x, scale_y, pos_x, pos_y,
                use_mediapipe_connections=True, connections=jaw_connections, expansion_level=expansion_level
            )
            if jaw_points and len(jaw_points) >= 3:
                # 삼각형 메쉬인지 확인 (4의 배수면 삼각형 메쉬)
                if len(jaw_points) % 4 == 0:
                    # 삼각형 메쉬: 4개씩 나눠서 각 삼각형을 개별 폴리곤으로 그리기
                    triangle_count = 0
                    for i in range(0, len(jaw_points), 4):
                        if i + 4 <= len(jaw_points):
                            triangle_points = jaw_points[i:i+4]
                            polygon_id = canvas.create_polygon(
                                triangle_points,
                                fill="",
                                outline=color,
                                width=1,
                                tags=("landmarks_polygon", "polygon_jaw")
                            )
                            items_list.append(polygon_id)
                            bind_polygon_click_events(polygon_id, jaw_indices_set)
                            triangle_count += 1
                    from utils.logger import get_logger
                    logger = get_logger('얼굴편집')
                    logger.debug(f"턱선 삼각형 메쉬 그리기: {triangle_count}개 삼각형")
                else:
                    # 단일 폴리곤 (폴백)
                    polygon_id = canvas.create_polygon(
                        jaw_points,
                        fill="",
                        outline=color,
                        width=2,
                        tags=("landmarks_polygon", "polygon_jaw")
                    )
                    items_list.append(polygon_id)
                    bind_polygon_click_events(polygon_id, jaw_indices_set)
        except ImportError:
            # 폴백: 인덱스 기반 (0-16)
            jaw_indices = list(range(17))  # 0-16
            jaw_indices_set = set(jaw_indices)
            # 폴리곤에 포함된 포인트 인덱스를 polygon_point_map에 저장
            if canvas == self.canvas_original:
                for idx in jaw_indices_set:
                    if idx < len(landmarks):
                        self.polygon_point_map_original.add(idx)
            elif canvas == self.canvas_edited:
                for idx in jaw_indices_set:
                    if idx < len(landmarks):
                        self.polygon_point_map_edited.add(idx)
            jaw_points = self._get_polygon_from_indices(jaw_indices, landmarks, img_width, img_height, scale_x, scale_y, pos_x, pos_y)
            if jaw_points and len(jaw_points) >= 3:
                polygon_id = canvas.create_polygon(
                    jaw_points,
                    fill="",
                    outline=color,
                    width=2,
                    tags=("landmarks_polygon", "polygon_jaw")
                )
                items_list.append(polygon_id)
                bind_polygon_click_events(polygon_id, jaw_indices_set)


    def _draw_iris_tab_polygons(self, canvas, image, landmarks, pos_x, pos_y, items_list, color, scale_x, scale_y, img_width, img_height, expansion_level, show_indices, bind_polygon_click_events, force_use_custom=False, iris_centers=None, clamping_enabled=True, margin_ratio=0.3):
        """iris 탭 폴리곤 그리기 - 눈동자만 표시
        
        Args:
            clamping_enabled: 눈동자 이동 범위 제한 활성화 여부
            margin_ratio: 눈동자 이동 범위 제한 마진 비율 (0.0 ~ 1.0)
        """
        try:
            import mediapipe as mp
            mp_face_mesh = mp.solutions.face_mesh
            
            # 눈동자 연결 정보 가져오기
            try:
                LEFT_IRIS = list(mp_face_mesh.FACEMESH_LEFT_IRIS)
                RIGHT_IRIS = list(mp_face_mesh.FACEMESH_RIGHT_IRIS)
            except AttributeError:
                LEFT_IRIS = []
                RIGHT_IRIS = []
            
            # LandmarkManager를 통해 얼굴/눈동자 분리 확인
            iris_landmarks = self.landmark_manager.get_original_iris_landmarks()
            has_iris_landmarks = (iris_landmarks is not None and len(iris_landmarks) > 0)
            
            if not LEFT_IRIS or not RIGHT_IRIS or not has_iris_landmarks:
                return
            
            # 눈동자 인덱스 수집
            iris_indices = set()
            left_iris_indices_set = set()
            right_iris_indices_set = set()
            
            for idx1, idx2 in LEFT_IRIS:
                if idx1 < len(landmarks) and idx2 < len(landmarks):
                    left_iris_indices_set.add(idx1)
                    left_iris_indices_set.add(idx2)
                    iris_indices.add(idx1)
                    iris_indices.add(idx2)
            
            for idx1, idx2 in RIGHT_IRIS:
                if idx1 < len(landmarks) and idx2 < len(landmarks):
                    right_iris_indices_set.add(idx1)
                    right_iris_indices_set.add(idx2)
                    iris_indices.add(idx1)
                    iris_indices.add(idx2)
            
            # 폴리곤에 포함된 포인트 인덱스를 polygon_point_map에 저장
            if canvas == self.canvas_original:
                for idx in iris_indices:
                    if idx < len(landmarks):
                        self.polygon_point_map_original.add(idx)
            elif canvas == self.canvas_edited:
                for idx in iris_indices:
                    if idx < len(landmarks):
                        self.polygon_point_map_edited.add(idx)
            
            # 왼쪽 눈동자 중심점 가져오기
            left_iris_center_current = None
            if iris_centers is not None and len(iris_centers) == 2:
                # iris_centers[1] = 화면상 왼쪽 눈동자 중심
                center_pt = iris_centers[1]
                if isinstance(center_pt, tuple):
                    left_iris_center_current = center_pt
                else:
                    left_iris_center_current = (center_pt.x * img_width, center_pt.y * img_height)
            elif len(landmarks) == 470: # Tesselation 모드 (470개 구조): landmarks[469]에서 직접 가져오기
                center_pt = landmarks[469] # 화면상 왼쪽 = landmarks[469]
                if hasattr(center_pt, 'x'):
                    left_iris_center_current = (center_pt.x * img_width, center_pt.y * img_height)
                else:
                    left_iris_center_current = center_pt
            
            # 눈꺼풀 랜드마크 가져오기
            try:
                LEFT_EYE = list(mp_face_mesh.FACEMESH_LEFT_EYE)
                # FACEMESH_LEFT_EYE는 [(idx1, idx2), ...] 형태이므로 평탄화
                left_eye_indices = set()
                for idx1, idx2 in LEFT_EYE:
                    left_eye_indices.add(idx1)
                    left_eye_indices.add(idx2)
                left_eye_landmarks = [landmarks[i] for i in left_eye_indices if i < len(landmarks)]
            except AttributeError:
                left_eye_landmarks = []

            # 원본 왼쪽 눈동자 윤곽 랜드마크 추출
            original_left_iris_landmarks = []
            for idx in sorted(left_iris_indices_set):
                if idx < len(landmarks):
                    original_left_iris_landmarks.append(landmarks[idx])

            # 눈동자 윤곽 재계산
            if left_iris_center_current and left_eye_landmarks and original_left_iris_landmarks:
                adjusted_landmarks_left_iris = self.calculate_iris_contour(
                    left_iris_center_current, left_eye_landmarks, original_left_iris_landmarks, img_width, img_height
                )
            else:
                adjusted_landmarks_left_iris = landmarks
            
            # _get_polygon_from_indices 호출 시 조정된 랜드마크 사용
            left_iris_points = self._get_polygon_from_indices(
                [], adjusted_landmarks_left_iris, img_width, img_height, scale_x, scale_y, pos_x, pos_y,
                use_mediapipe_connections=True, connections=LEFT_IRIS, expansion_level=0
            )

            if left_iris_points and len(left_iris_points) >= 3:
                polygon_id = canvas.create_polygon(
                    left_iris_points,
                    fill="",
                    outline=color,
                    width=2,
                    tags=("landmarks_polygon", "polygon_left_iris")
                )
                items_list.append(polygon_id)
                bind_polygon_click_events(polygon_id, list(left_iris_indices_set))
            
            # 오른쪽 눈동자 중심점 가져오기
            right_iris_center_current = None
            if iris_centers is not None and len(iris_centers) == 2:
                # iris_centers[0] = 화면상 오른쪽 눈동자 중심
                center_pt = iris_centers[0]
                if isinstance(center_pt, tuple):
                    right_iris_center_current = center_pt
                else:
                    right_iris_center_current = (center_pt.x * img_width, center_pt.y * img_height)
            elif len(landmarks) == 470: # Tesselation 모드 (470개 구조): landmarks[468]에서 직접 가져오기
                center_pt = landmarks[468] # 화면상 오른쪽 = landmarks[468]
                if hasattr(center_pt, 'x'):
                    right_iris_center_current = (center_pt.x * img_width, center_pt.y * img_height)
                else:
                    right_iris_center_current = center_pt
            
            # 눈꺼풀 랜드마크 가져오기
            try:
                RIGHT_EYE = list(mp_face_mesh.FACEMESH_RIGHT_EYE)
                # FACEMESH_RIGHT_EYE는 [(idx1, idx2), ...] 형태이므로 평탄화
                right_eye_indices = set()
                for idx1, idx2 in RIGHT_EYE:
                    right_eye_indices.add(idx1)
                    right_eye_indices.add(idx2)
                right_eye_landmarks = [landmarks[i] for i in right_eye_indices if i < len(landmarks)]
            except AttributeError:
                right_eye_landmarks = []

            # 원본 오른쪽 눈동자 윤곽 랜드마크 추출
            original_right_iris_landmarks = []
            for idx in sorted(right_iris_indices_set):
                if idx < len(landmarks):
                    original_right_iris_landmarks.append(landmarks[idx])

            # 눈동자 윤곽 재계산
            if right_iris_center_current and right_eye_landmarks and original_right_iris_landmarks:
                adjusted_landmarks_right_iris = self.calculate_iris_contour(
                    right_iris_center_current, right_eye_landmarks, original_right_iris_landmarks, img_width, img_height
                )
            else:
                adjusted_landmarks_right_iris = landmarks

            # _get_polygon_from_indices 호출 시 조정된 랜드마크 사용
            right_iris_points = self._get_polygon_from_indices(
                [], adjusted_landmarks_right_iris, img_width, img_height, scale_x, scale_y, pos_x, pos_y,
                use_mediapipe_connections=True, connections=RIGHT_IRIS, expansion_level=0
            )

            if right_iris_points and len(right_iris_points) >= 3:
                polygon_id = canvas.create_polygon(
                    right_iris_points,
                    fill="",
                    outline=color,
                    width=2,
                    tags=("landmarks_polygon", "polygon_right_iris")
                )
                items_list.append(polygon_id)
                bind_polygon_click_events(polygon_id, list(right_iris_indices_set))
            
            # 눈동자 중앙 포인트 표시 (IrisRenderer 사용)
            # 왼쪽 눈동자 중앙 포인트
            center_x = None
            center_y = None
            
            # iris_centers 파라미터가 전달된 경우 우선 사용 (Tesselation 모드)
            # iris_centers[0] = landmarks[468] = 화면상 오른쪽
            # iris_centers[1] = landmarks[469] = 화면상 왼쪽
            if iris_centers is not None and len(iris_centers) == 2:
                center_pt = iris_centers[1]  # 화면상 왼쪽 눈동자 → landmarks[469]
                if isinstance(center_pt, tuple):
                    center_x, center_y = center_pt
                else:
                    center_x = center_pt.x * img_width
                    center_y = center_pt.y * img_height
            # Tesselation 모드 (470개 구조): landmarks[469]에서 직접 가져오기
            elif len(landmarks) == 470:
                center_pt = landmarks[469]  # 화면상 왼쪽 = landmarks[469]
                if hasattr(center_pt, 'x'):
                    center_x = center_pt.x * img_width
                    center_y = center_pt.y * img_height
                else:
                    center_x, center_y = center_pt
            elif hasattr(self, '_left_iris_center_coord') and self._left_iris_center_coord is not None:
                center_x, center_y = self._left_iris_center_coord
            elif hasattr(self, '_get_iris_indices') and hasattr(self, '_calculate_iris_center'):
                original = self.landmark_manager.get_original_landmarks()
                
                if original is not None:
                    left_iris_indices, _ = self._get_iris_indices()
                    center = self._calculate_iris_center(original, left_iris_indices, img_width, img_height)
                    if center is not None:
                        center_x, center_y = center
                        self._left_iris_center_coord = center
                    else:
                        return
                else:
                    return
            else:
                return
            
            if center_x is not None and center_y is not None:
                # IrisRenderer를 사용하여 중심점 그리기
                if self.iris_renderer is not None:
                    try:
                        # iris_coords 추출
                        iris_coords = []
                        if has_iris_landmarks:
                            # 고정 분리: 처음 5개 = 오른쪽, 마지막 5개 = 왼쪽
                            left_coords = iris_landmarks[5:]  # 마지막 5개 = 왼쪽
                            right_coords = iris_landmarks[:5]  # 처음 5개 = 오른쪽
                            
                            # 왼쪽 눈동자이므로 왼쪽 좌표 사용
                            iris_coords = left_coords
                        
                        center_id = self.iris_renderer.draw_iris_center(
                            canvas, 'left', center_x, center_y,  # 명시적으로 'left' 전달
                            center_radius=5, pos_x=pos_x, pos_y=pos_y,  # All 탭과 동일한 크기
                            scale_x=scale_x, scale_y=scale_y,
                            img_width=img_width, img_height=img_height,
                            iris_coords=iris_coords, items_list=items_list
                        )
                        items_list.append(center_id)
                        
                        # 인덱스 표시
                        if show_indices:
                            rel_x = (center_x - img_width / 2) * scale_x
                            rel_y = (center_y - img_height / 2) * scale_y
                            canvas_x = pos_x + rel_x
                            canvas_y = pos_y + rel_y
                            
                            text_offset = 8 + 5
                            index_text = "C-L"
                            text_id = canvas.create_text(
                                canvas_x + text_offset,
                                canvas_y - text_offset,
                                text=index_text,
                                fill="red",
                                font=("Arial", 12, "bold"),
                                tags=("landmarks_polygon", "iris_center_left_text", "iris_center_left")
                            )
                            items_list.append(text_id)
                            # 텍스트도 최상위로 올리기
                            canvas.tag_raise(text_id)
                        
                        print(f"[DEBUG] Successfully drawn left iris center using IrisRenderer in iris tab")
                        
                    except Exception as e:
                        print(f"[DEBUG] Error drawing left iris center with IrisRenderer in iris tab: {e}")
                        # Fallback to original method
                        self._draw_iris_center_fallback(canvas, 'left', center_x, center_y, pos_x, pos_y, scale_x, scale_y, img_width, img_height, show_indices, items_list)
                else:
                    # Fallback to original method
                    self._draw_iris_center_fallback(canvas, 'left', center_x, center_y, pos_x, pos_y, scale_x, scale_y, img_width, img_height, show_indices, items_list)
            
            # 오른쪽 눈동자 중앙 포인트
            center_x = None
            center_y = None
            
            # iris_centers 파라미터가 전달된 경우 우선 사용 (Tesselation 모드)
            # iris_centers[0] = landmarks[468] = 화면상 오른쪽
            # iris_centers[1] = landmarks[469] = 화면상 왼쪽
            if iris_centers is not None and len(iris_centers) == 2:
                center_pt = iris_centers[0]  # 화면상 오른쪽 눈동자 → landmarks[468]
                if isinstance(center_pt, tuple):
                    center_x, center_y = center_pt
                else:
                    center_x = center_pt.x * img_width
                    center_y = center_pt.y * img_height
            # Tesselation 모드 (470개 구조): landmarks[468]에서 직접 가져오기
            elif len(landmarks) == 470:
                center_pt = landmarks[468]  # 화면상 오른쪽 = landmarks[468]
                if hasattr(center_pt, 'x'):
                    center_x = center_pt.x * img_width
                    center_y = center_pt.y * img_height
                else:
                    center_x, center_y = center_pt
            elif hasattr(self, '_right_iris_center_coord') and self._right_iris_center_coord is not None:
                center_x, center_y = self._right_iris_center_coord
            elif hasattr(self, '_get_iris_indices') and hasattr(self, '_calculate_iris_center'):
                original = self.landmark_manager.get_original_landmarks()
                
                if original is not None:
                    _, right_iris_indices = self._get_iris_indices()
                    center = self._calculate_iris_center(original, right_iris_indices, img_width, img_height)
                    if center is not None:
                        center_x, center_y = center
                        self._right_iris_center_coord = center
                    else:
                        return
                else:
                    return
            else:
                return
            
            if center_x is not None and center_y is not None:
                # IrisRenderer를 사용하여 중심점 그리기
                if self.iris_renderer is not None:
                    try:
                        # iris_coords 추출
                        iris_coords = []
                        if has_iris_landmarks:
                            # 고정 분리: 처음 5개 = 오른쪽, 마지막 5개 = 왼쪽
                            left_coords = iris_landmarks[5:]  # 마지막 5개 = 왼쪽
                            right_coords = iris_landmarks[:5]  # 처음 5개 = 오른쪽
                            
                            # 오른쪽 눈동자이므로 오른쪽 좌표 사용
                            iris_coords = right_coords
                        
                        center_id = self.iris_renderer.draw_iris_center(
                            canvas, 'right', center_x, center_y,  # 명시적으로 'right' 전달
                            center_radius=5, pos_x=pos_x, pos_y=pos_y,  # All 탭과 동일한 크기
                            scale_x=scale_x, scale_y=scale_y,
                            img_width=img_width, img_height=img_height,
                            iris_coords=iris_coords, items_list=items_list
                        )
                        items_list.append(center_id)
                        
                        # 인덱스 표시
                        if show_indices:
                            rel_x = (center_x - img_width / 2) * scale_x
                            rel_y = (center_y - img_height / 2) * scale_y
                            canvas_x = pos_x + rel_x
                            canvas_y = pos_y + rel_y
                            
                            text_offset = 8 + 5
                            index_text = "C-R"
                            text_id = canvas.create_text(
                                canvas_x + text_offset,
                                canvas_y - text_offset,
                                text=index_text,
                                fill="red",
                                font=("Arial", 12, "bold"),
                                tags=("landmarks_polygon", "iris_center_right_text", "iris_center_right")
                            )
                            items_list.append(text_id)
                            # 텍스트도 최상위로 올리기
                            canvas.tag_raise(text_id)
                        
                        print(f"[DEBUG] Successfully drawn right iris center using IrisRenderer in iris tab")
                        
                    except Exception as e:
                        print(f"[DEBUG] Error drawing right iris center with IrisRenderer in iris tab: {e}")
                        # Fallback to original method
                        self._draw_iris_center_fallback(canvas, 'right', center_x, center_y, pos_x, pos_y, scale_x, scale_y, img_width, img_height, show_indices, items_list)
                else:
                    # Fallback to original method
                    self._draw_iris_center_fallback(canvas, 'right', center_x, center_y, pos_x, pos_y, scale_x, scale_y, img_width, img_height, show_indices, items_list)
        
        except ImportError:
            pass
        except Exception as e:
            from utils.logger import get_logger
            logger = get_logger('얼굴편집')
            logger.error(f"눈동자 탭 폴리곤 그리기 실패: {e}", exc_info=True)

    def _draw_contour_tab_polygons(self, canvas, image, landmarks, pos_x, pos_y, items_list, color, scale_x, scale_y, img_width, img_height, expansion_level, show_indices, bind_polygon_click_events, force_use_custom=False):
        """contour 탭 폴리곤 그리기"""
        # 얼굴 외곽선: MediaPipe 연결 정보 사용
        try:
            import mediapipe as mp
            mp_face_mesh = mp.solutions.face_mesh
            FACE_OVAL = list(mp_face_mesh.FACEMESH_FACE_OVAL)
            # 윤곽 탭의 랜드마크 인덱스 수집
            face_oval_indices_set = set()
            for idx1, idx2 in FACE_OVAL:
                face_oval_indices_set.add(idx1)
                face_oval_indices_set.add(idx2)

            # 확장 레벨에 따라 주변 포인트 추가
            if expansion_level > 0:
                try:
                    import mediapipe as mp
                    mp_face_mesh = mp.solutions.face_mesh
                    tesselation = list(mp_face_mesh.FACEMESH_TESSELATION)
                    tesselation_graph = {}
                    for idx1, idx2 in tesselation:
                        if idx1 < len(landmarks) and idx2 < len(landmarks):
                            if idx1 not in tesselation_graph:
                                tesselation_graph[idx1] = []
                            if idx2 not in tesselation_graph:
                                tesselation_graph[idx2] = []
                            tesselation_graph[idx1].append(idx2)
                            tesselation_graph[idx2].append(idx1)
                    current_indices = face_oval_indices_set.copy()
                    for level in range(expansion_level):
                        next_level_indices = set()
                        for idx in current_indices:
                            if idx in tesselation_graph:
                                for neighbor in tesselation_graph[idx]:
                                    if neighbor < len(landmarks):
                                        next_level_indices.add(neighbor)
                        face_oval_indices_set.update(next_level_indices)
                        current_indices = next_level_indices
                except ImportError:
                    pass

            # 폴리곤에 포함된 포인트 인덱스를 polygon_point_map에 저장
            if canvas == self.canvas_original:
                for idx in face_oval_indices_set:
                    if idx < len(landmarks):
                        self.polygon_point_map_original.add(idx)
            elif canvas == self.canvas_edited:
                for idx in face_oval_indices_set:
                    if idx < len(landmarks):
                        self.polygon_point_map_edited.add(idx)

            face_oval_points = self._get_polygon_from_indices(
                [], landmarks, img_width, img_height, scale_x, scale_y, pos_x, pos_y,
                use_mediapipe_connections=True, connections=FACE_OVAL, expansion_level=expansion_level
            )
            if face_oval_points and len(face_oval_points) >= 3:
                # 삼각형 메쉬인지 확인 (4의 배수면 삼각형 메쉬)
                if len(face_oval_points) % 4 == 0:
                    # 삼각형 메쉬: 4개씩 나눠서 각 삼각형을 개별 폴리곤으로 그리기
                    triangle_count = 0
                    for i in range(0, len(face_oval_points), 4):
                        if i + 4 <= len(face_oval_points):
                            triangle_points = face_oval_points[i:i+4]
                            polygon_id = canvas.create_polygon(
                                triangle_points,
                                fill="",
                                outline=color,
                                width=1,
                                tags=("landmarks_polygon", "polygon_face_oval")
                            )
                            items_list.append(polygon_id)
                            bind_polygon_click_events(polygon_id, face_oval_indices_set)
                            triangle_count += 1
                else:
                    # 단일 폴리곤 (폴백)
                    polygon_id = canvas.create_polygon(
                        face_oval_points,
                        fill="",
                        outline=color,
                        width=2,
                        tags=("landmarks_polygon", "polygon_face_oval")
                    )
                    items_list.append(polygon_id)
                    bind_polygon_click_events(polygon_id, face_oval_indices_set)
        except ImportError:
            # 폴백: 인덱스 기반 (FACE_OVAL 인덱스는 연결 정보에서 추출)
            from utils.logger import get_logger
            logger = get_logger('얼굴편집')
            logger.warning("MediaPipe를 사용할 수 없어 얼굴 외곽선을 그릴 수 없음")

        except Exception as e:
            from utils.logger import get_logger
            logger = get_logger('얼굴편집')
            logger.error(f"폴리곤 그리기 실패: {e}", exc_info=True)
            import traceback
            traceback.print_exc()


