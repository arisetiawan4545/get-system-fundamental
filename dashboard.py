import streamlit as st
import requests
import pandas as pd
import time
import firebase_admin
from firebase_admin import credentials, firestore
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import json

# =========================================================================
# 1. INISIALISASI DATABASE & KONFIGURASI HALAMAN
# =========================================================================
st.set_page_config(page_title="GET SYSTEM FUNDAMENTAL", page_icon="📊", layout="wide")

# --- INISIALISASI FIREBASE (VERSI LOKAL STABIL) ---
@st.cache_resource
def init_firebase():
    try:
        if not firebase_admin._apps:
            cred = credentials.Certificate("firebase_key.json")
            firebase_admin.initialize_app(cred)
        return firestore.client()
    except Exception as e:
        st.sidebar.error(f"⚠️ Gagal hubungkan ke Firebase: {e}")
        return None

db = init_firebase()

# =========================================================================
# 2. TEMA UI/UX: HACKER NEON GREEN (PROFESSIONAL DARK MODE)
# =========================================================================
st.markdown("""
<style>
    [data-testid="stAppViewContainer"] { 
        background-color: #050505; 
    }
    [data-testid="stSidebar"] { 
        background-color: #0a0a0a; 
        border-right: 1px solid #00FF41; 
    }
    h1, h2, h3, h4, h5, h6, p, span, div, label { 
        color: #E0E0E0 !important; 
    }
    
    .premium-card {
        background-color: #000000; 
        border-radius: 8px; 
        padding: 20px; 
        margin-bottom: 20px;
        border-left: 5px solid #00FF41; 
        border-top: 1px solid #1a1a1a;
        border-right: 1px solid #1a1a1a; 
        border-bottom: 1px solid #1a1a1a;
        box-shadow: 0 4px 15px rgba(0, 255, 65, 0.1);
        transition: transform 0.2s ease-in-out, box-shadow 0.2s; 
        min-height: 170px; 
        display: flex; 
        flex-direction: column; 
        justify-content: space-between;
    }
    .premium-card:hover { 
        transform: translateY(-5px); 
        box-shadow: 0 8px 25px rgba(0, 255, 65, 0.3); 
    }
    .card-title { 
        color: #00FF41 !important; 
        font-size: 13px; 
        font-weight: 600; 
        text-transform: uppercase; 
        letter-spacing: 1.5px; 
        margin-bottom: 8px; 
    }
    .card-value { 
        color: #FFFFFF !important; 
        font-size: 30px; 
        font-weight: bold; 
        margin-bottom: 4px; 
        line-height: 1.2; 
    }
    .card-exact { 
        color: #000000 !important; 
        font-size: 13px; 
        font-family: 'Courier New', Courier, monospace; 
        background-color: #00FF41; 
        padding: 4px 8px; 
        border-radius: 4px; 
        display: inline-block; 
        font-weight: bold; 
    }
    
    .quarter-box {
        background-color: #000000; 
        padding: 15px; 
        border-radius: 8px; 
        text-align: center;
        border-bottom: 3px solid #00FF41; 
        border-top: 1px solid #1a1a1a;
        border-left: 1px solid #1a1a1a; 
        border-right: 1px solid #1a1a1a;
    }
    .q-title { color: #00FF41 !important; font-size: 16px; font-weight: bold; margin-bottom: 10px;}
    .q-val { color: #FFF !important; font-size: 18px; font-weight: bold;}
    .q-label { color: #888888 !important; font-size: 12px;}
    
    .terminal-box { 
        font-family: 'Courier New', monospace; 
        background-color: #000000; 
        color: #00FF41 !important; 
        padding: 15px; 
        border-radius: 8px; 
        height: 300px; 
        overflow-y: auto; 
        border: 1px solid #00FF41; 
        margin-top: 10px; 
        box-shadow: inset 0 0 10px rgba(0, 255, 65, 0.1);
    }
    .db-header { color: #00FF41 !important; font-weight: bold; margin-bottom: 5px; }
    hr { border-color: #00FF41 !important; opacity: 0.3; }
</style>
""", unsafe_allow_html=True)

