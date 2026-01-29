"""
얼굴 편집 지시선 기능
눈 중심선 기반 가이드라인 그리기
"""
import math
import tkinter as tk
from typing import List, Tuple, Optional

DEBUG_GUIDE_LINES = True


class GuideLinesManager:
    """지시선 관리자"""
    
    def __init__(self, parent):
        self.parent = parent
        self.guide_lines = {
            'original': [],
            'edited': []
        }
        self.guide_line_settings = {
            'eye_center_line': False,    # 눈 중심 직선
            'vertical_line': False,     # 수직선
            'nose_center_line': False,   # 코 중심선
            'lip_center_line': False,    # 입술 중심선
            'color': '#FF4444',         # 지시선 색상 (부드러운 빨간색)
            'width': 1,                 # 선 너비
            'dash': (2, 1)             # 점선 패턴 (원래대로)
        }
        self._force_guide_scaling = False  # 강제 지시선 스케일링 플래그
        self._ensure_state_initialized()

    def calculate_eye_center_line(self, landmarks, img_width, img_height, 
                                scale_x, scale_y, pos_x, pos_y) -> Optional[Tuple[float, float, float, float]]:
        """양쪽 눈 중심을 통과하는 수평선 계산"""
        if not landmarks or len(landmarks) < 468:
            return None
        
        try:
            # 왼쪽 눈 중심 계산 (눈 주변 랜드마크 사용 - 안정적)
            left_eye_indices = [33, 7, 163, 144, 145, 153, 154, 155, 133, 173, 157, 158, 159, 160, 161, 246]
            left_eye_points = []
            for idx in left_eye_indices:
                if idx < len(landmarks):
                    pt = landmarks[idx]
                    if isinstance(pt, tuple):
                        left_eye_points.append(pt)
                    else:
                        left_eye_points.append((pt.x * img_width, pt.y * img_height))
            
            # 오른쪽 눈 중심 계산 (눈 주변 랜드마크 사용 - 안정적)
            right_eye_indices = [362, 398, 384, 385, 386, 387, 388, 466, 263, 249, 390, 373, 374, 380, 381, 382]
            right_eye_points = []
            for idx in right_eye_indices:
                if idx < len(landmarks):
                    pt = landmarks[idx]
                    if isinstance(pt, tuple):
                        right_eye_points.append(pt)
                    else:
                        right_eye_points.append((pt.x * img_width, pt.y * img_height))
            
            if not left_eye_points or not right_eye_points:
                return None
            
            # 각 눈의 중심 계산
            left_center_x = sum(p[0] for p in left_eye_points) / len(left_eye_points)
            left_center_y = sum(p[1] for p in left_eye_points) / len(left_eye_points)
            
            right_center_x = sum(p[0] for p in right_eye_points) / len(right_eye_points)
            right_center_y = sum(p[1] for p in right_eye_points) / len(right_eye_points)
            
            # 디버깅: 눈동자 사용 여부 출력
            if DEBUG_GUIDE_LINES:
                use_iris_left = len([idx for idx in [468, 469, 470, 471, 472] if idx < len(landmarks)]) > 0
                use_iris_right = len([idx for idx in [473, 474, 475, 476, 477] if idx < len(landmarks)]) > 0
                print(f"[지시선] 스케일링용 눈 중심 계산: 왼쪽 눈동자={'사용' if use_iris_left else '눈주변'}, "
                      f"오른쪽 눈동자={'사용' if use_iris_right else '눈주변'}")

            # 두 눈 중심을 지나는 직선 계산
            # 직선의 기울기 계산
            dx = right_center_x - left_center_x
            dy = right_center_y - left_center_y
            
            if abs(dx) < 0.001:  # 수직선에 가까운 경우
                # 수직선 처리
                angle = math.pi / 2
            else:
                angle = math.atan2(dy, dx)
            
            # 직선의 중심점 (두 눈 중심의 중간)
            center_x = (left_center_x + right_center_x) / 2
            center_y = (left_center_y + right_center_y) / 2
            
            # 캔버스 좌표로 변환
            canvas_center_x = pos_x + (center_x - img_width / 2) * scale_x
            canvas_center_y = pos_y + (center_y - img_height / 2) * scale_y
            
            # 캔버스 크기
            canvas_width = pos_x * 2
            canvas_height = pos_y * 2
            
            # 직선의 끝점 계산 (캔버스 경계까지 연장)
            line_length = max(canvas_width, canvas_height) * 1.5  # 충분히 긴 길이
            
            # 직선 방향 벡터
            dir_x = math.cos(angle)
            dir_y = math.sin(angle)
            
            # 직선의 시작점과 끝점
            line_x1 = canvas_center_x - dir_x * line_length / 2
            line_y1 = canvas_center_y - dir_y * line_length / 2
            line_x2 = canvas_center_x + dir_x * line_length / 2
            line_y2 = canvas_center_y + dir_y * line_length / 2
            
            return (line_x1, line_y1, line_x2, line_y2, left_center_x, right_center_x, 
                   left_center_y, right_center_y, angle, center_x, center_y)
            
        except Exception as e:
            if DEBUG_GUIDE_LINES:
                print(f"눈 중심선 계산 오류: {e}")
            return None
    
    def calculate_perpendicular_lines(self, eye_center_info, img_width, img_height,
                                   scale_x, scale_y, pos_x, pos_y) -> List[Tuple[float, float, float, float]]:
        """직선에 수직인 선 계산 (왼쪽 눈 중심, 오른쪽 눈 중심)"""
        if not eye_center_info or len(eye_center_info) < 11:
            return []
        
        try:
            _, _, _, _, left_center_x, right_center_x, left_center_y, right_center_y, angle, center_x, center_y = eye_center_info
            
            perpendicular_lines = []
            
            # 수직 각도 (원래 각도 + 90도)
            perp_angle = angle + math.pi / 2
            
            # 캔버스 크기
            canvas_width = pos_x * 2
            canvas_height = pos_y * 2
            
            # 수직선의 길이 (얼굴 크기 반만큼)
            face_size = min(img_width, img_height)
            line_length = face_size * 0.25
           
            # 수직선 방향 벡터
            perp_dir_x = math.cos(perp_angle)
            perp_dir_y = math.sin(perp_angle)
            
            # 왼쪽 눈 중심 수직선
            left_canvas_x = pos_x + (left_center_x - img_width / 2) * scale_x
            left_canvas_y = pos_y + (left_center_y - img_height / 2) * scale_y
            
            left_line_x1 = left_canvas_x - perp_dir_x * line_length / 2
            left_line_y1 = left_canvas_y - perp_dir_y * line_length / 2
            left_line_x2 = left_canvas_x + perp_dir_x * line_length / 2
            left_line_y2 = left_canvas_y + perp_dir_y * line_length / 2
            
            perpendicular_lines.append((left_line_x1, left_line_y1, left_line_x2, left_line_y2))
            
            # 오른쪽 눈 중심 수직선
            right_canvas_x = pos_x + (right_center_x - img_width / 2) * scale_x
            right_canvas_y = pos_y + (right_center_y - img_height / 2) * scale_y
            
            right_line_x1 = right_canvas_x - perp_dir_x * line_length / 2
            right_line_y1 = right_canvas_y - perp_dir_y * line_length / 2
            right_line_x2 = right_canvas_x + perp_dir_x * line_length / 2
            right_line_y2 = right_canvas_y + perp_dir_y * line_length / 2
            
            perpendicular_lines.append((right_line_x1, right_line_y1, right_line_x2, right_line_y2))
            
            return perpendicular_lines
            
        except Exception as e:
            if DEBUG_GUIDE_LINES:
                print(f"수직선 계산 오류: {e}")
            return []
    
    def calculate_nose_center_line(self, landmarks, img_width, img_height, 
                                 scale_x, scale_y, pos_x, pos_y, eye_center_info=None) -> Optional[Tuple[float, float, float, float]]:
        """코 중심선 계산 (입술 중심점을 지나는 눈 연결선에 수직인 선)"""
        if not landmarks or len(landmarks) < 468:
            return None
        
        try:
            # 입술 중심점 (14번 랜드마크) 가져오기
            lip_center_indices = [14]
            
            lip_points = []
            for idx in lip_center_indices:
                if idx < len(landmarks):
                    pt = landmarks[idx]
                    if isinstance(pt, tuple):
                        lip_points.append(pt)
                    else:
                        lip_points.append((pt.x * img_width, pt.y * img_height))
            
            if not lip_points:
                return None
            
            # 입술 중심점
            lip_center_x = lip_points[0][0]
            lip_center_y = lip_points[0][1]
            
            # 입술 중심점의 캔버스 좌표
            canvas_lip_x = pos_x + (lip_center_x - img_width / 2) * scale_x
            canvas_lip_y = pos_y + (lip_center_y - img_height / 2) * scale_y
            
            # 눈 연결선의 각도 가져오기
            if eye_center_info and len(eye_center_info) >= 11:
                _, _, _, _, _, _, _, _, angle, _, _ = eye_center_info
                # 눈 연결선에 수직인 각도
                nose_angle = angle + math.pi / 2
            else:
                # 눈 정보가 없는 경우, 수직선으로 기본 설정
                nose_angle = math.pi / 2
            
            # 캔버스 크기
            canvas_width = pos_x * 2
            canvas_height = pos_y * 2
            
            # 코 중심선의 길이
            line_length = max(canvas_width, canvas_height) * 1.5
            
            # 코 중심선 방향 벡터
            dir_x = math.cos(nose_angle)
            dir_y = math.sin(nose_angle)
            
            # 코 중심선의 시작점과 끝점 (입술 중심점 통과)
            line_x1 = canvas_lip_x - dir_x * line_length / 2
            line_y1 = canvas_lip_y - dir_y * line_length / 2
            line_x2 = canvas_lip_x + dir_x * line_length / 2
            line_y2 = canvas_lip_y + dir_y * line_length / 2
            
            return (line_x1, line_y1, line_x2, line_y2)
            
        except Exception as e:
            if DEBUG_GUIDE_LINES:
                print(f"코 중심선 계산 오류: {e}")
            return None
    
    def calculate_lip_center_line(self, landmarks, img_width, img_height, 
                                 scale_x, scale_y, pos_x, pos_y, eye_center_info=None) -> Optional[Tuple[float, float, float, float]]:
        """입술 중심선 계산 (눈 연결선과 수평인 선)"""
        if not landmarks or len(landmarks) < 468:
            return None
        
        try:
            # 입술 중심 랜드마크 (MediaPipe 인덱스)
            # 14번: 입술 정중앙점 (윗입술-아랫입술 경계 중앙)
            lip_center_indices = [14]
            
            # 입술 중심점 (14번 랜드마크 직접 사용)
            lip_points = []
            for idx in lip_center_indices:
                if idx < len(landmarks):
                    pt = landmarks[idx]
                    if isinstance(pt, tuple):
                        lip_points.append(pt)
                    else:
                        lip_points.append((pt.x * img_width, pt.y * img_height))
            
            if not lip_points:
                return None
            
            # 입술 중심점 (14번 랜드마크)
            lip_center_x = lip_points[0][0]
            lip_center_y = lip_points[0][1]
            
            # 캔버스 좌표로 변환
            canvas_lip_x = pos_x + (lip_center_x - img_width / 2) * scale_x
            canvas_lip_y = pos_y + (lip_center_y - img_height / 2) * scale_y
            
            # 코 중심선의 각도 가져오기 (눈 연결선에 수직인 각도)
            if eye_center_info and len(eye_center_info) >= 11:
                _, _, _, _, _, _, _, _, angle, _, _ = eye_center_info
                # 입술 중심선 각도 (눈 연결선과 수평)
                lip_angle = angle
            else:
                # 눈 정보가 없는 경우, 수평선으로 기본 설정
                lip_angle = 0
            
            # 캔버스 크기
            canvas_width = pos_x * 2
            canvas_height = pos_y * 2
            
            # 입술 중심선의 길이
            line_length = max(canvas_width, canvas_height) * 1.5
            
            # 입술 중심선 방향 벡터
            dir_x = math.cos(lip_angle)
            dir_y = math.sin(lip_angle)
            
            # 입술 중심선의 시작점과 끝점
            line_x1 = canvas_lip_x - dir_x * line_length / 2
            line_y1 = canvas_lip_y - dir_y * line_length / 2
            line_x2 = canvas_lip_x + dir_x * line_length / 2
            line_y2 = canvas_lip_y + dir_y * line_length / 2
            
            return (line_x1, line_y1, line_x2, line_y2)
            
        except Exception as e:
            if DEBUG_GUIDE_LINES:
                print(f"입술 중심선 계산 오류: {e}")
            return None

    def draw_guide_lines(self, canvas, landmarks, img_width, img_height,
                        scale_x, scale_y, pos_x, pos_y, canvas_type='original'):
        """지시선 그리기"""
        self._ensure_canvas_key(canvas_type)
        signature = self._build_guide_line_signature(
            landmarks, img_width, img_height, scale_x, scale_y, pos_x, pos_y, canvas_type
        )

        if self._guide_line_signatures[canvas_type] == signature:
            if DEBUG_GUIDE_LINES:
                print(f"[지시선] 시그니처 동일로 스킵 ({canvas_type})")
            return

        if self._guide_line_draw_in_progress[canvas_type]:
            if DEBUG_GUIDE_LINES:
                print(f"[지시선] 재진입 감지 → 다음 프레임으로 미룸 ({canvas_type})")
            self._guide_line_pending_request[canvas_type] = (
                canvas, landmarks, img_width, img_height,
                scale_x, scale_y, pos_x, pos_y, canvas_type
            )
            return

        self._guide_line_draw_in_progress[canvas_type] = True
        try:
            show_flags = self._get_show_flags()
            if not any(show_flags):
                if DEBUG_GUIDE_LINES:
                    print(f"[지시선] 표시 옵션 꺼짐 ({canvas_type})")
                self.clear_guide_lines(canvas, canvas_type)
                self._guide_line_signatures[canvas_type] = signature
                return

            if not landmarks:
                if DEBUG_GUIDE_LINES:
                    print(f"[지시선] 랜드마크 없음 → 클리어 ({canvas_type})")
                self.clear_guide_lines(canvas, canvas_type)
                self._guide_line_signatures[canvas_type] = signature
                return

            # 기존 지시선 제거
            self.clear_guide_lines(canvas, canvas_type)

            eye_center_info = self.calculate_eye_center_line(
                landmarks, img_width, img_height, scale_x, scale_y, pos_x, pos_y
            )

            if not eye_center_info:
                if DEBUG_GUIDE_LINES:
                    print(f"[지시선] 눈 중심선 계산 실패 ({canvas_type})")
                self._guide_line_signatures[canvas_type] = signature
                return

            if getattr(self.parent, 'debug_guide_axis', False):
                _, _, _, _, left_center_x, right_center_x, left_center_y, right_center_y, angle, center_x, center_y = eye_center_info
                canvas_center_x = pos_x + (center_x - img_width / 2) * scale_x
                canvas_center_y = pos_y + (center_y - img_height / 2) * scale_y
                self.parent.current_guide_axis_info = {
                    'canvas': canvas_type,
                    'angle_rad': angle,
                    'angle_deg': math.degrees(angle),
                    'center_image': (center_x, center_y),
                    'center_canvas': (canvas_center_x, canvas_center_y),
                    'left_center': (left_center_x, left_center_y),
                    'right_center': (right_center_x, right_center_y),
                }
                print(
                    f"[GuideAxis] {canvas_type} angle={math.degrees(angle):.2f}° "
                    f"center_img=({center_x:.1f},{center_y:.1f}) center_canvas=({canvas_center_x:.1f},{canvas_center_y:.1f})"
                )

            drawn_lines = []

            # 눈 중심선 (두 눈 중심을 지나는 직선)
            if self.guide_line_settings['eye_center_line']:
                x1, y1, x2, y2, _, _, _, _, _, _, _ = eye_center_info
                line_id = canvas.create_line(
                    x1, y1, x2, y2,
                    fill=self.guide_line_settings['color'],
                    width=self.guide_line_settings['width'],
                    dash=self.guide_line_settings['dash'],
                    tags=("guide_lines", "eye_center_line")
                )
                drawn_lines.append(line_id)

            # 수직선 (직선에 수직인 선)
            if self.guide_line_settings['vertical_line']:
                perpendicular_lines = self.calculate_perpendicular_lines(
                    eye_center_info, img_width, img_height, scale_x, scale_y, pos_x, pos_y
                )

                for i, (vx1, vy1, vx2, vy2) in enumerate(perpendicular_lines):
                    line_id = canvas.create_line(
                        vx1, vy1, vx2, vy2,
                        fill=self.guide_line_settings['color'],
                        width=self.guide_line_settings['width'],
                        dash=self.guide_line_settings['dash'],
                        tags=("guide_lines", f"vertical_line_{i}")
                    )
                    drawn_lines.append(line_id)
            elif DEBUG_GUIDE_LINES:
                print("[지시선] 수직선 설정이 꺼져 있음")

            # 코 중심선
            if self.guide_line_settings['nose_center_line']:
                nose_line_info = self.calculate_nose_center_line(
                    landmarks, img_width, img_height, scale_x, scale_y, pos_x, pos_y, eye_center_info
                )

                if nose_line_info:
                    x1, y1, x2, y2 = nose_line_info
                    line_id = canvas.create_line(
                        x1, y1, x2, y2,
                        fill=self.guide_line_settings['color'],
                        width=self.guide_line_settings['width'],
                        dash=self.guide_line_settings['dash'],
                        tags=("guide_lines", "nose_center_line")
                    )
                    drawn_lines.append(line_id)
                elif DEBUG_GUIDE_LINES:
                    print("[지시선] 코 중심선 계산 실패")

            # 입술 중심선
            if self.guide_line_settings['lip_center_line']:
                lip_line_info = self.calculate_lip_center_line(
                    landmarks, img_width, img_height, scale_x, scale_y, pos_x, pos_y, eye_center_info
                )

                if lip_line_info:
                    x1, y1, x2, y2 = lip_line_info
                    line_id = canvas.create_line(
                        x1, y1, x2, y2,
                        fill=self.guide_line_settings['color'],
                        width=self.guide_line_settings['width'],
                        dash=self.guide_line_settings['dash'],
                        tags=("guide_lines", "lip_center_line")
                    )
                    drawn_lines.append(line_id)
                elif DEBUG_GUIDE_LINES:
                    print("[지시선] 입술 중심선 계산 실패")

            # 지시선 목록에 저장
            self.guide_lines[canvas_type] = drawn_lines

            # 지시선을 최상위로 올리기 (이미지 위, 랜드마크 아래)
            for line_id in drawn_lines:
                try:
                    canvas.tag_raise(line_id)
                except Exception as e:
                    if DEBUG_GUIDE_LINES:
                        print(f"[지시선] 태그 레벨 변경 실패: {e}")

            self._guide_line_signatures[canvas_type] = signature
        finally:
            self._guide_line_draw_in_progress[canvas_type] = False

    
    def clear_guide_lines(self, canvas, canvas_type='original'):
        """지시선 제거"""
        self._ensure_canvas_key(canvas_type)
        try:
            for line_id in self.guide_lines[canvas_type]:
                canvas.delete(line_id)
            self.guide_lines[canvas_type].clear()
        except Exception as e:
            if DEBUG_GUIDE_LINES:
                print(f"지시선 제거 오류: {e}")
        finally:
            self._guide_line_signatures[canvas_type] = None
    
    def get_eye_centers_and_angle(self, landmarks, img_width, img_height):
        """눈 중심점과 각도 정보 반환 (지시선 기반 스케일링용)"""
        if not landmarks or len(landmarks) < 468:
            return None, None, None
        
        try:
            # 왼쪽 눈 중심 계산 (눈 주변 랜드마크 사용 - 안정적)
            left_eye_indices = [33, 7, 163, 144, 145, 153, 154, 155, 133, 173, 157, 158, 159, 160, 161, 246]
            left_eye_points = []
            for idx in left_eye_indices:
                if idx < len(landmarks):
                    pt = landmarks[idx]
                    if isinstance(pt, tuple):
                        left_eye_points.append(pt)
                    else:
                        left_eye_points.append((pt.x * img_width, pt.y * img_height))
            
            # 오른쪽 눈 중심 계산 (눈 주변 랜드마크 사용 - 안정적)
            right_eye_indices = [362, 398, 384, 385, 386, 387, 388, 466, 263, 249, 390, 373, 374, 380, 381, 382]
            right_eye_points = []
            for idx in right_eye_indices:
                if idx < len(landmarks):
                    pt = landmarks[idx]
                    if isinstance(pt, tuple):
                        right_eye_points.append(pt)
                    else:
                        right_eye_points.append((pt.x * img_width, pt.y * img_height))
            
            if not left_eye_points or not right_eye_points:
                return None, None, None
            
            # 각 눈의 중심 계산
            left_center_x = sum(p[0] for p in left_eye_points) / len(left_eye_points)
            left_center_y = sum(p[1] for p in left_eye_points) / len(left_eye_points)
            
            right_center_x = sum(p[0] for p in right_eye_points) / len(right_eye_points)
            right_center_y = sum(p[1] for p in right_eye_points) / len(right_eye_points)
            
            # 디버깅: 눈동자 사용 여부 출력
            if DEBUG_GUIDE_LINES:
                use_iris_left = len([idx for idx in [468, 469, 470, 471, 472] if idx < len(landmarks)]) > 0
                use_iris_right = len([idx for idx in [473, 474, 475, 476, 477] if idx < len(landmarks)]) > 0
                print(f"[지시선] 스케일링용 눈 중심 계산: 왼쪽 눈동자={'사용' if use_iris_left else '눈주변'}, "
                      f"오른쪽 눈동자={'사용' if use_iris_right else '눈주변'}")
                print(f"[지시선] 계산된 눈 중심: 왼쪽=({left_center_x:.1f}, {left_center_y:.1f}), 오른쪽=({right_center_x:.1f}, {right_center_y:.1f})")
            
            # 눈 연결선 각도 계산
            dx = right_center_x - left_center_x
            dy = right_center_y - left_center_y
            
            if abs(dx) < 0.001:  # 수직선에 가까운 경우
                angle = math.pi / 2
            else:
                angle = math.atan2(dy, dx)
            
            return (left_center_x, left_center_y), (right_center_x, right_center_y), angle
            
        except Exception as e:
            if DEBUG_GUIDE_LINES:
                print(f"눈 중심점 계산 오류: {e}")
            return None, None, None
    
    def update_guide_line_style(self, color=None, width=None, dash=None):
        """지시선 스타일 업데이트"""
        if color:
            self.guide_line_settings['color'] = color
        if width:
            self.guide_line_settings['width'] = width
        if dash:
            self.guide_line_settings['dash'] = dash
    
    def toggle_guide_lines(self):
        """지시선 토글"""
        # 모든 지시선 토글
        for key in self.guide_line_settings:
            if key.endswith('_line'):
                self.guide_line_settings[key] = not self.guide_line_settings[key]
        self._reset_signatures()
    
    def get_guide_line_settings(self):
        """지시선 설정 반환"""
        return self.guide_line_settings.copy()

    def _compute_landmark_checksum(self, landmarks):
        if not landmarks:
            return None
        length = len(landmarks)
        if length == 0:
            return None
        sample_indices = [0, length // 2, length - 1]
        samples = []
        for idx in sample_indices:
            if idx < 0 or idx >= length:
                continue
            point = landmarks[idx]
            if isinstance(point, tuple):
                x, y = point[:2]
            else:
                x = getattr(point, 'x', 0)
                y = getattr(point, 'y', 0)
            try:
                x_val = float(x)
                y_val = float(y)
            except (TypeError, ValueError):
                x_val, y_val = 0.0, 0.0
            samples.append(round(x_val, 3))
            samples.append(round(y_val, 3))
        return (length, tuple(samples))

    def _build_guide_line_signature(self, landmarks, img_width, img_height,
                                    scale_x, scale_y, pos_x, pos_y, canvas_type):
        show_flags = self._get_show_flags()
        dash = self.guide_line_settings.get('dash')
        dash_tuple = tuple(dash) if isinstance(dash, (list, tuple)) else dash
        checksum = self._compute_landmark_checksum(landmarks)
        return (
            canvas_type,
            show_flags,
            self.guide_line_settings.get('color'),
            self.guide_line_settings.get('width'),
            dash_tuple,
            round(scale_x or 0.0, 4) if scale_x is not None else 0.0,
            round(scale_y or 0.0, 4) if scale_y is not None else 0.0,
            round(pos_x or 0.0, 2) if pos_x is not None else 0.0,
            round(pos_y or 0.0, 2) if pos_y is not None else 0.0,
            int(img_width or 0),
            int(img_height or 0),
            checksum,
        )

    def _get_show_flags(self):
        return (
            self.guide_line_settings.get('eye_center_line', False),
            self.guide_line_settings.get('vertical_line', False),
            self.guide_line_settings.get('nose_center_line', False),
            self.guide_line_settings.get('lip_center_line', False),
        )

    def _ensure_state_initialized(self):
        if not hasattr(self, '_guide_line_signatures'):
            self._guide_line_signatures = {'original': None, 'edited': None}
        if not hasattr(self, '_guide_line_draw_in_progress'):
            self._guide_line_draw_in_progress = {'original': False, 'edited': False}
        if not hasattr(self, '_guide_line_pending_request'):
            self._guide_line_pending_request = {'original': None, 'edited': None}

    def _ensure_canvas_key(self, canvas_type):
        self._ensure_state_initialized()
        if canvas_type not in self._guide_line_signatures:
            self._guide_line_signatures[canvas_type] = None
            self._guide_line_draw_in_progress[canvas_type] = False
            self._guide_line_pending_request[canvas_type] = None

    def _reset_signatures(self):
        self._ensure_state_initialized()
        for key in list(self._guide_line_signatures.keys()):
            self._guide_line_signatures[key] = None
            self._guide_line_draw_in_progress[key] = False
            self._guide_line_pending_request[key] = None
