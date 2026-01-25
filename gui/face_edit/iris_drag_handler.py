"""
눈동자 드래그 이벤트 핸들러
All 탭과 눈동자 탭에서 공통으로 사용하는 이벤트 처리 로직
"""

class IrisDragHandler:
    """눈동자 드래그 이벤트를 통합적으로 처리하는 핸들러"""
    
    def __init__(self, parent):
        """
        초기화
        
        Args:
            parent: 부모 클래스 인스턴스 (FaceEditPanel 등)
        """
        self.parent = parent
    
    def bind_iris_drag_events(self, canvas, center_id, iris_side):
        """
        눈동자 중심점에 드래그 이벤트 바인딩
        
        Args:
            canvas: 캔버스 객체
            center_id: 중심점 캔버스 ID
            iris_side: 'left' 또는 'right'
        """
        def on_iris_center_click(event):
            """눈동자 중심점 클릭 이벤트"""
            print(f"[DEBUG] Iris center clicked: {iris_side} at ({event.x}, {event.y})")
            self.parent.on_iris_center_drag_start(event, iris_side, canvas)
            return "break"
        
        def on_iris_center_drag(event):
            """눈동자 중심점 드래그 이벤트"""
            print(f"[DEBUG] Iris center dragging: {iris_side} at ({event.x}, {event.y})")
            self.parent.on_iris_center_drag(event, iris_side, canvas)
            return "break"
        
        def on_iris_center_release(event):
            """눈동자 중심점 드래그 종료 이벤트"""
            print(f"[DEBUG] Iris center released: {iris_side} at ({event.x}, {event.y})")
            self.parent.on_iris_center_drag_end(event, iris_side, canvas)
            return "break"
        
        # 기존 바인딩 제거 후 새로 바인딩
        try:
            canvas.tag_unbind(center_id, "<Button-1>")
            canvas.tag_unbind(center_id, "<B1-Motion>")
            canvas.tag_unbind(center_id, "<ButtonRelease-1>")
        except:
            pass  # 바인딩이 없는 경우 무시
        
        # 새로운 이벤트 바인딩
        canvas.tag_bind(center_id, "<Button-1>", on_iris_center_click)
        canvas.tag_bind(center_id, "<B1-Motion>", on_iris_center_drag)
        canvas.tag_bind(center_id, "<ButtonRelease-1>", on_iris_center_release)
        
        print(f"Bound iris drag events for {iris_side} center point (ID: {center_id})")
    
    def unbind_iris_drag_events(self, canvas, center_id):
        """
        눈동자 중심점에서 드래그 이벤트 언바인딩
        
        Args:
            canvas: 캔버스 객체
            center_id: 중심점 캔버스 ID
        """
        try:
            canvas.tag_unbind(center_id, "<Button-1>")
            canvas.tag_unbind(center_id, "<B1-Motion>")
            canvas.tag_unbind(center_id, "<ButtonRelease-1>")
        except:
            pass  # 바인딩이 없는 경우 무시
