@echo off
echo Setting up environment...

echo Running text extraction script...
echo Note: First run may take longer as PaddleOCR downloads necessary models.
python extract_text_from_images.py

echo.
echo Done! Press any key to exit.
pause > nul 