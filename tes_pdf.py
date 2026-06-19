import fitz  # PyMuPDF

def potong_pdf_keuangan(nama_file_pdf, output_pdf):
    print(f"Membuka file: {nama_file_pdf}...")
    try:
        dokumen = fitz.open(nama_file_pdf)
    except Exception as e:
        print(f"Gagal membuka PDF: {e}")
        return

    halaman_target = set()
    
    # Kata kunci yang biasa dipakai akuntan
    kata_kunci = [
        "laporan posisi keuangan", 
        "statement of financial position",
        "laporan laba rugi",
        "statement of profit or loss"
    ]

    print("Mencari halaman inti (Neraca & Laba Rugi)...")
    
    # Kita cuma cari di 20 halaman pertama biar super ngebut
    # (Karena laporan utama pasti ada di depan, sisanya cuma "Catatan/Notes")
    batas_halaman = min(20, len(dokumen)) 
    
    for nomor_halaman in range(batas_halaman):
        halaman = dokumen[nomor_halaman]
        teks = halaman.get_text("text").lower()
        
        for kata in kata_kunci:
            if kata in teks:
                print(f"✅ Ketemu '{kata}' di Halaman {nomor_halaman + 1}")
                halaman_target.add(nomor_halaman)
                break # Lanjut ke halaman berikutnya

    if not halaman_target:
        print("❌ Gagal menemukan halaman laporan keuangan utama.")
        return

    # Urutkan halaman biar rapi
    list_halaman = sorted(list(halaman_target))
    print(f"Mengekstrak Halaman: {list_halaman}")

    # Bikin dokumen PDF baru khusus menampung halaman yang dipotong
    dokumen_baru = fitz.open()
    for hal in list_halaman:
        dokumen_baru.insert_pdf(dokumen, from_page=hal, to_page=hal)

    dokumen_baru.save(output_pdf)
    dokumen_baru.close()
    dokumen.close()
    
    print(f"🎉 SUKSES! File potongan berhasil disimpan sebagai: {output_pdf}")

# --- JALANKAN FUNGSI ---
# Pastikan nama file di bawah ini sesuai dengan nama PDF BBRI lu
file_input = "FinancialStatement-2023-Tahunan-BBRI.pdf" 
file_output = "potongan_BBRI.pdf"

potong_pdf_keuangan(file_input, file_output)