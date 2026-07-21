import os
import io
import traceback
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from PIL import Image, ImageOps
from pillow_lut import load_cube_file

# --- ИНИЦИАЛИЗАЦИЯ И CORS ---
app = FastAPI(title="Immortal Jellyfish Core Engine")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- КОНФИГУРАЦИЯ ПУТЕЙ ---
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))

AVAILABLE_LUTS = {
    "riemann": "riemann.cube",
    "yang_mills": "yang_mills.cube",
    "noir": "noir.cube",
    "peugeot_night": "peugeot_night.cube",
    "zeta": "zeta.cube"
}

SECRET_PREMIUM_KEY = "RIEMANN_DEATH_TO_ZAVOD_2026"

# --- ФУНКЦИЯ ОЧИСТКИ CUBE-ФАЙЛА ---
def load_cleaned_lut(lut_path: str):
    if not os.path.exists(lut_path):
        raise FileNotFoundError(f"LUT matrix missing at: {lut_path}")
        
    cleaned_buffer = io.StringIO()
    
    with open(lut_path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            stripped = line.strip()
            if not stripped:
                continue
            
            parts = stripped.split()
            if parts and (parts[0].isdigit() or parts[0].startswith('-') or parts[0].startswith('.')):
                if len(parts) != 3:
                    continue
            
            cleaned_buffer.write(stripped + "\n")
            
    cleaned_buffer.seek(0)
    return load_cube_file(cleaned_buffer)

# --- КОРРЕКТНЫЙ КОНТУР ОБРАБОТКИ ---
def process_image_core(image_bytes: bytes, lut_name: str, license_key: str) -> io.BytesIO:
    if lut_name not in AVAILABLE_LUTS:
        raise ValueError("Unknown quantum matrix target.")
        
    lut_path = os.path.join(CURRENT_DIR, AVAILABLE_LUTS[lut_name])
    
    with Image.open(io.BytesIO(image_bytes)) as img:
        img = ImageOps.exif_transpose(img)
        
        if img.mode != "RGB":
            img = img.convert("RGB")
            
        is_premium = (license_key == SECRET_PREMIUM_KEY)
        max_side = 2000 if is_premium else 800
        
        w, h = img.size
        if max(w, h) > max_side:
            if w > h:
                new_w, new_h = max_side, int(h * (max_side / w))
            else:
                new_w, new_h = int(w * (max_side / h)), max_side
            img = img.resize((new_w, new_h), resample=Image.Resampling.BILINEAR)
            
        try:
            he_lut = load_cleaned_lut(lut_path)
            processed_img = img.filter(he_lut)
        except Exception as e:
            print("!!! КРИТИЧЕСКИЙ СБОЙ МАТРИЦЫ LUT !!!")
            traceback.print_exc()
            raise RuntimeError(f"Engine fault during matrix calibration: {str(e)}")
            
        output_buffer = io.BytesIO()
        processed_img.save(
            output_buffer, 
            format="JPEG", 
            quality=85, 
            optimize=True
        )
        output_buffer.seek(0)
        return output_buffer

# --- ЭНДПОИНТЫ ---
@app.get("/")
def read_root():
    return {
        "status": "ONLINE", 
        "engine": "Immortal Jellyfish v1.0.0-MVP", 
        "math_stabilizer": "Riemann/Yang-Mills Operational"
    }

@app.post("/api/process")
async def process_image(
    file: UploadFile = File(...),
    lut: str = Form(...),
    token: str = Form(default="")
):
    try:
        image_bytes = await file.read()
        result_stream = process_image_core(image_bytes, lut, token.strip())
        return StreamingResponse(result_stream, media_type="image/jpeg")
        
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=f"Validation error: {str(ve)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Engine fault: {str(e)}")
