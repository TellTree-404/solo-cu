"""Vision model client — supports Qwen-VL, Mimo, or any OpenAI-compatible vision API.

Configurable via VISION_API_KEY / VISION_BASE_URL / VISION_MODEL env vars.
"""

import logging

import httpx
from openai import OpenAI

from .config import VISION_API_KEY, VISION_BASE_URL, VISION_MODEL

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a computer vision assistant for a GUI automation agent.
You will receive a cropped screenshot of a single application window.

Provide a structured description optimized for automated interaction:

1. Window title and type
2. Interactive elements with pixel coordinates (top-left of image is 0,0):
   - buttons, input fields, checkboxes, dropdown menus, icons
   - Format each as: element_name: (x, y) — use the CENTER of the element
3. Visible text content and its location
4. Which element is likely focused/active

Be concise. Every coordinate must be within the visible image bounds."""


def describe_screen(base64_image: str, original_width: int = 0, original_height: int = 0) -> str:
    """Send a screenshot to the vision model and get a text description.

    Raises ValueError if VISION_API_KEY is not set.
    """
    if not VISION_API_KEY:
        raise ValueError(
            "VISION_API_KEY environment variable is not set. "
            "Configure it in .env or your MCP server config."
        )

    http_client = httpx.Client(transport=httpx.HTTPTransport(proxy=None))
    client = OpenAI(
        api_key=VISION_API_KEY,
        base_url=VISION_BASE_URL,
        http_client=http_client,
    )

    logger.info("Calling %s for screen description", VISION_MODEL)

    response = client.chat.completions.create(
        model=VISION_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Describe this application window. List all interactive elements with their pixel coordinates."},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{base64_image}",
                        },
                    },
                ],
            },
        ],
        max_completion_tokens=2048,
    )

    content = response.choices[0].message.content or ""
    logger.info(
        "Vision response: %d chars, %d tokens",
        len(content),
        response.usage.total_tokens if response.usage else 0,
    )
    return content.strip()
