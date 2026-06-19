import streamlit as st
import requests
import pandas as pd
import time
import firebase_admin
from firebase_admin import credentials, firestore
import json


# --- INISIALISASI FIREBASE ---
@st.cache_resource
def init_firebase():
    try:
        if not firebase_admin._apps:
            # 1. Kalau jalan di Server Streamlit (ambil dari Brankas)
            if "FIREBASE_JSON" in st.secrets:
                cred_dict = json.loads(st.secrets["FIREBASE_JSON"])
                cred = credentials.Certificate(cred_dict)
            # 2. Kalau jalan di komputer lu sendiri (ambil dari file lokal)
            else:
                cred = credentials.Certificate("firebase_key.json")
            
            firebase_admin.initialize_app(cred)
        return firestore.client()
    except Exception as e:
        return None

db = init_firebase()

# Konfigurasi Halaman 
st.set_page_config(page_title="GET SYSTEM FUNDAMENTAL", page_icon="📊", layout="wide")

# --- CUSTOM CSS: TEMA HITAM & HIJAU NEON (HACKER THEME) ---
st.markdown("""
<style>
    /* Mengubah warna background utama aplikasi jadi Hitam Pekat */
    [data-testid="stAppViewContainer"] {
        background-color: #050505;
    }
    
    /* Mengubah warna background sidebar */
    [data-testid="stSidebar"] {
        background-color: #0a0a0a;
        border-right: 1px solid #00FF41;
    }

    /* Mengubah warna teks utama Streamlit */
    h1, h2, h3, h4, h5, h6, p, span, div, label {
        color: #E0E0E0 !important;
    }

    /* Kustomisasi Kartu Premium */
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
        box-shadow: 0 8px 25px rgba(0, 255, 65, 0.3); /* Glow Hijau */
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
        width: fit-content;
        font-weight: bold;
    }
    
    /* Kustomisasi Box Kuartal */
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
    
    /* CSS Tambahan untuk Terminal Animasi Firebase */
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
    
    /* Kustomisasi Garis Pembatas (Divider) */
    hr {
        border-color: #00FF41 !important;
        opacity: 0.3;
    }
</style>
""", unsafe_allow_html=True)

# --- FUNGSI FORMAT ANGKA ---
def format_singkat(angka):
    if angka == 0: return "Rp 0"
    elif abs(angka) >= 1_000_000_000_000: return f"Rp {angka / 1_000_000_000_000:.2f} Triliun"
    elif abs(angka) >= 1_000_000_000: return f"Rp {angka / 1_000_000_000:.2f} Miliar"
    elif abs(angka) >= 1_000_000: return f"Rp {angka / 1_000_000:.2f} Juta"
    else: return f"Rp {angka:,.0f}".replace(",", ".")

def format_full(angka):
    return f"Rp {angka:,.0f}".replace(",", ".")

# --- FUNGSI TARIK DAFTAR EMITEN DARI FILE LOKAL ---
@st.cache_data
def get_daftar_emiten():
    try:
        with open("emiten.txt", "r", encoding="utf-8") as file:
            daftar = [line.strip() for line in file if line.strip()]
        return sorted(daftar)
    except FileNotFoundError:
        return ["AALI - Astra Agro Lestari", "BBCA - Bank Central Asia", "SYSTEM - File emiten.txt tidak ditemukan"]


# --- FUNGSI API (VERSI CERIWIT / DETEKSI ERROR CLOUD) ---
URL_API_PROD = "https://arisetiawan4545-api-get-system.hf.space" 

def tarik_data_api(emiten, tahun, periode):
    url_api = f"{URL_API_PROD}/api/v1/laporan/{emiten}/{tahun}/{periode}"
    try:
        res = requests.get(url_api, timeout=120) 
        if res.status_code == 200:
            return res.json()
        else:
            # BONGKAR ERROR: Munculkan status code mentah dari Hugging Face di Sidebar
            st.sidebar.error(f"❌ Server HF Mengirim Kode: {res.status_code}")
            try:
                st.sidebar.code(f"Respon Mentah:\n{res.json()}")
            except:
                st.sidebar.code(f"Respon Mentah:\n{res.text}")
            return None
    except Exception as e:
        st.sidebar.error(f"❌ Jaringan Putus / Timeout ke HF. Detail: {e}")
        return None

