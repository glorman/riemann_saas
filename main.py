import os
import traceback
from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from fastapi.responses import StreamingResponse, HTMLResponse
from PIL import Image, ImageOps
from io import BytesIO, StringIO
from pillow_lut import load_cube_file

app = FastAPI(title="Riemann Quantum Color Engine - Locked Core")

LUT_DIRECTORY = ""
AVAILABLE_LUTS = {
    "riemann": "riemann.cube",
    "yang_mills": "yang_mills.cube",
    "noir": "noir.cube",
    "peugeot_night": "peugeot_night.cube",
    "zeta": "zeta.cube"
}

# Наш секретный мастер-ключ для разблокировки полного разрешения
SECRET_PREMIUM_KEY = "RIEMANN_DEATH_TO_ZAVOD_2026"

# Лимиты разрешения
MAX_PREVIEW_SIZE = 800     # Для бесплатных юзеров (Free)
MAX_PREMIUM_SIZE = 3000    # Для оплативших (Premium)

def load_cube_with_fixed_title(lut_path: str):
    fixed_lines = []
    with open(lut_path, 'r', encoding='utf-8') as f:
        for line in f:
            if line.startswith("TITLE"):
                parts = line.split(maxsplit=1)
                title_val = parts[1].strip().strip('"').strip("'") if len(parts) > 1 else "Lut"
                line = f'TITLE "{title_val}"\n'
            fixed_lines.append(line)
    return load_cube_file(StringIO("".join(fixed_lines)))

def process_image_core(image_bytes: bytes, lut_name: str, license_key: str) -> BytesIO:
    if lut_name not in AVAILABLE_LUTS:
        raise HTTPException(status_code=400, detail="Quantum invariant not found.")
    
    # Исправленный путь: ищем прямо в корне без подпапки luts
    lut_path = os.path.join(LUT_DIRECTORY, AVAILABLE_LUTS[lut_name]) if LUT_DIRECTORY else AVAILABLE_LUTS[lut_name]
    
    if not os.path.exists(lut_path):
        raise HTTPException(status_code=500, detail=f"Critical Server Error: LUT file [{lut_path}] lost.")

    try:
        img = Image.open(BytesIO(image_bytes))
        img = ImageOps.exif_transpose(img)
        
        if img.mode != "RGB":
            img = img.convert("RGB")
            
        if license_key == SECRET_PREMIUM_KEY:
            print("[SERVER] PREMIUM STATUS VERIFIED. Processing high-res.")
            if max(img.size) > MAX_PREMIUM_SIZE:
                img.thumbnail((MAX_PREMIUM_SIZE, MAX_PREMIUM_SIZE), Image.Resampling.LANCZOS)
        else:
            print("[SERVER] FREE USER DETECTED. Forcing downscale to 800px preview.")
            img.thumbnail((MAX_PREVIEW_SIZE, MAX_PREVIEW_SIZE), Image.Resampling.LANCZOS)
        
        he_lut = load_cube_with_fixed_title(lut_path)
        processed_img = img.filter(he_lut)
        
        output_buffer = BytesIO()
        processed_img.save(output_buffer, format="JPEG", quality=90, optimize=True)
        output_buffer.seek(0)
        return output_buffer

    except Exception as e:
        print("\n" + "="*50)
        print("[CRITICAL ERROR]:")
        traceback.print_exc()
        print("="*50 + "\n")
        raise HTTPException(status_code=500, detail=f"Engine fault: {str(e)}")



@app.post("/api/process")
async def process_image(
    file: UploadFile = File(...),
    lut_type: str = Form("riemann"),
    license_key: str = Form("") # Принимаем ключ из веб-формы (по умолчанию пустой)
):
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Images only.")
    
    file_size = 0
    file_bytes = b""
    while chunk := await file.read(1024 * 1024):
        file_bytes += chunk
        file_size += len(chunk)
        if file_size > 25 * 1024 * 1024:
            raise HTTPException(status_code=413, detail="File too large. Max 25MB.")
            
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
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
