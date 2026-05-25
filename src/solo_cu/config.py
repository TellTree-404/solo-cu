"""Configuration: reads environment variables and optional local .env values."""

import os
from pathlib import Path


def _load_dotenv():
    env_file = Path(__file__).parent.parent.parent / ".env"
    if env_file.is_file():
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, val = line.partition("=")
                key, val = key.strip(), val.strip().strip("'\"")
                if key not in os.environ:
                    os.environ[key] = val

_load_dotenv()

def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() not in {"0", "false", "no", "off"}


# Vision model (screen_describe / screen_describe_window)
# Provider-agnostic: supports Qwen-VL, Mimo, or any OpenAI-compatible vision API.
VISION_API_KEY = os.getenv("VISION_API_KEY") or os.getenv("MIMO_API_KEY", "")
VISION_BASE_URL = os.getenv(
    "VISION_BASE_URL",
    os.getenv("MIMO_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1"),
)
VISION_MODEL = os.getenv("VISION_MODEL") or os.getenv("MIMO_MODEL", "qwen3-vl-flash")

# Screen
# Target resolution sent to vision models (XGA, per Anthropic best-practice)
TARGET_WIDTH = int(os.getenv("SOLO_CU_WIDTH", "1024"))
TARGET_HEIGHT = int(os.getenv("SOLO_CU_HEIGHT", "768"))

# Safety
MAX_STEPS_PER_TASK = int(os.getenv("SOLO_CU_MAX_STEPS", "25"))
PYAUTOGUI_FAILSAFE = _env_bool("SOLO_CU_FAILSAFE", True)
ACTION_DELAY = float(os.getenv("SOLO_CU_ACTION_DELAY", "0.3"))
SETTLE_DELAY = float(os.getenv("SOLO_CU_SETTLE_DELAY", "0.8"))
FOCUS_SETTLE_DELAY = float(os.getenv("SOLO_CU_FOCUS_SETTLE_DELAY", "0.6"))
TYPE_PRE_DELAY = float(os.getenv("SOLO_CU_TYPE_PRE_DELAY", "0.15"))

# Browser
BROWSER_CHANNEL = os.getenv("SOLO_CU_BROWSER_CHANNEL", "")
BROWSER_HEADLESS = _env_bool("SOLO_CU_BROWSER_HEADLESS", False)

# Logging
LOG_LEVEL = os.getenv("SOLO_CU_LOG_LEVEL", "INFO")