def tarik_data_rentang(emiten, t_awal, t_akhir, periode):
    url_api = f"{URL_API_PROD}/api/v1/rentang/{emiten}/{t_awal}/{t_akhir}/{periode}"
    try:
        res = requests.get(url_api, timeout=600) 
        if res.status_code == 200:
            return res.json()
        else:
            st.sidebar.error(f"❌ Server HF Mengirim Kode Rentang: {res.status_code}")
            try:
                st.sidebar.code(f"Respon Mentah:\n{res.json()}")
            except:
                st.sidebar.code(f"Respon Mentah:\n{res.text}")
            return None
    except Exception as e:
        st.sidebar.error(f"❌ Jaringan Massal Putus. Detail: {e}")
        return None

daftar_emiten_lengkap = get_daftar_emiten()

# =========================================================================
# HEADER & LOGO GET SYSTEM FUNDAMENTAL
# =========================================================================
try:
    st.image("icon.png", width=130)
except FileNotFoundError:
    st.warning("⚠️ File 'icon.png' tidak ditemukan.")

st.markdown("<h1 style='color: #00FF41;'>GET SYSTEM FUNDAMENTAL</h1>", unsafe_allow_html=True)

# =========================================================================
# SWITCH UTAMA (DI ATAS SIDEBAR)
# =========================================================================
st.sidebar.markdown("<h3 style='color: #00FF41;'>🎛️ Main Control</h3>", unsafe_allow_html=True)
app_mode = st.sidebar.radio("Pilih Tampilan:", ["Lihat Fundamental", "Simpan Fundamental (Database)"], index=0)
st.sidebar.markdown("---")

