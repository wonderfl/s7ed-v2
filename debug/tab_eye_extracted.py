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
