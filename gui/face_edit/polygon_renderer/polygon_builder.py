"""
폴리곤 생성 관련 메서드
"""
import math


class PolygonBuilderMixin:
    """폴리곤 생성 기능 Mixin"""
    
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
                
                # 부위별 인덱스 확인 (눈, 눈썹, 코, 입)
                LEFT_EYE_INDICES = [33, 7, 163, 144, 145, 153, 154, 155, 133, 173, 157, 158, 159, 160, 161, 246]
                RIGHT_EYE_INDICES = [362, 382, 381, 380, 374, 373, 390, 249, 263, 466, 388, 387, 386, 385, 384, 398]
                
                # FACEMESH_EYEBROW 인덱스
                LEFT_EYEBROW_INDICES = [70, 63, 105, 66, 107, 55, 65, 52, 53, 46]
                RIGHT_EYEBROW_INDICES = [300, 293, 334, 296, 336, 285, 295, 282, 283, 276]
                
                # FACEMESH_NOSE 인덱스 (테스트 결과 기반)
                NOSE_INDICES = [1, 2, 4, 5, 6, 19, 45, 48, 64, 94, 97, 98, 115, 168, 195, 197, 220, 275, 278, 294, 326, 327, 344, 440]
                
                # FACEMESH_LIPS 인덱스 (테스트 결과 기반)
                LIPS_INDICES = [0, 13, 14, 17, 37, 39, 40, 61, 78, 80, 81, 82, 84, 87, 88, 91, 95, 146, 178, 181, 185, 191, 267, 269, 270, 291, 308, 310, 311, 312, 314, 317, 318, 321, 324, 375, 402, 405, 409, 415]
                
                # FACEMESH_FACE_OVAL 인덱스
                FACE_OVAL_INDICES = [10, 21, 54, 58, 67, 93, 103, 109, 127, 132, 136, 148, 149, 150, 152, 162, 172, 176, 234, 251, 284, 288, 297, 323, 332, 338, 356, 361, 365, 377, 378, 379, 389, 397, 400, 454]
                
                is_eye = any(idx in LEFT_EYE_INDICES or idx in RIGHT_EYE_INDICES for idx in all_indices_set)
                is_eyebrow = any(idx in LEFT_EYEBROW_INDICES or idx in RIGHT_EYEBROW_INDICES for idx in all_indices_set)
                is_nose = any(idx in NOSE_INDICES for idx in all_indices_set)
                is_lips = any(idx in LIPS_INDICES for idx in all_indices_set)
                is_face_oval = any(idx in FACE_OVAL_INDICES for idx in all_indices_set)
                
                # 눈, 눈썹, 코, 입, 얼굴 외곽선인 경우 주변 확장 레벨에 따라 포함
                if (is_eye or is_eyebrow or is_nose or is_lips or is_face_oval) and expansion_level > 0:
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
                    if is_eyebrow:
                        part_name.append("눈썹")
                    if is_nose:
                        part_name.append("코")
                    if is_lips:
                        part_name.append("입")
                    if is_face_oval:
                        part_name.append("얼굴외곽")
                    #print(f"[얼굴편집] {'/'.join(part_name)} 주변 확장 (레벨 {expansion_level}): {len(all_indices_set)}개 포인트 (원본 {original_count}개에서 확장)")
                
                # TESSELATION에서 확장된 포인트들만 포함하는 연결 필터링
                filtered_connections = []
                for idx1, idx2 in tesselation:
                    if idx1 in all_indices_set and idx2 in all_indices_set:
                        if idx1 < len(landmarks) and idx2 < len(landmarks):
                            filtered_connections.append((idx1, idx2))
                
                # 눈동자 연결 정보 추가 (TESSELATION에 포함되지 않음, MediaPipe 정의 사용)
                try:
                    from utils.face_morphing.region_extraction import get_iris_indices
                    left_iris_indices, right_iris_indices = get_iris_indices()
                    iris_indices = set(left_iris_indices + right_iris_indices)
                except ImportError:
                    # 폴백: 하드코딩된 인덱스 사용 (실제 MediaPipe 정의: LEFT_IRIS=[474,475,476,477], RIGHT_IRIS=[469,470,471,472])
                    iris_indices = set([469, 470, 471, 472, 474, 475, 476, 477])
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
            
            #print(f"[얼굴편집] 삼각형 메쉬 구성 완료: {len(triangles)}개 삼각형 (전체 {len(all_indices)}개 포인트 중)")
            
            return all_triangle_points
            
        except Exception as e:
            print(f"[얼굴편집] 폴리곤 경로 구성 실패: {e}")
            import traceback
            traceback.print_exc()
            return []
    
