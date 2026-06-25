@echo off
:: GRU-953 MarkItDown Converter v4 — PyInstaller build script (pywebview)
:: Bundles: app + web frontend + assets + Tesseract (eng + ben) + WebView2 backend
:: Output: dist\MarkItDownConverter.exe  (standalone, no install needed)

setlocal
set TESS=C:\Program Files\Tesseract-OCR

echo [1/4] Installing dependencies...
pip install -r requirements.txt --quiet

echo [2/4] Converting icon PNG to ICO...
python -c "from PIL import Image; img=Image.open('assets/app_icon.png'); img.save('assets/app_icon.ico', format='ICO', sizes=[(256,256),(128,128),(64,64),(32,32),(16,16)])"

echo [3/4] Running PyInstaller...
python -m PyInstaller --noconfirm --onefile --windowed ^
  --name "MarkItDownConverter" ^
  --icon "assets/app_icon.ico" ^
  --add-data "web;web" ^
  --add-data "assets;assets" ^
  --add-binary "%TESS%\tesseract.exe;tesseract" ^
  --add-data "%TESS%\tessdata\eng.traineddata;tesseract/tessdata" ^
  --add-data "%TESS%\tessdata\ben.traineddata;tesseract/tessdata" ^
  --collect-all webview ^
  --collect-all clr_loader ^
  --collect-all magika ^
  --collect-all markitdown ^
  --collect-all pymupdf ^
  --hidden-import clr ^
  --hidden-import bottle ^
  --hidden-import markdown ^
  --hidden-import mammoth ^
  --hidden-import openpyxl ^
  --hidden-import pptx ^
  --hidden-import xlrd ^
  --hidden-import pdfminer ^
  --hidden-import olefile ^
  app.py

echo [4/4] Done.
if exist "dist\MarkItDownConverter.exe" (
  echo SUCCESS: dist\MarkItDownConverter.exe
) else (
  echo FAILED: check build output above.
  exit /b 1
)
endlocal
