"""Editing pipeline mixin for FaceEditPanel."""
from dataclasses import dataclass
from typing import Any, Optional, Tuple


@dataclass
class EditingContext:
    """Lightweight container describing a single apply_editing run."""

    depth: int
    base_image: Any
    face_morphing: Any
    style_transfer: Any
    face_transform: Any
    image_cls: Any
    os_module: Any
    left_eye_size: float
    right_eye_size: float


class EditingPipelineMixin:
    """Encapsulates apply_editing workflow and state caching."""

    def apply_editing(self, depth: int = 1):
        """편집 적용 (영역 파라미터를 기본값으로 고정)"""
        
        print_debug("EditingPipeline", f"apply_editing: called.. {depth}")        
        if self.current_image is None:
            return

        self._ensure_editing_signature_state()
        state_signature_before = self._build_apply_editing_signature()
        last_signature = getattr(self, '_last_apply_editing_signature', None)
        if state_signature_before is not None and last_signature == state_signature_before:
            return

        try:
            context = self._prepare_editing_context(depth)
            face_morphing = context.face_morphing
            style_transfer = context.style_transfer
            face_transform = context.face_transform
            os_module = context.os_module
            image_cls = context.image_cls

            # 처리 순서: 정렬 → 특징 보정 → 스타일 전송 → 나이 변환
            base_image = context.base_image
            left_eye_size = context.left_eye_size
            right_eye_size = context.right_eye_size

            base_landmarks = self._ensure_landmark_sources(context)
            self._update_landmarks_for_editing(context, base_landmarks)

            result = self._apply_face_adjustments(context)
            result = self._apply_style_transfer_if_requested(context, result)
            result = self._apply_age_transform_if_requested(context, result)

            self.edited_image = result
            self._update_previews_and_labels()

        except Exception as e:
            print(f"[Editing] Editing failed: {e}")
            import traceback
            traceback.print_exc()
            self.edited_image = self.current_image.copy()
            self._update_previews_and_labels()
            right_eye_value = self.right_eye_size.get()
            self.right_eye_size_label.config(text=f"{int(right_eye_value * 100)}%")
            self._last_apply_editing_signature = None

        self._update_slider_labels()

        # 고급 모드가 체크되었고 기존에 수정된 랜드마크가 있으면 즉시 적용
        if self.current_image is not None:
            use_warping = getattr(self, 'use_landmark_warping', None)
            if use_warping is not None and hasattr(use_warping, 'get') and use_warping.get():
                # 고급 모드일 때도 슬라이더 값에 따라 custom_landmarks 업데이트
                if hasattr(self, 'update_polygons_only'):
                    self.update_polygons_only()

                if hasattr(self, 'custom_landmarks') and self.custom_landmarks is not None:
                    if hasattr(self, 'apply_polygon_drag_final'):
                        self.apply_polygon_drag_final(desc="EditingPipeline")
                        if hasattr(self, 'show_landmark_points') and self.show_landmark_points.get():
                            self.update_face_features_display()
                        self._cache_apply_editing_signature()
                        return

        # 이미지가 로드되어 있으면 편집 적용 및 미리보기 업데이트
        if self.current_image is not None:
            # 폴리곤 표시를 위해 custom_landmarks 업데이트 (apply_editing 전에)
            if hasattr(self, 'show_landmark_polygons') and self.show_landmark_polygons.get():
                if hasattr(self, 'update_polygons_only'):
                    self.update_polygons_only()

            # 편집 적용 전에 현재 위치를 명시적으로 저장
            if self.image_created_original is not None:
                try:
                    original_coords = self.canvas_original.coords(self.image_created_original)
                    if original_coords and len(original_coords) >= 2:
                        self.canvas_original_pos_x = original_coords[0]
                        self.canvas_original_pos_y = original_coords[1]
                except Exception as e:
                    print(f"[얼굴편집] 원본 위치 저장 실패: {e}")

            # 편집된 이미지 위치도 저장
            if self.canvas_original_pos_x is not None and self.canvas_original_pos_y is not None:
                self.canvas_edited_pos_x = self.canvas_original_pos_x
                self.canvas_edited_pos_y = self.canvas_original_pos_y
            elif self.image_created_edited is not None:
                try:
                    edited_coords = self.canvas_edited.coords(self.image_created_edited)
                    if edited_coords and len(edited_coords) >= 2:
                        self.canvas_edited_pos_x = edited_coords[0]
                        self.canvas_edited_pos_y = edited_coords[1]
                except Exception as e:
                    print(f"[얼굴편집] 편집 위치 저장 실패: {e}")

            self.apply_editing(depth + 1)
            # 고급 모드에서 폴리곤 표시가 활성화되어 있으면 눈/입술 영역 표시는 하지 않음 (폴리곤으로 대체)
            show_polygons = hasattr(self, 'show_landmark_polygons') and self.show_landmark_polygons.get()
            if not show_polygons:
                # 눈 영역 표시 업데이트
                if self.show_eye_region.get():
                    self.update_eye_region_display()
                # 입술 영역 표시 업데이트
                if hasattr(self, 'show_lip_region') and self.show_lip_region.get():
                    self.update_lip_region_display()
            else:
                # 폴리곤이 활성화되면 기존 타원형 영역 제거
                if hasattr(self, 'clear_eye_region_display'):
                    self.clear_eye_region_display()
                if hasattr(self, 'clear_lip_region_display'):
                    self.clear_lip_region_display()

            # 폴리곤 표시 업데이트 (custom_landmarks가 이미 update_polygons_only에서 업데이트되었으므로)
            if hasattr(self, 'show_landmark_polygons') and self.show_landmark_polygons.get():
                # custom_landmarks가 있으면 폴리곤만 다시 그리기
                if hasattr(self, 'custom_landmarks') and self.custom_landmarks is not None:
                    # 기존 폴리곤 제거
                    for item_id in list(self.landmark_polygon_items['original']):
                        try:
                            self.canvas_original.delete(item_id)
                        except Exception:  # pylint: disable=broad-except
                            pass
                    self.landmark_polygon_items['original'].clear()
                    self.polygon_point_map_original.clear()

                    # 폴리곤 다시 그리기
                    current_tab = getattr(self, 'current_morphing_tab', '눈')
                    if hasattr(self, '_draw_landmark_polygons'):
                        # custom_landmarks 가져오기 (LandmarkManager 사용)
                        custom = self.landmark_manager.get_custom_landmarks()

                        if custom is not None:
                            # Tesselation 모드 확인
                            is_tesselation_selected = (hasattr(self, 'show_tesselation') and self.show_tesselation.get())

                            # Tesselation 모드일 때 iris_centers 전달
                            iris_centers_for_drawing = None
                            face_landmarks_for_drawing = custom

                            if is_tesselation_selected:
                                # Tesselation 모드: iris_centers 사용
                                iris_centers_for_drawing = self.landmark_manager.get_custom_iris_centers()
                                if iris_centers_for_drawing is None and len(custom) == 470:
                                    # custom_landmarks에서 중앙 포인트 추출 (마지막 2개)
                                    iris_centers_for_drawing = custom[-2:]
                                    face_landmarks_for_drawing = custom[:-2]  # 468개

                            self._draw_landmark_polygons(
                                self.canvas_original,
                                self.current_image,
                                face_landmarks_for_drawing,  # 468개 또는 470개
                                self.canvas_original_pos_x,
                                self.canvas_original_pos_y,
                                self.landmark_polygon_items['original'],
                                "green",
                                current_tab,
                                iris_centers=iris_centers_for_drawing,  # Tesselation 모드일 때만 전달
                                force_use_custom=True  # custom_landmarks를 명시적으로 전달했으므로 강제 사용
                            )
                    # custom_landmarks가 없으면 전체 업데이트
                    self.update_face_features_display()

    # ------------------------------------------------------------------
    # Signature helpers
    # ------------------------------------------------------------------
    def _ensure_editing_signature_state(self):
        if not hasattr(self, '_last_apply_editing_signature'):
            self._last_apply_editing_signature = None

    def _cache_apply_editing_signature(self, signature: Optional[Tuple[Any, ...]] = None):
        if signature is None:
            signature = self._build_apply_editing_signature()
        self._last_apply_editing_signature = signature

    def _build_apply_editing_signature(self) -> Optional[Tuple[Any, ...]]:
        if self.current_image is None:
            return None

        base_image = self.aligned_image if getattr(self, 'aligned_image', None) is not None else self.current_image
        base_image_id = id(base_image)

        def safe_get(var_name: str, default: float = 0.0) -> float:
            var = getattr(self, var_name, None)
            if var is None:
                return round(default, 4)
            if hasattr(var, 'get'):
                try:
                    return round(float(var.get()), 4)
                except Exception:  # pylint: disable=broad-except
                    return round(default, 4)
            try:
                return round(float(var), 4)
            except Exception:  # pylint: disable=broad-except
                return round(default, 4)

        bool_get = lambda name: bool(getattr(getattr(self, name, None), 'get', lambda: getattr(self, name, False))()) if hasattr(getattr(self, name, None), 'get') else bool(getattr(self, name, False))

        slider_fields = (
            safe_get('left_eye_size', 1.0),
            safe_get('right_eye_size', 1.0),
            safe_get('left_eye_position_x'),
            safe_get('right_eye_position_x'),
            safe_get('left_eye_position_y'),
            safe_get('right_eye_position_y'),
            safe_get('nose_size', 1.0),
            safe_get('upper_lip_shape', 1.0),
            safe_get('lower_lip_shape', 1.0),
            safe_get('upper_lip_width', 1.0),
            safe_get('lower_lip_width', 1.0),
            safe_get('upper_lip_vertical_move'),
            safe_get('lower_lip_vertical_move'),
            safe_get('jaw_size'),
            safe_get('face_width', 1.0),
            safe_get('face_height', 1.0),
            safe_get('region_size_x', 1.0),
            safe_get('region_size_y', 1.0),
            safe_get('region_position_x'),
            safe_get('region_position_y'),
            safe_get('region_center_offset_x'),
            safe_get('region_center_offset_y'),
            safe_get('blend_ratio', 1.0),
        )

        bool_flags = (
            bool_get('eye_spacing') if hasattr(self, 'eye_spacing') else False,
            bool_get('use_individual_eye_region') if hasattr(self, 'use_individual_eye_region') else False,
            bool_get('use_landmark_warping') if hasattr(self, 'use_landmark_warping') else False,
        )

        style_path = getattr(self, 'style_image_path', None) or None
        age_value = safe_get('age_adjustment')
        color_strength = safe_get('color_strength')
        texture_strength = safe_get('texture_strength')

        custom_signature = None
        if hasattr(self, 'landmark_manager'):
            get_sig = getattr(self.landmark_manager, 'get_custom_landmarks_signature', None)
            if callable(get_sig):
                try:
                    custom_signature = get_sig()
                except Exception:  # pylint: disable=broad-except
                    custom_signature = None

        return (
            base_image_id,
            slider_fields,
            bool_flags,
            style_path,
            age_value,
            color_strength,
            texture_strength,
            custom_signature,
        )

    # ------------------------------------------------------------------
    # Context helpers
    # ------------------------------------------------------------------
    def _prepare_editing_context(self, depth: int) -> EditingContext:
        """Collects import dependencies and slider defaults for apply_editing."""

        import utils.face_morphing as face_morphing
        import utils.style_transfer as style_transfer
        import utils.face_transform as face_transform
        import os
        from PIL import Image

        base_image = self.aligned_image if getattr(self, 'aligned_image', None) is not None else self.current_image
        if base_image is None:
            raise RuntimeError("Base image is not available for editing")

        if self.use_individual_eye_region.get():
            left_eye_size = self.left_eye_size.get()
            right_eye_size = self.right_eye_size.get()
        else:
            left_eye_size = self.left_eye_size.get()
            right_eye_size = self.left_eye_size.get()

        from utils.logger import print_warning

        if left_eye_size is None or not (0.1 <= left_eye_size <= 5.0):
            print_warning("얼굴편집", f"왼쪽 눈 크기 값이 유효하지 않음: {left_eye_size}, 기본값 1.0으로 설정")
            left_eye_size = 1.0
        if right_eye_size is None or not (0.1 <= right_eye_size <= 5.0):
            print_warning("얼굴편집", f"오른쪽 눈 크기 값이 유효하지 않음: {right_eye_size}, 기본값 1.0으로 설정")
            right_eye_size = 1.0

        return EditingContext(
            depth=depth,
            base_image=base_image,
            face_morphing=face_morphing,
            style_transfer=style_transfer,
            face_transform=face_transform,
            image_cls=Image,
            os_module=os,
            left_eye_size=left_eye_size,
            right_eye_size=right_eye_size,
        )

    def _ensure_landmark_sources(self, context: EditingContext):
        """Ensure original/custom landmarks are available and return base landmarks."""

        import utils.face_landmarks as face_landmarks

        base_image = context.base_image
        base_landmarks = None

        if not self.landmark_manager.has_original_landmarks():
            if self.landmark_manager.get_face_landmarks() is None:
                detected, _ = face_landmarks.detect_face_landmarks(base_image)
                if detected is not None:
                    self.landmark_manager.set_face_landmarks(detected)
                    img_width, img_height = base_image.size
                    self.landmark_manager.set_original_landmarks(detected, img_width, img_height)
                    self.face_landmarks = self.landmark_manager.get_face_landmarks()
                    self.original_landmarks = self.landmark_manager.get_original_landmarks()
            base_landmarks = self.landmark_manager.get_face_landmarks()
        else:
            base_landmarks = self.landmark_manager.get_original_landmarks()

        if base_landmarks is None:
            base_landmarks = self.landmark_manager.get_face_landmarks()

        return base_landmarks

    def _update_landmarks_for_editing(self, context: EditingContext, base_landmarks):
        """Apply slider-driven landmark transforms based on current settings."""

        face_morphing = context.face_morphing
        left_eye_size = context.left_eye_size
        right_eye_size = context.right_eye_size

        if self.use_landmark_warping.get():
            if base_landmarks is not None:
                transformed = face_morphing.transform_points_for_eye_size(
                    base_landmarks,
                    eye_size_ratio=1.0,
                    left_eye_size_ratio=left_eye_size,
                    right_eye_size_ratio=right_eye_size,
                )
                transformed = face_morphing.transform_points_for_eye_position(
                    transformed,
                    left_eye_position_x=self.left_eye_position_x.get(),
                    right_eye_position_x=self.right_eye_position_x.get(),
                    left_eye_position_y=self.left_eye_position_y.get(),
                    right_eye_position_y=self.right_eye_position_y.get(),
                )
                transformed = face_morphing.transform_points_for_nose_size(
                    transformed,
                    nose_size_ratio=self.nose_size.get(),
                )
                transformed = face_morphing.transform_points_for_lip_shape(
                    transformed,
                    upper_lip_shape=self.upper_lip_shape.get(),
                    lower_lip_shape=self.lower_lip_shape.get(),
                )
                transformed = face_morphing.transform_points_for_lip_width(
                    transformed,
                    upper_lip_width=self.upper_lip_width.get(),
                    lower_lip_width=self.lower_lip_width.get(),
                )

                self.landmark_manager.set_transformed_landmarks(transformed)
                self.landmark_manager.set_custom_landmarks(transformed, reason="apply_editing use_landmark_warping")
                self.transformed_landmarks = self.landmark_manager.get_transformed_landmarks()

                self._ensure_iris_centers_from_original()
            else:
                self.landmark_manager.set_transformed_landmarks(None)
                self.landmark_manager.set_custom_landmarks(None, reason="apply_editing use_landmark_warping_false")
                self.transformed_landmarks = self.landmark_manager.get_transformed_landmarks()
        else:
            self.transformed_landmarks = None
            if base_landmarks is not None:
                transformed = face_morphing.transform_points_for_eye_size(
                    base_landmarks,
                    eye_size_ratio=1.0,
                    left_eye_size_ratio=left_eye_size,
                    right_eye_size_ratio=right_eye_size,
                )
                transformed = face_morphing.transform_points_for_eye_position(
                    transformed,
                    left_eye_position_x=self.left_eye_position_x.get(),
                    right_eye_position_x=self.right_eye_position_x.get(),
                    left_eye_position_y=self.left_eye_position_y.get(),
                    right_eye_position_y=self.right_eye_position_y.get(),
                )
                transformed = face_morphing.transform_points_for_nose_size(
                    transformed,
                    nose_size_ratio=self.nose_size.get(),
                )
                transformed = face_morphing.transform_points_for_lip_shape(
                    transformed,
                    upper_lip_shape=self.upper_lip_shape.get(),
                    lower_lip_shape=self.lower_lip_shape.get(),
                )
                transformed = face_morphing.transform_points_for_lip_width(
                    transformed,
                    upper_lip_width=self.upper_lip_width.get(),
                    lower_lip_width=self.lower_lip_width.get(),
                )

                self.custom_landmarks = transformed
                self._ensure_iris_centers_from_original()
            else:
                self.custom_landmarks = None

    def _ensure_iris_centers_from_original(self):
        """Ensure iris center cache exists based on original landmarks when needed."""

        if not (hasattr(self, '_get_iris_indices') and hasattr(self, '_calculate_iris_center')):
            return
        if self.current_image is None:
            return

        original = self.landmark_manager.get_original_landmarks() or getattr(self, 'original_landmarks', None)
        if original is None:
            return

        img_width, img_height = self.current_image.size
        left_iris_indices, right_iris_indices = self._get_iris_indices()

        left_center = self.landmark_manager.get_left_iris_center_coord()
        if left_center is None:
            left_center = self._calculate_iris_center(original, left_iris_indices, img_width, img_height)
        right_center = self.landmark_manager.get_right_iris_center_coord()
        if right_center is None:
            right_center = self._calculate_iris_center(original, right_iris_indices, img_width, img_height)

        if left_center is not None or right_center is not None:
            self.landmark_manager.set_iris_center_coords(left_center, right_center)
            self._left_iris_center_coord = self.landmark_manager.get_left_iris_center_coord()
            self._right_iris_center_coord = self.landmark_manager.get_right_iris_center_coord()

    # ------------------------------------------------------------------
    # Adjustment helpers
    # ------------------------------------------------------------------
    def _apply_face_adjustments(self, context: EditingContext):
        """Apply core face adjustments via face_morphing."""

        face_morphing = context.face_morphing
        base_image = context.base_image

        return face_morphing.apply_all_adjustments(
            base_image,
            eye_size=None,
            left_eye_size=context.left_eye_size,
            right_eye_size=context.right_eye_size,
            eye_spacing=self.eye_spacing.get(),
            left_eye_position_y=self.left_eye_position_y.get(),
            right_eye_position_y=self.right_eye_position_y.get(),
            left_eye_position_x=self.left_eye_position_x.get(),
            right_eye_position_x=self.right_eye_position_x.get(),
            clamping_enabled=self.iris_clamping_enabled.get(),
            margin_ratio=self.iris_clamping_margin_ratio.get(),
            eye_region_padding=None,
            eye_region_offset_x=None,
            eye_region_offset_y=None,
            left_eye_region_padding=None,
            right_eye_region_padding=None,
            left_eye_region_offset_x=None,
            left_eye_region_offset_y=None,
            right_eye_region_offset_x=None,
            right_eye_region_offset_y=None,
            nose_size=self.nose_size.get(),
            upper_lip_shape=self.upper_lip_shape.get(),
            lower_lip_shape=self.lower_lip_shape.get(),
            upper_lip_width=self.upper_lip_width.get(),
            lower_lip_width=self.lower_lip_width.get(),
            upper_lip_vertical_move=self.upper_lip_vertical_move.get(),
            lower_lip_vertical_move=self.lower_lip_vertical_move.get(),
            use_individual_lip_region=self.use_individual_lip_region.get(),
            upper_lip_region_padding_x=None,
            upper_lip_region_padding_y=None,
            lower_lip_region_padding_x=None,
            lower_lip_region_padding_y=None,
            upper_lip_region_offset_x=None,
            upper_lip_region_offset_y=None,
            lower_lip_region_offset_x=None,
            lower_lip_region_offset_y=None,
            use_landmark_warping=self.use_landmark_warping.get(),
            jaw_adjustment=self.jaw_size.get(),
            face_width=self.face_width.get(),
            face_height=self.face_height.get(),
        )

    def _apply_style_transfer_if_requested(self, context: EditingContext, result):
        """Apply style transfer based on current settings and return updated image."""

        if not (self.style_image_path and context.os_module.path.exists(self.style_image_path)):
            return result

        try:
            style_image = context.image_cls.open(self.style_image_path)
            color_strength = self.color_strength.get()
            texture_strength = self.texture_strength.get()

            if color_strength > 0.0 or texture_strength > 0.0:
                return context.style_transfer.transfer_style(
                    style_image,
                    result,
                    color_strength=color_strength,
                    texture_strength=texture_strength,
                )
        except Exception as exc:  # pylint: disable=broad-except
            print(f"[얼굴편집] 스타일 전송 실패: {exc}")

        return result

    def _apply_age_transform_if_requested(self, context: EditingContext, result):
        """Apply age transformation if slider threshold exceeded."""

        age_adjustment = self.age_adjustment.get()
        if abs(age_adjustment) >= 1.0:
            return context.face_transform.transform_age(result, age_adjustment=int(age_adjustment))
        return result

    # ------------------------------------------------------------------
    # UI / Overlay helpers
    # ------------------------------------------------------------------
    def _update_previews_and_labels(self):
        """Refresh preview canvas and landmark displays via unified entry point."""

        if hasattr(self, 'update_face_edit_display'):
            overlays_enabled = False
            if hasattr(self, '_is_overlay_display_enabled'):
                overlays_enabled = self._is_overlay_display_enabled()
            else:
                overlays_enabled = bool(
                    (hasattr(self, 'show_eye_region') and self.show_eye_region.get())
                    or (hasattr(self, 'show_lip_region') and self.show_lip_region.get())
                    or (hasattr(self, 'show_landmark_polygons') and self.show_landmark_polygons.get())
                )

            self.update_face_edit_display(
                image=True,
                landmarks=True,
                overlays=overlays_enabled,
                guide_lines=True,
                force_original=True,
            )
        else:
            self.show_edited_preview()
            if hasattr(self, 'show_landmark_points') and self.show_landmark_points.get():
                self.update_face_features_display()

    def _refresh_overlays_and_polygons(self):
        """Refresh region overlays or landmark polygons based on user settings."""

        show_polygons = hasattr(self, 'show_landmark_polygons') and self.show_landmark_polygons.get()
        if not show_polygons:
            if hasattr(self, 'show_eye_region') and self.show_eye_region.get():
                self.update_eye_region_display()
            if hasattr(self, 'show_lip_region') and self.show_lip_region.get():
                self.update_lip_region_display()
        else:
            if hasattr(self, 'clear_eye_region_display'):
                self.clear_eye_region_display()
            if hasattr(self, 'clear_lip_region_display'):
                self.clear_lip_region_display()

        if hasattr(self, 'show_landmark_polygons') and self.show_landmark_polygons.get():
            if hasattr(self, 'custom_landmarks') and self.custom_landmarks is not None:
                if hasattr(self, 'update_polygons_only'):
                    self.update_polygons_only()
                if hasattr(self, 'custom_landmarks') and self.custom_landmarks is not None:
                    if hasattr(self, 'landmark_polygon_items') and 'original' in self.landmark_polygon_items:
                        for item_id in list(self.landmark_polygon_items['original']):
                            try:
                                self.canvas_original.delete(item_id)
                            except Exception:  # pylint: disable=broad-except
                                pass
                        self.landmark_polygon_items['original'].clear()
                        if hasattr(self, 'polygon_point_map_original'):
                            self.polygon_point_map_original.clear()

                        current_tab = getattr(self, 'current_morphing_tab', '눈')
                        if hasattr(self, '_draw_landmark_polygons'):
                            custom = self.landmark_manager.get_custom_landmarks()
                            if custom is not None:
                                is_tesselation_selected = (
                                    hasattr(self, 'show_tesselation') and self.show_tesselation.get()
                                )
                                iris_centers_for_drawing = None
                                face_landmarks_for_drawing = custom
                                if is_tesselation_selected:
                                    iris_centers_for_drawing = self.landmark_manager.get_custom_iris_centers()
                                    if iris_centers_for_drawing is None and len(custom) == 470:
                                        iris_centers_for_drawing = custom[-2:]
                                        face_landmarks_for_drawing = custom[:-2]

                                self._draw_landmark_polygons(
                                    self.canvas_original,
                                    self.current_image,
                                    face_landmarks_for_drawing,
                                    self.canvas_original_pos_x,
                                    self.canvas_original_pos_y,
                                    self.landmark_polygon_items['original'],
                                    "green",
                                    current_tab,
                                    iris_centers=iris_centers_for_drawing,
                                    force_use_custom=True,
                                )
            else:
                self.update_face_features_display()

    def _update_slider_labels(self):
        """Update slider readouts after editing completes."""

        if hasattr(self, 'nose_size_label'):
            nose_value = self.nose_size.get()
            self.nose_size_label.config(text=f"{int(nose_value * 100)}%")

        if hasattr(self, 'upper_lip_shape_label'):
            upper_lip_shape_value = self.upper_lip_shape.get()
            self.upper_lip_shape_label.config(text=f"{int(upper_lip_shape_value * 100)}%")

        if hasattr(self, 'lower_lip_shape_label'):
            lower_lip_shape_value = self.lower_lip_shape.get()
            self.lower_lip_shape_label.config(text=f"{int(lower_lip_shape_value * 100)}%")

        if hasattr(self, 'upper_lip_width_label'):
            upper_lip_width_value = self.upper_lip_width.get()
            self.upper_lip_width_label.config(text=f"{int(upper_lip_width_value * 100)}%")

        if hasattr(self, 'lower_lip_width_label'):
            lower_lip_width_value = self.lower_lip_width.get()
            self.lower_lip_width_label.config(text=f"{int(lower_lip_width_value * 100)}%")

        if hasattr(self, 'upper_lip_vertical_move_label'):
            upper_lip_vertical_move_value = self.upper_lip_vertical_move.get()
            self.upper_lip_vertical_move_label.config(text=f"{int(upper_lip_vertical_move_value)}")

        if hasattr(self, 'lower_lip_vertical_move_label'):
            lower_lip_vertical_move_value = self.lower_lip_vertical_move.get()
            self.lower_lip_vertical_move_label.config(text=f"{int(lower_lip_vertical_move_value)}")

        if hasattr(self, 'jaw_size_label'):
            jaw_value = self.jaw_size.get()
            self.jaw_size_label.config(text=f"{int(jaw_value)}")

        if hasattr(self, 'face_width_label'):
            face_width_value = self.face_width.get()
            self.face_width_label.config(text=f"{int(face_width_value * 100)}%")

        if hasattr(self, 'face_height_label'):
            face_height_value = self.face_height.get()
            self.face_height_label.config(text=f"{int(face_height_value * 100)}%")

        if hasattr(self, 'left_eye_position_y_label'):
            left_eye_position_y_value = self.left_eye_position_y.get()
            self.left_eye_position_y_label.config(text=f"{int(left_eye_position_y_value)}")

        if hasattr(self, 'right_eye_position_y_label'):
            right_eye_position_y_value = self.right_eye_position_y.get()
            self.right_eye_position_y_label.config(text=f"{int(right_eye_position_y_value)}")

        if hasattr(self, 'left_eye_position_x_label'):
            left_eye_position_x_value = self.left_eye_position_x.get()
            self.left_eye_position_x_label.config(text=f"{int(left_eye_position_x_value)}")

        if hasattr(self, 'right_eye_position_x_label'):
            right_eye_position_x_value = self.right_eye_position_x.get()
            self.right_eye_position_x_label.config(text=f"{int(right_eye_position_x_value)}")