if app_mode == "Lihat Fundamental":
    st.markdown("<span style='color:#00FF41;'>Sistem Ekstraksi Hybrid Auto-Pilot: XBRL & AI Vision</span>", unsafe_allow_html=True)
    st.divider()

    st.sidebar.markdown("<h4 style='color: #00FF41;'>⚙️ Parameter Ekstraksi</h4>", unsafe_allow_html=True)

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
            if periode_api == "audit":
                st.info(f"🔄 Mode Lengkap Aktif: Membongkar data Tahunan beserta rincian kuartal {emiten_input} tahun {tahun_pilihan}...")
                with st.spinner("Menarik Laporan Tahunan..."):
                    data_utama = tarik_data_api(emiten_input, tahun_pilihan, "audit")
                with st.spinner("Menarik Laporan Q1..."):
                    data_q1 = tarik_data_api(emiten_input, tahun_pilihan, "q1")
                with st.spinner("Menarik Laporan Q2..."):
                    data_q2 = tarik_data_api(emiten_input, tahun_pilihan, "q2")
                with st.spinner("Menarik Laporan Q3..."):
                    data_q3 = tarik_data_api(emiten_input, tahun_pilihan, "q3")
            else:
                with st.spinner(f"Memproses {emiten_input} ({periode_pilihan} {tahun_pilihan})..."):
                    data_utama = tarik_data_api(emiten_input, tahun_pilihan, periode_api)
                    data_q1 = data_q2 = data_q3 = None

            if data_utama and data_utama.get("hasil", {}).get("status") == "sukses":
                hasil = data_utama["hasil"]
                st.success(f"✅ Data Utama {emiten_input} tahun {tahun_pilihan} diamankan! (Via: {hasil.get('metode_ekstraksi')})")
                keuangan = hasil["data"]
                
                # --- RENDER KARTU (FULL HIJAU) ---
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.markdown(f"""
                    <div class="premium-card">
                        <div>
                            <div class="card-title">🏦 Total Aset</div>
                            <div class="card-value">{format_singkat(keuangan['Total_Aset'])}</div>
                        </div>
                        <div class="card-exact">{format_full(keuangan['Total_Aset'])}</div>
                    </div>
                    """, unsafe_allow_html=True)
                with col2:
                    st.markdown(f"""
                    <div class="premium-card">
                        <div>
                            <div class="card-title">📈 Laba/Rugi Bersih</div>
                            <div class="card-value">{format_singkat(keuangan['Laba_Rugi_Bersih'])}</div>
                        </div>
                        <div class="card-exact">{format_full(keuangan['Laba_Rugi_Bersih'])}</div>
                    </div>
                    """, unsafe_allow_html=True)
                with col3:
                    st.markdown(f"""
                    <div class="premium-card">
                        <div>
                            <div class="card-title">💰 Pendapatan</div>
                            <div class="card-value">{format_singkat(keuangan['Pendapatan'])}</div>
                        </div>
                        <div class="card-exact">{format_full(keuangan['Pendapatan'])}</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                if periode_api == "audit":
                    st.markdown("<br><h4 style='color: #00FF41;'>Riwayat Kinerja Kuartal (YTD)</h4>", unsafe_allow_html=True)
                    q_cols = st.columns(3)
                    
                    def render_q_box(data_q, title):
                        if data_q and data_q.get("hasil", {}).get("status") == "sukses":
                            k = data_q["hasil"]["data"]
                            return f"""
                            <div class="quarter-box">
                                <div class="q-title">{title}</div>
                                <div class="q-label">Total Aset</div>
                                <div class="q-val" style="color: #00FF41;">{format_singkat(k['Total_Aset'])}</div>
                                <div style="margin: 8px 0;"></div>
                                <div class="q-label">Laba Bersih</div>
                                <div class="q-val" style="color: #00FF41;">{format_singkat(k['Laba_Rugi_Bersih'])}</div>
                                <div class="q-label" style="margin-top:5px; font-size:10px; color:#555;">Mekanisme: {data_q['hasil'].get('metode_ekstraksi')}</div>
                            </div>
                            """
                        else:
                            return f"""
                            <div class="quarter-box" style="border-bottom-color: #333;">
                                <div class="q-title" style="color: #666 !important;">{title}</div>
                                <div class="q-label" style="color:#666 !important;">Data Belum Rilis / Tidak Ditemukan</div>
                            </div>
                            """
                    with q_cols[0]: st.markdown(render_q_box(data_q1, "Q1 (Maret)"), unsafe_allow_html=True)
                    with q_cols[1]: st.markdown(render_q_box(data_q2, "Q2 (Juni)"), unsafe_allow_html=True)
                    with q_cols[2]: st.markdown(render_q_box(data_q3, "Q3 (September)"), unsafe_allow_html=True)

            else:
                st.error(f"⚠️ Gagal mengekstrak data dari {emiten_input} untuk tahun {tahun_pilihan}.")
                if data_utama and "hasil" in data_utama:
                    st.info(f"🔍 Bisikan dari Backend: {data_utama['hasil'].get('pesan', 'Gagal tanpa alasan spesifik.')}")
                else:
                    st.info("💡 Petunjuk Analisis: Lirik ke panel SIDEBAR SEBELAH KIRI, gue udah buatin kotak ijo/merah buat ngintip respon mentah kenapa server Hugging Face lu nolak ngasih data!").")

    elif mode_ekstraksi == "Tren Historis (Multi-Tahun)":
        st.sidebar.markdown("---")
        
        col_a, col_b = st.sidebar.columns(2)
        with col_a:
            tahun_awal = st.text_input("Tahun Awal", value="2021", max_chars=4)
        with col_b:
            tahun_akhir = st.text_input("Tahun Akhir", value="2023", max_chars=4)
            
        periode_pilihan = st.sidebar.selectbox("Periode", ["Audit (Tahunan)", "Q1", "Q2", "Q3"])
        map_periode = {"Audit (Tahunan)": "audit", "Q1": "q1", "Q2": "q2", "Q3": "q3"}
        periode_api = map_periode[periode_pilihan]
        
        tombol_rentang = st.sidebar.button("Lihat Fundamental", use_container_width=True)
        
        if tombol_rentang and emiten_input and tahun_awal.isdigit() and tahun_akhir.isdigit():
            if periode_api == "audit":
                st.info(f"🔄 Mode Super Lengkap: Menarik rentang Tahunan + Kuartal dari {tahun_awal} hingga {tahun_akhir} secara terpisah...")
                
                with st.spinner("Membedah data Tahunan..."):
                    data_audit = tarik_data_rentang(emiten_input, tahun_awal, years_end:=tahun_akhir, "audit")
                
                time.sleep(3) # Kasih jeda napas 3 detik buat server HF
                with st.spinner("Membedah data Q1..."):
                    data_q1 = tarik_data_rentang(emiten_input, tahun_awal, years_end, "q1")
                
                time.sleep(3) # Kasih jeda napas lagi
                with st.spinner("Membedah data Q2..."):
                    data_q2 = tarik_data_rentang(emiten_input, tahun_awal, years_end, "q2")
                
                time.sleep(3) # Kasih jeda napas lagi
                with st.spinner("Membedah data Q3..."):
                    data_q3 = tarik_data_rentang(emiten_input, tahun_awal, years_end, "q3")
                    
                data_tahunan = []
                data_kuartal = []
                
                if data_audit and data_audit.get("status") == "sukses":
                    for item in data_audit["data_historis"]:
                        if item["status"] == "sukses":
                            data_tahunan.append({
                                "Tahun": item["tahun"],
                                "Aset (Rp)": item["data"]["Total_Aset"],
                                "Laba Bersih (Rp)": item["data"]["Laba_Rugi_Bersih"],
                                "Pendapatan (Rp)": item["data"]["Pendapatan"],
                                "Metode Ekstraksi": item["metode_ekstraksi"]
                            })
                
                def kumpulkan_kuartal(data_massal, label):
                    if data_massal and data_massal.get("status") == "sukses":
                        for item in data_massal["data_historis"]:
                            if item["status"] == "sukses":
                                order = 1 if label == "Q1" else 2 if label == "Q2" else 3
                                sort_key = int(item["tahun"]) + (order * 0.1)
                                
                                data_kuartal.append({
                                    "Sort": sort_key,
                                    "Kuartal": f"{item['tahun']} - {label}",
                                    "Aset (Rp)": item["data"]["Total_Aset"],
                                    "Laba Bersih (Rp)": item["data"]["Laba_Rugi_Bersih"],
                                    "Pendapatan (Rp)": item["data"]["Pendapatan"],
                                    "Metode Ekstraksi": item["metode_ekstraksi"]
                                })

                kumpulkan_kuartal(data_q1, "Q1")
                kumpulkan_kuartal(data_q2, "Q2")
                kumpulkan_kuartal(data_q3, "Q3")
                
                if data_tahunan or data_kuartal:
                    st.success(f"✅ Selesai! Data konsolidasi {emiten_input} berhasil dipisahkan.")
                
                if data_tahunan:
                    df_tahun = pd.DataFrame(data_tahunan).set_index("Tahun")
                    st.markdown("<hr><h2 style='color: #00FF41;'>🏢 Kinerja Tahunan (Audit)</h2>", unsafe_allow_html=True)
                    st.markdown("<h4 style='color: #E0E0E0;'>📈 Grafik Tren Tahunan</h4>", unsafe_allow_html=True)
                    st.line_chart(df_tahun[["Aset (Rp)", "Laba Bersih (Rp)", "Pendapatan (Rp)"]], height=350, use_container_width=True)
                    st.markdown("<h4 style='color: #E0E0E0;'>🗄️ Tabel Data Tahunan</h4>", unsafe_allow_html=True)
                    st.dataframe(df_tahun.style.format({
                        "Aset (Rp)": "{:,.0f}", "Laba Bersih (Rp)": "{:,.0f}", "Pendapatan (Rp)": "{:,.0f}"
                    }), use_container_width=True)
                    
                if data_kuartal:
                    df_q = pd.DataFrame(data_kuartal)
                    df_q = df_q.sort_values(by="Sort").reset_index(drop=True)
                    df_q_chart = df_q.set_index("Kuartal")[["Aset (Rp)", "Laba Bersih (Rp)", "Pendapatan (Rp)"]]
                    st.markdown("<hr><h2 style='color: #00FF41;'>📅 Kinerja Kuartalan (Q1 - Q3)</h2>", unsafe_allow_html=True)
                    st.markdown("<h4 style='color: #E0E0E0;'>📈 Grafik Progres Kuartal</h4>", unsafe_allow_html=True)
                    st.line_chart(df_q_chart, height=350, use_container_width=True)
                    st.markdown("<h4 style='color: #E0E0E0;'>🗄️ Tabel Data Kuartalan</h4>", unsafe_allow_html=True)
                    df_q_tabel = df_q.drop(columns=["Sort"])
                    st.dataframe(df_q_tabel.set_index("Kuartal").style.format({
                        "Aset (Rp)": "{:,.0f}", "Laba Bersih (Rp)": "{:,.0f}", "Pendapatan (Rp)": "{:,.0f}"
                    }), use_container_width=True)
                else:
                    # --- PERBAIKAN UI: Kalau kuartal kosong, munculkan pesan ini! ---
                    st.markdown("<hr><h2 style='color: #00FF41;'>📅 Kinerja Kuartalan (Q1 - Q3)</h2>", unsafe_allow_html=True)
                    st.warning("⚠️ Grafik kuartal tidak dapat ditampilkan karena koneksi diputus oleh Hugging Face atau datanya memang belum dirilis.")

            else:
                with st.spinner(f"Membedah data {emiten_input} khusus {periode_pilihan} dari {tahun_awal} sampai {tahun_akhir}..."):
                    data_spesifik = tarik_data_rentang(emiten_input, tahun_awal, tahun_akhir, periode_api)
                    
                data_grafik = []
                if data_spesifik and data_spesifik.get("status") == "sukses":
                    for item in data_spesifik["data_historis"]:
                        if item["status"] == "sukses":
                            data_grafik.append({
                                "Tahun": item["tahun"],
                                "Aset (Rp)": item["data"]["Total_Aset"],
                                "Laba Bersih (Rp)": item["data"]["Laba_Rugi_Bersih"],
                                "Pendapatan (Rp)": item["data"]["Pendapatan"],
                                "Metode Ekstraksi": item["metode_ekstraksi"]
                            })
                            
                if data_grafik:
                    st.success(f"✅ Berhasil menarik {len(data_grafik)} data {periode_pilihan} untuk {emiten_input}!")
                    df = pd.DataFrame(data_grafik).set_index("Tahun")
                    st.markdown(f"<h3 style='color: #00FF41;'>📈 Grafik Tren Khusus {periode_pilihan}</h3>", unsafe_allow_html=True)
                    st.line_chart(df[["Aset (Rp)", "Laba Bersih (Rp)", "Pendapatan (Rp)"]], height=400, use_container_width=True)
                    st.markdown("<h3 style='color: #00FF41;'>🗄️ Tabel Data Mentah</h3>", unsafe_allow_html=True)
                    st.dataframe(df.style.format({
                        "Aset (Rp)": "{:,.0f}", "Laba Bersih (Rp)": "{:,.0f}", "Pendapatan (Rp)": "{:,.0f}"
                    }), use_container_width=True)
                else:
                    st.error("⚠️ Proses selesai, tapi tidak ada data yang berhasil diekstrak.")

else:
    # =========================================================================
    # TAMPILAN 2: SIMPAN FUNDAMENTAL (SMART INCREMENTAL SYNC)
    # =========================================================================
    st.markdown("<span style='color:#00FF41;'>Mode Injeksi Cerdas ke Firebase - Mengisi Data yang Kosong Saja</span>", unsafe_allow_html=True)
    st.divider()

    st.sidebar.markdown("<h4 style='color: #00FF41;'>⚙️ Konfigurasi Database</h4>", unsafe_allow_html=True)
    emiten_massal = st.sidebar.multiselect("Pilih Target Emiten", daftar_emiten_lengkap, default=[e for e in daftar_emiten_lengkap if "BBCA" in e or "BBRI" in e])
    
    col_ta, col_tb = st.sidebar.columns(2)
    with col_ta: tahun_mulai = st.text_input("Dari Tahun", value="2022", max_chars=4)
    with col_tb: tahun_sampai = st.text_input("Sampai Tahun", value="2023", max_chars=4)
    
    # Proses Cek Database
    if emiten_massal and tahun_mulai.isdigit() and tahun_sampai.isdigit():
        if db is None:
            st.error("❌ Firebase belum terhubung! Pastikan file `firebase_key.json` ada di folder aplikasi lu.")
        else:
            st.markdown("<h3 style='color: #E0E0E0;'>🗂️ Status Kelengkapan Database Saat Ini</h3>", unsafe_allow_html=True)
            
            # Membangun daftar target dokumen
            target_dokumen = []
            semua_periode = ["audit", "q1", "q2", "q3"]
            
            for e in emiten_massal:
                ticker = e.split(" - ")[0]
                for y in range(int(tahun_mulai), int(tahun_sampai) + 1):
                    for p in semua_periode:
                        target_dokumen.append({
                            "doc_id": f"{ticker}_{y}_{p}",
                            "Emiten": ticker,
                            "Tahun": str(y),
                            "Periode": p.upper(),
                            "Status": "Belum Dicek"
                        })
            
            # Smart Checking ke Firestore
            data_missing = []
            status_table = []
            
            for item in target_dokumen:
                doc_ref = db.collection("fundamental_emiten").document(item["doc_id"])
                doc = doc_ref.get()
                if doc.exists:
                    item["Status"] = "✅ Sudah Tersimpan"
                else:
                    item["Status"] = "❌ Kosong (Perlu Download)"
                    data_missing.append(item)
                status_table.append(item)
                
            df_status = pd.DataFrame(status_table).drop(columns=["doc_id"])
            st.dataframe(df_status, use_container_width=True)
            
            if len(data_missing) == 0:
                st.success("🎉 Luar biasa! Semua data untuk emiten dan rentang tahun tersebut sudah lengkap di Database. Tidak ada yang perlu di-download lagi.")
            else:
                st.warning(f"⚠️ Ditemukan {len(data_missing)} data yang kosong. Sistem hanya akan mengekstrak data yang kosong ini.")
                
                tombol_injeksi = st.button("Ekstrak & Simpan Data yang Kosong", use_container_width=True, type="primary")
                
                if tombol_injeksi:
                    st.markdown("<div class='db-header'>📡 Live Streaming Sinkronisasi (Hanya Data Missing):</div>", unsafe_allow_html=True)
                    progress_bar = st.progress(0)
                    log_terminal = st.empty()
                    riwayat_log = []
                    
                    def update_terminal():
                        log_terminal.markdown("<div class='terminal-box'>" + "<br>".join(riwayat_log) + "</div>", unsafe_allow_html=True)

                    total_missing = len(data_missing)
                    for idx, missing_item in enumerate(data_missing):
                        ticker = missing_item["Emiten"]
                        thn = missing_item["Tahun"]
                        per = missing_item["Periode"].lower()
                        doc_id = missing_item["doc_id"]
                        
                        riwayat_log.append(f"[{time.strftime('%H:%M:%S')}] ⏳ Mengekstrak: {ticker} ({per.upper()} - {thn})...")
                        update_terminal()
                        
                        res_api = tarik_data_api(ticker, thn, per)
                        
                        if res_api and res_api.get("hasil", {}).get("status") == "sukses":
                            k = res_api["hasil"]["data"]
                            metode = res_api["hasil"].get("metode_ekstraksi", "Unknown")
                            
                            payload = {
                                "kode_emiten": ticker,
                                "tahun": int(thn),
                                "periode": per,
                                "total_aset": k["Total_Aset"],
                                "laba_bersih": k["Laba_Rugi_Bersih"],
                                "pendapatan": k["Pendapatan"],
                                "metode_ekstraksi": metode,
                                "timestamp": firestore.SERVER_TIMESTAMP
                            }
                            
                            try:
                                time.sleep(0.5) # Animasi natural
                                db.collection("fundamental_emiten").document(doc_id).set(payload)
                                riwayat_log[-1] = f"[{time.strftime('%H:%M:%S')}] ✅ {ticker} ({per.upper()}-{thn}) TERSIMPAN via {metode}."
                            except Exception as ex:
                                riwayat_log.append(f"[{time.strftime('%H:%M:%S')}] ❌ ERROR simpan {doc_id}: {ex}")
                        else:
                            riwayat_log[-1] = f"[{time.strftime('%H:%M:%S')}] ❌ {ticker} ({per.upper()}-{thn}) GAGAL diekstrak dari IDX."
                        
                        update_terminal()
                        progress_bar.progress((idx + 1) / total_missing)
                        
                    st.success("🎯 Proses Smart Sync selesai! Sedang merefresh tabel secara otomatis...")
                    st.balloons()
                    time.sleep(3) 
                    st.rerun()