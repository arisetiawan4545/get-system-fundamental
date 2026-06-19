import os
import fitz  
import json
import streamlit as st # WAJIB TAMBAHIN INI BUAT BACA SECRETS
from google import genai
from google.genai import types  

# --- 1. KONFIGURASI API KEY ---
# Cek apakah lagi jalan di cloud (punya st.secrets) atau lokal (pakai os.environ)
try:
    api_key = st.secrets["GCP_API_KEY"]
except (FileNotFoundError, KeyError):
    # Kalau di lokal (komputer lu), dia akan nyari dari environment variable atau .env
    api_key = os.environ.get("GCP_API_KEY", "KUNCI_LOKAL_LU_KLO_MAU_DITULIS_DISINI")

if not api_key:
    raise ValueError("GCP_API_KEY tidak ditemukan! Cek Secrets atau file .env lu.")

client = genai.Client(api_key=api_key)


def ekstrak_keuangan_otomatis(nama_file_asli):
    print(f"🤖 [ROBOT ADMIN] Memulai operasi bedah dokumen: {nama_file_asli}")
    
    file_potongan_sementara = "temp_potongan.pdf"
    
    # ==========================================
    # FASE 1: PEMOTONGAN PDF (Otak Pencari)
    # ==========================================
    try:
        print("🔍 Memindai halaman inti (Neraca & Laba Rugi)...")
        dokumen = fitz.open(nama_file_asli)
        halaman_target = set()
        
        # Kata kunci akuntansi
        kata_kunci = ["laporan posisi keuangan", "statement of financial position", "laporan laba rugi", "statement of profit or loss"]
        
        batas_halaman = min(20, len(dokumen))
        for i in range(batas_halaman):
            teks = dokumen[i].get_text("text").lower()
            if any(kata in teks for kata in kata_kunci):
                halaman_target.add(i)
        
        if not halaman_target:
            return {"status": "gagal", "pesan": "Halaman laporan keuangan tidak ditemukan di 20 halaman pertama."}

        list_halaman = sorted(list(halaman_target))
        dokumen_baru = fitz.open()
        for hal in list_halaman:
            dokumen_baru.insert_pdf(dokumen, from_page=hal, to_page=hal)
        dokumen_baru.save(file_potongan_sementara)
        
        dokumen_baru.close()
        dokumen.close()
        print(f"✂️ Sukses mengisolasi {len(list_halaman)} halaman penting.")
        
    except Exception as e:
        return {"status": "gagal", "pesan": f"Gagal memotong PDF: {e}"}

    # ==========================================
    # FASE 2: EKSTRAKSI AI (Otak Eksekutor Kaku)
    # ==========================================
    try:
        print("🧠 Menganalisis angka menggunakan Gemini 2.5 Flash (Mode Konsisten)...")
        uploaded_file = client.files.upload(file=file_potongan_sementara)
        
        # Prompt diperketat fokus pada data KONSOLIDASIAN (Consolidated)
        prompt = """
        Kamu adalah sistem ekstraksi data keuangan otomatis bersertifikasi.
        Baca dokumen ini dan temukan 3 nilai utama untuk tahun penuh 2023.
        
        PENTING: Ambil angka dari kolom KONSOLIDASIAN (CONSOLIDATED) jika ada pilihan.
        
        Format wajib:
        {
            "Total_Aset": 1234567890,
            "Laba_Rugi_Bersih": 123456,
            "Pendapatan": 123456
        }
        """
        
        # --- EKSEKUSI DENGAN CONFIG TEMPERATUR 0.0 ---
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=[uploaded_file, prompt],
            config=types.GenerateContentConfig(
                temperature=0.0,                  # <--- KUNCI KREATIVITAS JADI 0 (ANTI-NGANTOX)
                response_mime_type="application/json" # <--- PAKSA HARUS KELUAR JSON BERSIH
            )
        )
        
        if os.path.exists(file_potongan_temporary := file_potongan_sementara):
            os.remove(file_potongan_temporary)
            print("🧹 Membersihkan file sementara...")
            
        teks_ai = response.text.strip()
        data_json = json.loads(teks_ai)
            
        return {
            "status": "sukses",
            "metode_ekstraksi": "AI Vision (Gemini 2.5 - Deterministic Mode)",
            "data_keuangan": data_json
        }
        
    except Exception as e:
        if os.path.exists(file_potongan_sementara):
            os.remove(file_potongan_sementara)
        return {"status": "gagal", "pesan": f"AI Error: {e}"}

if __name__ == "__main__":
    file_target = "FinancialStatement-2023-Tahunan-BBRI.pdf"
    hasil_akhir = ekstrak_keuangan_otomatis(file_target)
    print("\n🎯 HASIL AKHIR (Bentuk Data Python Asli):")
    print(hasil_akhir)