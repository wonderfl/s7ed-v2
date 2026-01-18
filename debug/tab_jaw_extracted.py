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
