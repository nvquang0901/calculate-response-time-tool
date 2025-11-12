# config.py
"""
llm_eval_tool/
├── app.py                 # Streamlit main app
├── config.py              # Cấu hình, domain mapping, API
├── services/
│   ├── chat_service.py    # Hàm send_chat / send_tts
│   ├── evaluator.py       # Các hàm evaluate_text, evaluate_image, evaluate_folder
│   └── utils.py           # Hàm tiện ích: extract zip, save temp images, CSV
└── requirements.txt
"""
DOMAIN_OPTIONS = {
    "https://web.test.aibuddy.vn/chat": "https://fastapi.test.aibuddy.vn",
    "https://web-sit.aibuddy.vn/chat": "https://fastapi-sit.aibuddy.vn"
}

DEFAULT_VOICE = "sage"
CHAT_TIMEOUT = 120
TTS_TIMEOUT = 120
EXPORT_FILE_NAME = "response_time_result.xlsx"