import os
import traceback
from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from fastapi.responses import StreamingResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image, ImageOps
from io import BytesIO
from pillow_lut import load_cube_file

app = FastAPI(title="Riemann Engine - Production Core")

# CORS – разрешаем всё для теста
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Словарь доступных LUT – файлы должны лежать в корне проекта
AVAILABLE_LUTS = {
    "riemann": "riemann.cube",
    "yang_mills": "yang_mills.cube",
    "noir": "noir.cube",
    "peugeot_night": "peugeot_night.cube",
    "zeta": "zeta.cube"
}

# Проверяем, что все файлы LUT существуют при старте
for name, filename in AVAILABLE_LUTS.items():
    path = os.path.join(os.path.dirname(__file__), filename)
    if not os.path.exists(path):
        print(f"⚠️ WARNING: LUT file '{filename}' not found. The '{name}' LUT will fail.")

SECRET_PREMIUM_KEY = "RIEMANN_DEATH_TO_ZAVOD_2026"
MAX_PREVIEW_SIZE = 800
MAX_PREMIUM_SIZE = 2000

def process_image_core(image_bytes: bytes, lut_name: str, license_key: str) -> BytesIO:
    if lut_name not in AVAILABLE_LUTS:
        raise HTTPException(status_code=400, detail="Quantum invariant not found.")
    
    current_dir = os.path.dirname(os.path.abspath(__file__))
    lut_path = os.path.join(current_dir, AVAILABLE_LUTS[lut_name])
    
    if not os.path.exists(lut_path):
        raise HTTPException(status_code=500, detail=f"LUT file lost at {lut_path}")

    try:
        with Image.open(BytesIO(image_bytes)) as img:
            img = ImageOps.exif_transpose(img)
            if img.mode != "RGB":
                img = img.convert("RGB")
                
            if license_key == SECRET_PREMIUM_KEY:
                if max(img.size) > MAX_PREMIUM_SIZE:
                    img.thumbnail((MAX_PREMIUM_SIZE, MAX_PREMIUM_SIZE), Image.Resampling.BILINEAR)
            else:
                img.thumbnail((MAX_PREVIEW_SIZE, MAX_PREVIEW_SIZE), Image.Resampling.BILINEAR)
            
            he_lut = load_cube_file(lut_path)
            processed_img = img.filter(he_lut)
            
            output_buffer = BytesIO()
            processed_img.save(output_buffer, format="JPEG", quality=85, optimize=True)
            output_buffer.seek(0)
            return output_buffer

    except Exception as e:
        print("\n" + "="*50)
        traceback.print_exc()
        print("="*50 + "\n")
        raise HTTPException(status_code=500, detail=f"Engine fault: {str(e)}")

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
