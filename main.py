import io
import os
import base64
import requests
# Tambahkan Form di sini untuk menerima teks manual
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
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

# --- TAMBAHKAN KODE INI SETELAH BARIS 24 (setelah pengecekan API_KEY) ---

# Status awal aplikasi (bisa diakses)
app_active = True

# Endpoint untuk mengunci/membuka aplikasi
@app.get("/admin/toggle")
async def toggle_status(key: str):
    global app_active
    # Password rahasia yang nanti akan kamu tanam di kode Flutter
    if key == "KUNCI_RAHASIA_123":
        app_active = not app_active
        status_text = "Aktif" if app_active else "Terkunci"
        print(f"▶️ Status aplikasi diubah menjadi: {status_text}")
        return {"status": status_text}
    return {"error": "Akses Ditolak"}

# ---------------------------------------------------------------------

# Ubah parameter agar menerima file (foto) ATAU text (ketikan manual)
@app.post("/solve")
async def solve_problem(file: UploadFile = File(None), text: str = Form(None)):
    if not app_active:
        return {"status": "error", "answer": "MAJER JHEK GRATISEN MELOLOH!."}
    try:
        print("▶️ 1. Menerima request dari HP...")
        
        # Cek jika tidak ada foto dan tidak ada teks yang dikirim
        if not file and not text:
             return {"status": "error", "answer": "Tolong kirimkan foto atau teks soal."}
             
        # Prompt dasar bahasa Madura yang tidak diubah
        # Prompt dasar bahasa Madura + Persona Basri Capital yang sangat ketat
        base_prompt = (
            "Kamu adalah asisten kecerdasan buatan (AI) ciptaan 'Basri Capital'.\n"
            "Terdapat 2 ATURAN MUTLAK yang harus kamu patuhi secara ketat:\n"
            "1. JIKA PENGGUNA BERTANYA ATAU MENGIRIM SOAL MATEMATIKA/SAINS: Kamu WAJIB LANGSUNG menjawab langkah-langkah penyelesaiannya tanpa basa-basi. DILARANG KERAS memberikan kalimat salam, DILARANG memperkenalkan diri, dan DILARANG menyebutkan nama 'Basri Capital'. Fokus 100% langsung ke penyelesaian soal matematika/sains tersebut.\n"
            "2. JIKA PENGGUNA BERTANYA TENTANG IDENTITASMU (contoh: 'kamu siapa?', 'buatan siapa?', 'siapa penciptamu?'): BARULAH kamu menjawab bahwa kamu adalah asisten kecerdasan buatan yang diciptakan oleh 'Basri Capital'. Jangan pernah sebut nama Google, OpenAI, atau pihak lain.\n"
            "Selalu gunakan bahasa Madura probolinggo (bukan campuran Jawa) untuk semua responsmu dalam kondisi apa pun."
        )
        
        parts = []

        # LOGIKA 1: Jika user mengirim FOTO
        if file:
            print("▶️ 2. Membaca format gambar...")
            image_bytes = await file.read()
            mime_type = file.content_type

            # Trik: Paksa jadi JPEG jika Flutter mengirim format anonim
            if mime_type == "application/octet-stream" or not mime_type:
                mime_type = "image/jpeg"
            
            image_b64 = base64.b64encode(image_bytes).decode("utf-8")
            
            # Gabungkan prompt foto dengan prompt Madura
            parts.append({"text": "Identifikasi soal matematika/fisika/kimia di dalam foto ini. " + base_prompt})
            parts.append({
                "inline_data": {
                    "mime_type": mime_type,
                    "data": image_b64
                }
            })
            
        # LOGIKA 2: Jika user mengirim TEKS MANUAL
        else:
            print(f"▶️ 2. Membaca input manual: {text}")
            # Gabungkan teks ketikan user dengan prompt Madura
            parts.append({"text": f"Pertanyaan: {text}\n\n" + base_prompt})
            
        print("▶️ 3. Menghubungi Google Gemini (Direct REST API)...")
        # Endpoint resmi Google
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-flash-lite:generateContent?key={API_KEY}"
        
        # Merakit paket data untuk dikirim
        payload = {
            "contents": [{
                "parts": parts
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
        raise HTTPException(status_code=500, detail=f"Gagal memproses request: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000)