from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any
@dataclass
class LLMResponse: text:str; model:str; provider:str; raw:Any=None
class LLMProvider(ABC):
    @abstractmethod
    async def generate(self,prompt:str,context:dict)->LLMResponse: ...
class LocalLLMProvider(LLMProvider):
    async def generate(self,prompt:str,context:dict)->LLMResponse: return LLMResponse("Local LLM adapter placeholder; inference backend is configurable.","CONFIGURE_ME","local")
class EmbeddingProvider(ABC):
    @abstractmethod
    async def embed(self,texts:list[str])->list[list[float]]: ...
