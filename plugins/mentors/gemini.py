import json
import os
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional, Tuple

from plugins.mentors.base import MentorClient


BASE_URL = "https://generativelanguage.googleapis.com/v1beta"


class GeminiClient(MentorClient):
    """
    Robust Gemini REST client for API-key usage.

    - Uses x-goog-api-key header.
    - Tries multiple model candidates.
    - If a model 404s, it can list models and pick an available one that supports generateContent.
    """

    MODEL_CANDIDATES = [
        "models/gemini-3-flash-preview",
        "models/gemini-2.5-flash-lite",
        "models/gemini-2.5-pro",
        "models/gemini-2.0-flash",
        "models/gemini-1.5-flash",
        "models/gemini-1.5-pro",
    ]

    def __init__(self) -> None:
        self.api_key = os.getenv("GEMINI_API_KEY", "").strip()
        self._cached_model: Optional[str] = None

    def available(self) -> bool:
        return bool(self.api_key)

    def _headers(self) -> Dict[str, str]:
        return {
            "Content-Type": "application/json",
            "x-goog-api-key": self.api_key,
        }

    def _request_json(
        self,
        method: str,
        url: str,
        payload: Optional[Dict[str, Any]] = None,
        timeout: int = 60,
    ) -> Tuple[int, Any, str]:
        data = None
        if payload is not None:
            data = json.dumps(payload).encode("utf-8")

        req = urllib.request.Request(url, data=data, headers=self._headers(), method=method)

        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                raw = resp.read().decode("utf-8", errors="replace")
                try:
                    return resp.status, json.loads(raw), raw
                except Exception:
                    return resp.status, None, raw
        except urllib.error.HTTPError as e:
            body = ""
            try:
                body = e.read().decode("utf-8", errors="replace")
            except Exception:
                body = ""
            try:
                obj = json.loads(body) if body else None
            except Exception:
                obj = None
            return int(e.code), obj, body
        except Exception as e:
            return 0, None, str(e)

    def list_models(self) -> List[Dict[str, Any]]:
        if not self.available():
            return []
        url = f"{BASE_URL}/models"
        status, obj, raw = self._request_json("GET", url, payload=None, timeout=60)
        if status != 200 or not isinstance(obj, dict):
            return []
        models = obj.get("models", [])
        return models if isinstance(models, list) else []

    def pick_generate_model(self) -> Optional[str]:
        models = self.list_models()
        if not models:
            return None

        def supports_generate(model: Dict[str, Any]) -> bool:
            methods = model.get("supportedGenerationMethods", [])
            return isinstance(methods, list) and "generateContent" in methods

        candidates = [m for m in models if supports_generate(m)]
        if not candidates:
            return None

        flash = [m for m in candidates if "flash" in str(m.get("name", "")).lower()]
        chosen = flash[0] if flash else candidates[0]
        name = chosen.get("name")
        return str(name) if name else None

    def generate_text(self, prompt: str, model: Optional[str] = None) -> str:
        if not self.available():
            return "(Gemini unavailable: missing GEMINI_API_KEY)"

        model_try_list: List[str] = []
        if model:
            model_try_list.append(model)
        if self._cached_model and self._cached_model not in model_try_list:
            model_try_list.append(self._cached_model)
        for candidate in self.MODEL_CANDIDATES:
            if candidate not in model_try_list:
                model_try_list.append(candidate)

        last_error = ""
        for candidate in model_try_list:
            url = f"{BASE_URL}/{candidate}:generateContent"
            payload: Dict[str, Any] = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {
                    "temperature": 0.6,
                    "maxOutputTokens": 512,
                },
            }
            status, obj, raw = self._request_json("POST", url, payload=payload, timeout=60)

            if status == 200 and isinstance(obj, dict):
                try:
                    text = obj["candidates"][0]["content"]["parts"][0]["text"]
                    self._cached_model = candidate
                    return str(text)
                except Exception:
                    last_error = f"Parse error for {candidate}: {raw[:200]}"
                    continue

            if status == 404:
                last_error = f"{candidate} -> 404 Not Found"
                continue

            if status != 200:
                last_error = f"{candidate} -> HTTP {status}: {raw[:200]}"
                continue

        picked = self.pick_generate_model()
        if picked:
            url = f"{BASE_URL}/{picked}:generateContent"
            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": 0.6, "maxOutputTokens": 512},
            }
            status, obj, raw = self._request_json("POST", url, payload=payload, timeout=60)
            if status == 200 and isinstance(obj, dict):
                try:
                    text = obj["candidates"][0]["content"]["parts"][0]["text"]
                    self._cached_model = picked
                    return str(text)
                except Exception:
                    return f"(Gemini error: picked model parse failed: {picked})"

            return f"(Gemini error: picked model {picked} failed: HTTP {status}: {raw[:200]})"

        return f"(Gemini error: no working model. last={last_error})"
