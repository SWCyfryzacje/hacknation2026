"""Klient Eden AI (API udostępnione przez organizatorów wyzwania).

Używane endpointy:
  * POST /v3/chat/completions — model językowy (format OpenAI Chat Completions),
  * POST /v3/upload           — tymczasowe wgranie pliku (zwraca file_id),
  * POST /v3/universal-ai     — OCR (model w formacie ocr/ocr/{dostawca}).
"""

import re
import time
from dataclasses import dataclass, field
from typing import Any

import httpx


class AIError(Exception):
    """Usługa AI niedostępna albo zwróciła błąd — wywołujący przechodzi na tryb zapasowy."""

    def __init__(self, message: str, *, status: int | None = None, retry_after: str | None = None) -> None:
        super().__init__(message)
        self.status = status
        self.retry_after = retry_after


def _output_limit(message: str) -> int | None:
    """Limit długości odpowiedzi podany przez dostawcę w komunikacie błędu (np. „max_output_tokens 25000”)."""
    match = re.search(r"max_output_tokens\D{0,5}(\d{3,7})", message) or re.search(
        r"(?:cannot|must) (?:be )?(?:greater|more) than\D{0,30}(\d{3,7})", message)
    return int(match.group(1)) if match else None


def _retry_delay(retry_after: str | None, attempt: int, base: float) -> float:
    """Czas odczekania: nagłówek Retry-After (sekundy), a gdy go brak — base · 2^próba, maks. 60 s."""
    try:
        return min(float(retry_after), 60.0) if retry_after else min(base * 2**attempt, 60.0)
    except ValueError:
        return min(base * 2**attempt, 60.0)


@dataclass
class EdenAIClient:
    api_key: str
    base_url: str = "https://api.edenai.run/v3"
    timeout_s: float = 120.0
    # Zużycie tokenów zsumowane ze wszystkich wywołań tego klienta (pole `usage` odpowiedzi chat/completions).
    usage: dict[str, int] = field(default_factory=lambda: {"calls": 0, "prompt_tokens": 0, "completion_tokens": 0})
    max_retries: int = 4  # ponowienia przy limitowaniu przez dostawcę (HTTP 429/503)
    retry_base_s: float = 5.0

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
            raise AIError(f"Eden AI ({path}): HTTP {response.status_code}: {response.text[:300]}",
                          status=response.status_code, retry_after=response.headers.get("retry-after"))
        try:
            return response.json()
        except ValueError as exc:
            raise AIError(f"Eden AI ({path}): odpowiedź nie jest JSON-em.") from exc

    def chat(self, model: str, messages: list[dict[str, Any]], *, json_mode: bool = True,
             temperature: float = 0.1, max_tokens: int = 16000, fallbacks: list[str] | None = None) -> str:
        body: dict[str, Any] = {"model": model, "messages": messages, "temperature": temperature,
                                "max_tokens": max_tokens, "stream": False}
        if fallbacks:
            body["fallbacks"] = fallbacks
        if json_mode:
            body["response_format"] = {"type": "json_object"}
        data = self._post_with_retry(body)
        self.usage["calls"] += 1
        for key in ("prompt_tokens", "completion_tokens"):
            self.usage[key] += int((data.get("usage") or {}).get(key) or 0)
        try:
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise AIError("Eden AI: nieoczekiwany format odpowiedzi chat/completions.") from exc
        if isinstance(content, list):  # część dostawców zwraca listę fragmentów
            content = "".join(part.get("text", "") for part in content if isinstance(part, dict))
        return content or ""

    def _post_with_retry(self, body: dict[str, Any]) -> dict[str, Any]:
        """Ponawia przy limitowaniu (429/503) z wykładniczym odczekaniem; gdy model nie obsługuje trybu JSON
        (`response_format`) albo ma niższy limit odpowiedzi, ponawia z poprawionym żądaniem."""
        for attempt in range(self.max_retries + 1):
            try:
                return self._post("/chat/completions", json=body)
            except AIError as exc:
                if exc.status == 400 and "response_format" in body and "response_format" in str(exc):
                    body = {k: v for k, v in body.items() if k != "response_format"}
                    continue
                limit = _output_limit(str(exc))
                if exc.status == 400 and limit and limit < body.get("max_tokens", 0):
                    body = body | {"max_tokens": limit}  # model ma niższy limit odpowiedzi niż żądany
                    continue
                if exc.status not in (429, 503) or attempt == self.max_retries:
                    raise
                time.sleep(_retry_delay(exc.retry_after, attempt, self.retry_base_s))
        raise AIError("Eden AI: wyczerpano ponowienia.")  # nieosiągalne — pętla zawsze zwraca albo rzuca

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
