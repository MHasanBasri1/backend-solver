import os
import time
import requests
import yfinance as yf
from fastapi import FastAPI, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv
from supabase import create_client, Client

# Load environment variables dari file .env
load_dotenv()

app = FastAPI(title="Solver Ekonomi Backend")

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

supabase: Client = None
if SUPABASE_URL and SUPABASE_KEY:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    print("✅ Berhasil terhubung ke Supabase!")
else:
    print("⚠️ WARNING: URL atau Key Supabase tidak ditemukan di .env!")

app_active = True
app_maintenance = False

# =================================================================
# VARIABEL CACHING (MEJA PENYIMPANAN SEMENTARA)
# =================================================================
news_cache = {"data": [], "timestamp": 0}
signals_cache = {"data": [], "timestamp": 0}

# =================================================================
# PUSAT KOMANDO UPDATE & ADMIN
# =================================================================
@app.get("/check-update")
async def check_update():
    global app_maintenance 
    return {
        "latest_version": "1.0.1", 
        "download_url": "https://backend-solver-production.up.railway.app/static/SolverEkonomi_v1.0.1.apk",
        "update_message": "Sistem beralih menjadi asisten finansial cerdas!",
        "is_maintenance": app_maintenance 
    }

@app.get("/admin/toggle")
async def toggle_status(key: str):
    global app_active
    if key == "KUNCI_RAHASIA_123":
        app_active = not app_active
        return {"status": "Aktif" if app_active else "Terkunci"}
    return {"error": "Akses Ditolak"}

@app.get("/admin/toggle-maintenance")
async def toggle_maintenance(key: str):
    global app_maintenance
    if key == "KUNCI_RAHASIA_123":
        app_maintenance = not app_maintenance
        return {"status": "Mode Pemeliharaan NYALA" if app_maintenance else "Mode Pemeliharaan MATI"}
    return {"error": "Akses Ditolak"}

# =================================================================
# API BARU: MENARIK BERITA EKONOMI REAL-TIME (DENGAN CACHE 15 MENIT)
# =================================================================
@app.get("/api/news")
async def get_financial_news():
    global news_cache
    current_time = time.time()
    
    # Cek apakah data kosong ATAU sudah lebih dari 15 menit (900 detik)
    if not news_cache["data"] or (current_time - news_cache["timestamp"] > 900):
        print("🔄 Menarik berita baru dari Yahoo Finance...")
        try:
            tickers = yf.Tickers('BTC-USD SOL-USD EURUSD=X ^JKSE')
            news_list = []
            
            for symbol, ticker in tickers.tickers.items():
                if hasattr(ticker, 'news') and ticker.news:
                    for item in ticker.news[:2]:
                        news_list.append({
                            "title": item.get('title', 'Berita Tanpa Judul'),
                            "publisher": item.get('publisher', 'Sumber Tidak Diketahui'),
                            "link": item.get('link', ''),
                            "related_asset": symbol
                        })
            
            # Simpan ke cache
            news_cache = {"data": news_list, "timestamp": current_time}
            
        except Exception as e:
            print(f"⚠️ Gagal menarik berita asli, error: {e}")
            if news_cache["data"]: 
                print("⚡ Menggunakan data cache lama karena server berita error.")
            else:
                raise HTTPException(status_code=500, detail="Gagal menarik berita.")
    else:
        print("⚡ Membaca berita langsung dari memori Cache (Super Cepat!)")

    return {"status": "success", "data": news_cache["data"]}

