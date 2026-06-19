import streamlit as st
import requests
import pandas as pd
import time
import firebase_admin
from firebase_admin import credentials, firestore
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# --- INISIALISASI FIREBASE ---
@st.cache_resource
def init_firebase():
    try:
        if not firebase_admin._apps:
            cred = credentials.Certificate("firebase_key.json")
            firebase_admin.initialize_app(cred)
        return firestore.client()
    except Exception as e:
        st.error(f"❌ Gagal menyambungkan Firebase: {e}")
        return None

db = init_firebase()

# Konfigurasi Tampilan
st.set_page_config(page_title="IDX Data Ingestion System", page_icon="💾", layout="wide")

# --- CUSTOM CSS UNTUK EFEK TERMINAL STREAMING ---
st.markdown("""
<style>
    .terminal-box {
        font-family: 'Courier New', Courier, monospace;
        background-color: #0D1117;
        color: #00FF41;
        padding: 18px;
        border-radius: 8px;
        height: 320px;
        overflow-y: auto;
        border: 1px solid #30363D;
        line-height: 1.5;
        box-shadow: inset 0 0 10px rgba(0,0,0,0.8);
        margin-top: 10px;
        margin-bottom: 20px;
    }
    .db-header { color: #FFFFFF; font-weight: bold; margin-bottom: 5px; }
</style>
""", unsafe_allow_html=True)

