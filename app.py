import os
import uuid
import socket
import asyncio
from datetime import datetime
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
import edge_tts

app = FastAPI(title="AI Voice Generator")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Support cloud environments like Vercel/Render where filesystem might be in /tmp
if os.access(BASE_DIR, os.W_OK):
    OUTPUT_DIR = os.path.join(BASE_DIR, "output")
else:
    OUTPUT_DIR = os.path.join("/tmp", "output")
STATIC_DIR = os.path.join(BASE_DIR, "static")

os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(STATIC_DIR, exist_ok=True)

# Curated popular natural female voices with human-friendly descriptions
POPULAR_FEMALE_VOICES = [
    {
        "id": "en-US-AvaNeural",
        "name": "Ava",
        "accent": "US (American)",
        "tone": "Warm, Natural & Conversational",
        "category": "Recommended"
    },
    {
        "id": "en-US-JennyNeural",
        "name": "Jenny",
        "accent": "US (American)",
        "tone": "Friendly, Professional & Clear",
        "category": "Recommended"
    },
    {
        "id": "en-US-AriaNeural",
        "name": "Aria",
        "accent": "US (American)",
        "tone": "Expressive, Storyteller & Podcast",
        "category": "Recommended"
    },
    {
        "id": "en-US-EmmaNeural",
        "name": "Emma",
        "accent": "US (American)",
        "tone": "Cheerful & Youthful",
        "category": "US"
    },
    {
        "id": "en-US-MichelleNeural",
        "name": "Michelle",
        "accent": "US (American)",
        "tone": "Confident, Executive & News",
        "category": "US"
    },
    {
        "id": "en-GB-SoniaNeural",
        "name": "Sonia",
        "accent": "UK (British)",
        "tone": "Crisp, Elegant & Polite",
        "category": "UK"
    },
    {
        "id": "en-GB-LibbyNeural",
        "name": "Libby",
        "accent": "UK (British)",
        "tone": "Warm, Narrative & Storytelling",
        "category": "UK"
    },
    {
        "id": "en-GB-MaisieNeural",
        "name": "Maisie",
        "accent": "UK (British)",
        "tone": "Youthful & Bright",
        "category": "UK"
    },
    {
        "id": "en-IN-NeerjaNeural",
        "name": "Neerja",
        "accent": "Indian English",
        "tone": "Natural, Fluent & Expressive",
        "category": "Indian"
    },
    {
        "id": "en-IN-AnanyaNeural",
        "name": "Ananya",
        "accent": "Indian English",
        "tone": "Soft, Modern & Clear",
        "category": "Indian"
    },
    {
        "id": "hi-IN-SwaraNeural",
        "name": "Swara",
        "accent": "Hindi / Hinglish",
        "tone": "Melodic, Friendly & Expressive",
        "category": "Indian"
    },
    {
        "id": "en-AU-NatashaNeural",
        "name": "Natasha",
        "accent": "Australian",
        "tone": "Casual, Friendly & Clear",
        "category": "International"
    },
    {
        "id": "en-CA-ClaraNeural",
        "name": "Clara",
        "accent": "Canadian",
        "tone": "Neutral, Polite & Friendly",
        "category": "International"
    }
]

def get_local_ip():
    """Detect local WiFi / LAN IP address for phone connection"""
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
    rate: int = 0      # Speed offset (-50 to +50 percent)
    pitch: int = 0     # Pitch offset (-50 to +50 Hz)

@app.get("/api/info")
async def get_info():
    ip = get_local_ip()
    port = int(os.environ.get("PORT", 5050))
    return {
        "local_ip": ip,
        "port": port,
        "phone_url": f"http://{ip}:{port}",
        "local_url": f"http://localhost:{port}"
    }

@app.get("/api/voices")
async def list_voices():
    try:
        all_voices = await edge_tts.list_voices()
        female_all = [
            {
                "id": v["ShortName"],
                "name": v["FriendlyName"].split("-")[0].strip(),
                "locale": v["Locale"],
                "gender": v["Gender"]
            }
            for v in all_voices if v.get("Gender") == "Female"
        ]
        return {
            "curated": POPULAR_FEMALE_VOICES,
            "all_female": female_all
        }
    except Exception as e:
        return {
            "curated": POPULAR_FEMALE_VOICES,
            "all_female": []
        }

@app.post("/api/generate")
async def generate_voice(req: GenerateRequest):
    text = req.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Text cannot be empty.")
    if len(text) > 10000:
        raise HTTPException(status_code=400, detail="Text exceeds 10,000 character limit.")

    # Format rate and pitch
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
    return {"history": files[:15]}

# Serve index.html directly from static
@app.get("/")
async def root():
    index_path = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"status": "running"}

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
