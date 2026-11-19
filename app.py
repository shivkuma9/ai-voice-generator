import os
import uuid
import socket
import asyncio
from datetime import datetime
from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import edge_tts

app = FastAPI(title="Persona AI Voice Generator")

# Enable CORS for cross-device requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Support cloud environments like Render/Vercel where filesystem might be ephemeral
if os.access(BASE_DIR, os.W_OK):
    OUTPUT_DIR = os.path.join(BASE_DIR, "output")
    SAMPLES_DIR = os.path.join(BASE_DIR, "samples")
else:
    OUTPUT_DIR = os.path.join("/tmp", "output")
    SAMPLES_DIR = os.path.join("/tmp", "samples")

STATIC_DIR = os.path.join(BASE_DIR, "static")

os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(SAMPLES_DIR, exist_ok=True)
os.makedirs(STATIC_DIR, exist_ok=True)

# 100% verified top-tier natural female voices
POPULAR_FEMALE_VOICES = [
    {
        "id": "en-US-AvaNeural",
        "name": "Ava",
        "flag": "🇺🇸",
        "accent": "US English",
        "tone": "Warm, Natural & Conversational",
        "category": "Recommended",
        "sample": "Hello! I am Ava. My voice is warm, natural, and friendly."
    },
    {
        "id": "en-US-JennyNeural",
        "name": "Jenny",
        "flag": "🇺🇸",
        "accent": "US English",
        "tone": "Crisp, Clear & Professional",
        "category": "Recommended",
        "sample": "Hello! I am Jenny. I speak with a clear and professional tone."
    },
    {
        "id": "en-US-AriaNeural",
        "name": "Aria",
        "flag": "🇺🇸",
        "accent": "US English",
        "tone": "Expressive, Storyteller & Podcast",
        "category": "Recommended",
        "sample": "Welcome! I am Aria. I love storytelling, narration, and podcasts."
    },
    {
        "id": "en-IN-NeerjaExpressiveNeural",
        "name": "Neerja (Expressive)",
        "flag": "🇮🇳",
        "accent": "Indian English",
        "tone": "Lively, Fluent & Expressive",
        "category": "Recommended",
        "sample": "Namaste! I am Neerja Expressive. Great to meet you!"
    },
    {
        "id": "en-IN-NeerjaNeural",
        "name": "Neerja (Natural)",
        "flag": "🇮🇳",
        "accent": "Indian English",
        "tone": "Calm, Clear & Polite",
        "category": "Indian",
        "sample": "Hello! I am Neerja. I can read your articles and scripts naturally."
    },
    {
        "id": "hi-IN-SwaraNeural",
        "name": "Swara",
        "flag": "🇮🇳",
        "accent": "Hindi / Hinglish",
        "tone": "Melodic, Sweet & Fluent",
        "category": "Indian",
        "sample": "Namaste! Main Swara hoon. Aapka swagat hai."
    },
    {
        "id": "en-GB-SoniaNeural",
        "name": "Sonia",
        "flag": "🇬🇧",
        "accent": "British UK",
        "tone": "Crisp, Elegant & Classic British",
        "category": "UK",
        "sample": "Good day! I am Sonia. I speak with an elegant British accent."
    },
    {
        "id": "en-GB-LibbyNeural",
        "name": "Libby",
        "flag": "🇬🇧",
        "accent": "British UK",
        "tone": "Warm, Narrative & Storytelling",
        "category": "UK",
        "sample": "Hello! I am Libby. Perfect for audiobooks and gentle narration."
    },
    {
        "id": "en-GB-MaisieNeural",
        "name": "Maisie",
        "flag": "🇬🇧",
        "accent": "British UK",
        "tone": "Youthful, Bright & Modern",
        "category": "UK",
        "sample": "Hi! I am Maisie. Bright, cheerful, and ready to help!"
    },
    {
        "id": "en-US-EmmaNeural",
        "name": "Emma",
        "flag": "🇺🇸",
        "accent": "US English",
        "tone": "Cheerful, Casual & Engaging",
        "category": "US",
        "sample": "Hey there! I am Emma. Looking forward to reading your text."
    },
    {
        "id": "en-US-MichelleNeural",
        "name": "Michelle",
        "flag": "🇺🇸",
        "accent": "US English",
        "tone": "Executive, Formal & News Anchor",
        "category": "US",
        "sample": "Greetings. I am Michelle. Ideal for corporate and broadcast scripts."
    },
    {
        "id": "en-AU-NatashaNeural",
        "name": "Natasha",
        "flag": "🇦🇺",
        "accent": "Australian",
        "tone": "Relaxed, Friendly & Upbeat",
        "category": "International",
        "sample": "G'day! I am Natasha with a friendly Australian accent."
    },
    {
        "id": "en-CA-ClaraNeural",
        "name": "Clara",
        "flag": "🇨🇦",
        "accent": "Canadian",
        "tone": "Polite, Neutral & Smooth",
        "category": "International",
        "sample": "Hello! I am Clara, speaking with a smooth Canadian accent."
    },
    {
        "id": "ta-IN-PallaviNeural",
        "name": "Pallavi",
        "flag": "🇮🇳",
        "accent": "Tamil (India)",
        "tone": "Traditional & Fluent Tamil",
        "category": "Regional",
        "sample": "Vanakkam! Naan Pallavi."
    },
    {
        "id": "te-IN-ShrutiNeural",
        "name": "Shruti",
        "flag": "🇮🇳",
        "accent": "Telugu (India)",
        "tone": "Clear & Pleasant Telugu",
        "category": "Regional",
        "sample": "Namaskaram! Nenu Shruti."
    },
    {
        "id": "mr-IN-AarohiNeural",
        "name": "Aarohi",
        "flag": "🇮🇳",
        "accent": "Marathi (India)",
        "tone": "Warm & Expressive Marathi",
        "category": "Regional",
        "sample": "Namaskar! Mee Aarohi."
    }
]

