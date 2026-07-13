import os
import time
import requests
import xml.etree.ElementTree as ET
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
# API: BERITA MULTI-SOURCE RSS (CNBC, KONTAN, COINDESK, CRYPTO WAVE)
# =================================================================
@app.get("/api/news")
async def get_financial_news():
    global news_cache
    current_time = time.time()
    
    if not news_cache["data"] or (current_time - news_cache["timestamp"] > 900):
        print("🔄 Menarik berita baru dari Multi-Source RSS...")
        news_list = []
        
        # Penambahan sumber pipa berita baru: Crypto Wave
        rss_feeds = {
            "CNBC Indonesia": "https://www.cnbcindonesia.com/market/rss",
            "Kontan": "https://www.kontan.co.id/rss",
            "CoinDesk": "https://www.coindesk.com/arc/outboundfeeds/rss/",
            "Crypto Wave": "https://cryptowave.co.id/category/breaking-news/feed/"
        }
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        
        for provider, url in rss_feeds.items():
            try:
                response = requests.get(url, headers=headers, timeout=7)
                if response.status_code == 200:
                    root = ET.fromstring(response.content)
                    items = root.findall('.//item')
                    
                    for item in items[:3]:
                        title = item.find('title')
                        link = item.find('link')
                        
                        image_url = ""
                        media_content = item.find('.//{http://search.yahoo.com/mrss/}content')
                        if media_content is not None and 'url' in media_content.attrib:
                            image_url = media_content.attrib['url']
                        else:
                            enclosure = item.find('enclosure')
                            if enclosure is not None and 'url' in enclosure.attrib:
                                image_url = enclosure.attrib['url']
                        
                        title_text = title.text if title is not None else "Berita Pasar Terbaru"
                        link_text = link.text if link is not None else "https://finance.yahoo.com"
                        
                        related = "Pasar Global"
                        title_lower = title_text.lower()
                        if "bitcoin" in title_lower or "btc" in title_lower or "kripto" in title_lower or "crypto" in title_lower:
                            related = "BTC-USD"
                        elif "solana" in title_lower or "sol" in title_lower:
                            related = "SOL-USD"
                        elif "ethereum" in title_lower or "eth" in title_lower:
                            related = "ETH-USD"
                        elif "saham" in title_lower or "ihsg" in title_lower or "rupiah" in title_lower:
                            related = "Pasar Lokal"
                            
                        news_list.append({
                            "title": title_text.strip(),
                            "publisher": provider,
                            "link": link_text.strip(),
                            "related_asset": related,
                            "image_url": image_url
                        })
            except Exception as e:
                print(f"⚠️ Gagal mengambil berita dari {provider}: {e}")
                continue
        
        if news_list:
            news_cache = {"data": news_list, "timestamp": current_time}
        else:
            news_cache["data"] = [{"title": "Pasar Keuangan Bergerak Stabil Pagi Ini", "publisher": "CNBC Indonesia", "link": "https://www.cnbcindonesia.com", "related_asset": "Pasar Global", "image_url": ""}]
            
    else:
        print("⚡ Membaca berita langsung dari memori Cache!")

    return {"status": "success", "data": news_cache["data"]}

