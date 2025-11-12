import os
import aiohttp
import asyncio
import random
from services.chat_service import send_chat, send_tts
import streamlit as st


async def evaluate_folder_zip(folder_path, progress_bar, log_box, CHAT_API, TTS_API):
    results = []
    pair_idx = 1

    # Tính tổng số prompt để chạy progress
    total_prompts = 0
    for case_name in os.listdir(folder_path):
        case_path = os.path.join(folder_path, case_name)
        prompt_file = os.path.join(case_path, "query.txt")
        if os.path.exists(prompt_file):
            total_prompts += len(open(prompt_file, "r", encoding="utf-8").read().splitlines())

    if total_prompts == 0:
        log_box.write("⚠️ Không tìm thấy prompt nào trong folder.")
        return results

    processed_prompts = 0

    async with aiohttp.ClientSession() as session:
        for case_name in sorted(os.listdir(folder_path)):
            case_path = os.path.join(folder_path, case_name)
            if not os.path.isdir(case_path):
                continue
            prompt_file = os.path.join(case_path, "query.txt")
            image_folder = os.path.join(case_path, "images")
            if not os.path.exists(prompt_file) or not os.path.exists(image_folder):
                log_box.write(f"⚠️ Case `{case_name}` thiếu query.txt hoặc folder images/")
                continue

            prompts = open(prompt_file, "r", encoding="utf-8").read().splitlines()
            image_paths = [os.path.join(image_folder, f) for f in sorted(os.listdir(image_folder))
                        if f.lower().endswith((".png", ".jpg", ".jpeg"))]

            for prompt in prompts:
                chat_res, chat_time = await send_chat(session, pair_idx, prompt, CHAT_API, image_paths)
                reply = chat_res.get("reply", "")
                tts_time = await send_tts(session, reply, TTS_API) if reply else 0.0

                results.append({
                    "id": pair_idx,
                    "case_name": case_name,
                    "num_images": len(image_paths),
                    "chat_time": chat_time,
                    "tts_time": tts_time,
                    "reply": reply
                })

                log_box.text(f"🟢 Xử lý case {pair_idx}/{total_prompts} | {case_name} | Chat: {chat_time:.2f}s | TTS: {tts_time:.2f}s")

                pair_idx += 1
                processed_prompts += 1
                progress_bar.progress(min(processed_prompts / total_prompts, 1.0))

                await asyncio.sleep(0.05)

    return results
# ================== Evaluate functions ==================
async def evaluate_text(prompts, progress_box, log_box, CHAT_API, TTS_API):
    chat_times, tts_times = [], []
    n = len(prompts)
    progress_bar = st.progress(0)
    async with aiohttp.ClientSession() as session:
        for i, prompt in enumerate(prompts, start=1):
            progress_box.write(f"🟡 Đang xử lý câu {i}/{n}: `{prompt[:50]}...`")
            chat_res, chat_elapsed = await send_chat(session, i, prompt, CHAT_API)
            chat_times.append((i, prompt, chat_elapsed))
            reply = chat_res.get("reply", "")
            if reply:
                tts_elapsed = await send_tts(session, reply, TTS_API)
                tts_times.append((i, reply, tts_elapsed))
                log_box.write(f"✅ Câu {i} | Chat: {chat_elapsed:.2f}s | TTS: {tts_elapsed:.2f}s | Tổng: {chat_elapsed+tts_elapsed:.2f}s")
            else:
                tts_elapsed = 0
                log_box.write(f"⚠️ Câu {i} không có reply | Chat: {chat_elapsed:.2f}s")
            progress_bar.progress(i / n)
            await asyncio.sleep(0.05)
    progress_box.empty()
    progress_bar.empty()
    return chat_times, tts_times

# async def evaluate_image(prompts, images, n_samples, progress_box, log_box, CHAT_API, TTS_API):
#     results = []
#     n = n_samples
#     progress_bar = st.progress(0)
#     samples = random.sample(
#         list(zip(images * (len(prompts)//len(images)+1), prompts * (len(images)//len(prompts)+1))), n
#     )

#     async with aiohttp.ClientSession() as session:
#         for i, (img, prompt) in enumerate(samples, start=1):
#             progress_box.write(f"🖼️ Đang gửi ảnh {os.path.basename(img)} + câu: `{prompt[:50]}...`")
#             chat_res, chat_elapsed = await send_chat(session, i, prompt, CHAT_API, image_paths=img)
            
