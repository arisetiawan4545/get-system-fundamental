from google import genai


api_key = "KUNCI_GUE_TARUH_DI_SECRETS"
client = genai.Client(api_key=API_KEY)

def ekstrak_pdf_pakai_ai(nama_file):
    print("🚀 Membangunkan Robot AI Flash 2.5...")
    
    try:
       
        print(f"📂 Mengunggah dokumen {nama_file}...")
        uploaded_file = client.files.upload(file=nama_file)
        
    
        prompt = """
        Kamu adalah sistem ekstraksi data keuangan otomatis.
        Baca dokumen laporan keuangan ini dan temukan 3 nilai utama untuk tahun penuh 2023:
        1. Total Aset
        2. Laba Bersih Tahun Berjalan (Profit for the year)
        3. Pendapatan (Bunga / Revenue)

        Aturan ketat: 
        - Jawab HANYA menggunakan struktur JSON murni.
        - Jangan tambahkan teks pengantar atau penjelasan apa pun.
        - Angka harus berupa integer (bilangan bulat utuh tanpa titik atau koma).
        - Jika data tidak ditemukan, isi dengan angka 0.

        Format:
        {
            "Total_Aset": 1234567890,
            "Laba_Rugi_Bersih": 123456,
            "Pendapatan": 123456
        }
        """
        
        print("🧠 AI sedang membaca tabel dan mengekstrak angka. Tunggu sekitar 3-5 detik...")
        
        
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=[uploaded_file, prompt]
        )
        
        print("\n🎉 BINGO! Ini hasil dari AI:")
        print(response.text)
        
    except Exception as e:
        print(f"❌ Terjadi kesalahan saat menghubungi AI: {str(e)}")


ekstrak_pdf_pakai_ai("potongan_BBRI.pdf")