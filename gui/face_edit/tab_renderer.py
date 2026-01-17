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
                # 왼쪽 눈동자: 468 (중심), 469, 470, 471, 472
                # 오른쪽 눈동자: 473 (중심), 474, 475, 476, 477
                iris_indices = [468, 469, 470, 471, 472, 473, 474, 475, 476, 477]
                for idx in iris_indices:
                    indices.add(idx)
                return list(indices)
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
                # 전체 탭은 모든 인덱스 (기본 468개 + 눈동자 10개)
                indices = set(range(468))
                # 눈동자 인덱스 추가 (refine_landmarks=True일 때 사용 가능)
                # 왼쪽 눈동자: 468 (중심), 469, 470, 471, 472
                # 오른쪽 눈동자: 473 (중심), 474, 475, 476, 477
                iris_indices = [468, 469, 470, 471, 472, 473, 474, 475, 476, 477]
                for idx in iris_indices:
                    indices.add(idx)
                return list(indices)
            else:
                # 기본 468개 인덱스
                indices = set(range(468))
                # 눈동자 인덱스 추가 (refine_landmarks=True일 때 사용 가능)
                iris_indices = [468, 469, 470, 471, 472, 473, 474, 475, 476, 477]
                for idx in iris_indices:
                    indices.add(idx)
                return list(indices)
        except Exception as e:
            print(f"[얼굴편집] 탭 인덱스 가져오기 실패: {e}")
            return list(range(468))
