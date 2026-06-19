import io
import os
import zipfile
import requests
import re
import time
from bs4 import BeautifulSoup
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware # TAMBAHAN 1: Import CORS
from ekstraksi_ai import ekstrak_keuangan_otomatis

app = FastAPI(title="IDX Data Provider API (Hybrid AI + Rentang Waktu)")

# =========================================================
# TAMBAHAN 2: BUKA JALUR CORS BIAR STREAMLIT BISA MASUK
# =========================================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

TAXONOMY_MAP = {
    "umum": {
        "aset": [r"\bassets$"],
        "laba": [r"\bprofitlossattributabletoownersofparententity$", r"\bprofitloss$"],
        "pendapatan": [r"\brevenue$"]
    },
    "bank": {
        "aset": [r"\bassets$"],
        "laba": [r"\bprofitlossattributabletoownersofparententity$", r"\bprofitloss$"],
        "pendapatan": [r"\binterestandshariaincome$", r"\binterestincome$"]
    }
}

def cari_nilai_xbrl(soup, kata_kunci_list):
    for kata_kunci in kata_kunci_list:
        tags = soup.find_all(re.compile(kata_kunci, re.IGNORECASE))
        for tag in tags:
            if tag.has_attr('contextRef'):
                context = tag['contextRef'].lower()
                if 'prior' in context or 'prev' in context:
                    continue
                try:
                    if tag.text.strip():
                        return int(float(tag.text.strip()))
                except ValueError:
                    continue
    return 0

# =========================================================
# FUNGSI INTI: PROSES 1 TAHUN (MODULAR)
# =========================================================
def proses_satu_laporan(kode_emiten: str, tahun: str, periode: str):
    kode_emiten = kode_emiten.upper()
    periode = periode.lower()
    
    if periode == "q1": periode_idx = "TW1"
    elif periode == "q2": periode_idx = "TW2"
    elif periode == "q3": periode_idx = "TW3"
    elif periode in ["q4", "tahunan", "audit"]: periode_idx = "audit"
    else: periode_idx = periode.upper()

    idx_url = f"https://www.idx.co.id/primary/ListedCompany/GetFinancialReport?indexFrom=1&pageSize=50&year={tahun}&periode={periode_idx}&reportType=rdf&emitentipe=&kodeEmiten={kode_emiten}"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7",
        "Referer": "https://www.idx.co.id/id/perusahaan-tercatat/laporan-keuangan-dan-tahunan",
        "Connection": "keep-alive",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin"
    }

    try:
        session = requests.Session()
        session.headers.update(headers)
        session.get("https://www.idx.co.id/id/perusahaan-tercatat/laporan-keuangan-dan-tahunan")
        
        response = session.get(idx_url)
        response.raise_for_status()
        data_asli = response.json()
        
        hasil_pencarian = data_asli.get("Results", [])
        
        link_xbrl = None
        link_pdf = None 
        nama_file_xbrl = "Dokumen XBRL" 
        nama_file_pdf = "Dokumen PDF"   
        tipe = "Tidak ada data"

        for hasil in hasil_pencarian:
            for file in hasil.get("Attachments", []):
                nama_file = file.get("File_Name", "")
                nama_file_lower = nama_file.lower()
                
                # 1. Cari XBRL dan simpan nama filenya
                if "instance.zip" in nama_file_lower:
                    link_xbrl = f"https://www.idx.co.id{file.get('File_Path', '')}"
                    nama_file_xbrl = nama_file
                elif link_xbrl is None and "xbrl" in nama_file_lower and "inline" not in nama_file_lower:
                    link_xbrl = f"https://www.idx.co.id{file.get('File_Path', '')}"
                    nama_file_xbrl = nama_file

                # 2. Cari PDF dan simpan nama filenya
                if nama_file_lower.endswith(".pdf"):
                    if "financial" in nama_file_lower or "lk" in nama_file_lower:
                        link_pdf = f"https://www.idx.co.id{file.get('File_Path', '')}"
                        nama_file_pdf = nama_file
                    elif link_pdf is None:
                        link_pdf = f"https://www.idx.co.id{file.get('File_Path', '')}"
                        nama_file_pdf = nama_file

        data_keuangan_bersih = {"Total_Aset": 0, "Laba_Rugi_Bersih": 0, "Pendapatan": 0}
        
        # --- JALUR 1: XBRL ---
        if link_xbrl:
            zip_response = session.get(link_xbrl)
            with zipfile.ZipFile(io.BytesIO(zip_response.content)) as z:
                nama_file_xml = next((f for f in z.namelist() if f.lower().endswith('.xml') or f.lower().endswith('.xbrl')), None)
                
                if nama_file_xml:
                    xml_content = z.read(nama_file_xml)
                    soup = BeautifulSoup(xml_content, "xml")
                    
                    is_bank = soup.find(lambda tag: tag.name and 'bank' in tag.name.lower()) is not None
                    tipe = "bank" if is_bank else "umum"
                    
                    data_keuangan_bersih['Total_Aset'] = cari_nilai_xbrl(soup, TAXONOMY_MAP[tipe]["aset"])
                    data_keuangan_bersih['Laba_Rugi_Bersih'] = cari_nilai_xbrl(soup, TAXONOMY_MAP[tipe]["laba"])
                    data_keuangan_bersih['Pendapatan'] = cari_nilai_xbrl(soup, TAXONOMY_MAP[tipe]["pendapatan"])

            if data_keuangan_bersih['Total_Aset'] != 0:
                return {
                    "tahun": tahun,
                    "status": "sukses",
                    "metode_ekstraksi": "XBRL Asli IDX",
                    "nama_dokumen": nama_file_xbrl,  
                    "link_dokumen": link_xbrl,       
                    "data": data_keuangan_bersih
                }

        # --- JALUR 2: AI VISION FALLBACK ---
        if link_pdf:
            print(f"⚠️ [{tahun}] XBRL kosong. Memicu Robot AI membaca PDF...")
            pdf_response = session.get(link_pdf)
            nama_pdf_temp = f"temp_{kode_emiten}_{tahun}_{periode_idx}.pdf"
            
            with open(nama_pdf_temp, "wb") as f:
                f.write(pdf_response.content)
            
            hasil_ai = ekstrak_keuangan_otomatis(nama_pdf_temp)
            
            if os.path.exists(nama_pdf_temp):
                os.remove(nama_pdf_temp)
                
            if hasil_ai["status"] == "sukses":
                return {
                    "tahun": tahun,
                    "status": "sukses",
                    "metode_ekstraksi": hasil_ai["metode_ekstraksi"],
                    "nama_dokumen": nama_file_pdf,  
                    "link_dokumen": link_pdf,       
                    "data": hasil_ai["data_keuangan"]
                }
            else:
                return {"tahun": tahun, "status": "gagal", "pesan": hasil_ai['pesan']}
                
        # --- JALUR 3: ZONK ---
        return {"tahun": tahun, "status": "gagal", "pesan": "Tidak ada file XBRL atau PDF di IDX."}
        
    except Exception as e:
        return {"tahun": tahun, "status": "gagal", "pesan": f"Sistem Error: {str(e)}"}


