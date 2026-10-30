import os

import requests

DEFAULT_BASE_URL = "https://copa.codyssey.kr/v1"
STATUS_HINTS = {401: "인증 실패, API Key 확인", 403: "권한 없음", 404: "엔드포인트/모델 확인", 429: "요청 한도 초과"}


def chat(messages: list[dict], model: str, temperature: float, max_tokens: int) -> str:
    """OpenAI 호환 /chat/completions를 REST로 호출하고 응답 텍스트를 돌려준다."""
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        raise RuntimeError('OPENAI_API_KEY 환경변수가 설정되지 않았습니다.\n예) export OPENAI_API_KEY="YOUR_KEY"')
    url = os.getenv("OPENAI_BASE_URL", DEFAULT_BASE_URL).rstrip("/") + "/chat/completions"
    payload = {"model": model, "messages": messages, "temperature": temperature, "max_tokens": max_tokens}
    try:
        response = requests.post(url, headers={"Authorization": f"Bearer {key}"}, json=payload, timeout=120)
    except requests.RequestException as e:
        raise RuntimeError(f"AI API 요청 실패 (네트워크 오류): {e}") from None

    if not response.ok:
        # 프록시 오류는 원인이 모호하므로 상태 코드와 error.message를 함께 보여준다.
        try:
            error = response.json().get("error")
            message = error.get("message") if isinstance(error, dict) else error
        except ValueError:
            message = None
        hint = STATUS_HINTS.get(response.status_code)
        status = f"HTTP {response.status_code}" + (f", {hint}" if hint else "")
        raise RuntimeError(f"AI API 오류 ({status}): {message or response.text[:300]}")

    try:
        return response.json()["choices"][0]["message"]["content"] or ""
    except (ValueError, KeyError, IndexError, TypeError):
        raise RuntimeError(f"AI API 응답 형식 오류: {response.text[:300]}") from None
