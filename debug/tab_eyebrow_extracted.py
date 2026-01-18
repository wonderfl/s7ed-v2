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