# =========================================================
# ENDPOINT API
# =========================================================

@app.get("/")
def read_root():
    return {"status": "aktif", "pesan": "Mesin API IDX menyala. Siap mode Rentang Tahun!"}

# Endpoint 1: Versi Satuan
@app.get("/api/v1/laporan/{kode_emiten}/{tahun}/{periode}")
def get_laporan_idx(kode_emiten: str, tahun: str, periode: str):
    print(f"🚀 Menjalankan ekstraksi tunggal: {kode_emiten} Tahun {tahun}")
    hasil = proses_satu_laporan(kode_emiten, tahun, periode)
    return {"emiten": kode_emiten.upper(), "periode": periode.upper(), "hasil": hasil}

# Endpoint 2: Versi Rentang Tahun
@app.get("/api/v1/rentang/{kode_emiten}/{tahun_awal}/{tahun_akhir}/{periode}")
def get_laporan_rentang(kode_emiten: str, tahun_awal: int, tahun_akhir: int, periode: str):
    
    if tahun_awal > tahun_akhir:
        raise HTTPException(status_code=400, detail="Tahun awal tidak boleh lebih besar dari tahun akhir.")
        
    print(f"🚀 Menjalankan ekstraksi massal: {kode_emiten} ({tahun_awal} - {tahun_akhir})")
    
    data_historis = []
    
    for thn in range(tahun_awal, tahun_akhir + 1):
        if thn > tahun_awal:
            time.sleep(2)
            
        hasil_tahun_ini = proses_satu_laporan(kode_emiten, str(thn), periode)
        data_historis.append(hasil_tahun_ini)
        
    return {
        "status": "sukses",
        "emiten": kode_emiten.upper(),
        "rentang": f"{tahun_awal} - {tahun_akhir}",
        "periode": periode.upper(),
        "total_data": len(data_historis),
        "data_historis": data_historis
    }