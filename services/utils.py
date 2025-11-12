import os, tempfile, zipfile
import io, pandas as pd
import tempfile, os
import streamlit as st

def extract_zip_to_temp(zip_file):
    """Giải nén zip và trả về thư mục gốc chứa test_case_*"""
    temp_dir = tempfile.mkdtemp()
    with zipfile.ZipFile(zip_file, "r") as zip_ref:
        zip_ref.extractall(temp_dir)

    # Tìm thư mục gốc chứa các test_case_*
    for d in os.listdir(temp_dir):
        d_path = os.path.join(temp_dir, d)
        if os.path.isdir(d_path) and any(f.startswith("test_case_") for f in os.listdir(d_path)):
            return d_path
    return temp_dir

def export_to_excel(df, filename):
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Chat Results")
    buffer.seek(0)
    return st.download_button(
        "⬇️ Tải file Excel",
        data=buffer,
        file_name=filename,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

def prepare_uploaded_images(uploaded_imgs):
    import tempfile, os
    temp_dir = tempfile.mkdtemp()
    image_paths = []
    for img in uploaded_imgs:
        path = os.path.join(temp_dir, img.name)
        with open(path, "wb") as f:
            f.write(img.getbuffer())
        image_paths.append(path)
    return image_paths