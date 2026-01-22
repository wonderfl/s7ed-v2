import unittest
import numpy as np
from PIL import Image
from unittest.mock import patch

from utils.face_morphing.polygon_morphing.core import _validate_and_prepare_inputs, _prepare_iris_centers, _create_delaunay_triangulation, _check_and_fix_flipped_triangles, _calculate_landmark_bounding_box, _apply_pixel_transformation, _scale_image, _map_pixels, _perform_interpolation, _fill_empty_spaces, morph_face_by_polygons

class TestFaceMorphingCore(unittest.TestCase):

    def setUp(self):
        # Mock external dependencies if necessary
        pass

    def test_validate_and_prepare_inputs_valid(self):
        # Given
        dummy_image = Image.new('RGB', (100, 100), color = 'red')
        original_landmarks = [(10, 10), (20, 20)]
        transformed_landmarks = [(15, 15), (25, 25)]

        # When
        with patch('utils.face_morphing.polygon_morphing.core._cv2_available', True),
             patch('utils.face_morphing.polygon_morphing.core._scipy_available', True):
            img_array, img_width, img_height = _validate_and_prepare_inputs(dummy_image, original_landmarks, transformed_landmarks)

        # Then
        self.assertIsInstance(img_array, np.ndarray)
        self.assertEqual(img_width, 100)
        self.assertEqual(img_height, 100)

    def test_validate_and_prepare_inputs_invalid_image_type(self):
        # Given
        invalid_image = "not an image"
        original_landmarks = [(10, 10)]
        transformed_landmarks = [(20, 20)]

        # When / Then
        with patch('utils.face_morphing.polygon_morphing.core._cv2_available', True),
             patch('utils.face_morphing.polygon_morphing.core._scipy_available', True):
            with self.assertRaises(ValueError) as cm:
                _validate_and_prepare_inputs(invalid_image, original_landmarks, transformed_landmarks)
            self.assertIn("입력된 이미지가 유효하지 않습니다.", str(cm.exception))

    def test_validate_and_prepare_inputs_missing_landmarks(self):
        # Given
        dummy_image = Image.new('RGB', (100, 100), color = 'red')
        original_landmarks = None
        transformed_landmarks = [(20, 20)]

        # When / Then
        with patch('utils.face_morphing.polygon_morphing.core._cv2_available', True),
             patch('utils.face_morphing.polygon_morphing.core._scipy_available', True):
            with self.assertRaises(ValueError) as cm:
                _validate_and_prepare_inputs(dummy_image, original_landmarks, transformed_landmarks)
            self.assertIn("랜드마크 목록이 누락되었습니다.", str(cm.exception))

    def test_validate_and_prepare_inputs_mismatched_landmark_count(self):
        # Given
        dummy_image = Image.new('RGB', (100, 100), color = 'red')
        original_landmarks = [(10, 10), (20, 20)]
        transformed_landmarks = [(15, 15)]

        # When / Then
        with patch('utils.face_morphing.polygon_morphing.core._cv2_available', True),
             patch('utils.face_morphing.polygon_morphing.core._scipy_available', True):
            with self.assertRaises(ValueError) as cm:
                _validate_and_prepare_inputs(dummy_image, original_landmarks, transformed_landmarks)
            self.assertIn("랜덤크 수가 다릅니다.", str(cm.exception))

    def test_validate_and_prepare_inputs_opencv_not_available(self):
        # Given
        dummy_image = Image.new('RGB', (100, 100), color = 'red')
        original_landmarks = [(10, 10), (20, 20)]
        transformed_landmarks = [(15, 15), (25, 25)]

        # When
        with patch('utils.face_morphing.polygon_morphing.core._cv2_available', False),
             patch('utils.face_morphing.polygon_morphing.core._scipy_available', True):
            result = _validate_and_prepare_inputs(dummy_image, original_landmarks, transformed_landmarks)

        # Then
        self.assertIsNone(result)

    def test_validate_and_prepare_inputs_scipy_not_available(self):
        # Given
        dummy_image = Image.new('RGB', (100, 100), color = 'red')
        original_landmarks = [(10, 10), (20, 20)]
        transformed_landmarks = [(15, 15), (25, 25)]

        # When
        with patch('utils.face_morphing.polygon_morphing.core._cv2_available', True),
             patch('utils.face_morphing.polygon_morphing.core._scipy_available', False),
             patch('builtins.print') as mock_print:
            result = _validate_and_prepare_inputs(dummy_image, original_landmarks, transformed_landmarks)
        
        # Then
        self.assertIsNone(result)
        mock_print.assert_called_with("[얼굴모핑] scipy가 설치되지 않았습니다. Delaunay Triangulation을 사용하려면 'pip install scipy'를 실행하세요.")

    # Test cases for _prepare_iris_centers
    @patch('utils.face_morphing.polygon_morphing.core.LEFT_EYE_INDICES', [474, 475, 476, 477])
    @patch('utils.face_morphing.polygon_morphing.core.RIGHT_EYE_INDICES', [469, 470, 471, 472])
    @patch('utils.face_morphing.polygon_morphing.core.print_info')
    def test_prepare_iris_centers_with_coords(self, mock_print_info):
        # Given
        original_landmarks = [(i, i) for i in range(500)]
        transformed_landmarks = [(i + 5, i + 5) for i in range(500)]
        left_iris_center_coord = (100, 100)
        right_iris_center_coord = (200, 100)
        left_iris_center_orig = (95, 95)
        right_iris_center_orig = (195, 95)
        img_width, img_height = 500, 500

        # When
        original_landmarks_no_iris, transformed_landmarks_no_iris,\
        original_points_array, transformed_points_array, iris_indices = \
            _prepare_iris_centers(original_landmarks, transformed_landmarks,
                                  left_iris_center_coord, right_iris_center_coord,
                                  left_iris_center_orig, right_iris_center_orig,
                                  img_width, img_height)

        # Then
        self.assertIn(left_iris_center_orig, original_landmarks_no_iris)
        self.assertIn(right_iris_center_orig, original_landmarks_no_iris)
        self.assertIn(left_iris_center_coord, transformed_landmarks_no_iris)
        self.assertIn(right_iris_center_coord, transformed_landmarks_no_iris)
        self.assertEqual(len(iris_indices), 10)  # 8 contour + 2 center
        self.assertEqual(original_points_array.shape[0], len(original_landmarks) - 10 + 2 + 4) # orig - iris + new iris + boundary
        self.assertEqual(transformed_points_array.shape[0], len(transformed_landmarks) - 10 + 2 + 4)

    @patch('utils.face_morphing.polygon_morphing.core.LEFT_EYE_INDICES', [474, 475, 476, 477])
    @patch('utils.face_morphing.polygon_morphing.core.RIGHT_EYE_INDICES', [469, 470, 471, 472])
    @patch('utils.face_morphing.polygon_morphing.core.print_info')
    def test_prepare_iris_centers_calculate_centers(self, mock_print_info):
        # Given
        original_landmarks = [(i, i) for i in range(500)]
        transformed_landmarks = [(i + 5, i + 5) for i in range(500)]
        img_width, img_height = 500, 500

        # When
        original_landmarks_no_iris, transformed_landmarks_no_iris,\
        original_points_array, transformed_points_array, iris_indices = \
            _prepare_iris_centers(original_landmarks, transformed_landmarks,
                                  None, None, None, None,
                                  img_width, img_height)

        # Then
        # Check if new iris centers are added and are roughly the average of contour points
        # More robust assertion would involve calculating expected centers
        self.assertEqual(len(iris_indices), 10)
        self.assertEqual(original_points_array.shape[0], len(original_landmarks) - 10 + 2 + 4) # orig - iris + new iris + boundary
        self.assertEqual(transformed_points_array.shape[0], len(transformed_landmarks) - 10 + 2 + 4)

    # Test cases for _create_delaunay_triangulation
    def test_create_delaunay_triangulation(self):
        # Given
        points = np.array([[0, 0], [1, 0], [0, 1], [1, 1]], dtype=np.float32)

        # When
        with patch('utils.face_morphing.polygon_morphing.core._delaunay_cache', {}),
             patch('utils.face_morphing.polygon_morphing.core._delaunay_cache_max_size', 1):
            tri = _create_delaunay_triangulation(points)

        # Then
        self.assertIsInstance(tri, Delaunay)
        self.assertEqual(len(tri.simplices), 2)  # For a square, typically 2 triangles

    def test_create_delaunay_triangulation_cache(self):
        # Given
        points = np.array([[0, 0], [1, 0], [0, 1], [1, 1]], dtype=np.float32)
        # When
        with patch('utils.face_morphing.polygon_morphing.core._delaunay_cache', {}),
             patch('utils.face_morphing.polygon_morphing.core._delaunay_cache_max_size', 1):
            tri1 = _create_delaunay_triangulation(points)
            tri2 = _create_delaunay_triangulation(points) # Should hit cache

        # Then
        self.assertIs(tri1, tri2)
        self.assertEqual(len(_delaunay_cache), 1)

    def test_create_delaunay_triangulation_cache_eviction(self):
        # Given
        points1 = np.array([[0, 0], [1, 0], [0, 1], [1, 1]], dtype=np.float32)
        points2 = np.array([[10, 10], [11, 10], [10, 11], [11, 11]], dtype=np.float32)

        # When
        with patch('utils.face_morphing.polygon_morphing.core._delaunay_cache', {}),
             patch('utils.face_morphing.polygon_morphing.core._delaunay_cache_max_size', 1):
            tri1 = _create_delaunay_triangulation(points1)
            tri2 = _create_delaunay_triangulation(points2) # Should evict tri1 from cache
        
        # Then
        self.assertIsInstance(tri1, Delaunay)
        self.assertIsInstance(tri2, Delaunay)
        self.assertIsNot(tri1, tri2) # Different Delaunay objects
        self.assertEqual(len(_delaunay_cache), 1) # Only points2 should be in cache
        self.assertNotIn(hash(tuple(map(tuple, points1))), _delaunay_cache)
        self.assertIn(hash(tuple(map(tuple, points2))), _delaunay_cache)

    # Test cases for _check_and_fix_flipped_triangles
    @patch('utils.face_morphing.polygon_morphing.core.LEFT_EYE_INDICES', [1, 2])
    @patch('utils.face_morphing.polygon_morphing.core.RIGHT_EYE_INDICES', [3, 4])
    @patch('utils.face_morphing.polygon_morphing.core._check_triangles_flipped')
    @patch('builtins.print')
    def test_check_and_fix_flipped_triangles_no_flipped(self, mock_print, mock_check_triangles_flipped):
        # Given
        original_points = np.array([[0,0],[10,0],[0,10],[10,10],[5,5]], dtype=np.float32)
        transformed_points = original_points.copy()
        tri = Delaunay(original_points)
        original_landmarks_no_iris = [(0,0),(10,0),(0,10),(10,10)] # Exclude iris and boundary points

        mock_check_triangles_flipped.return_value = (0, [], [], []) # No flipped triangles

        # When
        result_transformed_points = _check_and_fix_flipped_triangles(original_points, transformed_points, tri, original_landmarks_no_iris)

        # Then
        np.testing.assert_array_equal(result_transformed_points, transformed_points)
        mock_print.assert_not_called()

    @patch('utils.face_morphing.polygon_morphing.core.LEFT_EYE_INDICES', [])
    @patch('utils.face_morphing.polygon_morphing.core.RIGHT_EYE_INDICES', [])
    @patch('utils.face_morphing.polygon_morphing.core._check_triangles_flipped')
    @patch('builtins.print')
    def test_check_and_fix_flipped_triangles_with_flipped(self, mock_print, mock_check_triangles_flipped):
        # Given
        original_points = np.array([[0,0],[10,0],[0,10],[10,10],[5,5]], dtype=np.float32)
        # Simulate a flipped point for index 4
        transformed_points = np.array([[0,0],[10,0],[0,10],[10,10],[100,100]], dtype=np.float32)
        tri = Delaunay(original_points)
        original_landmarks_no_iris = [(0,0),(10,0),(0,10),(10,10)]

        # Mock _check_triangles_flipped to report a flipped triangle involving index 4
        mock_check_triangles_flipped.return_value = (1, [0], [4], []) # 1 flipped, simplex 0, point 4 is problematic

        # When
        result_transformed_points = _check_and_fix_flipped_triangles(original_points, transformed_points, tri, original_landmarks_no_iris)

        # Then
        # The problematic point (index 4) should be restored to its original position
        np.testing.assert_array_equal(result_transformed_points[4], original_points[4])
        mock_print.assert_any_call(self.assertRegex("[얼굴모핑] 경고: 뒤집힌 삼각형", ""))

    # Test cases for _calculate_landmark_bounding_box
    def test_calculate_landmark_bounding_box_valid_landmarks(self):
        # Given
        landmarks = [(10, 10), (20, 50), (30, 20)]
        img_width, img_height = 100, 100
        padding_ratio = 0.1

        # When
        min_x, min_y, max_x, max_y = _calculate_landmark_bounding_box(landmarks, img_width, img_height, padding_ratio)

        # Then (expected bounding box with padding)
        self.assertEqual(min_x, 8) # 10 - (20 * 0.1)
        self.assertEqual(min_y, 7) # 10 - (40 * 0.1)
        self.assertEqual(max_x, 32) # 30 + (20 * 0.1)
        self.assertEqual(max_y, 53) # 50 + (40 * 0.1)

    def test_calculate_landmark_bounding_box_empty_landmarks(self):
        # Given
        landmarks = []
        img_width, img_height = 100, 100
        padding_ratio = 0.1

        # When
        result = _calculate_landmark_bounding_box(landmarks, img_width, img_height, padding_ratio)

        # Then
        self.assertIsNone(result)

    def test_calculate_landmark_bounding_box_with_excluded_indices(self):
        # Given
        landmarks = [(0, 0), (10, 10), (20, 20), (30, 30)]
        img_width, img_height = 100, 100
        padding_ratio = 0.0
        exclude_indices = {0, 3}

        # When
        min_x, min_y, max_x, max_y = _calculate_landmark_bounding_box(landmarks, img_width, img_height, padding_ratio, exclude_indices)

        # Then (bounding box only for (10,10) and (20,20) with no padding)
        self.assertEqual(min_x, 10)
        self.assertEqual(min_y, 10)
        self.assertEqual(max_x, 20)
        self.assertEqual(max_y, 20)

    def test_calculate_landmark_bounding_box_out_of_bounds_landmarks(self):
        # Given
        landmarks = [(-10, -10), (110, 110)]
        img_width, img_height = 100, 100
        padding_ratio = 0.0

        # When
        min_x, min_y, max_x, max_y = _calculate_landmark_bounding_box(landmarks, img_width, img_height, padding_ratio)

        # Then (should be clipped to image bounds)
        self.assertEqual(min_x, 0)
        self.assertEqual(min_y, 0)
        self.assertEqual(max_x, 100)
        self.assertEqual(max_y, 100)

    # Test cases for _scale_image
    def test_scale_image_upscale(self):
        # Given
        original_image = np.zeros((50, 50, 3), dtype=np.uint8)
        scale_factor = 2.0
        img_width, img_height = 50, 50

        # When
        with patch('utils.face_morphing.polygon_morphing.core.cv2.resize') as mock_resize:
            mock_resize.return_value = np.zeros((100, 100, 3), dtype=np.uint8)
            working_img, working_width, working_height = _scale_image(original_image, scale_factor, img_width, img_height)

        # Then
        self.assertEqual(working_width, 100)
        self.assertEqual(working_height, 100)
        self.assertEqual(working_img.shape, (100, 100, 3))
        mock_resize.assert_called_once_with(original_image, (100, 100), interpolation=cv2.INTER_LINEAR)

    def test_scale_image_downscale(self):
        # Given
        original_image = np.zeros((100, 100, 3), dtype=np.uint8)
        scale_factor = 0.5
        img_width, img_height = 100, 100

        # When
        with patch('utils.face_morphing.polygon_morphing.core.cv2.resize') as mock_resize:
            mock_resize.return_value = np.zeros((50, 50, 3), dtype=np.uint8)
            working_img, working_width, working_height = _scale_image(original_image, scale_factor, img_width, img_height)

        # Then
        self.assertEqual(working_width, 50)
        self.assertEqual(working_height, 50)
        self.assertEqual(working_img.shape, (50, 50, 3))
        mock_resize.assert_called_once_with(original_image, (50, 50), interpolation=cv2.INTER_LINEAR)

    def test_scale_image_no_scale(self):
        # Given
        original_image = np.zeros((100, 100, 3), dtype=np.uint8)
        scale_factor = 1.0
        img_width, img_height = 100, 100

        # When
        with patch('utils.face_morphing.polygon_morphing.core.cv2.resize') as mock_resize:
            working_img, working_width, working_height = _scale_image(original_image, scale_factor, img_width, img_height)

        # Then
        self.assertEqual(working_width, 100)
        self.assertEqual(working_height, 100)
        self.assertIs(working_img, original_image) # Should return the same image if no scaling
        mock_resize.assert_not_called()

    @patch('utils.face_morphing.polygon_morphing.core._cv2_cuda_available', True)
    @patch('utils.face_morphing.polygon_morphing.core.cv2.cuda.GpuMat')
    @patch('utils.face_morphing.polygon_morphing.core.cv2.cuda.resize')
    def test_scale_image_cuda_available(self, mock_cuda_resize, mock_gpu_mat):
        # Given
        original_image = np.zeros((100, 100, 3), dtype=np.uint8)
        scale_factor = 0.5
        img_width, img_height = 100, 100
        mock_gpu_instance = mock_gpu_mat.return_value
        mock_cuda_resize.return_value.download.return_value = np.zeros((50, 50, 3), dtype=np.uint8)

        # When
        _scale_image(original_image, scale_factor, img_width, img_height)

        # Then
        mock_gpu_instance.upload.assert_called_once()
        mock_cuda_resize.assert_called_once_with(mock_gpu_instance, (50, 50), interpolation=cv2.INTER_LINEAR)

    @patch('utils.face_morphing.polygon_morphing.core._cv2_cuda_available', True)
    @patch('utils.face_morphing.polygon_morphing.core.cv2.cuda.GpuMat', side_effect=Exception("CUDA error"))
    @patch('utils.face_morphing.polygon_morphing.core.cv2.resize')
    def test_scale_image_cuda_fallback(self, mock_cpu_resize, mock_gpu_mat):
        # Given
        original_image = np.zeros((100, 100, 3), dtype=np.uint8)
        scale_factor = 0.5
        img_width, img_height = 100, 100
        mock_cpu_resize.return_value = np.zeros((50, 50, 3), dtype=np.uint8)

        # When
        _scale_image(original_image, scale_factor, img_width, img_height)

        # Then
        mock_cpu_resize.assert_called_once_with(original_image, (50, 50), interpolation=cv2.INTER_LINEAR)

    # Test cases for _map_pixels (simplified, as it calls _perform_interpolation)
    @patch('utils.face_morphing.polygon_morphing.core._perform_interpolation')
    @patch('utils.face_morphing.polygon_morphing.core.Delaunay')
    def test_map_pixels_basic(self, MockDelaunay, mock_perform_interpolation):
        # Given
        working_img = np.zeros((100, 100, 3), dtype=np.uint8)
        original_points_array = np.array([[0,0],[99,0],[0,99]], dtype=np.float32)
        transformed_points_array = np.array([[0,0],[99,0],[0,99]], dtype=np.float32)
        # Mock a simple Delaunay triangulation
        mock_tri = MockDelaunay.return_value
        mock_tri.simplices = np.array([[0,1,2]])
        mock_tri.find_simplex.return_value = np.zeros(100*100, dtype=np.int32)

        valid_simplex_indices = np.array([0])
        simplex_indices_orig = np.zeros(100*100, dtype=np.int32)
        pixel_coords_orig_global = np.array([[x,y] for y in range(100) for x in range(100)])
        bbox_width, min_x, min_y = 100, 0, 0
        working_width, working_height = 100, 100
        result = np.zeros_like(working_img, dtype=np.float32)
        result_count = np.zeros((working_height, working_width), dtype=np.float32)
        transformed_mask = np.zeros((working_height, working_width), dtype=np.bool_)

        mock_perform_interpolation.return_value = (result, result_count, transformed_mask, 10000, 0)

        # When
        _map_pixels(working_img, original_points_array, transformed_points_array, mock_tri,
                    valid_simplex_indices, simplex_indices_orig, pixel_coords_orig_global,
                    bbox_width, min_x, min_y, working_width, working_height,
                    result, result_count, transformed_mask)

        # Then
        mock_perform_interpolation.assert_called_once() # Verify that interpolation was called

    # Test cases for _perform_interpolation
    @patch('numpy.add.at')
    def test_perform_interpolation_valid_coords(self, mock_add_at):
        # Given
        working_img = np.zeros((10, 10, 3), dtype=np.uint8)
        M_forward = np.array([[1, 0, 0], [0, 1, 0]], dtype=np.float32)
        pixel_mask = np.array([True, True])
        pixel_coords_orig_global = np.array([[0,0],[1,1]], dtype=np.float32)
        bbox_width, min_x, min_y = 10, 0, 0
        working_width, working_height = 10, 10
        result = np.zeros_like(working_img, dtype=np.float32)
        result_count = np.zeros((working_height, working_width), dtype=np.float32)
        transformed_mask = np.zeros((working_height, working_width), dtype=np.bool_)

        # When
        result, result_count, transformed_mask, processed_pixels, out_of_bounds_pixels = _perform_interpolation(
            working_img, M_forward, pixel_mask, pixel_coords_orig_global, bbox_width, min_x, min_y,
            working_width, working_height, result, result_count, transformed_mask
        )

        # Then
        self.assertEqual(processed_pixels, 2)
        self.assertEqual(out_of_bounds_pixels, 0)
        self.assertEqual(mock_add_at.call_count, 8) # 4 calls for result, 4 for result_count

    @patch('numpy.add.at')
    def test_perform_interpolation_out_of_bounds_coords(self, mock_add_at):
        # Given
        working_img = np.zeros((10, 10, 3), dtype=np.uint8)
        M_forward = np.array([[1, 0, 100], [0, 1, 100]], dtype=np.float32) # Transforms pixels way out of bounds
        pixel_mask = np.array([True])
        pixel_coords_orig_global = np.array([[0,0]], dtype=np.float32)
        bbox_width, min_x, min_y = 10, 0, 0
        working_width, working_height = 10, 10
        result = np.zeros_like(working_img, dtype=np.float32)
        result_count = np.zeros((working_height, working_width), dtype=np.float32)
        transformed_mask = np.zeros((working_height, working_width), dtype=np.bool_)

        # When
        result, result_count, transformed_mask, processed_pixels, out_of_bounds_pixels = _perform_interpolation(
            working_img, M_forward, pixel_mask, pixel_coords_orig_global, bbox_width, min_x, min_y,
            working_width, working_height, result, result_count, transformed_mask
        )

        # Then
        self.assertEqual(processed_pixels, 1)
        self.assertEqual(out_of_bounds_pixels, 1)
        self.assertEqual(mock_add_at.call_count, 2) # 1 call for result, 1 for result_count due to out of bounds

    # Test cases for _fill_empty_spaces
    @patch('utils.face_morphing.polygon_morphing.core._cv2_available', True)
    @patch('cv2.inpaint')
    def test_fill_empty_spaces_with_inpainting(self, mock_inpaint):
        # Given
        result_img = np.zeros((10, 10, 3), dtype=np.uint8)
        result_count = np.zeros((10, 10), dtype=np.float32)
        result_count[0,0] = 1.0 # One non-empty pixel
        working_img = np.ones((10, 10, 3), dtype=np.uint8) * 255
        working_height, working_width = 10, 10

        mock_inpaint.return_value = np.zeros_like(result_img)

        # When
        _fill_empty_spaces(result_img, result_count, working_img, working_height, working_width)

        # Then
        mock_inpaint.assert_called_once()

    @patch('utils.face_morphing.polygon_morphing.core._cv2_available', False)
    def test_fill_empty_spaces_no_opencv(self):
        # Given
        result_img = np.zeros((10, 10, 3), dtype=np.uint8)
        result_count = np.zeros((10, 10), dtype=np.float32)
        working_img = np.ones((10, 10, 3), dtype=np.uint8) * 255
        working_height, working_width = 10, 10

        # When
        filled_result = _fill_empty_spaces(result_img, result_count, working_img, working_height, working_width)

        # Then
        # Should fill empty spaces with working_img content
        # Assert that a specific empty pixel is now filled with the working_img value
        np.testing.assert_array_equal(filled_result[0, 0], working_img[0, 0])

    @patch('utils.face_morphing.polygon_morphing.core._cv2_available', True)
    @patch('cv2.inpaint')
    def test_fill_empty_spaces_high_empty_ratio(self, mock_inpaint):
        # Given
        result_img = np.zeros((10, 10, 3), dtype=np.uint8)
        result_count = np.zeros((10, 10), dtype=np.float32) # Almost all empty
        result_count[0,0] = 1.0 # Only one pixel is not empty
        working_img = np.ones((10, 10, 3), dtype=np.uint8) * 255
        working_height, working_width = 10, 10

        # When
        filled_result = _fill_empty_spaces(result_img, result_count, working_img, working_height, working_width)

        # Then
        mock_inpaint.assert_not_called() # Inpainting should not be called due to high empty ratio
        np.testing.assert_array_equal(filled_result[1, 1], working_img[1, 1]) # Check if an empty pixel is filled by working_img

    # Test cases for _apply_pixel_transformation
    @patch('utils.face_morphing.polygon_morphing.core._map_pixels')
    def test_apply_pixel_transformation_calls_map_pixels(self, mock_map_pixels):
        # Given
        working_img = np.zeros((100, 100, 3), dtype=np.uint8)
        original_points_array = np.array([[0,0],[99,0],[0,99]], dtype=np.float32)
        transformed_points_array = np.array([[0,0],[99,0],[0,99]], dtype=np.float32)
        tri = Delaunay(original_points_array)
        min_x, min_y, max_x, max_y = 0, 0, 100, 100
        working_width, working_height = 100, 100

        # Mock return values for _map_pixels
        mock_map_pixels.return_value = (np.zeros_like(working_img), np.zeros((working_height, working_width)), np.zeros((working_height, working_width), dtype=np.bool_))

        # When
        _apply_pixel_transformation(working_img, original_points_array, transformed_points_array, tri, 
                                   min_x, min_y, max_x, max_y, working_width, working_height)

        # Then
        mock_map_pixels.assert_called_once()

    # Integration test for morph_face_by_polygons
    @patch('utils.face_morphing.polygon_morphing.core._validate_and_prepare_inputs')
    @patch('utils.face_morphing.polygon_morphing.core._prepare_iris_centers')
    @patch('utils.face_morphing.polygon_morphing.core._create_delaunay_triangulation')
    @patch('utils.face_morphing.polygon_morphing.core._check_and_fix_flipped_triangles')
    @patch('utils.face_morphing.polygon_morphing.core._calculate_landmark_bounding_box')
    @patch('utils.face_morphing.polygon_morphing.core._scale_image')
    @patch('utils.face_morphing.polygon_morphing.core._apply_pixel_transformation')
    @patch('utils.face_morphing.polygon_morphing.core._fill_empty_spaces')
    @patch('builtins.print')
    @patch('PIL.Image.fromarray')
    def test_morph_face_by_polygons_integration(self, mock_fromarray, mock_print, 
                                                mock_fill_empty_spaces, mock_apply_pixel_transformation, 
                                                mock_scale_image, mock_calculate_landmark_bounding_box, 
                                                mock_check_and_fix_flipped_triangles, mock_create_delaunay_triangulation,
                                                mock_prepare_iris_centers, mock_validate_and_prepare_inputs):
        # Given
        dummy_image = Image.new('RGB', (100, 100), color='red')
        original_landmarks = [(0, 0), (99, 0), (0, 99)]
        transformed_landmarks = [(0, 0), (99, 0), (0, 99)]
        img_array = np.array(dummy_image)
        img_width, img_height = 100, 100

        # Mock return values for helper functions
        mock_validate_and_prepare_inputs.return_value = (img_array, img_width, img_height)
        mock_prepare_iris_centers.return_value = (original_landmarks, transformed_landmarks, np.array(original_landmarks), np.array(transformed_landmarks), set())
        mock_create_delaunay_triangulation.return_value = Delaunay(np.array(original_landmarks))
        mock_check_and_fix_flipped_triangles.return_value = np.array(transformed_landmarks)
        mock_calculate_landmark_bounding_box.side_effect = [(0, 0, 100, 100), (0, 0, 100, 100)] # orig and trans bbox
        mock_scale_image.return_value = (img_array, img_width, img_height)
        mock_apply_pixel_transformation.return_value = (img_array.astype(np.float32), np.ones((img_height, img_width)), np.zeros((img_height, img_width), dtype=np.bool_))
        mock_fill_empty_spaces.return_value = img_array
        mock_fromarray.return_value = dummy_image

        # When
        result_image = morph_face_by_polygons(dummy_image, original_landmarks, transformed_landmarks)

        # Then
        self.assertIs(result_image, dummy_image)
        mock_validate_and_prepare_inputs.assert_called_once()
        mock_prepare_iris_centers.assert_called_once()
        mock_create_delaunay_triangulation.assert_called_once()
        mock_check_and_fix_flipped_triangles.assert_called_once()
        mock_calculate_landmark_bounding_box.assert_called_once()
        mock_scale_image.assert_called_once()
        mock_apply_pixel_transformation.assert_called_once()
        mock_fill_empty_spaces.assert_called_once()
        mock_fromarray.assert_called_once()

if __name__ == '__main__':
    unittest.main()
