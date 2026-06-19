import os
import json
import re
import PyPDF2
from google import genai


kunci_rahasia = os.environ.get("GCP_API_KEY")
if not kunci_rahasia:
    print("⚠️ PERINGATAN: Kunci API tidak ditemukan di Environment Variables!")
    # Bisa tambahkan exit(1) di sini kalau mau scriptnya langsung berhenti

client = genai.Client(api_key=kunci_rahasia)

# =====================================================================
# 2. METODE GANDA: RANGKUM PDF LOKAL -> TERJEMAHKAN VIA AI
# =====================================================================
def ekstrak_keuangan_otomatis(nama_file):
    print(f"🚀 Memulai Metode Ganda untuk {nama_file}...")
    
    # ---------------------------------------------------------
    # TAHAP 1: RANGKUM DATA (Ekstrak Teks Lokal)
    # ---------------------------------------------------------
    print("📄 Tahap 1: Merangkum data teks dari PDF lokal...")
    teks_rangkuman = ""
    try:
        with open(nama_file, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            jumlah_halaman = len(reader.pages)
            batas_halaman = min(20, jumlah_halaman)
            for page_num in range(batas_halaman):
                halaman = reader.pages[page_num]
                teks = halaman.extract_text()
                if teks:
                    teks_rangkuman += teks + "\n"
                    
    except Exception as e:
        print(f"❌ Gagal merangkum PDF: {e}")
        return {"status": "gagal", "pesan": f"Sistem gagal merangkum PDF lokal: {str(e)}"}

    if not teks_rangkuman.strip():
        return {"status": "gagal", "pesan": "PDF tidak mengandung teks (mungkin dokumen hasil scan gambar/blur)."}

    # ---------------------------------------------------------
    # TAHAP 2: TERJEMAHKAN PAKAI AI GEMINI
    # ---------------------------------------------------------
    print("🧠 Tahap 2: AI sedang menerjemahkan teks menjadi JSON...")
    try:
        prompt = f"""
        Kamu adalah sistem ekstraksi data keuangan. 
        Tugasmu menerjemahkan teks laporan keuangan yang sudah dirangkum ini dan temukan 3 nilai utama:
        1. Total Aset
        2. Laba Bersih Tahun Berjalan (Profit for the year / Laba Rugi Bersih)
        3. Pendapatan (Bunga / Revenue / Total Pendapatan Operasional)

        Aturan ketat: 
        - Jawab HANYA menggunakan struktur JSON murni.
        - Jangan gunakan format markdown ```json.
        - Angka harus berupa integer bulat (tanpa titik atau koma).
        - Jika data tidak ditemukan, isi dengan angka 0.

        Berikut adalah teks laporannya:
        {teks_rangkuman}
        """
        
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt
        )
        
        # Bersihkan balasan AI dari sisa-sisa markdown
        raw_text = response.text.strip()
        raw_text = re.sub(r'```json\s*', '', raw_text)
        raw_text = re.sub(r'```', '', raw_text).strip()
        
        data_json = json.loads(raw_text)
        print("🎉 BINGO! AI berhasil menerjemahkan data.")
        
        return {
            "status": "sukses",
            "metode_ekstraksi": "AI Ekstraksi Ganda (PyPDF + Gemini)",
            "data_keuangan": data_json
        }
        
    except json.JSONDecodeError:
        print(f"❌ AI gagal merespons JSON. Raw text: {response.text}")
        return {"status": "gagal", "pesan": "AI gagal memberikan format JSON yang valid."}
    except Exception as e:
        print(f"❌ Terjadi kesalahan saat menghubungi AI: {e}")
        return {"status": "gagal", "pesan": f"Gagal menerjemahkan via AI: {str(e)}"}

# =====================================================================
# 3. BLOK TESTING
# =====================================================================
if __name__ == "__main__":
    file_test = "potongan_BBRI.pdf"
    if os.path.exists(file_test):
        hasil = ekstrak_keuangan_otomatis(file_test)
        print("\n=== HASIL AKHIR ===")
        print(json.dumps(hasil, indent=4))
    else:
        print("Siap digunakan sebagai modul.")