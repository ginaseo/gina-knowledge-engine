from processor.config import cfg
from processor.llm.cache import LLMCache
from processor.log import get_logger

logger = get_logger(__name__)


class LLMClient:
    def __init__(self):
        cfg.validate_llm()
        self.local = cfg.local_heuristic
        if self.local:
            from processor.llm.local_engine import LocalHeuristicEngine

            self.engine = LocalHeuristicEngine()
        else:
            from openai import OpenAI

            self.client = OpenAI(base_url=cfg.api_url, api_key=cfg.api_key)
        self.cache = LLMCache()
        # Cache keys are hashed from this string, not the raw prompt -- so a
        # backend/model change invalidates old entries instead of silently
        # replaying output from whichever backend answered first.
        self._cache_namespace = "local-heuristic-v1" if self.local else f"remote:{cfg.model}"

    def ask(self, prompt: str) -> str:
        cache_key = f"{self._cache_namespace}\x00{prompt}"
        cached = self.cache.get(cache_key)
        if cached is not None:
            logger.info("[CACHE HIT]")
            return cached

        if self.local:
            logger.info("[LOCAL]")
            answer = self.engine.answer(prompt)
        else:
            logger.info("[LLM]")
            response = self.client.chat.completions.create(
                model=cfg.model,
                messages=[{"role": "user", "content": prompt}],
            )
            answer = response.choices[0].message.content or ""

        answer = self._clean_json(answer)
        self.cache.put(cache_key, answer)
        return answer

    @staticmethod
    def _clean_json(text: str) -> str:
        text = text.strip()
        if text.startswith("```"):
            lines = text.splitlines()
            lines = lines[1:] if lines[0].startswith("```") else lines
            lines = lines[:-1] if lines and lines[-1].strip() == "```" else lines
            text = "\n".join(lines).strip()
        return text

    def __enter__(self) -> "LLMClient":
        return self

    def __exit__(self, *args) -> None:
        self.cache.flush()
