"""
editing_steps.py 생성 스크립트
logic.py의 apply_editing 메서드를 단계별로 분리
"""
import os

def extract_editing_steps():
    """editing_steps.py 파일 생성"""
    input_file = 'gui/face_edit/morphing/logic.py'
    
    with open(input_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # 각 단계의 범위 정의 (1-based line number)
    step_ranges = {
        'prepare_params': (934, 1013),  # 파라미터 준비 및 특징 보정 적용
        'style_transfer': (1015, 1030),  # 스타일 전송
        'age_transform': (1032, 1035),   # 나이 변환
        'update_landmarks': (1042, 1264)  # 랜드마크 업데이트
    }
    
    step_methods = {
        'prepare_params': '_prepare_editing_parameters',
        'style_transfer': '_apply_style_transfer_step',
        'age_transform': '_apply_age_transform_step',
        'update_landmarks': '_update_landmarks_after_editing'
    }
    
    output_lines = []
    output_lines.append('"""\n')
    output_lines.append('편집 단계별 처리 메서드\n')
    output_lines.append('apply_editing의 각 단계를 분리한 메서드들\n')
    output_lines.append('"""\n')
    output_lines.append('import os\n')
    output_lines.append('from PIL import Image\n')
    output_lines.append('\n')
    output_lines.append('import utils.face_morphing as face_morphing\n')
    output_lines.append('import utils.style_transfer as style_transfer\n')
    output_lines.append('import utils.face_transform as face_transform\n')
    output_lines.append('import utils.face_landmarks as face_landmarks\n')
    output_lines.append('\n\n')
    output_lines.append('class EditingStepsMixin:\n')
    output_lines.append('    """편집 단계별 처리 기능 Mixin"""\n')
    output_lines.append('    \n')
    
    # 각 단계별 메서드 생성
    for step_name, (start, end) in step_ranges.items():
        method_name = step_methods[step_name]
        step_lines = lines[start-1:end]  # 0-based index
        
        # 메서드 시그니처 작성
        if step_name == 'prepare_params':
            output_lines.append(f'    def {method_name}(self, base_image):\n')
            output_lines.append(f'        """파라미터 준비 및 얼굴 특징 보정 적용"""\n')
        elif step_name == 'style_transfer':
            output_lines.append(f'    def {method_name}(self, image):\n')
            output_lines.append(f'        """스타일 전송 적용"""\n')
        elif step_name == 'age_transform':
            output_lines.append(f'    def {method_name}(self, image):\n')
            output_lines.append(f'        """나이 변환 적용"""\n')
        elif step_name == 'update_landmarks':
            output_lines.append(f'    def {method_name}(self):\n')
            output_lines.append(f'        """변형된 랜드마크 계산 및 업데이트"""\n')
        
        # 각 줄 처리 (들여쓰기 조정)
        for line in step_lines:
            stripped = line.rstrip('\n')
            
            # 빈 줄
            if not stripped.strip():
                output_lines.append('\n')
                continue
            
            # 들여쓰기 조정
            # 원본은 12칸 들여쓰기 (try 블록 내부)
            # 메서드 내부는 8칸 기본
            indent = len(stripped) - len(stripped.lstrip())
            content = stripped.lstrip()
            
            if indent >= 12:
                # 12칸 이상: 4칸씩 줄임 (12->8, 16->12, 20->16, 24->20)
                new_indent = indent - 4
                output_lines.append(' ' * new_indent + content + '\n')
            elif indent == 0:
                # 최상위 레벨
                output_lines.append('        ' + content + '\n')
            else:
                # 그 외 (8칸 이하)
                output_lines.append('        ' + content + '\n')
        
        output_lines.append('\n\n')
    
    # 파일로 저장
    output_file = 'gui/face_edit/morphing/editing_steps.py'
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(''.join(output_lines))
    
    print(f"editing_steps.py 생성 완료: {output_file}")

if __name__ == '__main__':
    extract_editing_steps()
