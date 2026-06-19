# Pakai mesin Python versi 3.10
FROM python:3.10

# Bikin folder kerja
WORKDIR /code

# Copy daftar belanjaan dan install
COPY ./requirements.txt /code/requirements.txt
RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

# Copy semua file kode lu
COPY . .

# Tekan tombol ON (PENTING: Hugging Face wajib pakai port 7860)
# GANTI kata 'main' di bawah ini dengan nama file FastAPI lu (contoh: api_backend:app)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "7860"]