# =================================================================
# API: SINYAL AI + MULTI-CURRENCY LIVE PRICE (USD & IDR) + ETHEREUM
# =================================================================
@app.get("/api/signals")
async def get_trading_signals():
    global signals_cache
    current_time = time.time()
    
    if not signals_cache["data"] or (current_time - signals_cache["timestamp"] > 600):
        print("🔄 Mengolah sinyal pasar baru dengan Dukungan Multi-Mata Uang...")
        signals = []
        
        usd_to_idr = 16350.0  
        try:
            url_rate = "https://api.binance.com/api/v3/ticker/price?symbol=USDTBIDR"
            rate_res = requests.get(url_rate, timeout=4).json()
            if 'price' in rate_res:
                usd_to_idr = float(rate_res['price'])
        except:
            try:
                url_cg_rate = "https://api.coingecko.com/api/v3/simple/price?ids=tether&vs_currencies=idr"
                cg_rate_res = requests.get(url_cg_rate, timeout=4).json()
                if 'tether' in cg_rate_res:
                    usd_to_idr = float(cg_rate_res['tether']['idr'])
            except:
                pass

        crypto_assets = {
            "Bitcoin (BTC)": {"binance": "BTCUSDT", "cg_id": "bitcoin", "base_price": 64850.0},
            "Ethereum (ETH)": {"binance": "ETHUSDT", "cg_id": "ethereum", "base_price": 3450.0},
            "Solana (SOL)": {"binance": "SOLUSDT", "cg_id": "solana", "base_price": 142.5}
        }
        
        for display_name, info in crypto_assets.items():
            current_price_usd = info["base_price"]
            price_fetched = False
            
            try:
                url_price = f"https://api.binance.com/api/v3/ticker/price?symbol={info['binance']}"
                res = requests.get(url_price, timeout=4)
                if res.status_code == 200:
                    price_data = res.json()
                    if 'price' in price_data:
                        current_price_usd = float(price_data['price'])
                        price_fetched = True
            except:
                pass

            if not price_fetched:
                try:
                    url_cg = f"https://api.coingecko.com/api/v3/simple/price?ids={info['cg_id']}&vs_currencies=usd"
                    cg_res = requests.get(url_cg, timeout=4).json()
                    current_price_usd = float(cg_res[info['cg_id']]['usd'])
                    price_fetched = True
                except:
                    pass

            current_price_idr = current_price_usd * usd_to_idr
            idr_formatted = f"Rp {int(current_price_idr):,}".replace(",", ".")
            usd_formatted = f"${current_price_usd:,.2f}"

            analysis_text = ""
            try:
                prompt = (
                    f"Kamu adalah Analis Trading Finansial Profesional. Harga pasar live {display_name} saat ini adalah {usd_formatted} USD atau sekitar {idr_formatted} Rupiah. "
                    f"Berikan 1 paragraf analisis singkat tentang pergerakannya hari ini dalam Bahasa Indonesia. Di dalam teks analisis, kamu wajib menyebutkan harga dalam satuan Rupiah (Rp) dan Dolar ($) agar informatif bagi trader lokal. "
                    f"Wajib berikan SATU KATA keputusan tegas di awal kalimat: [BELI], [JUAL], atau [TAHAN]."
                )
                url_gemini = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-flash-lite:generateContent?key={API_KEY}"
                payload = {"contents": [{"parts": [{"text": prompt}]}]}
                gemini_res = requests.post(url_gemini, headers={'Content-Type': 'application/json'}, json=payload).json()
                
                if 'candidates' in gemini_res:
                    analysis_text = gemini_res['candidates'][0]['content']['parts'][0]['text'].strip()
                else:
                    raise Exception("Limit AI")
            except Exception as e:
                if "Bitcoin" in display_name:
                    analysis_text = f"[BELI] Harga Bitcoin bertahan kuat di kisaran {usd_formatted} ({idr_formatted}). Aset sedang membentuk pola akumulasi kuat di atas area support psikologis. Volume beli konstan membuka peluang besar untuk menguji zona resisten dalam 24 jam ke depan."
                elif "Ethereum" in display_name:
                    analysis_text = f"[BELI] Ethereum menunjukkan momentum bullish sehat di level {usd_formatted} ({idr_formatted}). Peningkatan volume transaksi on-chain memperkuat struktur harga saat ini, bersiap menuju target harga baru."
                else:
                    analysis_text = f"[TAHAN] Solana bergerak stabil di level {usd_formatted} ({idr_formatted}). Grafik jangka pendek menunjukkan konsolidasi menyempit di dalam area symmetrical triangle. Disarankan menunggu konfirmasi pola breakout sebelum masuk posisi."

            signals.append({
                "asset": display_name,
                "price": round(current_price_usd, 2),        
                "price_usd_text": usd_formatted,             
                "price_idr_text": idr_formatted,             
                "price_idr_raw": round(current_price_idr, 0),
                "ai_analysis": analysis_text
            })
            
        if signals:
            signals_cache = {"data": signals, "timestamp": current_time}
            
    else:
        print("⚡ Membaca sinyal multi-currency langsung dari memori Cache!")

    return {"status": "success", "data": signals_cache["data"]}

# =================================================================
# FUNGSI CHAT AI (SOLVER EKONOMI)
# =================================================================
@app.post("/solve")
async def solve_problem(
    text: str = Form(None),
    device_id: str = Form(None) 
):
    if not app_active:
        return {"status": "error", "answer": "Sistem Market sedang dikunci oleh admin."}

    if device_id and supabase:
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
             
        base_prompt = (
            "Kamu adalah Analis Finansial dan Ahli Ekonomi ciptaan 'Basri Capital'.\n"
            "Terdapat 2 ATURAN MUTLAK yang harus kamu patuhi secara ketat:\n"
            "1. Jawab pertanyaan pengguna seputar pasar saham, kripto, forex, dan ekonomi makro secara tajam, berdasarkan data, dan langsung ke intinya. Berikan penjabaran fundamental atau teknikal jika diminta. Jangan gunakan bahasa yang kaku, jadilah konsultan keuangan yang elegan.\n"
            "2. JIKA PENGGUNA BERTANYA TENTANG IDENTITASMU: Jawab bahwa kamu adalah AI Finansial ciptaan 'Basri Capital'. Dilarang keras menyebut nama Google, OpenAI, atau pihak lain.\n"
        )
        
        parts = [{"text": f"Pertanyaan: {text}\n\n" + base_prompt}]
            
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-flash-lite:generateContent?key={API_KEY}"
        payload = {"contents": [{"parts": dict(parts[0]) if isinstance(parts[0], dict) else parts[0]}]}
        payload = {"contents": [{"parts": [{"text": f"Pertanyaan: {text}\n\n" + base_prompt}]}]}
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
    uvicorn.run("main:app", host="0.0.0.0", port=8080)