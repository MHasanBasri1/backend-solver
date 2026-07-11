import io
import os
import base64
import requests
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv
from supabase import create_client, Client

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

app.mount("/static", StaticFiles(directory="static"), name="static")

# =================================================================
# PERSIAPAN KUNCI RAHASIA (GEMINI & SUPABASE)
# =================================================================
API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    print("⚠️ WARNING: GEMINI_API_KEY tidak ditemukan!")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Menghidupkan koneksi ke Supabase
supabase: Client = None
if SUPABASE_URL and SUPABASE_KEY:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    print("✅ Berhasil terhubung ke Supabase!")
else:
    print("⚠️ WARNING: URL atau Key Supabase tidak ditemukan di .env!")

# Status awal aplikasi
app_active = True
app_maintenance = False

# =================================================================
# PUSAT KOMANDO UPDATE & ADMIN
# =================================================================
@app.get("/check-update")
async def check_update():
    global app_maintenance 
    return {
        "latest_version": "1.0.1", 
        "download_url": "https://backend-solver-production.up.railway.app/static/SolverSains_v1.0.1.apk",
        "update_message": "Sistem penyelesaian soal yang lebih canggih, animasi sains baru, dan tombol copy!",
        "is_maintenance": app_maintenance 
    }

@app.get("/admin/toggle")
async def toggle_status(key: str):
    global app_active
    if key == "KUNCI_RAHASIA_123":
        app_active = not app_active
        status_text = "Aktif" if app_active else "Terkunci"
        return {"status": status_text}
    return {"error": "Akses Ditolak"}

@app.get("/admin/toggle-maintenance")
async def toggle_maintenance(key: str):
    global app_maintenance
    if key == "KUNCI_RAHASIA_123":
        app_maintenance = not app_maintenance
        status_text = "Mode Pemeliharaan NYALA" if app_maintenance else "Mode Pemeliharaan MATI"
        return {"status": status_text}
    return {"error": "Akses Ditolak"}

# =================================================================
# FUNGSI UTAMA PENYELESAIAN SOAL
# =================================================================
@app.post("/solve")
async def solve_problem(
    file: UploadFile = File(None), 
    text: str = Form(None),
    device_id: str = Form(None) 
):

    print(f"DEBUGGING: KTP yang diterima server adalah: '{device_id}'")
    # 1. Cek Kunci Utama Aplikasi
    if not app_active:
        return {"status": "error", "answer": "MAJER JHEK GRATISEN MELOLOH!."}

    # 2. SATPAM SUPABASE: Cek apakah KTP ini ada di daftar hitam
    if device_id and supabase:
        print(f"▶️ Mengecek status blokir untuk HP: {device_id}")
        response = supabase.table("banned_devices").select("*").eq("device_id", device_id).execute()
        
        if len(response.data) > 0:
             print(f"🚫 HP DIBLOKIR MENCOBA AKSES: {device_id}")
             return {"status": "banned", "answer": "Akses Anda telah diblokir secara permanen."}
             
        # 3. BUKU TAMU SUPABASE: Catat KTP jika belum pernah dicatat
        try:
            log_check = supabase.table("users_log").select("device_id").eq("device_id", device_id).execute()
            if len(log_check.data) == 0: # Jika KTP belum ada di tabel
                supabase.table("users_log").insert({"device_id": device_id}).execute()
                print(f"📝 Pengguna baru berhasil dicatat di Buku Tamu: {device_id}")
        except Exception as e:
            print(f"⚠️ Gagal mencatat buku tamu: {e}") # Error mencatat tidak boleh menggagalkan AI

    try:
        print("▶️ 1. Menerima request soal dari HP...")
        
        if not file and not text:
             return {"status": "error", "answer": "Tolong kirimkan foto atau teks soal."}
             
        base_prompt = (
            "Kamu adalah sistem kecerdasan buatan ciptaan 'Basri Capital'.\n"
            "Terdapat 2 ATURAN MUTLAK yang harus kamu patuhi secara ketat:\n"
            "1. JIKA PENGGUNA MENGIRIM SOAL MATEMATIKA/SAINS: DILARANG memberikan salam, perkenalan diri, atau menyebut 'Basri Capital'. NAMUN, kamu WAJIB memberikan penjelasan penyelesaian yang SANGAT DETAIL, edukatif, dan panjang. Jelaskan konsep/teori dasarnya terlebih dahulu (misal: aturan urutan operasi perkalian/pembagian sebelum penjumlahan), jabarkan setiap langkah secara perlahan, dan berikan kesimpulan agar pengguna benar-benar paham. Bertindaklah seperti guru privat yang sabar.\n"
            "2. JIKA PENGGUNA BERTANYA TENTANG IDENTITASMU (contoh: 'kamu siapa?', 'buatan siapa?'): BARULAH kamu menjawab bahwa kamu adalah sistem kecerdasan buatan ciptaan 'Basri Capital'. Jangan pernah sebut nama Google, OpenAI, atau pihak lain.\n"
        )
        
        parts = []

        if file:
            print("▶️ 2. Membaca format gambar...")
            image_bytes = await file.read()
            mime_type = file.content_type
            if mime_type == "application/octet-stream" or not mime_type:
                mime_type = "image/jpeg"
            
            image_b64 = base64.b64encode(image_bytes).decode("utf-8")
            parts.append({"text": "Identifikasi soal matematika/fisika/kimia di dalam foto ini. " + base_prompt})
            parts.append({"inline_data": {"mime_type": mime_type, "data": image_b64}})
            
        else:
            print(f"▶️ 2. Membaca input manual: {text}")
            parts.append({"text": f"Pertanyaan: {text}\n\n" + base_prompt})
            
        print("▶️ 3. Menghubungi Google Gemini...")
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-flash-lite:generateContent?key={API_KEY}"
        
        payload = {"contents": [{"parts": parts}]}
        headers = {'Content-Type': 'application/json'}
        gemini_response = requests.post(url, headers=headers, json=payload)
        
        if gemini_response.status_code != 200:
            raise HTTPException(status_code=500, detail=f"Google API Error: {gemini_response.text}")
            
        data = gemini_response.json()
        answer_text = data['candidates'][0]['content']['parts'][0]['text']
        
        print("▶️ 4. Jawaban berhasil dikirim ke HP!")
        return {"status": "success", "answer": answer_text}
        
    except Exception as e:
        print(f"🔥 ERROR DETAIL: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Gagal memproses request: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000)