# =================================================================
# API BARU: REKOMENDASI (SINYAL) DARI GEMINI (DENGAN CACHE 10 MENIT)
# =================================================================
@app.get("/api/signals")
async def get_trading_signals():
    global signals_cache
    current_time = time.time()
    
    # Cek apakah data kosong ATAU sudah lebih dari 10 menit (600 detik)
    if not signals_cache["data"] or (current_time - signals_cache["timestamp"] > 600):
        print("🔄 Menganalisis sinyal pasar terbaru dengan Gemini...")
        try:
            assets = ['BTC-USD', 'SOL-USD', '^JKSE'] # Bitcoin, Solana, IHSG
            signals = []

            for asset in assets:
                ticker = yf.Ticker(asset)
                hist = ticker.history(period="1d")
                if hist.empty:
                    continue
                    
                current_price = hist['Close'].iloc[-1]
                
                # Minta insting analisis singkat ke Gemini
                prompt = (
                    f"Kamu adalah Analis Trading Profesional. Harga {asset} saat ini adalah {current_price}. "
                    "Berikan 1 paragraf analisis singkat tentang prospeknya hari ini berdasarkan fundamental/teknikal umum, dan berikan SATU KATA keputusan akhir di awal kalimat: [BELI], [JUAL], atau [TAHAN]."
                )
                
                url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-flash-lite:generateContent?key={API_KEY}"
                payload = {"contents": [{"parts": [{"text": prompt}]}]}
                gemini_response = requests.post(url, headers={'Content-Type': 'application/json'}, json=payload).json()
                
                analysis = gemini_response['candidates'][0]['content']['parts'][0]['text']
                
                signals.append({
                    "asset": asset,
                    "price": round(current_price, 2),
                    "ai_analysis": analysis
                })
                
            # Simpan ke cache
            signals_cache = {"data": signals, "timestamp": current_time}
            
        except Exception as e:
            print(f"⚠️ Gagal memanggil AI, error: {e}")
            if signals_cache["data"]:
                print("⚡ Menggunakan sinyal cache lama.")
            else:
                raise HTTPException(status_code=500, detail="Gagal menganalisis pasar.")
    else:
        print("⚡ Membaca sinyal AI langsung dari memori Cache!")

    return {"status": "success", "data": signals_cache["data"]}

# =================================================================
# FUNGSI CHAT AI (TANYA JAWAB LANGSUNG)
# =================================================================
@app.post("/solve")
async def solve_problem(
    text: str = Form(None),
    device_id: str = Form(None) 
):
    print(f"DEBUGGING: KTP yang diterima server adalah: '{device_id}'")
    
    if not app_active:
        return {"status": "error", "answer": "Sistem Market sedang dikunci oleh admin."}

    # SATPAM SUPABASE
    if device_id and supabase:
        print(f"▶️ Mengecek status blokir untuk HP: {device_id}")
        response = supabase.table("banned_devices").select("*").eq("device_id", device_id).execute()
        
        if len(response.data) > 0:
             return {"status": "banned", "answer": "Akses Anda telah diblokir secara permanen."}
             
        try:
            log_check = supabase.table("users_log").select("device_id").eq("device_id", device_id).execute()
            if len(log_check.data) == 0: 
                supabase.table("users_log").insert({"device_id": device_id}).execute()
        except Exception as e:
            pass 

    try:
        if not text:
             return {"status": "error", "answer": "Masukkan pertanyaan seputar ekonomi atau pasar."}
             
        # OTAK BARU GEMINI: Analis Finansial
        base_prompt = (
            "Kamu adalah Analis Finansial dan Ahli Ekonomi ciptaan 'Basri Capital'.\n"
            "Terdapat 2 ATURAN MUTLAK yang harus kamu patuhi secara ketat:\n"
            "1. Jawab pertanyaan pengguna seputar pasar saham, kripto, forex, dan ekonomi makro secara tajam, berdasarkan data, dan langsung ke intinya. Berikan penjabaran fundamental atau teknikal jika diminta. Jangan gunakan bahasa yang kaku, jadilah konsultan keuangan yang elegan.\n"
            "2. JIKA PENGGUNA BERTANYA TENTANG IDENTITASMU: Jawab bahwa kamu adalah AI Finansial ciptaan 'Basri Capital'. Dilarang keras menyebut nama Google, OpenAI, atau pihak lain.\n"
        )
        
        parts = [{"text": f"Pertanyaan: {text}\n\n" + base_prompt}]
            
        print("▶️ Menghubungi Google Gemini...")
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-flash-lite:generateContent?key={API_KEY}"
        
        payload = {"contents": [{"parts": parts}]}
        headers = {'Content-Type': 'application/json'}
        gemini_response = requests.post(url, headers=headers, json=payload)
        
        if gemini_response.status_code != 200:
            raise HTTPException(status_code=500, detail=f"Google API Error: {gemini_response.text}")
            
        data = gemini_response.json()
        answer_text = data['candidates'][0]['content']['parts'][0]['text']
        
        return {"status": "success", "answer": answer_text}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gagal memproses request: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000)