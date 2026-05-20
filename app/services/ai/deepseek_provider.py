"""Proveedor DeepSeek usando una interfaz compatible con chat completions."""

from __future__ import annotations

import json
import urllib.error
import urllib.request

try:
    from config import settings
    from services.ai.provider_base import AIProvider
except ModuleNotFoundError:
    from app.config import settings
    from app.services.ai.provider_base import AIProvider


class DeepSeekProvider(AIProvider):
    """Primer backend real sin acoplar el resto del sistema a DeepSeek."""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
        timeout_seconds: int | None = None,
        temperature: float | None = None,
    ) -> None:
        self.api_key = api_key or settings.ai_api_key
        self.base_url = (base_url or settings.ai_base_url).rstrip("/")
        self.model = model or settings.ai_model
        self.timeout_seconds = timeout_seconds or settings.ai_timeout_seconds
        self.temperature = (
            settings.ai_temperature if temperature is None else temperature
        )

    def generate(self, prompt: str) -> str:
        if not self.api_key:
            raise RuntimeError("No hay AI_API_KEY configurada para el proveedor AI.")

        payload = {
            "model": self.model,
            "temperature": self.temperature,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "Responde solo con JSON valido. No incluyas markdown, "
                        "comentarios ni texto adicional."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
        }

        request = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(  # noqa: S310
                request,
                timeout=self.timeout_seconds,
            ) as response:
                response_payload = json.loads(response.read().decode("utf-8"))
        except urllib.error.URLError as exc:
            raise RuntimeError(
                "No fue posible obtener respuesta del proveedor AI."
            ) from exc

        choices = response_payload.get("choices") or []
        if not choices:
            raise RuntimeError("El proveedor AI no devolvio una respuesta util.")

        message = choices[0].get("message") or {}
        content = message.get("content")
        if not content:
            raise RuntimeError("La respuesta del proveedor AI no contiene contenido.")

        return str(content)