# =========================================================================
# 3. UTILITIES & API ENGINE (OPTIMAL & PRO VERSION)
# =========================================================================
def create_session():
    session = requests.Session()
    retries = Retry(total=3, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
    adapter = HTTPAdapter(max_retries=retries, pool_connections=10, pool_maxsize=10)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session

api_session = create_session()
BASE_URL = "http://127.0.0.1:8000"

def format_singkat(angka):
    if angka == 0: return "Rp 0"
    elif abs(angka) >= 1_000_000_000_000: return f"Rp {angka / 1_000_000_000_000:.2f} Triliun"
    elif abs(angka) >= 1_000_000_000: return f"Rp {angka / 1_000_000_000:.2f} Miliar"
    elif abs(angka) >= 1_000_000: return f"Rp {angka / 1_000_000:.2f} Juta"
    else: return f"Rp {angka:,.0f}".replace(",", ".")

def format_full(angka):
    return f"Rp {angka:,.0f}".replace(",", ".")

@st.cache_data
def get_daftar_emiten():
    try:
        with open("emiten.txt", "r", encoding="utf-8") as file:
            return sorted([line.strip() for line in file if line.strip()])
    except FileNotFoundError:
        return ["BBCA - Bank Central Asia", "SYSTEM - File emiten.txt tidak ditemukan"]

@st.cache_data(ttl=3600, show_spinner=False)
def tarik_data_api(emiten, tahun, periode):
    url_api = f"{BASE_URL}/api/v1/laporan/{emiten}/{tahun}/{periode}"
    try:
        # Timeout disesuaikan ke 30 detik untuk server lokal (lebih responsif)
        res = api_session.get(url_api, timeout=30) 
        res.raise_for_status()
        return res.json()
    except requests.exceptions.RequestException as e:
        print(f"ERROR API ({emiten} {tahun} {periode}): {e}")
        return None

@st.cache_data(ttl=3600, show_spinner=False)
def tarik_data_rentang(emiten, t_awal, t_akhir, periode):
    url_api = f"{BASE_URL}/api/v1/rentang/{emiten}/{t_awal}/{t_akhir}/{periode}"
    try:
        # Timeout direvisi ke 60 detik untuk rentang multi-tahun
        res = api_session.get(url_api, timeout=60) 
        res.raise_for_status()
        return res.json()
    except requests.exceptions.RequestException as e:
        print(f"ERROR API Rentang ({emiten} {t_awal}-{t_akhir} {periode}): {e}")
        return None

daftar_emiten_lengkap = get_daftar_emiten()

# =========================================================================
# 4. MAIN DASHBOARD (HEADER & SIDEBAR)
# =========================================================================
try:
    st.image("icon.png", width=150)
except FileNotFoundError:
    pass

st.markdown("<h1 style='color: #00FF41;'>GET SYSTEM FUNDAMENTAL</h1>", unsafe_allow_html=True)

st.sidebar.markdown("<h3 style='color: #00FF41;'>🎛️ Main Control</h3>", unsafe_allow_html=True)
app_mode = st.sidebar.radio("Pilih Tampilan:", ["Lihat Fundamental", "Simpan Fundamental (Database)"], index=0)
st.sidebar.markdown("---")

# =========================================================================
# 5. MODE A: LIHAT FUNDAMENTAL (VIEWER)
# =========================================================================
if app_mode == "Lihat Fundamental":
    st.markdown("<span style='color:#00FF41;'>Sistem Ekstraksi Hybrid Auto-Pilot: XBRL & AI Vision</span>", unsafe_allow_html=True)
    st.divider()

    st.sidebar.markdown("<h4 style='color: #00FF41;'>Parameter Ekstraksi</h4>", unsafe_allow_html=True)
    idx_default = daftar_emiten_lengkap.index([e for e in daftar_emiten_lengkap if "BBCA" in e][0]) if any("BBCA" in e for e in daftar_emiten_lengkap) else 0
    emiten_terpilih_raw = st.sidebar.selectbox("Pilih / Cari Kode Emiten", daftar_emiten_lengkap, index=idx_default)
    emiten_input = emiten_terpilih_raw.split(" - ")[0]

    mode_ekstraksi = st.sidebar.radio("Pilih Mode Analisis:", ["Detail 1 Tahun (Q1-Q4)", "Tren Historis (Multi-Tahun)"])

    if mode_ekstraksi == "Detail 1 Tahun (Q1-Q4)":
        st.sidebar.markdown("---")
        tahun_pilihan = st.sidebar.text_input("Tahun Laporan", value="2023", max_chars=4)
        periode_pilihan = st.sidebar.selectbox("Periode", ["Audit (Tahunan)", "Q1", "Q2", "Q3"])
        
        map_periode = {"Audit (Tahunan)": "audit", "Q1": "q1", "Q2": "q2", "Q3": "q3"}
        periode_api = map_periode[periode_pilihan]
        tombol_tarik = st.sidebar.button("Lihat Fundamental", use_container_width=True)

        if tombol_tarik and emiten_input and tahun_pilihan.isdigit():
            data_utama = data_q1 = data_q2 = data_q3 = None
            
            if periode_api == "audit":
                st.info(f"🔄 Menjalankan Pipeline Lengkap untuk {emiten_input} tahun {tahun_pilihan}...")
                
                # SLEEP DIHAPUS SEMUA DI SINI BIAR KILAT
                with st.spinner("Memuat Laporan Tahunan..."):
                    data_utama = tarik_data_api(emiten_input, tahun_pilihan, "audit")
                with st.spinner("Memuat Laporan Q1..."):
                    data_q1 = tarik_data_api(emiten_input, tahun_pilihan, "q1")
                with st.spinner("Memuat Laporan Q2..."):
                    data_q2 = tarik_data_api(emiten_input, tahun_pilihan, "q2")
                with st.spinner("Memuat Laporan Q3..."):
                    data_q3 = tarik_data_api(emiten_input, tahun_pilihan, "q3")
            else:
                with st.spinner(f"Memproses {emiten_input} ({periode_pilihan} {tahun_pilihan})..."):
                    data_utama = tarik_data_api(emiten_input, tahun_pilihan, periode_api)

            # --- RENDER UI HASIL KARTU & KUARTAL ---
            if data_utama and data_utama.get("hasil", {}).get("status") == "sukses":
                hasil = data_utama["hasil"]
                st.success(f"✅ Data {emiten_input} berhasil diamankan! (Engine: {hasil.get('metode_ekstraksi')})")
                
                # PENCEGAHAN ERROR DATA KOSONG
                k = hasil.get("data", {}) 
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.markdown(f"""
                    <div class="premium-card">
                        <div>
                            <div class="card-title">🏦 Total Aset</div>
                            <div class="card-value">{format_singkat(k.get("Total_Aset", 0))}</div>
                        </div>
                        <div class="card-exact">{format_full(k.get("Total_Aset", 0))}</div>
                    </div>
                    """, unsafe_allow_html=True)
                with col2:
                    st.markdown(f"""
                    <div class="premium-card">
                        <div>
                            <div class="card-title">📈 Laba/Rugi Bersih</div>
                            <div class="card-value">{format_singkat(k.get("Laba_Rugi_Bersih", 0))}</div>
                        </div>
                        <div class="card-exact">{format_full(k.get("Laba_Rugi_Bersih", 0))}</div>
                    </div>
                    """, unsafe_allow_html=True)
                with col3:
                    st.markdown(f"""
                    <div class="premium-card">
                        <div>
                            <div class="card-title">💰 Pendapatan</div>
                            <div class="card-value">{format_singkat(k.get("Pendapatan", 0))}</div>
                        </div>
                        <div class="card-exact">{format_full(k.get("Pendapatan", 0))}</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                if periode_api == "audit":
                    st.markdown("<br><h4 style='color: #00FF41;'>Riwayat Kinerja Kuartal (YTD)</h4>", unsafe_allow_html=True)
                    q_cols = st.columns(3)
                    
                    def render_q_box(data_q, title):
                        if data_q and data_q.get("hasil", {}).get("status") == "sukses":
                            # PENCEGAHAN ERROR DATA KOSONG
                            dt = data_q.get("hasil", {}).get("data", {})
                            return f"""
                            <div class="quarter-box">
                                <div class="q-title">{title}</div>
                                <div class="q-label">Total Aset</div>
                                <div class="q-val" style="color: #00FF41;">{format_singkat(dt.get('Total_Aset', 0))}</div>
                                <div style="margin: 8px 0;"></div>
                                <div class="q-label">Laba Bersih</div>
                                <div class="q-val" style="color: #00FF41;">{format_singkat(dt.get('Laba_Rugi_Bersih', 0))}</div>
                                <div class="q-label" style="margin-top:5px; font-size:10px; color:#555;">Engine: {data_q['hasil'].get('metode_ekstraksi')}</div>
                            </div>
                            """
                        else:
                            return f"""
                            <div class="quarter-box" style="border-bottom-color: #333;">
                                <div class="q-title" style="color: #666 !important;">{title}</div>
                                <div class="q-label" style="color:#666 !important;">Gagal Ditarik / Belum Rilis</div>
                            </div>
                            """
                    with q_cols[0]: st.markdown(render_q_box(data_q1, "Q1 (Maret)"), unsafe_allow_html=True)
                    with q_cols[1]: st.markdown(render_q_box(data_q2, "Q2 (Juni)"), unsafe_allow_html=True)
                    with q_cols[2]: st.markdown(render_q_box(data_q3, "Q3 (September)"), unsafe_allow_html=True)

                    # =====================================================================
                    # 🔥 PANEL SUMBER DATA & LOG MENTAH (VERSI KLIKABEL)
                    # =====================================================================
                    st.markdown("<br>", unsafe_allow_html=True)
                    with st.expander("📄 Panel Sumber Data & Log Mentah (Audit & Kuartal)"):
                        st.markdown("Fitur inspeksi untuk melihat apakah data berasal dari format asli **XBRL IDX** atau AI Gemini, beserta akses ke dokumen aslinya.")
                        
                        def render_link_sumber(data_json):
                            if not data_json or data_json.get("hasil", {}).get("status") != "sukses":
                                return "`Data Tidak Ditemukan / Kosong`"
                            
                            hasil_data = data_json["hasil"]
                            metode = hasil_data.get("metode_ekstraksi", "Unknown")
                            url_dokumen = hasil_data.get("link_dokumen", "") 
                            nama_dokumen = hasil_data.get("nama_dokumen", metode) 
                            
                            if url_dokumen:
                                return f"<a href='{url_dokumen}' target='_blank' style='color: #00FF41; text-decoration: none; border-bottom: 1px dashed #00FF41;'>🔗 {nama_dokumen}</a>"
                            else:
                                return f"`{nama_dokumen}`"

                        st.markdown(f"**1. Audit Tahunan:** {render_link_sumber(data_utama)}", unsafe_allow_html=True)
                        
                        if periode_api == "audit":
                            for idx, q_data in enumerate([data_q1, data_q2, data_q3]):
                                label = f"Q{idx+1}"
                                st.markdown(f"**{idx+2}. Kuartal {label}:** {render_link_sumber(q_data)}", unsafe_allow_html=True)
                        
                        st.markdown("---")
                        st.markdown("**Respon JSON Mentah (Tahunan):**")
                        st.json(data_utama)
                        
            else:
                st.error(f"⚠️ Gagal memproses data utama {emiten_input}. Periksa log atau koneksi backend API-mu.")

    elif mode_ekstraksi == "Tren Historis (Multi-Tahun)":
        st.sidebar.markdown("---")
        col_a, col_b = st.sidebar.columns(2)
        with col_a: tahun_awal = st.text_input("Tahun Awal", value="2021", max_chars=4)
        with col_b: tahun_akhir = st.text_input("Tahun Akhir", value="2023", max_chars=4)
        periode_pilihan = st.sidebar.selectbox("Periode", ["Audit (Tahunan)", "Q1", "Q2", "Q3"])
        map_periode = {"Audit (Tahunan)": "audit", "Q1": "q1", "Q2": "q2", "Q3": "q3"}
        periode_api = map_periode[periode_pilihan]
        
        tombol_rentang = st.sidebar.button("Lihat Fundamental", use_container_width=True)
        
        if tombol_rentang and emiten_input and tahun_awal.isdigit() and tahun_akhir.isdigit():
            if periode_api == "audit":
                st.info(f"🔄 Mode Super Lengkap: Menarik rentang dari {tahun_awal} hingga {tahun_akhir}...")
                
                # SLEEP DIHAPUS DI SINI JUGA
                with st.spinner("Membedah data Tahunan..."):
                    data_audit = tarik_data_rentang(emiten_input, tahun_awal, tahun_akhir, "audit")
                with st.spinner("Membedah data Q1..."):
                    data_q1 = tarik_data_rentang(emiten_input, tahun_awal, tahun_akhir, "q1")
                with st.spinner("Membedah data Q2..."):
                    data_q2 = tarik_data_rentang(emiten_input, tahun_awal, tahun_akhir, "q2")
                with st.spinner("Membedah data Q3..."):
                    data_q3 = tarik_data_rentang(emiten_input, tahun_awal, tahun_akhir, "q3")
                    
                data_tahunan = []
                data_kuartal = []
                
                if data_audit and data_audit.get("status") == "sukses":
                    for item in data_audit.get("data_historis", []):
                        if item.get("status") == "sukses":
                            # PENCEGAHAN ERROR DATA KOSONG (.get("data", {}))
                            data_tahunan.append({
                                "Tahun": item["tahun"], 
                                "Aset (Rp)": item.get("data", {}).get("Total_Aset", 0),
                                "Laba Bersih (Rp)": item.get("data", {}).get("Laba_Rugi_Bersih", 0), 
                                "Pendapatan (Rp)": item.get("data", {}).get("Pendapatan", 0),
                                "Metode (Engine)": item.get("metode_ekstraksi", "Unknown")
                            })
                
                def kumpulkan_kuartal(data_massal, label):
                    if data_massal and data_massal.get("status") == "sukses":
                        for item in data_massal.get("data_historis", []):
                            if item.get("status") == "sukses":
                                order = 1 if label == "Q1" else 2 if label == "Q2" else 3
                                sort_key = int(item["tahun"]) + (order * 0.1)
                                # PENCEGAHAN ERROR DATA KOSONG
                                data_kuartal.append({
                                    "Sort": sort_key, 
                                    "Kuartal": f"{item['tahun']} - {label}", 
                                    "Aset (Rp)": item.get("data", {}).get("Total_Aset", 0),
                                    "Laba Bersih (Rp)": item.get("data", {}).get("Laba_Rugi_Bersih", 0), 
                                    "Pendapatan (Rp)": item.get("data", {}).get("Pendapatan", 0),
                                    "Metode (Engine)": item.get("metode_ekstraksi", "Unknown")
                                })

                kumpulkan_kuartal(data_q1, "Q1")
                kumpulkan_kuartal(data_q2, "Q2")
                kumpulkan_kuartal(data_q3, "Q3")
                
                st.success("✅ Proses Tarik Massal Selesai!")
                
                if data_tahunan:
                    df_tahun = pd.DataFrame(data_tahunan).set_index("Tahun")
                    st.markdown("<hr><h2 style='color: #00FF41;'>🏢 Kinerja Tahunan (Audit)</h2>", unsafe_allow_html=True)
                    st.line_chart(df_tahun[["Aset (Rp)", "Laba Bersih (Rp)", "Pendapatan (Rp)"]], height=350, use_container_width=True)
                    st.dataframe(df_tahun.style.format({"Aset (Rp)": "{:,.0f}", "Laba Bersih (Rp)": "{:,.0f}", "Pendapatan (Rp)": "{:,.0f}"}), use_container_width=True)
                    
                if data_kuartal:
                    df_q = pd.DataFrame(data_kuartal).sort_values(by="Sort").reset_index(drop=True)
                    df_q_chart = df_q.set_index("Kuartal")[["Aset (Rp)", "Laba Bersih (Rp)", "Pendapatan (Rp)"]]
                    st.markdown("<hr><h2 style='color: #00FF41;'>📅 Kinerja Kuartalan (Q1 - Q3)</h2>", unsafe_allow_html=True)
                    st.line_chart(df_q_chart, height=350, use_container_width=True)
                    st.dataframe(df_q.drop(columns=["Sort"]).set_index("Kuartal").style.format({"Aset (Rp)": "{:,.0f}", "Laba Bersih (Rp)": "{:,.0f}", "Pendapatan (Rp)": "{:,.0f}"}), use_container_width=True)
            else:
                with st.spinner(f"Membedah data {emiten_input} khusus {periode_pilihan} dari {tahun_awal} sampai {tahun_akhir}..."):
                    data_spesifik = tarik_data_rentang(emiten_input, tahun_awal, tahun_akhir, periode_api)
                
                if data_spesifik and data_spesifik.get("status") == "sukses":
                    data_grafik = []
                    for i in data_spesifik.get("data_historis", []):
                        if i.get("status") == "sukses":
                            # PENCEGAHAN ERROR DATA KOSONG
                            data_grafik.append({
                                "Tahun": i["tahun"], 
                                "Aset (Rp)": i.get("data", {}).get("Total_Aset", 0), 
                                "Laba Bersih (Rp)": i.get("data", {}).get("Laba_Rugi_Bersih", 0), 
                                "Pendapatan (Rp)": i.get("data", {}).get("Pendapatan", 0), 
                                "Metode (Engine)": i.get("metode_ekstraksi", "Unknown")
                            })
                    
                    if data_grafik:
                        st.success("✅ Berhasil menarik data!")
                        df = pd.DataFrame(data_grafik).set_index("Tahun")
                        st.markdown(f"<h3 style='color: #00FF41;'>📈 Grafik Tren {periode_pilihan}</h3>", unsafe_allow_html=True)
                        st.line_chart(df[["Aset (Rp)", "Laba Bersih (Rp)", "Pendapatan (Rp)"]], height=400, use_container_width=True)
                        st.dataframe(df.style.format({"Aset (Rp)": "{:,.0f}", "Laba Bersih (Rp)": "{:,.0f}", "Pendapatan (Rp)": "{:,.0f}"}), use_container_width=True)
                    else:
                        st.error("⚠️ Data ditemukan tapi kosong. Mungkin AI Limit / Terblokir.")
                else:
                    st.error("⚠️ Gagal mengekstrak massal. Periksa koneksi API lokalmu.")

# =========================================================================
# 6. MODE B: SIMPAN FUNDAMENTAL (SYNC DATABASE)
# =========================================================================
else:
    st.markdown("<span style='color:#00FF41;'>Mode Injeksi Cerdas ke Firebase - Mengisi Data yang Kosong Saja</span>", unsafe_allow_html=True)
    st.divider()

    st.sidebar.markdown("<h4 style='color: #00FF41;'>⚙️ Konfigurasi Database</h4>", unsafe_allow_html=True)
    emiten_massal = st.sidebar.multiselect("Pilih Target Emiten", daftar_emiten_lengkap, default=[e for e in daftar_emiten_lengkap if "BBCA" in e or "BBRI" in e])
    
    col_ta, col_tb = st.sidebar.columns(2)
    with col_ta: tahun_mulai = st.text_input("Dari Tahun", value="2022", max_chars=4)
    with col_tb: tahun_sampai = st.text_input("Sampai Tahun", value="2023", max_chars=4)
    
    if emiten_massal and tahun_mulai.isdigit() and tahun_sampai.isdigit():
        if db is None:
            st.error("❌ Firebase belum terhubung! Pastikan file `firebase_key.json` ada di folder aplikasimu.")
        else:
            st.markdown("<h3 style='color: #E0E0E0;'>🗂️ Status Kelengkapan Database Saat Ini</h3>", unsafe_allow_html=True)
            
            target_dokumen = []
            for e in emiten_massal:
                ticker = e.split(" - ")[0]
                for y in range(int(tahun_mulai), int(tahun_sampai) + 1):
                    for p in ["audit", "q1", "q2", "q3"]:
                        target_dokumen.append({"doc_id": f"{ticker}_{y}_{p}", "Emiten": ticker, "Tahun": str(y), "Periode": p.upper(), "Status": "Belum Dicek"})
            
            data_missing = []
            status_table = []
            
            for item in target_dokumen:
                doc_ref = db.collection("fundamental_emiten").document(item["doc_id"])
                if doc_ref.get().exists:
                    item["Status"] = "✅ Sudah Tersimpan"
                else:
                    item["Status"] = "❌ Kosong (Perlu Download)"
                    data_missing.append(item)
                status_table.append(item)
                
            df_status = pd.DataFrame(status_table).drop(columns=["doc_id"])
            st.dataframe(df_status, use_container_width=True)
            
            if len(data_missing) == 0:
                st.success("🎉 Luar biasa! Semua data sudah lengkap di Database. Tidak ada yang perlu di-download lagi.")
            else:
                st.warning(f"⚠️ Ditemukan {len(data_missing)} data yang kosong. Siap disedot...")
                
                if st.button("🚀 Ekstrak & Simpan Data yang Kosong", use_container_width=True, type="primary"):
                    st.markdown("<div class='db-header'>📡 Live Streaming Sinkronisasi:</div>", unsafe_allow_html=True)
                    progress_bar = st.progress(0)
                    log_terminal = st.empty()
                    riwayat_log = []
                    
                    def update_terminal():
                        log_terminal.markdown("<div class='terminal-box'>" + "<br>".join(riwayat_log) + "</div>", unsafe_allow_html=True)

                    total_missing = len(data_missing)
                    for idx, missing_item in enumerate(data_missing):
                        ticker, thn, per, doc_id = missing_item["Emiten"], missing_item["Tahun"], missing_item["Periode"].lower(), missing_item["doc_id"]
                        
                        riwayat_log.append(f"[{time.strftime('%H:%M:%S')}] ⏳ Mengekstrak: {ticker} ({per.upper()} - {thn})...")
                        update_terminal()
                        
                        res_api = tarik_data_api(ticker, thn, per)
                        
                        if res_api and res_api.get("hasil", {}).get("status") == "sukses":
                            # PENCEGAHAN ERROR DATA KOSONG
                            k = res_api.get("hasil", {}).get("data", {})
                            metode = res_api["hasil"].get("metode_ekstraksi", "Unknown")
                            
                            payload = {
                                "kode_emiten": ticker, "tahun": int(thn), "periode": per,
                                "total_aset": k.get("Total_Aset", 0), "laba_bersih": k.get("Laba_Rugi_Bersih", 0), "pendapatan": k.get("Pendapatan", 0),
                                "metode_ekstraksi": metode, "timestamp": firestore.SERVER_TIMESTAMP
                            }
                            try:
                                # SLEEP DIHAPUS BIAR CEPAT NYIMPENNYA
                                db.collection("fundamental_emiten").document(doc_id).set(payload)
                                riwayat_log[-1] = f"[{time.strftime('%H:%M:%S')}] ✅ {ticker} ({per.upper()}-{thn}) TERSIMPAN via {metode}."
                            except Exception as ex:
                                riwayat_log.append(f"[{time.strftime('%H:%M:%S')}] ❌ ERROR simpan {doc_id}: {ex}")
                        else:
                            riwayat_log[-1] = f"[{time.strftime('%H:%M:%S')}] ❌ {ticker} ({per.upper()}-{thn}) GAGAL diekstrak."
                        
                        update_terminal()
                        progress_bar.progress((idx + 1) / total_missing)
                        
                        # SLEEP DIHAPUS DI SINI BIAR GAK NUNGGU 3 DETIK PER DATA
                        
                    st.success("🎯 Proses Smart Sync selesai!")
                    st.balloons()
                    time.sleep(3) 
                    st.rerun()