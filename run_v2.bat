@echo off
title FaceEditPanel v2
cd /d "d:\03.python\s7ed-v2"
echo FaceEditPanel v2 실행 중...
python gui\face_edit_v2\run_clean.py
if errorlevel 1 (
    echo 실행 실패!
    pause
)
