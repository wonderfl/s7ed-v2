"""
눈동자 렌더러
All 탭과 눈동자 탭에서 공통으로 사용하는 눈동자 그리기 로직
"""

import math
from .iris_drag_handler import IrisDragHandler


class IrisRenderer:
    """눈동자 관련 그리기 기능을 통합적으로 처리하는 렌더러"""
    
    def __init__(self, parent):
        """
        초기화
        
        Args:
            parent: 부모 클래스 인스턴스 (FaceEditPanel 등)
        """
        self.parent = parent
        self.drag_handler = IrisDragHandler(parent)
    
    def draw_iris_center(self, canvas, iris_side, center_x, center_y, 
                        center_radius=5, pos_x=0, pos_y=0, scale_x=1, scale_y=1,
                        img_width=None, img_height=None, iris_coords=None, items_list=None):
        """
        눈동자 중심점 그리기 (연결선과 외곽선 포함)
        
        Args:
            canvas: 캔버스 객체
            iris_side: 'left' 또는 'right'
            center_x: 중심점 X 좌표
            center_y: 중심점 Y 좌표
            center_radius: 중심점 반지름
            pos_x: 캔버스 내 X 위치
            pos_y: 캔버스 내 Y 위치
            scale_x: X 스케일
            scale_y: Y 스케일
            img_width: 이미지 너비
            img_height: 이미지 높이
            iris_coords: 눈동자 외곽점 좌표 리스트
            items_list: 캔버스 아이템 리스트
            
        Returns:
            int: 생성된 중심점의 캔버스 ID
        """
        # 이미지 크기가 없으면 부모 객체에서 가져오기
        if img_width is None:
            img_width = getattr(self.parent, 'img_width', 512)
        if img_height is None:
            img_height = getattr(self.parent, 'img_height', 512)
        
        # 이미지 좌표를 캔버스 좌표로 변환
        center_canvas_x = pos_x + (center_x - img_width / 2) * scale_x
        center_canvas_y = pos_y + (center_y - img_height / 2) * scale_y
        
        # 중심점 생성
        center_id = canvas.create_oval(
            center_canvas_x - center_radius,
            center_canvas_y - center_radius,
            center_canvas_x + center_radius,
            center_canvas_y + center_radius,
            fill="yellow",
            outline="red",
            width=2,
            tags=("iris_center", f"iris_center_{iris_side}", "landmarks_polygon")
        )
        
        # 중심점을 최상위로 올리기 (다른 모든 요소들 위로)
        canvas.tag_raise(center_id)
        canvas.tag_raise("iris_center")
        canvas.tag_raise(f"iris_center_{iris_side}")
        
        # 드래그 이벤트 바인딩
        self.drag_handler.bind_iris_drag_events(canvas, center_id, iris_side)
        
        # 연결선과 외곽선 그리기 (옵션 확인) - 중심점보다 아래에 그리기
        if iris_coords and items_list is not None:
            # 옵션 확인
            show_connections = hasattr(self.parent, 'show_iris_connections') and self.parent.show_iris_connections.get()
            
            if show_connections:
                print(f"[DEBUG] Drawing iris connections for {iris_side} (public module)")
                # 연결선 그리기
                self.draw_iris_connections(
                    canvas, iris_side, center_x, center_y,
                    iris_coords, img_width, img_height, 
                    scale_x, scale_y, pos_x, pos_y, items_list
                )
                
                # 외곽선 그리기
                if len(iris_coords) >= 4:
                    self.draw_iris_outline(
                        canvas, iris_side, iris_coords, 
                        img_width, img_height, scale_x, scale_y, 
                        pos_x, pos_y, items_list
                    )
            else:
                print(f"[DEBUG] Skipping iris connections for {iris_side} - checkbox not checked")
        
        # 중심점을 다시 최상위로 올리기 (연결선 그린 후)
        canvas.tag_raise(center_id)
        canvas.tag_raise("iris_center")
        canvas.tag_raise(f"iris_center_{iris_side}")
        
        print(f"[DEBUG] Created iris center with ID: {center_id} for {iris_side} - raised to top")
        
        return center_id
    
    def draw_iris_connections(self, canvas, iris_side, center_x, center_y,
                             iris_coords, img_width, img_height, scale_x, scale_y, 
                             pos_x, pos_y, items_list):
        """
        눈동자 중심점과 외곽점 연결선 그리기
        
        Args:
            canvas: 캔버스 객체
            iris_side: 'left' 또는 'right'
            center_x: 중심점 X 좌표
            center_y: 중심점 Y 좌표
            iris_coords: 눈동자 외곽점 좌표 리스트
            img_width: 이미지 너비
            img_height: 이미지 높이
            scale_x: X 스케일
            scale_y: Y 스케일
            pos_x: 캔버스 내 X 위치
            pos_y: 캔버스 내 Y 위치
            items_list: 캔버스 아이템 리스트
        """
        if not iris_coords:
            return
        
        # 중심점을 캔버스 좌표로 변환
        center_canvas_x = pos_x + (center_x - img_width / 2) * scale_x
        center_canvas_y = pos_y + (center_y - img_height / 2) * scale_y
        
        # 연결선 색상 및 너비 설정
        connection_color = "#FF6B6B" if iris_side == 'left' else "#4ECDC4"
        connection_width = 1  # 더 두껍게
        
        # 각 외곽점과 중심점 연결
        for i, coord in enumerate(iris_coords):
            iris_canvas_x = pos_x + (coord[0] - img_width / 2) * scale_x
            iris_canvas_y = pos_y + (coord[1] - img_height / 2) * scale_y
            
            line_id = canvas.create_line(
                center_canvas_x, center_canvas_y,
                iris_canvas_x, iris_canvas_y,
                fill=connection_color,
                width=connection_width,
                #dash=(5, 3),  # 점선 스타일
                tags=("iris_connections", f"iris_connection_{iris_side}_{i}")
            )
            items_list.append(line_id)
        
        print(f"Drew {len(iris_coords)} connection lines for {iris_side}")
    
    def draw_iris_outline(self, canvas, iris_side, iris_coords, 
                         img_width, img_height, scale_x, scale_y, 
                         pos_x, pos_y, items_list):
        """
        눈동자 외곽선 그리기 (4개 점을 연결하는 사각형)
        
        Args:
            canvas: 캔버스 객체
            iris_side: 'left' 또는 'right'
            iris_coords: 눈동자 외곽점 좌표 리스트
            img_width: 이미지 너비
            img_height: 이미지 높이
            scale_x: X 스케일
            scale_y: Y 스케일
            pos_x: 캔버스 내 X 위치
            pos_y: 캔버스 내 Y 위치
            items_list: 캔버스 아이템 리스트
        """
        if len(iris_coords) < 4:
            return
        
        # 중심점 찾기 (가장 중앙에 있는 점)
        center_x_avg = sum(coord[0] for coord in iris_coords) / len(iris_coords)
        center_y_avg = sum(coord[1] for coord in iris_coords) / len(iris_coords)
        
        # 중심점에서 가장 가까운 점을 중심점으로 간주하고 제외
        def distance_from_center(coord):
            return math.sqrt((coord[0] - center_x_avg)**2 + (coord[1] - center_y_avg)**2)
        
        # 거리순으로 정렬하여 가장 가까운 점(중심점)을 찾음
        sorted_by_distance = sorted(iris_coords, key=distance_from_center)
        center_point = sorted_by_distance[0]  # 중심점
        
        # 중심점을 제외한 외곽선 점들
        outer_points = [coord for coord in iris_coords if coord != center_point]
        
        # 외곽점을 각도순으로 정렬
        def angle_from_point(coord):
            return -math.atan2(coord[1] - center_y_avg, coord[0] - center_x_avg)  # 시계 반대 방향
        
        sorted_outer_points = sorted(outer_points, key=angle_from_point)
        
        # 외곽선 4개 점을 연결하는 선 그리기
        canvas_points = []
        for coord in sorted_outer_points[:4]:  # 외곽선 4개 점만 사용
            rel_x = (coord[0] - img_width / 2) * scale_x
            rel_y = (coord[1] - img_height / 2) * scale_y
            canvas_pt = (pos_x + rel_x, pos_y + rel_y)
            canvas_points.extend(canvas_pt)
        
        # 색상 설정 (왼쪽: 붉은색 계열, 오른쪽: 청록색 계열)
        line_color = "#FF6B6B" if iris_side == 'left' else "#4ECDC4"  # 더 진한 색상
        
        # 외곽선 4개 점을 순서대로 연결하는 선들 그리기
        for i in range(len(canvas_points) // 2):
            start_idx = i * 2
            end_idx = ((i + 1) * 2) % len(canvas_points)
            
            line_id = canvas.create_line(
                canvas_points[start_idx], canvas_points[start_idx + 1],
                canvas_points[end_idx], canvas_points[end_idx + 1],
                fill=line_color,
                width=3,
                tags=("iris_connections", f"iris_outline_{iris_side}")
            )
            items_list.append(line_id)
