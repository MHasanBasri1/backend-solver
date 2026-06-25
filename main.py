import io
import os
import base64
import requests
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# Load environment variables dari file .env
load_dotenv()

app = FastAPI(title="Problem Solver Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ambil API Key dari environment variable GEMINI_API_KEY
API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    print("⚠️ WARNING: GEMINI_API_KEY tidak ditemukan di environment variables atau file .env!")

@app.post("/solve")
async def solve_problem(file: UploadFile = File(...)):
    try:
        print("▶️ 1. Menerima foto dari HP...")
        image_bytes = await file.read()
        
        print("▶️ 2. Membaca format gambar...")
        mime_type = file.content_type

        # Trik: Paksa jadi JPEG jika Flutter mengirim format anonim
        if mime_type == "application/octet-stream" or not mime_type:
            mime_type = "image/jpeg"
        
        print("▶️ 3. Menghubungi Google Gemini (Direct REST API)...")
        prompt = (
            "Identifikasi soal matematika/fisika/kimia di dalam foto ini. "
            "Selesaikan soalnya dan berikan jawaban akhir beserta langkah-langkah "
            "penyelesaiannya secara detail dan terstruktur."
        )
        
        # Konversi gambar ke format Base64 yang diminta oleh Google
        image_b64 = base64.b64encode(image_bytes).decode("utf-8")
        
        # Endpoint resmi Google
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-flash-lite:generateContent?key={API_KEY}"
        
        # Merakit paket data untuk dikirim
        payload = {
            "contents": [{
                "parts": [
                    {"text": prompt},
                    {
                        "inline_data": {
                            "mime_type": mime_type,
                            "data": image_b64
                        }
                    }
                ]
            }]
        }
        
        # Mengirim data menggunakan requests (Bypass SDK yang buggy)
        headers = {'Content-Type': 'application/json'}
        response = requests.post(url, headers=headers, json=payload)
        
        # Jika Google mengembalikan error
        if response.status_code != 200:
            print(f"🔥 ERROR DARI GOOGLE: {response.text}")
            raise HTTPException(status_code=500, detail=f"Google API Error: {response.text}")
            
        data = response.json()
        
        # Mengekstrak teks jawaban dari struktur JSON
        answer_text = data['candidates'][0]['content']['parts'][0]['text']
        
        print("▶️ 4. Jawaban dari Gemini berhasil didapatkan! Mengirim balik ke HP...")
        return {
            "status": "success",
            "answer": answer_text
        }
        
    except Exception as e:
        print(f"🔥 ERROR DETAIL: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Gagal memproses gambar: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000)