import os
import subprocess
import uuid
import base64
from fastapi import FastAPI, UploadFile, File, HTTPException

app = FastAPI()

# Đường dẫn đến thực thi của LibreOffice
# - Docker/Linux: mặc định "soffice" (có trong PATH khi cài libreoffice)
# - Windows: có thể set env LIBREOFFICE_PATH hoặc dùng default bên dưới
_DEFAULT_WINDOWS_SOFFICE = r"C:\Program Files\LibreOffice\program\soffice.exe"
LIBREOFFICE_PATH = os.getenv("LIBREOFFICE_PATH") or (
    _DEFAULT_WINDOWS_SOFFICE if os.name == "nt" else "soffice"
)

@app.post("/convert-excel-to-pdf")
async def convert_to_pdf(file: UploadFile = File(...)):
    # Chỉ cho phép file Word & Excel
    allowed_exts = {".doc", ".docx", ".xls", ".xlsx", ".xlsm", ".xlsb"}
    _, ext = os.path.splitext(file.filename or "")
    ext = ext.lower()

    if ext not in allowed_exts:
        raise HTTPException(
            status_code=400,
            detail="Chỉ hỗ trợ chuyển đổi file Word/Excel (doc, docx, xls, xlsx, xlsm, xlsb).",
        )

    # Giới hạn dung lượng file: tối đa 10MB
    max_bytes = 10 * 1024 * 1024

    # 1. Tạo tên file tạm duy nhất để tránh xung đột khi nhiều người cùng dùng
    unique_id = str(uuid.uuid4())
    temp_excel = f"temp_{unique_id}_{file.filename}"
    output_dir = f"out_{unique_id}"
    
    # Tạo thư mục output tạm
    os.makedirs(output_dir, exist_ok=True)

    try:
        # 2. Lưu file Excel tạm thời xuống đĩa
        total_bytes = 0
        chunk_size = 1024 * 1024  # 1MB
        with open(temp_excel, "wb") as buffer:
            while True:
                chunk = await file.read(chunk_size)
                if not chunk:
                    break
                total_bytes += len(chunk)
                if total_bytes > max_bytes:
                    raise HTTPException(
                        status_code=413,
                        detail="Dung lượng file tối đa là 10MB.",
                    )
                buffer.write(chunk)

        # 3. Gọi lệnh LibreOffice để convert sang PDF
        # --headless: chạy ngầm không hiện cửa sổ
        # --convert-to pdf: định dạng đầu ra
        # --outdir: nơi chứa file PDF sau khi xong
        command = [
            LIBREOFFICE_PATH,
            "--headless",
            "--convert-to", "pdf",
            "--outdir", output_dir,
            temp_excel
        ]
        
        process = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        if process.returncode != 0:
            raise HTTPException(status_code=500, detail="Lỗi khi convert bằng LibreOffice")

        # 4. Tìm file PDF vừa tạo và chuyển sang Base64
        # LibreOffice sẽ tạo file PDF trùng tên với file Excel nhưng đuôi .pdf
        pdf_filename = os.path.splitext(temp_excel)[0] + ".pdf"
        pdf_path = os.path.join(output_dir, pdf_filename)

        with open(pdf_path, "rb") as pdf_file:
            base64_pdf = base64.b64encode(pdf_file.read()).decode('utf-8')

        return {
            "filename": file.filename,
            "base64": base64_pdf
        }

    finally:
        # 5. Dọn dẹp: Xóa sạch file và thư mục tạm
        if os.path.exists(temp_excel): os.remove(temp_excel)
        if os.path.exists(output_dir):
            import shutil
            shutil.rmtree(output_dir)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8900)