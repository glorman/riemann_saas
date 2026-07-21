import os
import traceback
from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from fastapi.responses import StreamingResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image, ImageOps
from io import BytesIO
from pillow_lut import load_cube_file

app = FastAPI(title="Riemann Engine - Production Core")

# CORS КОНТУР ДЛЯ СВЯЗКИ С ХАГГИНГФЕЙСОМ
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

LUT_DIRECTORY = ""
AVAILABLE_LUTS = {
    "riemann": "riemann.cube",
    "yang_mills": "yang_mills.cube",
    "noir": "noir.cube",
    "peugeot_night": "peugeot_night.cube",
    "zeta": "zeta.cube"
}

SECRET_PREMIUM_KEY = "RIEMANN_DEATH_TO_ZAVOD_2026"
MAX_PREVIEW_SIZE = 800     
MAX_PREMIUM_SIZE = 2000    # Лимит 2000px, чтобы уложиться в 512MB RAM бесплатного Render

            # === ВОЗВРАЩАЕМ ЗАЩИТНЫЙ КОНТУР ФИЛЬТРАЦИИ ПОТОКА ===
            cleaned_lines = []
            with open(lut_path, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    stripped = line.strip()
                    if not stripped: 
                        continue  # Фильтруем пустые строки, вызывающие IndexError
                    
                    parts = stripped.split()
                    # Если это строка с данными (начинается с цифры/минуса), проверяем валидность
                    if parts and (parts[0][0].isdigit() or parts[0].startswith('-') or parts[0].startswith('.')):
                        if len(parts) != 3:
                            continue  # Дропаем битые строки матрицы, спасая от out of range
                    
                    cleaned_lines.append(stripped)
            
            # Передаем очищенный массив строк напрямую в парсер
            he_lut = load_cube_file(cleaned_lines)
            processed_img = img.filter(he_lut)
            # ====================================================



@app.post("/api/process")
async def process_image(
    file: UploadFile = File(...),
    lut_type: str = Form("riemann"),
    license_key: str = Form("")
):
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Images only.")
    
    file_bytes = await file.read()
    
    if len(file_bytes) > 10 * 1024 * 1024:
         raise HTTPException(status_code=413, detail="File limit 10MB.")
         
    processed_buffer = process_image_core(file_bytes, lut_type, license_key.strip())
    return StreamingResponse(processed_buffer, media_type="image/jpeg")


@app.get("/", response_class=HTMLResponse)
async def read_root():
    html_path = "index.html"
    if not os.path.exists(html_path):
        return "<h1>Error: index.html not found!</h1>"
    with open(html_path, "r", encoding="utf-8") as f:
        return f.read()


if __name__ == "__main__":
    import uvicorn
    import os
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)

for name, filename in AVAILABLE_LUTS.items():
    path = os.path.join(os.path.dirname(__file__), filename)
    if not os.path.exists(path):
        print(f"⚠️ WARNING: LUT file '{filename}' not found. The '{name}' LUT will fail.")
