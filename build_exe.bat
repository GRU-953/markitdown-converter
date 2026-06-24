@echo off
:: GRU-953 MarkItDown Converter — PyInstaller build script
:: Bundles: app, all assets, Tesseract binary + tessdata (eng + ben)
:: Output: dist\MarkItDownConverter.exe  (standalone, no install needed)

setlocal
set TESS=C:\Program Files\Tesseract-OCR

echo [1/4] Installing dependencies...
pip install -r requirements.txt --quiet

echo [2/4] Converting icon PNG to ICO...
python -c "from PIL import Image; img=Image.open('assets/app_icon.png'); img.save('assets/app_icon.ico', format='ICO', sizes=[(256,256),(128,128),(64,64),(32,32),(16,16)])"

echo [3/4] Running PyInstaller...
pyinstaller --noconfirm --onefile --windowed ^
  --name "MarkItDownConverter" ^
  --icon "assets/app_icon.ico" ^
  --add-data "assets;assets" ^
  --add-data "bijoy_unicode.py;." ^
  --add-data "ocr_engine.py;." ^
  --add-data "brand.py;." ^
  --add-binary "%TESS%\tesseract.exe;tesseract" ^
  --add-data "%TESS%\tessdata\eng.traineddata;tesseract/tessdata" ^
  --add-data "%TESS%\tessdata\ben.traineddata;tesseract/tessdata" ^
  --hidden-import customtkinter ^
  --hidden-import tkinterdnd2 ^
  --hidden-import pytesseract ^
  --hidden-import PIL._tkinter_finder ^
  --hidden-import markdown ^
  --collect-all customtkinter ^
  --collect-all tkinterdnd2 ^
  converter.py

echo [4/4] Done.
if exist "dist\MarkItDownConverter.exe" (
  echo SUCCESS: dist\MarkItDownConverter.exe
) else (
  echo FAILED: check build output above.
  exit /b 1
)
endlocal
