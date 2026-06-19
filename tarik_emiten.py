import requests

def download_semua_emiten():
    # URL resmi API IDX
    url = "https://www.idx.co.id/primary/ListedCompany/GetCompanyProfiles?emitenType=s&start=0&length=9999"
    
    # Header penyamaran
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://www.idx.co.id/"
    }
    
    print("⏳ Lagi nyedot data 900+ emiten dari IDX, tunggu bentar bro...")
    
    try:
        res = requests.get(url, headers=headers, timeout=15)
        if res.status_code == 200:
            json_data = res.json()
            data = json_data.get('data', [])
            
            if not data:
                print("❌ Wah, datanya kosong bro. Struktur API IDX mungkin ganti.")
                print(f"Isi mentahan JSON-nya: {json_data}")
                return

            emiten_list = []
            for d in data:
                # Ekstraksi aman (pake .get), jaga-jaga kalau key-nya diubah IDX
                kode = d.get('EmitenCode') or d.get('KodeEmiten') or d.get('Code') or d.get('emitenCode') or d.get('Symbol')
                nama = d.get('EmitenName') or d.get('NamaEmiten') or d.get('Name') or d.get('emitenName') or d.get('CompanyName')
                
                # Cuma ambil yang kodenya valid
                if kode and nama:
                    emiten_list.append(f"{kode} - {nama}")
                elif kode:
                    emiten_list.append(f"{kode} - Tidak Ada Nama")

            # Hilangkan duplikat dan urutkan A-Z
            emiten_list = sorted(list(set(emiten_list)))
            
            # Simpan ke file
            with open("emiten.txt", "w", encoding="utf-8") as f:
                for emiten in emiten_list:
                    f.write(emiten + "\n")
                    
            print(f"✅ SAKSES BRO! Berhasil menyimpan {len(emiten_list)} emiten ke dalam file 'emiten.txt'")
        else:
            print(f"❌ Gagal ditarik nih. Error Code: {res.status_code}")
            
    except Exception as e:
        print(f"❌ Yah ada error sistem: {e}")

if __name__ == "__main__":
    download_semua_emiten()