# --- SETUP CONNECTION POOLING (YANG BENAR) ---
def create_session():
    session = requests.Session()
    retries = Retry(total=3, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
    adapter = HTTPAdapter(max_retries=retries, pool_connections=10, pool_maxsize=10)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session

api_session = create_session()
BASE_URL = "http://127.0.0.1:8000"

# --- FUNGSI TARIK NAMA EMITEN REAL-TIME ---
@st.cache_data
def get_daftar_emiten():
    url = "https://www.idx.co.id/primary/ListedCompany/GetCompanyProfiles?emitenType=s&start=0&length=9999"
    headers = {"User-Agent": "Mozilla/5.0", "Referer": "https://www.idx.co.id/"}
    try:
        # Ini aman pakai requests biasa karena cuma nembak 1x ke IDX langsung
        res = requests.get(url, headers=headers, timeout=5)
        if res.status_code == 200:
            return sorted([f"{d['EmitenCode']} - {d['EmitenName']}" for d in res.json().get('data', [])])
    except: pass
    return ["BBCA - Bank Central Asia", "BBRI - Bank Rakyat Indonesia", "BMRI - Bank Mandiri", "BBNI - Bank Negara Indonesia"]

def tarik_data_api(emiten, tahun, periode):
    try:
        # PERBAIKAN: Gunakan api_session.get, BUKAN requests.get
        res = api_session.get(f"{BASE_URL}/api/v1/laporan/{emiten}/{tahun}/{periode}", timeout=120)
        if res.status_code == 200: 
            return res.json()
    except Exception as e: 
        print(f"Error injeksi: {e}")
        return None
    return None

# --- UI MAIN ---
st.title("🤖 Robot Admin: Ingestion Engine")
st.markdown("<span style='color:#8A92B2;'>Modul Pengeruk & Sinkronisasi Fundamental Emiten ke Firebase</span>", unsafe_allow_html=True)
st.divider()

# Layout Kolom Parameter Input
col_param1, col_param2, col_param3 = st.columns([2, 1, 1])

with col_param1:
    daftar_emiten = get_daftar_emiten()
    emiten_massal = st.multiselect(
        "🎯 Pilih Target Kode Emiten (Bisa Banyak Sekaligus)", 
        daftar_emiten,
        default=[e for e in daftar_emiten if "BBCA" in e or "BBRI" in e] if any("BBCA" in e for e in daftar_emiten) else None
    )

with col_param2:
    tahun_input = st.text_input("📆 Tahun Laporan", value="2023", max_chars=4)

with col_param3:
    periode_box = st.selectbox("📊 Periode Laporan", ["Audit (Tahunan)", "Q1", "Q2", "Q3"])
    map_periode = {"Audit (Tahunan)": "audit", "Q1": "q1", "Q2": "q2", "Q3": "q3"}
    periode_api = map_periode[periode_box]

st.markdown("---")

# Tombol Eksekusi
tombol_injeksi = st.button("🚀 MULAI SINKRONISASI MASSAL", use_container_width=True)

if tombol_injeksi:
    if db is None:
        st.error("❌ Firebase SDK gagal inisialisasi. Periksa file `firebase_key.json` lu!")
    elif not emiten_massal:
        st.warning("⚠️ Silakan pilih minimal 1 emiten target untuk diproses!")
    elif not tahun_input.isdigit() or len(tahun_input) != 4:
        st.warning("⚠️ Format kode tahun salah!")
    else:
        st.markdown("<div class='db-header'>📡 Live Streaming Ingestion Logs:</div>", unsafe_allow_html=True)
        
        progress_bar = st.progress(0)
        log_terminal = st.empty()
        
        riwayat_log = []
        data_sukses_injeksi = []
        
        def update_terminal():
            html_content = "<div class='terminal-box'>" + "<br>".join(riwayat_log) + "</div>"
            log_terminal.markdown(html_content, unsafe_allow_html=True)

        for idx, emiten_full in enumerate(emiten_massal):
            ticker = emiten_full.split(" - ")[0]
            nama_perusahaan = emiten_full.split(" - ")[1]
            
            riwayat_log.append(f"[{time.strftime('%H:%M:%S')}] ⏳ Memanggil API Gitect untuk emiten: {ticker}...")
            update_terminal()
            
            res_api = tarik_data_api(ticker, tahun_input, periode_api)
            
            if res_api and res_api.get("hasil", {}).get("status") == "sukses":
                keuangan_data = res_api["hasil"]["data"]
                metode = res_api["hasil"].get("metode_ekstraksi", "Unknown")
                
                riwayat_log[-1] = f"[{time.strftime('%H:%M:%S')}] ✅ Ekstraksi {ticker} SUKSES (via {metode}). Memulai transfer ke Firebase..."
                update_terminal()
                
                doc_id = f"{ticker}_{tahun_input}_{periode_api}"
                
                # PERBAIKAN: Menggunakan .get() agar aman dari KeyError jika data bolong
                payload = {
                    "kode_emiten": ticker,
                    "nama_emiten": nama_perusahaan,
                    "tahun": int(tahun_input),
                    "periode": periode_api,
                    "total_aset": keuangan_data.get("Total_Aset", 0),
                    "laba_bersih": keuangan_data.get("Laba_Rugi_Bersih", 0),
                    "pendapatan": keuangan_data.get("Pendapatan", 0),
                    "metode_ekstraksi": metode,
                    "sinkronisasi_timestamp": firestore.SERVER_TIMESTAMP
                }
                
                try:
                    time.sleep(0.8)
                    db.collection("fundamental_emiten").document(doc_id).set(payload)
                    riwayat_log.append(f"[{time.strftime('%H:%M:%S')}] 💾 SUCCESS: Dokumen `{doc_id}` aman tersimpan di Firestore Cloud!")
                    
                    data_sukses_injeksi.append({
                        "Emiten": ticker, "Tahun": tahun_input, "Periode": periode_box,
                        "Aset": payload["total_aset"], "Laba": payload["laba_bersih"], "Status": "Saved"
                    })
                except Exception as ex:
                    riwayat_log.append(f"[{time.strftime('%H:%M:%S')}] ❌ ERROR FIREBASE pada emiten {ticker}: {ex}")
            else:
                pesan_err = res_api.get("hasil", {}).get("pesan", "Data tidak ditemukan di server IDX.") if res_api else "Gagal koneksi API/Timeout."
                riwayat_log[-1] = f"[{time.strftime('%H:%M:%S')}] ❌ Ekstraksi {ticker} GAGAL: {pesan_err}"
            
            update_terminal()
            progress_bar.progress((idx + 1) / len(emiten_massal))
            
        st.success(f"🎉 Pipeline Selesai! Berhasil memproses {len(data_sukses_injeksi)} emiten ke Firebase.")
        
        if data_sukses_injeksi:
            st.markdown("### 🗄️ Ringkasan Data Yang Berhasil Tersimpan")
            st.dataframe(pd.DataFrame(data_sukses_injeksi), use_container_width=True)
            st.balloons()