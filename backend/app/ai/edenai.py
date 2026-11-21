"""Klient Eden AI (API udostępnione przez organizatorów wyzwania).

Używane endpointy:
  * POST /v3/chat/completions — model językowy (format OpenAI Chat Completions),
  * POST /v3/upload           — tymczasowe wgranie pliku (zwraca file_id),
  * POST /v3/universal-ai     — OCR (model w formacie ocr/ocr/{dostawca}).
"""

from dataclasses import dataclass
from typing import Any

import httpx


class AIError(Exception):
    """Usługa AI niedostępna albo zwróciła błąd — wywołujący przechodzi na tryb zapasowy."""


@dataclass
class EdenAIClient:
    api_key: str
    base_url: str = "https://api.edenai.run/v3"
    timeout_s: float = 120.0

    def _client(self) -> httpx.Client:
        return httpx.Client(base_url=self.base_url, timeout=self.timeout_s,
                            headers={"Authorization": f"Bearer {self.api_key}"})

    def _post(self, path: str, **kwargs: Any) -> dict[str, Any]:
        try:
            with self._client() as client:
                response = client.post(path, **kwargs)
        except httpx.HTTPError as exc:
            raise AIError(f"Eden AI ({path}): błąd połączenia: {exc}") from exc
        if response.status_code >= 400:
            raise AIError(f"Eden AI ({path}): HTTP {response.status_code}: {response.text[:300]}")
        try:
            return response.json()
        except ValueError as exc:
            raise AIError(f"Eden AI ({path}): odpowiedź nie jest JSON-em.") from exc

    def chat(self, model: str, messages: list[dict[str, Any]], *, json_mode: bool = True,
             temperature: float = 0.1, max_tokens: int = 16000) -> str:
        body: dict[str, Any] = {"model": model, "messages": messages, "temperature": temperature,
                                "max_tokens": max_tokens, "stream": False}
        if json_mode:
            body["response_format"] = {"type": "json_object"}
        data = self._post("/chat/completions", json=body)
        try:
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise AIError("Eden AI: nieoczekiwany format odpowiedzi chat/completions.") from exc
        if isinstance(content, list):  # część dostawców zwraca listę fragmentów
            content = "".join(part.get("text", "") for part in content if isinstance(part, dict))
        return content or ""

    def upload(self, data: bytes, filename: str, mime: str, purpose: str = "ocr") -> str:
        result = self._post("/upload", files={"file": (filename, data, mime)}, data={"purpose": purpose})
        file_id = result.get("file_id")
        if not file_id:
            raise AIError("Eden AI: upload nie zwrócił file_id.")
        return str(file_id)

    def ocr(self, file_id: str, model: str, language: str | None = None) -> str:
        payload: dict[str, Any] = {"file": file_id}
        if language:
            payload["language"] = language
        result = self._post("/universal-ai", json={"model": model, "input": payload})
        text = _find_text(result)
        if text is None:
            raise AIError("Eden AI: odpowiedź OCR nie zawiera tekstu.")
        return text


def _find_text(result: Any) -> str | None:
    """Dokumentacja podaje pole `text` na najwyższym poziomie; tolerujemy też opakowanie w `output`."""
    if isinstance(result, dict):
        if isinstance(result.get("text"), str):
            return result["text"]
        for key in ("output", "result", "data"):
            found = _find_text(result.get(key))
            if found is not None:
                return found
    return None
