"""LLM Provider supporting streaming from Local Ollama and Cloud APIs (Groq, Grok, DeepSeek, OpenAI, OpenRouter)."""

from __future__ import annotations
import json
import urllib.request
import urllib.error
from typing import Callable, Optional, Generator
from desktop_overlay.config import OverlayConfig

class LLMProvider:
    """Manages communication with local Ollama and Cloud OpenAI-compatible endpoints with streaming support."""
    
    def __init__(self, config: OverlayConfig):
        self.config = config

    @staticmethod
    def get_installed_models(ollama_host: str = "http://localhost:11434") -> list[str]:
        """Dynamically queries Ollama /api/tags for all installed local models."""
        try:
            url = f"{ollama_host.rstrip('/')}/api/tags"
            req = urllib.request.Request(url, headers={"User-Agent": "PopUpAI/1.0"})
            with urllib.request.urlopen(req, timeout=4) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                models = [m["name"] for m in data.get("models", []) if "name" in m]
                if models:
                    return models
        except Exception:
            pass
        return ["phi3:latest", "phi3", "llama3.2", "qwen2.5:3b", "llava", "mistral"]

    def generate_stream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        images: Optional[list[str]] = None,
        stop: Optional[list[str]] = None,
        on_token: Optional[Callable[[str], None]] = None,
        cancel_check: Optional[Callable[[], bool]] = None
    ) -> str:
        """
        Streams response from active AI provider (Local Ollama or Cloud API).
        If system_prompt is None, acts as an unrestricted, raw LLM in terminal mode.
        """
        if self.config.ai_provider != "Ollama" and self.config.api_key.strip():
            return self._generate_stream_openai_compatible(
                prompt=prompt,
                system_prompt=system_prompt,
                stop=stop,
                on_token=on_token,
                cancel_check=cancel_check
            )
            
        return self._generate_stream_ollama(
            prompt=prompt,
            system_prompt=system_prompt,
            images=images,
            stop=stop,
            on_token=on_token,
            cancel_check=cancel_check
        )

    def _generate_stream_ollama(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        images: Optional[list[str]] = None,
        stop: Optional[list[str]] = None,
        on_token: Optional[Callable[[str], None]] = None,
        cancel_check: Optional[Callable[[], bool]] = None
    ) -> str:
        raw_url = self.config.ollama_url.strip() if self.config.ollama_url else "http://localhost:11434/api/generate"
        if not raw_url.endswith("/api/generate"):
            base = raw_url.rstrip("/")
            if base.endswith("/v1"): base = base[:-3]
            elif base.endswith("/api"): base = base[:-4]
            url = f"{base}/api/generate"
        else:
            url = raw_url
        model = self.config.ollama_model
        
        options = {
            "temperature": self.config.temperature,
            "num_predict": self.config.max_tokens
        }
        if stop:
            options["stop"] = stop
            
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": True,
            "options": options
        }
        if system_prompt:
            payload["system"] = system_prompt
        model_lower = model.lower()
        supports_vision = any(v in model_lower for v in ["vision", "llava", "moondream", "minicpm", "bakllava"])
        if images and supports_vision:
            payload["images"] = images
        
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
        
        full_response = []
        try:
            with urllib.request.urlopen(req, timeout=120) as response:
                for line in response:
                    if cancel_check and cancel_check():
                        break
                    if line:
                        chunk = json.loads(line.decode("utf-8"))
                        token = chunk.get("response", "")
                        full_response.append(token)
                        if on_token:
                            on_token(token)
                        if chunk.get("done", False):
                            break
                            
            return "".join(full_response)
        except urllib.error.HTTPError as e:
            err_body = ""
            try:
                err_body = e.read().decode("utf-8")
            except Exception:
                pass
            if "does not support images" in err_body.lower() or "image" in err_body.lower():
                err_msg = f"⚠️ [Vision Error]: The selected model '{model}' is a text-only model and cannot analyze images directly.\n\nTo analyze screenshots with raw pixels, switch the model dropdown to a vision-capable model (like 'llava') in Ollama:\n`ollama pull llava`"
            else:
                err_msg = f"[Ollama Error {e.code}]: {e.reason}\n{err_body}"
            if on_token:
                on_token(err_msg)
            return err_msg
        except urllib.error.URLError as e:
            err_msg = f"[Ollama Connection Error]: {e}\n\n💡 Tip: Make sure Ollama is running (`ollama serve`) and model '{model}' is installed (`ollama pull {model}`)."
            if on_token:
                on_token(err_msg)
            return err_msg
        except Exception as e:
            err_msg = f"[LLM Error] {e}"
            if on_token:
                on_token(err_msg)
            return err_msg

    def _generate_stream_openai_compatible(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        stop: Optional[list[str]] = None,
        on_token: Optional[Callable[[str], None]] = None,
        cancel_check: Optional[Callable[[], bool]] = None
    ) -> str:
        """Streams response from OpenAI-compatible cloud endpoints (Groq, Grok, DeepSeek, OpenAI, OpenRouter)."""
        raw_url = self.config.api_base_url.strip() if self.config.api_base_url else "https://api.groq.com/openai/v1/chat/completions"
        if not raw_url.endswith("/chat/completions"):
            url = f"{raw_url.rstrip('/')}/chat/completions"
        else:
            url = raw_url
        model = self.config.api_model
        api_key = self.config.api_key.strip()
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        payload = {
            "model": model,
            "messages": messages,
            "stream": True,
            "temperature": self.config.temperature,
            "max_tokens": self.config.max_tokens
        }
        if stop:
            payload["stop"] = stop
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
            "User-Agent": "PopUpAI/1.0"
        }
        
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers=headers)
        
        full_response = []
        try:
            with urllib.request.urlopen(req, timeout=60) as response:
                for raw_line in response:
                    if cancel_check and cancel_check():
                        break
                    line = raw_line.decode("utf-8").strip()
                    if not line:
                        continue
                    if line.startswith("data: "):
                        data_str = line[6:].strip()
                        if data_str == "[DONE]":
                            break
                        try:
                            chunk = json.loads(data_str)
                            choices = chunk.get("choices", [])
                            if choices:
                                delta = choices[0].get("delta", {})
                                token = delta.get("content", "")
                                if token:
                                    full_response.append(token)
                                    if on_token:
                                        on_token(token)
                        except Exception:
                            pass
                            
            return "".join(full_response)
        except urllib.error.HTTPError as e:
            err_body = ""
            try:
                err_body = e.read().decode("utf-8")
            except Exception:
                pass
            err_msg = f"[{self.config.ai_provider} API Error {e.code}]: {e.reason}\n{err_body}"
            if on_token:
                on_token(err_msg)
            return err_msg
        except Exception as e:
            err_msg = f"[{self.config.ai_provider} Error]: {e}"
            if on_token:
                on_token(err_msg)
            return err_msg
