import streamlit as st
import asyncio
from services.evaluate import evaluate_image, evaluate_folder_zip
import aiohttp
from services.chat_service import send_chat, send_tts
from services.utils import extract_zip_to_temp, export_to_excel, prepare_uploaded_images
import aiohttp, asyncio, pandas as pd
from io import StringIO
import nest_asyncio
from config import DOMAIN_OPTIONS, EXPORT_FILE_NAME

# Streamlit config
st.set_page_config(page_title="Respone Time Tool", page_icon="🧠", layout="centered")
st.title("Evaluate Response Time")

nest_asyncio.apply()
# Chọn môi trường
env_choice = st.selectbox("🌍 Chọn môi trường test:", list(DOMAIN_OPTIONS.keys()))
base_domain = DOMAIN_OPTIONS[env_choice]
CHAT_API = f"{base_domain}/api/chat/chat"
TTS_API = f"{base_domain}/api/speak/tts"


log_box = st.empty()
progress_box = st.empty()

# Mode selection
mode = st.radio("Chọn chế độ:", ["Texts", "Images"])
progress_box = st.empty()
log_box = st.empty()

if mode == "Texts":
    st.subheader("🧠 Đánh giá Text only")
    input_method = st.radio("Chọn phương thức nhập:", ["Nhập trực tiếp", "Tải file TXT"])
    prompts = []

    # Nhập dữ liệu
    if input_method == "Nhập trực tiếp":
        text_input = st.text_area("Nhập mỗi câu hỏi 1 dòng")
        prompts = [p.strip() for p in text_input.splitlines() if p.strip()]
    else:
        uploaded_file = st.file_uploader("Tải file TXT", type=["csv","txt"])
        if uploaded_file:
            if uploaded_file.name.lower().endswith(".csv"):
                df = pd.read_csv(uploaded_file)
                if "prompt" in df.columns:
                    prompts = df["prompt"].dropna().astype(str).tolist()
                else:
                    st.warning("⚠️ CSV phải có cột 'prompt'")
            else:
                prompts = [line.strip() for line in uploaded_file.read().decode("utf-8").splitlines() if line.strip()]
    total_prompts = len(prompts)
    st.write(f"📊 Tổng số câu hỏi: {total_prompts}")
    # Button duy nhất
    start_eval = st.button("🚀 Bắt đầu đánh giá")
    if start_eval:
        if not prompts:
            st.warning("⚠️ Nhập ít nhất 1 câu hỏi hoặc upload file .txt")
        else:
            st.info("⏳ Đang đánh giá, vui lòng chờ...")
            progress_bar = st.progress(0)
            log_box = st.empty()
            results = []

            # Hàm chạy async
            async def run_evaluation(prompts):
                
                async with aiohttp.ClientSession() as session:
                    for idx, prompt in enumerate(prompts, start=1):
                        log_box.text(f"🟡 Đang xử lý câu {idx}/{len(prompts)}: {prompt[:50]}...")
                        chat_res, chat_time = await send_chat(session, idx, prompt, CHAT_API)
                        reply = chat_res.get("reply", "")
                        tts_time = await send_tts(session, reply, TTS_API) if reply else 0
                        results.append({
                            "idx": idx,
                            "prompt": prompt,
                            "chat_time": chat_time,
                            "tts_time": tts_time,
                            "reply": reply
                        })
                        progress_bar.progress(idx / len(prompts))
                        await asyncio.sleep(0.05)

            
            nest_asyncio.apply()
            loop = asyncio.get_event_loop()
            loop.run_until_complete(run_evaluation(prompts))

            st.success("✅ Hoàn tất đánh giá!")

            # Trung bình
            avg_chat = sum(r["chat_time"] for r in results)/len(results)
            avg_tts = sum(r["tts_time"] for r in results)/len(results)
            st.markdown(f"**Tổng số câu hỏi:** {total_prompts} câu | **AVG No TTS:** {avg_chat:.2f}s | **AVG Have TTS:** {(avg_chat+avg_tts):.2f}s")

            # Tạo DataFrame từ kết quả
            df_results = pd.DataFrame(results)
            df_results["Chat Time No TTS"] = df_results["chat_time"]
            df_results["TTS Time"] = df_results["tts_time"]
            df_results["Chat Time have TTS"] = df_results["chat_time"] + df_results["tts_time"]

            # Sắp xếp cột chuẩn
            df_results = df_results[["idx", "prompt", "Chat Time No TTS", "TTS Time", "Chat Time have TTS", "reply"]]
            df_results.rename(columns={
                "idx": "STT",
                "prompt": "Prompt",
                "reply": "Reply"
            }, inplace=True)

            # Xuất Excel với UTF-8 để hiển thị tiếng Việt
            export_to_excel(df_results, EXPORT_FILE_NAME)
            


