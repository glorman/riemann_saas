import os
import traceback
from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from fastapi.responses import StreamingResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image, ImageOps
from io import BytesIO, StringIO
from pillow_lut import load_cube_file

app = FastAPI(title="Riemann Engine - Ultra Low RAM")

# CORS КОНТУР
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
MAX_PREMIUM_SIZE = 2000    # Снизили планку до 2000px для Premium, чтобы 512MB RAM на Render не взрывались

def load_cube_with_fixed_title(lut_path: str):
    """
    Всеядный загрузчик кубов. Пытается прочесть файл в UTF-8, 
    а если падает — переключается на виндовую кодировку cp1251.
    """
    fixed_lines = []
    try:
        with open(lut_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except UnicodeDecodeError:
        print(f"[SERVER WARNING] UTF-8 failed for {lut_path}. Retrying with cp1251...")
        with open(lut_path, 'r', encoding='cp1251') as f:
            lines = f.readlines()

    for line in lines:
        if line.startswith("TITLE"):
            parts = line.split(maxsplit=1)
            title_val = parts[1].strip().strip('"').strip("'") if len(parts) > 1 else "Lut"
            line = f'TITLE "{title_val}"\n'
        fixed_lines.append(line)
        
    return load_cube_file(StringIO("".join(fixed_lines)))


def process_image_core(image_bytes: bytes, lut_name: str, license_key: str) -> BytesIO:
    if lut_name not in AVAILABLE_LUTS:
        raise HTTPException(status_code=400, detail="Quantum invariant not found.")
    
    current_dir = os.path.dirname(os.path.abspath(__file__))
    lut_path = os.path.join(current_dir, AVAILABLE_LUTS[lut_name])
    
    if not os.path.exists(lut_path):
        raise HTTPException(status_code=500, detail="LUT file lost.")

    try:
        # LOW RAM OPTIMIZATION: Открываем лениво через буфер
        with Image.open(BytesIO(image_bytes)) as img:
            img = ImageOps.exif_transpose(img)
            
            if img.mode != "RGB":
                img = img.convert("RGB")
                
            if license_key == SECRET_PREMIUM_KEY:
                if max(img.size) > MAX_PREMIUM_SIZE:
                    img.thumbnail((MAX_PREMIUM_SIZE, MAX_PREMIUM_SIZE), Image.Resampling.BILINEAR) # Быстрый метод сжатия
            else:
                img.thumbnail((MAX_PREVIEW_SIZE, MAX_PREVIEW_SIZE), Image.Resampling.BILINEAR)
            
            he_lut = load_cube_with_fixed_title(lut_path)
            processed_img = img.filter(he_lut)
            
            output_buffer = BytesIO()
            processed_img.save(output_buffer, format="JPEG", quality=85, optimize=True) # Чуть снизили качество до 85 для экономии RAM
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
    
    # Читаем экономно
    file_bytes = await file.read()
    
    # Сразу проверяем размер сырых байт (если больше 10МБ, режем на корню, чтобы спасти оперативку сервера)
    if len(file_bytes) > 10 * 1024 * 1024:
         raise HTTPException(status_code=413, detail="File too heavy for Free Server. Limit 10MB.")
         
    processed_buffer = process_image_core(file_bytes, lut_type, license_key.strip())
    return StreamingResponse(processed_buffer, media_type="image/jpeg")


@app.get("/", response_class=HTMLResponse)
async def read_root():
    html_path = "index.html"
    if not os.path.exists(html_path):
        return "<h1>Error: index.html not found!</h1>"
    with open(html_path, "r", encoding="utf-8") as f:
        # Корректируем относительный путь запроса фронтенда, если запуск идет прямо на Render
        html_content = f.read()
        return html_content.replace("https://onrender.com", "/api/process")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
