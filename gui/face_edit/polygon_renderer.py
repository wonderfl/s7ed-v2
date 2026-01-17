"""
얼굴 편집 패널 - 폴리곤 렌더링 Mixin
폴리곤 그리기 관련 기능을 담당
"""
import math
import tkinter as tk
import numpy as np

# scipy와 cv2 import 확인
try:
    from scipy.spatial import Delaunay
    _scipy_available = True
except ImportError:
    _scipy_available = False
    Delaunay = None


class PolygonRendererMixin:
    """폴리곤 렌더링 기능 Mixin"""
    
    def _draw_landmark_polygons(self, canvas, image, landmarks, pos_x, pos_y, items_list, color, current_tab):
        """랜드마크 폴리곤 그리기 (해당 부위의 모든 랜드마크 포인트를 찾아서 폴리곤으로 그리기)"""
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
            
            # 폴리곤을 다시 그리기 전에 polygon_point_map 초기화
            # 폴리곤이 추가/변경/삭제될 때마다 갱신되도록
            if canvas == self.canvas_original:
                self.polygon_point_map_original.clear()
            elif canvas == self.canvas_edited:
                self.polygon_point_map_edited.clear()
            
            # 확장 레벨 가져오기
            expansion_level = getattr(self, 'polygon_expansion_level', tk.IntVar(value=1)).get() if hasattr(self, 'polygon_expansion_level') else 1
            
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
                # 전체 탭: 모든 부위의 폴리곤 그리기 (눈, 눈썹, 코, 입, 얼굴 외곽선)
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
                        if canvas == self.canvas_original:
                            for idx in polygon_indices:
                                if idx < len(landmarks):
                                    # 포인트 인덱스 -> True (화면에 보이는 포인트로 표시)
                                    self.polygon_point_map_original[idx] = True
                        elif canvas == self.canvas_edited:
                            for idx in polygon_indices:
                                if idx < len(landmarks):
                                    self.polygon_point_map_edited[idx] = True
                        
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
                    
                    # 전체 탭에서는 모든 랜드마크를 선택 가능하도록 target_indices를 None으로 설정
                    # 왼쪽 눈 (눈동자 제외, 눈동자는 별도로 그림)
                    draw_polygon_mesh(LEFT_EYE, "polygon_left_eye", "왼쪽 눈", None)
                    # 오른쪽 눈 (눈동자 제외, 눈동자는 별도로 그림)
                    draw_polygon_mesh(RIGHT_EYE, "polygon_right_eye", "오른쪽 눈", None)
                    
                    # 왼쪽 눈동자 (별도로 그리기)
                    if LEFT_IRIS and len(landmarks) > 468:
                        left_iris_indices_set = set()
                        for idx1, idx2 in LEFT_IRIS:
                            if idx1 < len(landmarks) and idx2 < len(landmarks):
                                left_iris_indices_set.add(idx1)
                                left_iris_indices_set.add(idx2)
                        # 눈동자 중심점(468)도 인덱스에 추가
                        if 468 < len(landmarks):
                            left_iris_indices_set.add(468)
                        
                        left_iris_points = self._get_polygon_from_indices(
                            [], landmarks, img_width, img_height, scale_x, scale_y, pos_x, pos_y,
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
                            # 폴리곤 클릭 이벤트 바인딩
                            bind_polygon_click_events(polygon_id, None)
                            # polygon_point_map에 저장
                            if canvas == self.canvas_original:
                                for idx in left_iris_indices_set:
                                    if idx < len(landmarks):
                                        self.polygon_point_map_original[idx] = True
                            elif canvas == self.canvas_edited:
                                for idx in left_iris_indices_set:
                                    if idx < len(landmarks):
                                        self.polygon_point_map_edited[idx] = True
                    
                    # 오른쪽 눈동자 (별도로 그리기)
                    if RIGHT_IRIS and len(landmarks) > 468:
                        right_iris_indices_set = set()
                        for idx1, idx2 in RIGHT_IRIS:
                            if idx1 < len(landmarks) and idx2 < len(landmarks):
                                right_iris_indices_set.add(idx1)
                                right_iris_indices_set.add(idx2)
                        # 눈동자 중심점(473)도 인덱스에 추가
                        if 473 < len(landmarks):
                            right_iris_indices_set.add(473)
                        
                        right_iris_points = self._get_polygon_from_indices(
                            [], landmarks, img_width, img_height, scale_x, scale_y, pos_x, pos_y,
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
                            # 폴리곤 클릭 이벤트 바인딩
                            bind_polygon_click_events(polygon_id, None)
                            # polygon_point_map에 저장
                            if canvas == self.canvas_original:
                                for idx in right_iris_indices_set:
                                    if idx < len(landmarks):
                                        self.polygon_point_map_original[idx] = True
                            elif canvas == self.canvas_edited:
                                for idx in right_iris_indices_set:
                                    if idx < len(landmarks):
                                        self.polygon_point_map_edited[idx] = True
                    
                    # 왼쪽 눈썹
                    draw_polygon_mesh(LEFT_EYEBROW, "polygon_left_eyebrow", "왼쪽 눈썹", None)
                    # 오른쪽 눈썹
                    draw_polygon_mesh(RIGHT_EYEBROW, "polygon_right_eyebrow", "오른쪽 눈썹", None)
                    # 코
                    draw_polygon_mesh(NOSE, "polygon_nose", "코", None)
                    # 입
                    draw_polygon_mesh(LIPS, "polygon_lips", "입", None)
                    # 얼굴 외곽선
                    draw_polygon_mesh(FACE_OVAL, "polygon_face_oval", "얼굴 외곽선", None)
                    
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
                    jaw_indices = list(range(17))  # 0-16
                    
                    # 눈 탭인 경우 눈썹 제외
                    if current_tab == '눈':
                        # 눈과 눈동자만 포함
                        eye_indices_set = set(LEFT_EYE_INDICES + RIGHT_EYE_INDICES)
                        # 눈동자 인덱스 추가
                        if len(landmarks) > 468:
                            iris_indices = [468, 469, 470, 471, 472, 473, 474, 475, 476, 477]
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
                    else:
                        # 전체 탭: 모든 부위 폴리곤 그리기
                        for indices, tag_name, part_name in [
                            (LEFT_EYE_INDICES, "polygon_left_eye", "왼쪽 눈"),
                            (RIGHT_EYE_INDICES, "polygon_right_eye", "오른쪽 눈"),
                            (LEFT_EYEBROW_INDICES, "polygon_left_eyebrow", "왼쪽 눈썹"),
                            (RIGHT_EYEBROW_INDICES, "polygon_right_eyebrow", "오른쪽 눈썹"),
                            (NOSE_INDICES, "polygon_nose", "코"),
                            (MOUTH_ALL_INDICES, "polygon_lips", "입"),
                            (jaw_indices, "polygon_jaw", "턱선")
                        ]:
                            # 폴리곤에 포함된 포인트 인덱스를 polygon_point_map에 저장
                            if canvas == self.canvas_original:
                                for idx in indices:
                                    if idx < len(landmarks):
                                        self.polygon_point_map_original[idx] = True
                            elif canvas == self.canvas_edited:
                                for idx in indices:
                                    if idx < len(landmarks):
                                        self.polygon_point_map_edited[idx] = True
                            
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
                
            elif current_tab == '눈':
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
                    if LEFT_IRIS and RIGHT_IRIS and len(landmarks) > 468:
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
                                        self.polygon_point_map_original[idx] = True
                            elif canvas == self.canvas_edited:
                                for idx in polygon_indices:
                                    if idx < len(landmarks):
                                        self.polygon_point_map_edited[idx] = True
                        
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
                    
                    if LEFT_IRIS and len(landmarks) > 468:
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
                    
                    if RIGHT_IRIS and len(landmarks) > 468:
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
                    # 눈동자 인덱스 추가
                    if len(landmarks) > 468:
                        iris_indices = [468, 469, 470, 471, 472, 473, 474, 475, 476, 477]
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
                    
            elif current_tab == '코':
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
                                self.polygon_point_map_original[idx] = True
                    elif canvas == self.canvas_edited:
                        for idx in nose_indices_set:
                            if idx < len(landmarks):
                                self.polygon_point_map_edited[idx] = True
                    
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
                                self.polygon_point_map_original[idx] = True
                    elif canvas == self.canvas_edited:
                        for idx in nose_indices_set:
                            if idx < len(landmarks):
                                self.polygon_point_map_edited[idx] = True
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
                    
            elif current_tab == '입':
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
                                self.polygon_point_map_original[idx] = True
                    elif canvas == self.canvas_edited:
                        for idx in lips_indices_set:
                            if idx < len(landmarks):
                                self.polygon_point_map_edited[idx] = True
                    
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
                                self.polygon_point_map_original[idx] = True
                    elif canvas == self.canvas_edited:
                        for idx in lips_indices_set:
                            if idx < len(landmarks):
                                self.polygon_point_map_edited[idx] = True
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
            
            elif current_tab == '눈썹':
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
                                self.polygon_point_map_original[idx] = True
                    elif canvas == self.canvas_edited:
                        for idx in eyebrow_indices_set:
                            if idx < len(landmarks):
                                self.polygon_point_map_edited[idx] = True
                    
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
                                self.polygon_point_map_original[idx] = True
                    elif canvas == self.canvas_edited:
                        for idx in eyebrow_indices_set:
                            if idx < len(landmarks):
                                self.polygon_point_map_edited[idx] = True
                    
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
                    
            elif current_tab == '턱선':
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
                                self.polygon_point_map_original[idx] = True
                    elif canvas == self.canvas_edited:
                        for idx in jaw_indices_set:
                            if idx < len(landmarks):
                                self.polygon_point_map_edited[idx] = True
                    
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
                                self.polygon_point_map_original[idx] = True
                    elif canvas == self.canvas_edited:
                        for idx in jaw_indices_set:
                            if idx < len(landmarks):
                                self.polygon_point_map_edited[idx] = True
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
                    
            elif current_tab == '윤곽':
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
                                self.polygon_point_map_original[idx] = True
                    elif canvas == self.canvas_edited:
                        for idx in face_oval_indices_set:
                            if idx < len(landmarks):
                                self.polygon_point_map_edited[idx] = True
                    
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
    

    def _get_polygon_from_indices(self, indices, landmarks, img_width, img_height, scale_x, scale_y, pos_x, pos_y, use_mediapipe_connections=False, connections=None, expansion_level=1):
        """랜드마크 인덱스 리스트에서 폴리곤 경로 생성
        
        Args:
            indices: 랜드마크 인덱스 리스트
            landmarks: 랜드마크 포인트 리스트
            use_mediapipe_connections: MediaPipe 연결 정보를 사용할지 여부
            connections: MediaPipe 연결 정보 (FACEMESH_* 상수)
            expansion_level: 주변 확장 레벨 (0~5, 기본값: 1)
        """
        if landmarks is None:
            from utils.logger import get_logger
            logger = get_logger('얼굴편집')
            logger.warning("폴리곤 경로 생성 실패: 랜드마크가 None")
            return []
        
        try:
            # MediaPipe 연결 정보를 사용하는 경우 (인덱스 리스트가 비어있어도 괜찮음)
            if use_mediapipe_connections and connections:
                from utils.logger import get_logger
                logger = get_logger('얼굴편집')
                logger.debug(f"폴리곤 경로 생성 시작: MediaPipe 연결 정보 사용, 연결 개수={len(connections) if connections else 0}, 랜드마크 배열 길이={len(landmarks) if landmarks else 0}, 확장 레벨={expansion_level}")
                return self._build_polygon_path_from_connections(connections, landmarks, img_width, img_height, scale_x, scale_y, pos_x, pos_y, expansion_level)
            
            # 인덱스 리스트가 비어있으면 실패
            if not indices or len(indices) == 0:
                from utils.logger import get_logger
                logger = get_logger('얼굴편집')
                logger.warning("폴리곤 경로 생성 실패: 인덱스 리스트가 비어있음")
                return []
            
            print(f"[얼굴편집] 폴리곤 경로 생성 시작: 요청 인덱스 {len(indices)}개, 랜드마크 배열 길이={len(landmarks) if landmarks else 0}, MediaPipe 연결 사용={use_mediapipe_connections}")
            
            # 유효한 인덱스만 필터링
            valid_indices = [idx for idx in indices if idx < len(landmarks)]
            invalid_indices = [idx for idx in indices if idx >= len(landmarks)]
            
            if invalid_indices:
                print(f"[얼굴편집] 경고: 유효하지 않은 인덱스 {len(invalid_indices)}개: {invalid_indices[:10]}{'...' if len(invalid_indices) > 10 else ''}")
            
            if len(valid_indices) < 3:
                print(f"[얼굴편집] 폴리곤 경로 생성 실패: 유효한 인덱스가 3개 미만 ({len(valid_indices)}개)")
                return []
            
            print(f"[얼굴편집] 유효한 인덱스 {len(valid_indices)}개 사용")
            
            # 포인트 좌표 수집 (인덱스와 함께 저장)
            point_coords_with_idx = []
            failed_count = 0
            for idx in valid_indices:
                try:
                    pt = landmarks[idx]
                    if pt is None:
                        failed_count += 1
                        continue
                    
                    if isinstance(pt, tuple) and len(pt) >= 2:
                        img_x, img_y = pt[0], pt[1]
                    elif hasattr(pt, 'x') and hasattr(pt, 'y'):
                        img_x = pt.x * img_width
                        img_y = pt.y * img_height
                    else:
                        print(f"[얼굴편집] 경고: 인덱스 {idx}의 랜드마크 포인트 형식이 예상과 다름: {type(pt)}")
                        failed_count += 1
                        continue
                    
                    point_coords_with_idx.append((idx, img_x, img_y))
                except Exception as e:
                    print(f"[얼굴편집] 경고: 인덱스 {idx}의 좌표 추출 실패: {e}")
                    failed_count += 1
                    continue
            
            if failed_count > 0:
                print(f"[얼굴편집] 경고: {failed_count}개 포인트의 좌표 추출 실패")
            
            print(f"[얼굴편집] 좌표 추출 완료: {len(point_coords_with_idx)}개 포인트")
            
            if len(point_coords_with_idx) < 3:
                print(f"[얼굴편집] 폴리곤 경로 생성 실패: 유효한 좌표가 3개 미만 ({len(point_coords_with_idx)}개)")
                return []
            
            # 모든 포인트를 포함하는 폴리곤 생성 (Convex Hull 대신 모든 포인트를 각도 순으로 정렬)
            # 중심점 기준 각도 정렬로 모든 포인트 포함
            point_coords = [(x, y) for _, x, y in point_coords_with_idx]
            center_x = sum(p[0] for p in point_coords) / len(point_coords)
            center_y = sum(p[1] for p in point_coords) / len(point_coords)
            
            def get_angle(x, y):
                dx = x - center_x
                dy = y - center_y
                return math.atan2(dy, dx)
            
            # 각도 순으로 정렬 (모든 포인트 포함)
            sorted_points = sorted(point_coords, key=lambda p: get_angle(p[0], p[1]))
            # 시작점으로 다시 돌아가기
            if len(sorted_points) > 0:
                sorted_points.append(sorted_points[0])
            
            print(f"[얼굴편집] 폴리곤 경로 구성: {len(sorted_points)}개 포인트 (모든 포인트 포함)")
            
            # 캔버스 좌표로 변환
            polygon_points = []
            for img_x, img_y in sorted_points:
                rel_x = (img_x - img_width / 2) * scale_x
                rel_y = (img_y - img_height / 2) * scale_y
                canvas_x = pos_x + rel_x
                canvas_y = pos_y + rel_y
                polygon_points.append((canvas_x, canvas_y))
            
            return polygon_points
            
        except Exception as e:
            print(f"[얼굴편집] 폴리곤 경로 생성 실패: {e}")
            import traceback
            traceback.print_exc()
            return []
    

    def _build_polygon_path_from_connections(self, connections, landmarks, img_width, img_height, scale_x, scale_y, pos_x, pos_y, expansion_level=1):
        """MediaPipe 연결 정보를 사용해서 삼각형 메쉬로 폴리곤 경로 구성
        
        FACEMESH_TESSELATION을 사용하여 각 부위의 포인트만 필터링하여 삼각형 메쉬로 구성
        모든 포인트를 포함하는 삼각형들을 반환하여 어떤 포인트가 빠졌는지 확인 가능
        
        Args:
            connections: MediaPipe 연결 정보 (FACEMESH_* 상수)
            landmarks: 랜드마크 포인트 리스트
            img_width, img_height: 이미지 크기
            scale_x, scale_y: 스케일 팩터
            pos_x, pos_y: 캔버스 위치
            expansion_level: 주변 확장 레벨 (0~5, 기본값: 1)
        """
        if not connections or len(connections) == 0:
            return []
        
        try:
            import mediapipe as mp
            mp_face_mesh = mp.solutions.face_mesh
            tesselation = mp_face_mesh.FACEMESH_TESSELATION
        except ImportError:
            print(f"[얼굴편집] 경고: MediaPipe를 사용할 수 없어 기본 방법 사용")
            tesselation = None
        except Exception as e:
            print(f"[얼굴편집] 경고: TESSELATION 로드 실패: {e}")
            tesselation = None
        
        try:
            # 연결 정보에서 모든 포인트 인덱스 수집
            all_indices_set = set()
            for idx1, idx2 in connections:
                if idx1 < len(landmarks) and idx2 < len(landmarks):
                    all_indices_set.add(idx1)
                    all_indices_set.add(idx2)
            
            if len(all_indices_set) == 0:
                return []
            
            all_indices = list(all_indices_set)
            
            # TESSELATION이 있으면 해당 포인트들만 포함하는 연결 필터링
            if tesselation:
                # 눈의 경우 주변 한 줄 더 포함하기 위해 이웃 포인트 추가
                # TESSELATION 그래프를 먼저 구성하여 이웃 포인트 찾기
                tesselation_graph = {}
                for idx1, idx2 in tesselation:
                    if idx1 < len(landmarks) and idx2 < len(landmarks):
                        if idx1 not in tesselation_graph:
                            tesselation_graph[idx1] = []
                        if idx2 not in tesselation_graph:
                            tesselation_graph[idx2] = []
                        tesselation_graph[idx1].append(idx2)
                        tesselation_graph[idx2].append(idx1)
                
                # 부위별 인덱스 확인 (눈, 코, 입)
                LEFT_EYE_INDICES = [33, 7, 163, 144, 145, 153, 154, 155, 133, 173, 157, 158, 159, 160, 161, 246]
                RIGHT_EYE_INDICES = [362, 382, 381, 380, 374, 373, 390, 249, 263, 466, 388, 387, 386, 385, 384, 398]
                
                # FACEMESH_NOSE 인덱스 (테스트 결과 기반)
                NOSE_INDICES = [1, 2, 4, 5, 6, 19, 45, 48, 64, 94, 97, 98, 115, 168, 195, 197, 220, 275, 278, 294, 326, 327, 344, 440]
                
                # FACEMESH_LIPS 인덱스 (테스트 결과 기반)
                LIPS_INDICES = [0, 13, 14, 17, 37, 39, 40, 61, 78, 80, 81, 82, 84, 87, 88, 91, 95, 146, 178, 181, 185, 191, 267, 269, 270, 291, 308, 310, 311, 312, 314, 317, 318, 321, 324, 375, 402, 405, 409, 415]
                
                # FACEMESH_FACE_OVAL 인덱스
                FACE_OVAL_INDICES = [10, 21, 54, 58, 67, 93, 103, 109, 127, 132, 136, 148, 149, 150, 152, 162, 172, 176, 234, 251, 284, 288, 297, 323, 332, 338, 356, 361, 365, 377, 378, 379, 389, 397, 400, 454]
                
                is_eye = any(idx in LEFT_EYE_INDICES or idx in RIGHT_EYE_INDICES for idx in all_indices_set)
                is_nose = any(idx in NOSE_INDICES for idx in all_indices_set)
                is_lips = any(idx in LIPS_INDICES for idx in all_indices_set)
                is_face_oval = any(idx in FACE_OVAL_INDICES for idx in all_indices_set)
                
                # 눈, 코, 입, 얼굴 외곽선인 경우 주변 확장 레벨에 따라 포함
                if (is_eye or is_nose or is_lips or is_face_oval) and expansion_level > 0:
                    original_count = len(all_indices_set)
                    extended_indices_set = set(all_indices_set)
                    current_level_indices = set(all_indices_set)
                    
                    # 확장 레벨만큼 반복하여 이웃 포인트 추가
                    for level in range(expansion_level):
                        next_level_indices = set()
                        for idx in current_level_indices:
                            if idx in tesselation_graph:
                                # 직접 이웃 포인트 추가
                                for neighbor in tesselation_graph[idx]:
                                    if neighbor < len(landmarks) and neighbor not in extended_indices_set:
                                        extended_indices_set.add(neighbor)
                                        next_level_indices.add(neighbor)
                        current_level_indices = next_level_indices
                    
                    all_indices_set = extended_indices_set
                    part_name = []
                    if is_eye:
                        part_name.append("눈")
                    if is_nose:
                        part_name.append("코")
                    if is_lips:
                        part_name.append("입")
                    if is_face_oval:
                        part_name.append("얼굴외곽")
                    print(f"[얼굴편집] {'/'.join(part_name)} 주변 확장 (레벨 {expansion_level}): {len(all_indices_set)}개 포인트 (원본 {original_count}개에서 확장)")
                
                # TESSELATION에서 확장된 포인트들만 포함하는 연결 필터링
                filtered_connections = []
                for idx1, idx2 in tesselation:
                    if idx1 in all_indices_set and idx2 in all_indices_set:
                        if idx1 < len(landmarks) and idx2 < len(landmarks):
                            filtered_connections.append((idx1, idx2))
                
                # 눈동자 연결 정보 추가 (TESSELATION에 포함되지 않음)
                # 눈동자 인덱스: 468-477
                iris_indices = set([468, 469, 470, 471, 472, 473, 474, 475, 476, 477])
                if any(idx in iris_indices for idx in all_indices_set):
                    # 눈동자 연결 정보가 원본 connections에 포함되어 있으면 추가
                    for idx1, idx2 in connections:
                        if (idx1 in iris_indices or idx2 in iris_indices) and \
                           idx1 < len(landmarks) and idx2 < len(landmarks):
                            if (idx1, idx2) not in filtered_connections:
                                filtered_connections.append((idx1, idx2))
                
                if len(filtered_connections) == 0:
                    print(f"[얼굴편집] 경고: TESSELATION에서 필터링된 연결이 없음, 기본 방법 사용")
                    filtered_connections = list(connections)
            else:
                filtered_connections = list(connections)
            
            # 확장된 인덱스 리스트 업데이트
            all_indices = list(all_indices_set)
            
            # 필터링된 연결 정보를 그래프로 구성
            graph = {}
            for idx1, idx2 in filtered_connections:
                if idx1 < len(landmarks) and idx2 < len(landmarks):
                    if idx1 not in graph:
                        graph[idx1] = []
                    if idx2 not in graph:
                        graph[idx2] = []
                    graph[idx1].append(idx2)
                    graph[idx2].append(idx1)
            
            if len(graph) == 0:
                return []
            
            # 삼각형 메쉬 찾기: 3개의 연결이 순환하는 경우
            triangles = []
            visited_triangles = set()
            
            for idx1, neighbors in graph.items():
                for idx2 in neighbors:
                    if idx2 in graph:
                        # idx1과 idx2가 연결되어 있고, 공통 이웃이 있으면 삼각형
                        common_neighbors = set(graph[idx1]) & set(graph[idx2])
                        for idx3 in common_neighbors:
                            if idx3 != idx1 and idx3 != idx2:
                                # 삼각형 (idx1, idx2, idx3) 구성
                                triangle = tuple(sorted([idx1, idx2, idx3]))
                                if triangle not in visited_triangles:
                                    visited_triangles.add(triangle)
                                    triangles.append(triangle)
            
            if len(triangles) == 0:
                print(f"[얼굴편집] 경고: 삼각형을 찾을 수 없음, 각도 순 정렬로 폴백")
                # 삼각형을 찾을 수 없으면 각도 순 정렬로 폴백
                point_coords_with_idx = []
                for idx in all_indices:
                    if idx < len(landmarks):
                        pt = landmarks[idx]
                        if isinstance(pt, tuple):
                            img_x, img_y = pt
                        else:
                            img_x = pt.x * img_width
                            img_y = pt.y * img_height
                        point_coords_with_idx.append((idx, img_x, img_y))
                
                if len(point_coords_with_idx) < 3:
                    return []
                
                # 중심점 기준 각도 정렬
                point_coords = [(x, y) for _, x, y in point_coords_with_idx]
                center_x = sum(p[0] for p in point_coords) / len(point_coords)
                center_y = sum(p[1] for p in point_coords) / len(point_coords)
                
                def get_angle(x, y):
                    dx = x - center_x
                    dy = y - center_y
                    return math.atan2(dy, dx)
                
                sorted_points_with_idx = sorted(point_coords_with_idx, key=lambda p: get_angle(p[1], p[2]))
                path_indices = [idx for idx, _, _ in sorted_points_with_idx]
                if len(path_indices) >= 3:
                    path_indices.append(path_indices[0])
                
                # 단일 폴리곤으로 반환 (하위 호환성)
                polygon_points = []
                for idx in path_indices:
                    if idx < len(landmarks):
                        pt = landmarks[idx]
                        if isinstance(pt, tuple):
                            img_x, img_y = pt
                        else:
                            img_x = pt.x * img_width
                            img_y = pt.y * img_height
                        
                        rel_x = (img_x - img_width / 2) * scale_x
                        rel_y = (img_y - img_height / 2) * scale_y
                        canvas_x = pos_x + rel_x
                        canvas_y = pos_y + rel_y
                        polygon_points.append((canvas_x, canvas_y))
                
                return polygon_points
            
            # 삼각형들을 좌표로 변환하여 평탄화된 리스트로 반환
            # 각 삼각형은 3개의 점으로 구성되므로, 전체 리스트는 [삼각형1점1, 삼각형1점2, 삼각형1점3, 삼각형2점1, ...] 형태
            all_triangle_points = []
            for triangle in triangles:
                triangle_points = []
                for idx in triangle:
                    if idx < len(landmarks):
                        pt = landmarks[idx]
                        if isinstance(pt, tuple):
                            img_x, img_y = pt
                        else:
                            img_x = pt.x * img_width
                            img_y = pt.y * img_height
                        
                        rel_x = (img_x - img_width / 2) * scale_x
                        rel_y = (img_y - img_height / 2) * scale_y
                        canvas_x = pos_x + rel_x
                        canvas_y = pos_y + rel_y
                        triangle_points.append((canvas_x, canvas_y))
                
                if len(triangle_points) == 3:
                    # 삼각형을 순환 경로로 만들기 (마지막 점을 다시 첫 번째 점으로)
                    triangle_points.append(triangle_points[0])
                    all_triangle_points.extend(triangle_points)
            
            print(f"[얼굴편집] 삼각형 메쉬 구성 완료: {len(triangles)}개 삼각형 (전체 {len(all_indices)}개 포인트 중)")
            
            return all_triangle_points
            
        except Exception as e:
            print(f"[얼굴편집] 폴리곤 경로 구성 실패: {e}")
            import traceback
            traceback.print_exc()
            return []
    

    def on_polygon_line_click(self, event, current_tab, canvas, image, landmarks, pos_x, pos_y, items_list, color):
        """연결선 클릭 시 폴리곤 영역 표시"""
        print(f"[얼굴편집] 연결선 클릭: 탭={current_tab}")
        try:
            # 기존 폴리곤 제거
            if canvas == self.canvas_original:
                for item_id in self.landmark_polygon_items_original:
                    try:
                        canvas.delete(item_id)
                    except Exception:
                        pass
                self.landmark_polygon_items_original.clear()
            else:
                for item_id in self.landmark_polygon_items_edited:
                    try:
                        canvas.delete(item_id)
                    except Exception:
                        pass
                self.landmark_polygon_items_edited.clear()
            
            # 선택된 탭에 해당하는 폴리곤 그리기
            self.selected_polygon_group = current_tab
            print(f"[얼굴편집] 폴리곤 영역 채우기 시작: 탭={current_tab}")
            self._fill_polygon_area(canvas, image, landmarks, pos_x, pos_y, items_list, color, current_tab)
            print(f"[얼굴편집] 폴리곤 영역 채우기 완료")
            
            # 이벤트 전파 중단
            return "break"
            
        except Exception as e:
            print(f"[얼굴편집] 폴리곤 클릭 처리 실패: {e}")
            import traceback
            traceback.print_exc()
            return "break"
    

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
                    if canvas == self.canvas_original:
                        self.landmark_polygon_items_original.append(polygon_id)
                    else:
                        self.landmark_polygon_items_edited.append(polygon_id)
                    
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
    def _update_connected_polygons(self, canvas_obj, landmark_index):
        """연결된 폴리곤 실시간 갱신"""
        # 폴리곤을 다시 그리기 위해 얼굴 특징 표시 업데이트
        if hasattr(self, 'update_face_features_display'):
            try:
                # 원본 이미지의 폴리곤만 갱신 (편집된 이미지는 폴리곤 표시 안 함)
                if canvas_obj == self.canvas_original:
                    # 기존 폴리곤 삭제
                    for item_id in list(self.landmark_polygon_items_original):
                        try:
                            canvas_obj.delete(item_id)
                        except:
                            pass
                    self.landmark_polygon_items_original.clear()
                    
                    # 폴리곤 다시 그리기
                    if hasattr(self, 'show_landmark_polygons') and self.show_landmark_polygons.get():
                        # 랜드마크 표시 업데이트 (폴리곤만)
                        if self.custom_landmarks is not None:
                            landmarks = self.custom_landmarks
                        elif self.face_landmarks is not None:
                            landmarks = self.face_landmarks
                        else:
                            return
                        
                        current_tab = getattr(self, 'current_morphing_tab', '눈')
                        self._draw_landmark_polygons(
                            canvas_obj,
                            self.current_image,
                            landmarks,
                            self.canvas_original_pos_x,
                            self.canvas_original_pos_y,
                            self.landmark_polygon_items_original,
                            "green",
                            current_tab
                        )
            except Exception as e:
                print(f"[얼굴편집] 폴리곤 갱신 실패: {e}")
                import traceback
                traceback.print_exc()
    
    def _draw_flipped_triangles(self, canvas, image, original_landmarks, transformed_landmarks, 
                                pos_x, pos_y, items_list, img_width, img_height, scale_x, scale_y):
        """뒤집힌 삼각형을 감지하고 빨간색으로 표시"""
        if not _scipy_available or Delaunay is None:
            return
        
        try:
            # numpy 배열로 변환
            original_points_array = np.array(original_landmarks, dtype=np.float32)
            transformed_points_array = np.array(transformed_landmarks, dtype=np.float32)
            
            # 이미지 경계 포인트 추가
            margin = 10
            boundary_points = [
                (-margin, -margin),
                (img_width + margin, -margin),
                (img_width + margin, img_height + margin),
                (-margin, img_height + margin)
            ]
            
            all_original_points = list(original_landmarks) + boundary_points
            all_transformed_points = list(transformed_landmarks) + boundary_points
            
            original_points_array = np.array(all_original_points, dtype=np.float32)
            transformed_points_array = np.array(all_transformed_points, dtype=np.float32)
            
            # Delaunay Triangulation 생성
            tri = Delaunay(original_points_array)
            
            # 뒤집힌 삼각형 감지
            flipped_indices = []
            for simplex_idx, simplex in enumerate(tri.simplices):
                # 원본 삼각형의 3개 포인트
                pt1_orig = original_points_array[simplex[0]]
                pt2_orig = original_points_array[simplex[1]]
                pt3_orig = original_points_array[simplex[2]]
                
                # 변형된 삼각형의 3개 포인트
                pt1_trans = transformed_points_array[simplex[0]]
                pt2_trans = transformed_points_array[simplex[1]]
                pt3_trans = transformed_points_array[simplex[2]]
                
                # 외적 계산
                v1_orig = pt2_orig - pt1_orig
                v2_orig = pt3_orig - pt1_orig
                cross_product_orig = v1_orig[0] * v2_orig[1] - v1_orig[1] * v2_orig[0]
                
                v1_trans = pt2_trans - pt1_trans
                v2_trans = pt3_trans - pt1_trans
                cross_product_trans = v1_trans[0] * v2_trans[1] - v1_trans[1] * v2_trans[0]
                
                # 뒤집혔는지 확인 (외적의 부호가 바뀌면 뒤집힘)
                if cross_product_orig * cross_product_trans < 0:
                    flipped_indices.append(simplex_idx)
            
            # 뒤집힌 삼각형을 빨간색으로 표시
            if flipped_indices:
                print(f"[얼굴편집] 뒤집힌 삼각형 {len(flipped_indices)}개 감지")
                for simplex_idx in flipped_indices:
                    simplex = tri.simplices[simplex_idx]
                    # 경계 포인트는 제외
                    boundary_start_idx = len(original_landmarks)
                    if (simplex[0] >= boundary_start_idx or 
                        simplex[1] >= boundary_start_idx or 
                        simplex[2] >= boundary_start_idx):
                        continue
                    
                    # 뒤집힌 삼각형 표시: 원본 이미지 위에 그리므로 원본 랜드마크 좌표 사용
                    # 변형된 랜드마크는 뒤집힌 삼각형 감지에만 사용하고, 표시는 원본 좌표 사용
                    pt1_orig = original_points_array[simplex[0]]
                    pt2_orig = original_points_array[simplex[1]]
                    pt3_orig = original_points_array[simplex[2]]
                    
                    # 캔버스 좌표로 변환 (원본 이미지 좌표 사용)
                    def img_to_canvas(img_x, img_y):
                        rel_x = (img_x - img_width / 2) * scale_x
                        rel_y = (img_y - img_height / 2) * scale_y
                        return (pos_x + rel_x, pos_y + rel_y)
                    
                    canvas_pt1 = img_to_canvas(pt1_orig[0], pt1_orig[1])
                    canvas_pt2 = img_to_canvas(pt2_orig[0], pt2_orig[1])
                    canvas_pt3 = img_to_canvas(pt3_orig[0], pt3_orig[1])
                    
                    # 빨간색 삼각형 그리기
                    triangle_id = canvas.create_polygon(
                        [canvas_pt1[0], canvas_pt1[1], 
                         canvas_pt2[0], canvas_pt2[1],
                         canvas_pt3[0], canvas_pt3[1]],
                        fill="",  # 채우지 않음
                        outline="red",  # 빨간색
                        width=2,
                        tags=("flipped_triangle", "landmarks_polygon")
                    )
                    items_list.append(triangle_id)
                    
                    # 폴리곤 아이템 저장
                    if canvas == self.canvas_original:
                        self.landmark_polygon_items_original.append(triangle_id)
                    elif canvas == self.canvas_edited:
                        self.landmark_polygon_items_edited.append(triangle_id)
        except Exception as e:
            print(f"[얼굴편집] 뒤집힌 삼각형 감지 실패: {e}")
            import traceback
            traceback.print_exc()