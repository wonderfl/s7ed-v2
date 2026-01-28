"""Guide line scaling helper mixin for FaceEditPanel."""

from utils.face_morphing.polygon_morphing.transformations import (
    set_guide_scaling_enabled,
)


class GuideLineScalingMixin:
    """Provides guide-line scaling state synchronization."""

    def _apply_guide_scaling_state(self, enabled: bool):
        """지시선 스케일링 상태를 GuideLinesManager와 전역 플래그에 반영"""
        self._last_guide_scaling_state = enabled

        if hasattr(self, 'guide_lines_manager'):
            try:
                self.guide_lines_manager._force_guide_scaling = enabled
            except Exception:  # pragma: no cover - defensive
                pass

        try:
            set_guide_scaling_enabled(enabled)
        except Exception as exc:  # pragma: no cover - log only
            print(f"[디버그] 전역 지시선 스케일링 설정 실패: {exc}")
