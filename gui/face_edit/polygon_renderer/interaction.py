"""
폴리곤 상호작용 관련 메서드
"""


class InteractionMixin:
    """폴리곤 상호작용 기능 Mixin"""
    
    def on_polygon_line_click(self, event, current_tab, canvas, image, landmarks, pos_x, pos_y, items_list, color):
        """연결선 클릭 시 폴리곤 영역 표시"""
        print(f"[얼굴편집] 연결선 클릭: 탭={current_tab}")
        try:
            # 기존 폴리곤 제거
            if canvas == self.canvas_original:
                for item_id in self.landmark_polygon_items['original']:
                    try:
                        canvas.delete(item_id)
                    except Exception:
                        pass
                canvas_type = 'original'
            else:
                canvas_type = 'edited'
            
            # 폴리곤 아이템 제거
            for item_id in self.landmark_polygon_items[canvas_type]:
                try:
                    canvas.delete(item_id)
                except Exception:
                    pass
            self.landmark_polygon_items[canvas_type].clear()
            
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
    

    def _update_connected_polygons(self, canvas_obj, landmark_index):
        """연결된 폴리곤 실시간 갱신"""
        # 폴리곤을 다시 그리기 위해 얼굴 특징 표시 업데이트
        if hasattr(self, 'update_face_features_display'):
            try:
                # 원본 이미지의 폴리곤만 갱신 (편집된 이미지는 폴리곤 표시 안 함)
                if canvas_obj == self.canvas_original:
                    # 기존 폴리곤 삭제
                    for item_id in list(self.landmark_polygon_items['original']):
                        try:
                            canvas_obj.delete(item_id)
                        except:
                            pass
                    self.landmark_polygon_items['original'].clear()
                    
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
                            self.landmark_polygon_items['original'],
                            "green",
                            current_tab
                        )
            except Exception as e:
                print(f"[얼굴편집] 폴리곤 갱신 실패: {e}")
                import traceback
                traceback.print_exc()
    
