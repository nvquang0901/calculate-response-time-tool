import aiohttp, os, time, random, io, ssl, json
import zstandard as zstd

async def send_chat(session, i, prompt, CHAT_API, image_paths=None):
    """
    Gửi request chat tới API, hỗ trợ auto-decompress zstd và fallback an toàn.
    """
    history = f"""[{{"role": "assistant", "content": "Xin chào! Tôi là AI Buddy của bạn. Tôi có thể giúp bạn học tập và trả lời các câu hỏi. Bạn cũng có thể gửi file âm thanh hoặc ảnh cho tôi. Bạn cần hỗ trợ gì hôm nay?"}},{{"role": "user", "content": "{prompt}"}}]"""
    class_name = random.randint(1, 12)

    form = aiohttp.FormData()
    form.add_field("user_id", f"user_{i}")
    form.add_field("conversation_id", f"conv_{i}")
    form.add_field("class_name", str(class_name))
    form.add_field("query", prompt)
    form.add_field("history", history)

    # ✅ Nếu có ảnh đính kèm
    if image_paths:
        if isinstance(image_paths, str):
            image_paths = [image_paths]
        for img_path in image_paths:
            if os.path.exists(img_path):
                form.add_field(
                    "files",
                    open(img_path, "rb"),
                    filename=os.path.basename(img_path)
                )

    # ✅ Thiết lập SSL an toàn + timeout
    timeout = aiohttp.ClientTimeout(total=120)
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE

    headers = {
        "Accept-Encoding": "zstd, gzip, deflate, identity"
    }

    start_time = time.time()
    async with session.post(
        CHAT_API,
        data=form,
        ssl=ssl_context,
        timeout=timeout,
        headers=headers,
        raise_for_status=False,
        auto_decompress=False  # 👈 Quan trọng: tắt auto-decompress để tự xử lý
    ) as resp:

        raw_bytes = await resp.read()
        encoding = resp.headers.get("Content-Encoding", "").lower()
        status = resp.status

        try:
            # ✅ Nếu server trả về nén Zstandard (Cloudflare, FastAPI,...)
            if encoding == "zstd":
                dctx = zstd.ZstdDecompressor()
                with dctx.stream_reader(io.BytesIO(raw_bytes)) as reader:
                    decompressed = reader.read()
                res = json.loads(decompressed.decode("utf-8"))

            # ✅ Các dạng khác: gzip, deflate, hoặc none
            else:
                res = json.loads(raw_bytes.decode("utf-8"))

        except Exception as e:
            print("⚠️ Lỗi parse JSON hoặc giải nén:", e)
            res = {"reply": None}
        elapsed = time.time() - start_time
        return res, elapsed


async def send_tts(session, reply_text, TTS_API):
    form = aiohttp.FormData()
    form.add_field("text", reply_text)
    form.add_field("voice", "sage")
    timeout = aiohttp.ClientTimeout(total=120)
    start_time = time.time()
    async with session.post(TTS_API, data=form, timeout=timeout) as resp:
        if resp.status != 200:
            print(f"TTS request failed: {resp.status}")
        await resp.read()
    elapsed = time.time() - start_time
    return elapsed