#             reply = chat_res.get("reply", "")
#             if reply:
#                 tts_elapsed = await send_tts(session, reply, TTS_API)
#             else:
#                 tts_elapsed = 0
            
#             results.append((i, os.path.basename(img), prompt, chat_elapsed, reply, tts_elapsed))
#             log_box.write(
#                 f"✅ Cặp {i}: {os.path.basename(img)} | {prompt[:30]}... → "
#                 f"Chat: {chat_elapsed:.2f}s | TTS: {tts_elapsed:.2f}s | Tổng: {chat_elapsed+tts_elapsed:.2f}s"
#                 if reply else
#                 f"⚠️ Cặp {i}: {os.path.basename(img)} | {prompt[:30]}... không có reply | Chat: {chat_elapsed:.2f}s"
#             )

#             # cập nhật progress bar, luôn <= 1
#             progress_bar.progress(min(i / n, 1.0))
#             await asyncio.sleep(0.05)

#     progress_box.empty()
#     progress_bar.empty()
#     return results
async def evaluate_image(prompts, images, n_samples, progress_box, log_box, CHAT_API, TTS_API):
    """Đánh giá nhiều ảnh + prompt, trả về kết quả list"""
    results = []
    progress_bar = st.progress(0)

    samples = random.sample(
        list(zip(images * (len(prompts)//len(images)+1), prompts * (len(images)//len(prompts)+1))),
        n_samples
    )

    async with aiohttp.ClientSession() as session:
        for i, (img, prompt) in enumerate(samples, start=1):
            progress_box.write(f"🖼️ Đang gửi ảnh `{os.path.basename(img)}` + câu: `{prompt[:50]}...`")
            chat_res, chat_elapsed = await send_chat(session, i, prompt, CHAT_API, image_paths=img)
            reply = chat_res.get("reply")
            tts_elapsed = await send_tts(session, reply, TTS_API) if reply else 0.0

            results.append((i, os.path.basename(img), prompt, chat_elapsed, reply, tts_elapsed))
            log_box.write(
                f"✅ Cặp {i}: {os.path.basename(img)} | {prompt[:30]}... → Chat: {chat_elapsed:.2f}s | "
                f"TTS: {tts_elapsed:.2f}s | Tổng: {chat_elapsed+tts_elapsed:.2f}s" if reply else
                f"⚠️ Cặp {i}: {os.path.basename(img)} | {prompt[:30]}... không có reply | Chat: {chat_elapsed:.2f}s"
            )

            # Cập nhật progress bar, giá trị phải từ 0 → 1
            progress_value = min(i / n_samples, 1.0)
            progress_bar.progress(progress_value)

            await asyncio.sleep(0.05)

    progress_box.empty()
    progress_bar.empty()
    return results


async def evaluate_folder(folder_path, progress_box, log_box, CHAT_API, TTS_API):
    results = []
    pair_idx = 1
    async with aiohttp.ClientSession() as session:
        for case_name in sorted(os.listdir(folder_path)):
            case_path = os.path.join(folder_path, case_name)
            if not os.path.isdir(case_path):
                continue
            prompt_file = os.path.join(case_path, "query.txt")
            image_folder = os.path.join(case_path, "images")
            if not os.path.exists(prompt_file) or not os.path.exists(image_folder):
                log_box.write(f"⚠️ Case `{case_name}` thiếu query.txt hoặc folder images/")
                continue
            prompts = open(prompt_file, "r", encoding="utf-8").read().splitlines()
            image_paths = [os.path.join(image_folder, f) for f in sorted(os.listdir(image_folder))
                           if f.lower().endswith((".png", ".jpg", ".jpeg"))]
            for prompt in prompts:
                chat_res, chat_time = await send_chat(session, pair_idx, prompt, CHAT_API, image_paths)
                reply = chat_res.get("reply", "")
                tts_time = await send_tts(session, reply, TTS_API) if reply else None
                results.append({
                    "id": pair_idx,
                    "case_name": case_name,
                    "num_images": len(image_paths),
                    "chat_time": chat_time,
                    "tts_time": tts_time if tts_time is not None else 0.0,
                    "reply": reply
                })

                log_box.write(f"✅ Cặp {pair_idx} | Chat: {chat_time:.2f}s | TTS: {tts_time:.2f}s" if reply else f"⚠️ Cặp {pair_idx} không có reply | Chat: {chat_time:.2f}s")
                pair_idx += 1
                await asyncio.sleep(0.05)
    progress_box.empty()
    return results