elif mode == "Images":
    st.subheader("🖼️ Đánh giá Images")

    # Chọn kiểu xử lý
    eval_type = st.radio("Chọn kiểu đánh giá:", ["Random ghép ảnh với câu hỏi", "Theo Folder .zip"])
    progress_box = st.empty()
    log_box = st.empty()
    if eval_type == "Random ghép ảnh với câu hỏi":
        uploaded_imgs = st.file_uploader("Tải lên nhiều ảnh:", type=["jpg","png"], accept_multiple_files=True)
        uploaded_txt = st.file_uploader("Tải file .txt chứa câu hỏi:", type=["txt"])

        if uploaded_imgs and uploaded_txt:
            image_paths = prepare_uploaded_images(uploaded_imgs)
            prompts = uploaded_txt.read().decode("utf-8").splitlines()
            total_prompts = len(prompts)

            if total_prompts == 0:
                st.warning("⚠️ File TXT không có câu hỏi nào!")
            else:
                if st.button("🚀 Bắt đầu đánh giá ngẫu nhiên bằng cách ghép random câu hỏi vs ảnh"):
                    st.info(f"⏳ Đang xử lý {total_prompts} câu hỏi với {len(image_paths)} ảnh...")

                    import random
                    paired_image_paths = [random.choice(image_paths) for _ in range(total_prompts)]

                    results = asyncio.run(evaluate_image(prompts, paired_image_paths, total_prompts, progress_box, log_box, CHAT_API, TTS_API))
                    st.success("✅ Hoàn tất đánh giá!")

                    # DataFrame
                    df_results = pd.DataFrame(results, columns=["STT", "Ảnh", "Câu hỏi", "Chat Time", "Reply", "TTS Time"])
                    df_results["TTS Time"] = df_results["TTS Time"].apply(lambda x: float(x) if x is not None else 0.0)
                    df_results["Tổng (s)"] = df_results["Chat Time"] + df_results["TTS Time"]

                    st.markdown(f"**Trung bình Chat:** {df_results['Chat Time'].mean():.2f}s | "
                                f"**Trung bình TTS:** {df_results['TTS Time'].mean():.2f}s | "
                                f"**Tổng trung bình:** {df_results['Tổng (s)'].mean():.2f}s")

                    # Sắp xếp cột
                    df_results = df_results[["STT", "Ảnh", "Câu hỏi", "Chat Time", "Tổng (s)", "Reply"]]

                    # Excel
                    export_to_excel(df_results, EXPORT_FILE_NAME)

    elif eval_type == "Theo Folder .zip":
        st.markdown("""
        **📦 Cấu trúc file .zip cần tuân thủ:**
        ```
        my_folder.zip
        └── dataset/
            ├── test_case_1/
            │   ├── query.txt
            │   ├── images/
            │   │   ├── image_1.jpg
            │   │   ├── image_2.png
            ├── test_case_2/
            │   ├── query.txt
            │   ├── images/
            │   │   ├── image_1.png
        ```
        """)

        uploaded_zip = st.file_uploader("📁 Tải lên file ZIP chứa các case:", type=["zip"])

        if uploaded_zip and st.button("🚀 Bắt đầu đánh giá Folder"):
            st.info("⏳ Đang xử lý, vui lòng chờ...")

            temp_folder = extract_zip_to_temp(uploaded_zip)

            # Tạo progress bar
            progress_bar = st.progress(0)
            log_box = st.empty()
            
            nest_asyncio.apply()
            results = asyncio.run(evaluate_folder_zip(temp_folder, progress_bar, log_box, CHAT_API, TTS_API))

            if not results:
                st.warning("⚠️ Không có kết quả nào.")
            else:
                st.success(f"✅ Hoàn tất {len(results)} case.")

                # Tạo DataFrame
                df_results = pd.DataFrame(results)
                df_results["Tổng Chat + TTS (s)"] = df_results["chat_time"] + df_results["tts_time"]

                # Chọn cột và đổi tên
                df_results = df_results[["id", "case_name", "num_images", "chat_time", "Tổng Chat + TTS (s)", "reply"]]
                df_results.rename(columns={
                    "id": "STT",
                    "case_name": "Case",
                    "num_images": "Số ảnh",
                    "chat_time": "Chat Time (s)",
                    "reply": "Reply"
                }, inplace=True)

                # Xuất Excel chuẩn UTF-8
                export_to_excel(df_results, EXPORT_FILE_NAME)
