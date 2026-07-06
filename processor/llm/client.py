from openai import OpenAI

from processor.config import cfg
from processor.llm.cache import LLMCache
from processor.log import get_logger

logger = get_logger(__name__)


class LLMClient:

    def __init__(self):
        cfg.validate_llm()
        self.client = OpenAI(base_url=cfg.api_url, api_key=cfg.api_key)
        self.cache = LLMCache()

    def ask(self, prompt: str) -> str:
        cached = self.cache.get(prompt)
        if cached is not None:
            logger.info("[CACHE HIT]")
            return cached

        logger.info("[LLM]")
        response = self.client.chat.completions.create(
            model=cfg.model,
            messages=[{"role": "user", "content": prompt}],
        )
        answer = response.choices[0].message.content
        self.cache.put(prompt, answer)
        return answer

    def __enter__(self) -> "LLMClient":
        return self

    def __exit__(self, *args) -> None:
        self.cache.flush()
