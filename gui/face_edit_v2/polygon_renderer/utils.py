"""
폴리곤 유틸리티 함수
"""
import numpy as np

# scipy import 확인
try:
    from scipy.spatial import Delaunay
    _scipy_available = True
except ImportError:
    _scipy_available = False
    Delaunay = None


class UtilsMixin:
    """폴리곤 유틸리티 기능 Mixin"""
    
    def _draw_flipped_triangles(self, canvas, image, original_landmarks, transformed_landmarks,
                                pos_x, pos_y, items_list, img_width, img_height, scale_x, scale_y):
        """뒤집힌 삼각형을 감지하고 빨간색으로 표시"""
        # scipy import 확인
        try:
            from scipy.spatial import Delaunay
            scipy_available = True
        except ImportError:
            scipy_available = False
            Delaunay = None
        
        if not scipy_available or Delaunay is None:
            return
        
        try:
            # numpy 배열로 변환
            original_points_array = np.array(original_landmarks, dtype=np.float32)
            transformed_points_array = np.array(transformed_landmarks, dtype=np.float32)
            
            # 이미지 경계 포인트 추가
            margin = 10
            boundary_points = [
                (-margin, -margin),
                (img_width + margin, -margin),
                (img_width + margin, img_height + margin),
                (-margin, img_height + margin)
            ]
            
            all_original_points = list(original_landmarks) + boundary_points
            all_transformed_points = list(transformed_landmarks) + boundary_points
            
            original_points_array = np.array(all_original_points, dtype=np.float32)
            transformed_points_array = np.array(all_transformed_points, dtype=np.float32)
            
            # Delaunay Triangulation 생성
            tri = Delaunay(original_points_array)
            
            # 뒤집힌 삼각형 감지
            flipped_indices = []
            for simplex_idx, simplex in enumerate(tri.simplices):
                # 원본 삼각형의 3개 포인트
                pt1_orig = original_points_array[simplex[0]]
                pt2_orig = original_points_array[simplex[1]]
                pt3_orig = original_points_array[simplex[2]]
                
                # 변형된 삼각형의 3개 포인트
                pt1_trans = transformed_points_array[simplex[0]]
                pt2_trans = transformed_points_array[simplex[1]]
                pt3_trans = transformed_points_array[simplex[2]]
                
                # 외적 계산
                v1_orig = pt2_orig - pt1_orig
                v2_orig = pt3_orig - pt1_orig
                cross_product_orig = v1_orig[0] * v2_orig[1] - v1_orig[1] * v2_orig[0]
                
                v1_trans = pt2_trans - pt1_trans
                v2_trans = pt3_trans - pt1_trans
                cross_product_trans = v1_trans[0] * v2_trans[1] - v1_trans[1] * v2_trans[0]
                
                # 뒤집혔는지 확인 (외적의 부호가 바뀌면 뒤집힘)
                if cross_product_orig * cross_product_trans < 0:
                    flipped_indices.append(simplex_idx)
            
            # 뒤집힌 삼각형을 빨간색으로 표시
            if flipped_indices:
                for simplex_idx in flipped_indices:
                    simplex = tri.simplices[simplex_idx]
                    # 경계 포인트는 제외
                    boundary_start_idx = len(original_landmarks)
                    if (simplex[0] >= boundary_start_idx or 
                        simplex[1] >= boundary_start_idx or 
                        simplex[2] >= boundary_start_idx):
                        continue
                    
                    # 뒤집힌 삼각형 표시: 원본 이미지 위에 그리므로 원본 랜드마크 좌표 사용
                    # 변형된 랜드마크는 뒤집힌 삼각형 감지에만 사용하고, 표시는 원본 좌표 사용
                    pt1_orig = original_points_array[simplex[0]]
                    pt2_orig = original_points_array[simplex[1]]
                    pt3_orig = original_points_array[simplex[2]]
                    
                    # 캔버스 좌표로 변환 (원본 이미지 좌표 사용)
                    def img_to_canvas(img_x, img_y):
                        rel_x = (img_x - img_width / 2) * scale_x
                        rel_y = (img_y - img_height / 2) * scale_y
                        return (pos_x + rel_x, pos_y + rel_y)
                    
                    canvas_pt1 = img_to_canvas(pt1_orig[0], pt1_orig[1])
                    canvas_pt2 = img_to_canvas(pt2_orig[0], pt2_orig[1])
                    canvas_pt3 = img_to_canvas(pt3_orig[0], pt3_orig[1])
                    
                    # 빨간색 삼각형 그리기
                    triangle_id = canvas.create_polygon(
                        [canvas_pt1[0], canvas_pt1[1], 
                         canvas_pt2[0], canvas_pt2[1],
                         canvas_pt3[0], canvas_pt3[1]],
                        fill="",  # 채우지 않음
                        outline="red",  # 빨간색
                        width=2,
                        tags=("flipped_triangle", "landmarks_polygon")
                    )
                    items_list.append(triangle_id)
                    
                    # 폴리곤 아이템 저장
                    canvas_type = 'original' if canvas == self.canvas_original else 'edited'
                    self.landmark_polygon_items[canvas_type].append(triangle_id)
        except Exception as e:
            import traceback
            traceback.print_exc()
