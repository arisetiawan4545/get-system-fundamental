import os
import fitz  
import json
import re
from google import genai
from google.genai import types  

# --- 1. KONFIGURASI API KEY (HARDCODE BACKEND) ---
# Masukkan API Key lu yang baru (jangan pakai yang lama yang udah bocor!)
api_key = "MASUKAN_API_KEY_BARU_LU_DISINI"

if not api_key or api_key == "MASUKAN_API_KEY_BARU_LU_DISINI":
    print("⚠️ PERINGATAN: Kunci API masih kosong!")

client = genai.Client(api_key=api_key)

def ekstrak_keuangan_otomatis(nama_file_asli):
    print(f"🤖 [ROBOT ADMIN] Memulai operasi bedah dokumen: {nama_file_asli}")
    
    file_potongan_sementara = f"temp_potongan_{os.path.basename(nama_file_asli)}"
    
    # Deteksi Tahun/Periode dari nama file agar Prompt Dinamis
    # Contoh format masuk: temp_BBCA_2023_TW1.pdf
    prompt_tambahan = "periode berjalan sesuai dokumen"
    if "temp_" in nama_file_asli:
        parts = os.path.basename(nama_file_asli).replace(".pdf", "").split("_")
        if len(parts) >= 4:
            prompt_tambahan = f"Tahun {parts[2]} Periode {parts[3]}"

    # ==========================================
    # FASE 1: PEMOTONGAN PDF (Otak Pencari)
    # ==========================================
    try:
        print("🔍 Memindai halaman inti (Neraca & Laba Rugi)...")
        dokumen = fitz.open(nama_file_asli)
        halaman_target = set()
        
        # Kata kunci akuntansi (Indonesia & Inggris)
        kata_kunci = ["laporan posisi keuangan", "statement of financial position", "laporan laba rugi", "statement of profit or loss"]
        
        batas_halaman = min(150, len(dokumen))
        for i in range(batas_halaman):
            teks = dokumen[i].get_text("text").lower()
            if any(kata in teks for kata in kata_kunci):
                halaman_target.add(i)
        
        if not halaman_target:
            dokumen.close()
            return {"status": "gagal", "pesan": f"Halaman laporan keuangan tidak ditemukan di {batas_halaman} halaman pertama."}

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
    uploaded_file = None
    try:
        print("🧠 Menganalisis angka menggunakan Gemini 2.5 Flash (Mode Konsisten)...")
        uploaded_file = client.files.upload(file=file_potongan_sementara)
        
        prompt = f"""
        Kamu adalah sistem ekstraksi data keuangan otomatis bersertifikasi.
        Baca dokumen ini dan temukan 3 nilai utama untuk {prompt_tambahan}.
        
        PENTING: Ambil angka dari kolom KONSOLIDASIAN (CONSOLIDATED) jika ada pilihan.
        
        Format wajib (hanya output JSON tanpa markdown):
        {{
            "Total_Aset": 1234567890,
            "Laba_Rugi_Bersih": 123456,
            "Pendapatan": 123456
        }}
        """
        
        # Eksekusi dengan Strict JSON Configuration
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=[uploaded_file, prompt],
            config=types.GenerateContentConfig(
                temperature=0.0,
                response_mime_type="application/json" 
            )
        )
            
        teks_ai = response.text.strip()
        data_json = json.loads(teks_ai)
            
        return {
            "status": "sukses",
            "metode_ekstraksi": "AI Vision (Gemini 2.5 - Deterministic Mode)",
            "data": data_json
        }
        
    except Exception as e:
        return {"status": "gagal", "pesan": f"AI Error: {e}"}
        
    finally:
        # ==========================================
        # CLEANUP PROTOCOL (WAJIB ADA)
        # ==========================================
        # 1. Hapus file sementara di lokal
        if os.path.exists(file_potongan_sementara):
            try:
                os.remove(file_potongan_sementara)
            except: pass
            
        # 2. Hapus dokumen rahasia dari Server Google Cloud (PENTING!)
        if uploaded_file:
            try:
                client.files.delete(name=uploaded_file.name)
                print("🧹 Jejak dokumen di server Google berhasil dihapus.")
            except Exception as e:
                print(f"⚠️ Gagal menghapus file dari server Google: {e}")

if __name__ == "__main__":
    # Pastikan ada file dummy buat testing
    file_target = "FinancialStatement-2023-Tahunan-BBCA.pdf"
    if os.path.exists(file_target):
        hasil_akhir = ekstrak_keuangan_otomatis(file_target)
        print("\n🎯 HASIL AKHIR (Bentuk Data Python Asli):")
        print(json.dumps(hasil_akhir, indent=4))
    else:
        print(f"File {file_target} tidak ditemukan. Siap digunakan sebagai modul impor.")