def get_local_ip():
    """Detect local WiFi / LAN IP address for local running"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

class GenerateRequest(BaseModel):
    text: str
    voice: str = "en-US-AvaNeural"
    rate: int = 0      # Speed offset (-40 to +40 percent)
    pitch: int = 0     # Pitch offset (-30 to +30 Hz)

@app.get("/api/info")
async def get_info(request: Request):
    ip = get_local_ip()
    port = int(os.environ.get("PORT", 5050))
    host = request.headers.get("host", f"{ip}:{port}")
    scheme = "https" if "render.com" in host or request.headers.get("x-forwarded-proto") == "https" else "http"
    public_url = f"{scheme}://{host}"

    return {
        "local_ip": ip,
        "port": port,
        "public_url": public_url,
        "phone_url": public_url,
        "local_url": f"http://localhost:{port}"
    }

@app.get("/api/voices")
async def list_voices():
    return {
        "curated": POPULAR_FEMALE_VOICES
    }

@app.get("/api/sample/{voice_id}")
async def get_sample(voice_id: str):
    voice_obj = next((v for v in POPULAR_FEMALE_VOICES if v["id"] == voice_id), None)
    if not voice_obj:
        raise HTTPException(status_code=404, detail="Voice not found")

    sample_file = os.path.join(SAMPLES_DIR, f"{voice_id}.mp3")
    if not os.path.exists(sample_file):
        try:
            communicate = edge_tts.Communicate(
                text=voice_obj["sample"],
                voice=voice_id
            )
            await communicate.save(sample_file)
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    return FileResponse(sample_file, media_type="audio/mpeg", filename=f"{voice_id}_sample.mp3")

@app.post("/api/generate")
async def generate_voice(req: GenerateRequest):
    text = req.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Text cannot be empty.")
    if len(text) > 10000:
        raise HTTPException(status_code=400, detail="Text exceeds 10,000 character limit.")

    rate_str = f"{req.rate:+d}%" if req.rate != 0 else "+0%"
    pitch_str = f"{req.pitch:+d}Hz" if req.pitch != 0 else "+0Hz"

    file_id = f"voice_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}.mp3"
    file_path = os.path.join(OUTPUT_DIR, file_id)

    try:
        communicate = edge_tts.Communicate(
            text=text,
            voice=req.voice,
            rate=rate_str,
            pitch=pitch_str
        )
        await communicate.save(file_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Voice synthesis failed: {str(e)}")

    return {
        "success": True,
        "filename": file_id,
        "audio_url": f"/api/audio/{file_id}",
        "preview_text": text[:60] + ("..." if len(text) > 60 else "")
    }

@app.get("/api/audio/{filename}")
async def get_audio(filename: str):
    file_path = os.path.join(OUTPUT_DIR, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Audio file not found")
    return FileResponse(file_path, media_type="audio/mpeg", filename=filename)

@app.get("/api/history")
async def get_history():
    files = []
    if os.path.exists(OUTPUT_DIR):
        for f in sorted(os.listdir(OUTPUT_DIR), reverse=True):
            if f.endswith(".mp3"):
                file_path = os.path.join(OUTPUT_DIR, f)
                stat = os.stat(file_path)
                files.append({
                    "filename": f,
                    "audio_url": f"/api/audio/{f}",
                    "size_kb": round(stat.st_size / 1024, 1),
                    "time": datetime.fromtimestamp(stat.st_mtime).strftime("%I:%M %p")
                })
    return {"history": files[:10]}

@app.get("/")
async def root():
    index_path = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"status": "Persona AI Voice Running"}

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

if __name__ == "__main__":
    import uvicorn
    local_ip = get_local_ip()
    port = int(os.environ.get("PORT", 5050))
    print("=" * 60)
    print("  PERSONA AI FEMALE VOICE GENERATOR READY!")
    print(f"  > Open on PC:    http://localhost:{port}")
    print(f"  > Open on Phone: http://{local_ip}:{port}")
    print("=" * 60)
    uvicorn.run("app:app", host="0.0.0.0", port=port, reload=False)
