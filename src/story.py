"""Generate a short story from detected objects using an LLM.

Supports:
- OpenAI Chat Completions (requires OPENAI_API_KEY)
- Hugging Face Inference API text-generation (requires HF_API_TOKEN and model id)
"""

import os
from typing import List, Dict, Literal, Optional

from openai import OpenAI
import requests
from huggingface_hub import InferenceClient


def _objects_to_bullets(objects: List[Dict]) -> str:
    lines = []
    for obj in objects:
        label = obj.get("label", "object")
        box = obj.get("box", (0, 0, 0, 0))
        area = max(1, (box[2] - box[0]) * (box[3] - box[1]))
        lines.append(f"- {label} at {box} (area ~{area} px^2)")
    return "\n".join(lines) if lines else "- none"


def generate_story(
    objects: List[Dict],
    extra_note: str | None = None,
    provider: Literal["openai", "huggingface", "huggingface_openai"] = "openai",
    model: str = "gpt-4o-mini",
    hf_model: str = "HuggingFaceH4/zephyr-7b-beta",
    temperature: float = 0.8,
    max_tokens: int = 220,
) -> str:
    """
    Turn detected objects into a short hiding-story.

    provider:
      - "openai": uses OpenAI Chat Completions (OPENAI_API_KEY)
      - "huggingface": uses HF Inference API text-generation (HF_API_TOKEN)
      - "huggingface_openai": uses OpenAI client pointed at HF router (HF_TOKEN or HF_API_TOKEN)
    """
    object_text = _objects_to_bullets(objects)

    system = (
        "You are a concise scene writer. "
        "Given a list of detected objects, craft a short (<=120 words) story "
        "describing the room and suggesting two plausible hiding spots for Batman. "
        "Stay grounded in the listed objects; don't invent new furniture."
    )
    user = f"Detected objects:\n{object_text}\nWrite the story now."
    if extra_note:
        user += f"\nExtra note: {extra_note}"

    if provider == "openai":
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("Set OPENAI_API_KEY to call the OpenAI API.")
        client = OpenAI(api_key=api_key)
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return resp.choices[0].message.content.strip()

    if provider == "huggingface":
        hf_token = os.getenv("HF_API_TOKEN")
        if not hf_token:
            raise RuntimeError("Set HF_API_TOKEN to call the Hugging Face Inference API.")
        client = InferenceClient(model=hf_model, token=hf_token)
        prompt = f"{system}\nUser: {user}\nAssistant:"
        try:
            text = client.text_generation(
                prompt,
                max_new_tokens=max_tokens,
                temperature=temperature,
                do_sample=True,
                return_full_text=False,
            )
        except Exception as e:
            raise RuntimeError(f"HF API error: {e}") from e
        return text.strip()

    if provider == "huggingface_openai":
        hf_token = os.getenv("HF_TOKEN") or os.getenv("HF_API_TOKEN")
        if not hf_token:
            raise RuntimeError("Set HF_TOKEN (or HF_API_TOKEN) for HF OpenAI-compatible endpoint.")
        base_url = os.getenv("HF_OPENAI_BASE", "https://router.huggingface.co/v1")
        client = OpenAI(api_key=hf_token, base_url=base_url)
        resp = client.chat.completions.create(
            model=hf_model,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return resp.choices[0].message.content.strip()

    raise RuntimeError(f"Provider {provider} not handled.")
    raise ValueError(f"Unknown provider: {provider}")
