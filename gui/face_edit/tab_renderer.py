"""
얼굴 편집 패널 - 탭별 렌더링 Mixin
탭별 랜드마크 인덱스 및 렌더링 로직을 담당
"""


class TabRendererMixin:
    """탭별 렌더링 기능 Mixin"""
    
    def _get_target_indices_for_tab(self, current_tab):
        """현재 탭에 해당하는 랜드마크 인덱스 목록 반환"""
        try:
            import mediapipe as mp
            mp_face_mesh = mp.solutions.face_mesh
            
            if current_tab == '눈':
                LEFT_EYE = list(mp_face_mesh.FACEMESH_LEFT_EYE)
                RIGHT_EYE = list(mp_face_mesh.FACEMESH_RIGHT_EYE)
                indices = set()
                for conn in LEFT_EYE + RIGHT_EYE:
                    indices.add(conn[0])
                    indices.add(conn[1])
                # 눈동자 인덱스 추가 (refine_landmarks=True일 때 사용 가능)
                # 눈동자 인덱스 (MediaPipe 정의 사용)
                try:
                    from utils.face_morphing.region_extraction import get_iris_indices
                    left_iris_indices, right_iris_indices = get_iris_indices()
                    iris_indices = left_iris_indices + right_iris_indices
                except ImportError:
                    # 폴백: 하드코딩된 인덱스 사용 (실제 MediaPipe 정의: LEFT_IRIS=[474,475,476,477], RIGHT_IRIS=[469,470,471,472])
                    iris_indices = [469, 470, 471, 472, 474, 475, 476, 477]
                for idx in iris_indices:
                    indices.add(idx)
                return list(indices)
            elif current_tab == '눈동자':
                # 눈동자 탭: 눈동자 인덱스만 반환
                try:
                    from utils.face_morphing.region_extraction import get_iris_indices
                    left_iris_indices, right_iris_indices = get_iris_indices()
                    iris_indices = left_iris_indices + right_iris_indices
                except ImportError:
                    # 폴백: 하드코딩된 인덱스 사용
                    iris_indices = [469, 470, 471, 472, 474, 475, 476, 477]
                return iris_indices
            elif current_tab == '눈썹':
                LEFT_EYEBROW = list(mp_face_mesh.FACEMESH_LEFT_EYEBROW)
                RIGHT_EYEBROW = list(mp_face_mesh.FACEMESH_RIGHT_EYEBROW)
                indices = set()
                for conn in LEFT_EYEBROW + RIGHT_EYEBROW:
                    indices.add(conn[0])
                    indices.add(conn[1])
                return list(indices)
            elif current_tab == '턱선':
                FACE_OVAL = list(mp_face_mesh.FACEMESH_FACE_OVAL)
                indices = set()
                for conn in FACE_OVAL:
                    indices.add(conn[0])
                    indices.add(conn[1])
                return list(indices)
            elif current_tab == '전체':
                # 전체 탭: 선택된 부위가 있으면 선택된 부위만, 없으면 전체 표시
                selected_indices = self._get_selected_region_indices()
                if selected_indices is not None and len(selected_indices) > 0:
                    # 선택된 부위가 있으면 선택된 부위만 반환
                    return selected_indices
                else:
                    # 선택된 부위가 없으면 전체 인덱스 (기본 468개 + 눈동자 10개)
                    indices = set(range(468))
                    # 눈동자 인덱스 추가 (refine_landmarks=True일 때 사용 가능)
                    # 눈동자 인덱스 (MediaPipe 정의 사용)
                    try:
                        from utils.face_morphing.region_extraction import get_iris_indices
                        left_iris_indices, right_iris_indices = get_iris_indices()
                        iris_indices = left_iris_indices + right_iris_indices
                    except ImportError:
                        # 폴백: 하드코딩된 인덱스 사용 (실제 MediaPipe 정의: LEFT_IRIS=[474,475,476,477], RIGHT_IRIS=[469,470,471,472])
                        iris_indices = [469, 470, 471, 472, 474, 475, 476, 477]
                    for idx in iris_indices:
                        indices.add(idx)
                    return list(indices)
            else:
                # 기본 468개 인덱스
                # 눈동자 인덱스 추가 (refine_landmarks=True일 때 사용 가능, MediaPipe 정의 사용)
                try:
                    from utils.face_morphing.region_extraction import get_iris_indices
                    left_iris_indices, right_iris_indices = get_iris_indices()
                    iris_indices = left_iris_indices + right_iris_indices
                    min_iris_index = min(iris_indices) if iris_indices else 468
                except ImportError:
                    # 폴백: 하드코딩된 인덱스 사용 (실제 MediaPipe 정의: LEFT_IRIS=[474,475,476,477], RIGHT_IRIS=[469,470,471,472])
                    iris_indices = [469, 470, 471, 472, 474, 475, 476, 477]
                    min_iris_index = 469
                indices = set(range(min_iris_index))
                for idx in iris_indices:
                    indices.add(idx)
                return list(indices)
        except Exception as e:
            return list(range(468))
    
    def _get_selected_region_indices(self):
        """선택된 부위의 랜드마크 인덱스 목록 반환 (전체 탭용)"""
        try:
            import mediapipe as mp
            mp_face_mesh = mp.solutions.face_mesh
            
            indices = set()
            
            # 선택된 부위에 따라 인덱스 추가
            if hasattr(self, 'show_face_oval') and self.show_face_oval.get():
                FACE_OVAL = list(mp_face_mesh.FACEMESH_FACE_OVAL)
                for conn in FACE_OVAL:
                    indices.add(conn[0])
                    indices.add(conn[1])
            
            if hasattr(self, 'show_left_eye') and self.show_left_eye.get():
                LEFT_EYE = list(mp_face_mesh.FACEMESH_LEFT_EYE)
                for conn in LEFT_EYE:
                    indices.add(conn[0])
                    indices.add(conn[1])
            
            if hasattr(self, 'show_right_eye') and self.show_right_eye.get():
                RIGHT_EYE = list(mp_face_mesh.FACEMESH_RIGHT_EYE)
                for conn in RIGHT_EYE:
                    indices.add(conn[0])
                    indices.add(conn[1])
            
            if hasattr(self, 'show_left_eyebrow') and self.show_left_eyebrow.get():
                LEFT_EYEBROW = list(mp_face_mesh.FACEMESH_LEFT_EYEBROW)
                for conn in LEFT_EYEBROW:
                    indices.add(conn[0])
                    indices.add(conn[1])
            
            if hasattr(self, 'show_right_eyebrow') and self.show_right_eyebrow.get():
                RIGHT_EYEBROW = list(mp_face_mesh.FACEMESH_RIGHT_EYEBROW)
                for conn in RIGHT_EYEBROW:
                    indices.add(conn[0])
                    indices.add(conn[1])
            
            if hasattr(self, 'show_nose') and self.show_nose.get():
                NOSE = list(mp_face_mesh.FACEMESH_NOSE)
                for conn in NOSE:
                    indices.add(conn[0])
                    indices.add(conn[1])
            
            if hasattr(self, 'show_lips') and self.show_lips.get():
                LIPS = list(mp_face_mesh.FACEMESH_LIPS)
                for conn in LIPS:
                    indices.add(conn[0])
                    indices.add(conn[1])
            
            # 눈동자는 refine_landmarks=True일 때만 사용 가능
            try:
                if hasattr(self, 'show_left_iris') and self.show_left_iris.get():
                    LEFT_IRIS = list(mp_face_mesh.FACEMESH_LEFT_IRIS)
                    for conn in LEFT_IRIS:
                        indices.add(conn[0])
                        indices.add(conn[1])
                
                if hasattr(self, 'show_right_iris') and self.show_right_iris.get():
                    RIGHT_IRIS = list(mp_face_mesh.FACEMESH_RIGHT_IRIS)
                    for conn in RIGHT_IRIS:
                        indices.add(conn[0])
                        indices.add(conn[1])
            except AttributeError:
                # FACEMESH_LEFT_IRIS 또는 FACEMESH_RIGHT_IRIS가 없는 경우 (refine_landmarks=False)
                pass
            
            return list(indices) if indices else None
            
        except Exception as e:
            return None