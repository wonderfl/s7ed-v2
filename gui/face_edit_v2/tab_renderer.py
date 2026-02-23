"""
얼굴 편집 패널 - 전체 탭 전용 렌더링 Mixin
전체 탭과 고급 모드에 집중한 단순화된 구조
"""


class TabRendererMixin:
    """전체 탭 전용 렌더링 기능 Mixin"""
    
    def _get_target_indices_for_tab(self, current_tab):
        """현재 탭에 해당하는 랜드마크 인덱스 목록 반환 (전체 탭만 지원)"""
        if current_tab == '전체':
            # 전체 탭: 모든 랜드마크 인덱스 반환
            return list(range(468))
        else:
            # 다른 탭은 지원하지 않음
            print(f"[경고] 지원하지 않는 탭: {current_tab}, 전체 탭으로 처리")
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
            
            if hasattr(self, 'show_tesselation') and self.show_tesselation.get():
                # Tesselation은 전체 메쉬
                return list(range(468))
            
            return list(indices) if indices else None
            
        except Exception as e:
            return None
