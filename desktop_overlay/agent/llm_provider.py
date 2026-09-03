"""LLM Provider supporting streaming from Ollama and local APIs."""

from __future__ import annotations
import json
import urllib.request
import urllib.error
from typing import Callable, Optional, Generator
from desktop_overlay.config import OverlayConfig

class LLMProvider:
    """Manages communication with Ollama and local LLM endpoints with streaming support."""
    
    def __init__(self, config: OverlayConfig):
        self.config = config

    def generate_stream(
        self,
        prompt: str,
        system_prompt: str = "You are a helpful, capable desktop AI assistant. Provide concise, direct answers.",
        images: Optional[list[str]] = None,
        on_token: Optional[Callable[[str], None]] = None,
        cancel_check: Optional[Callable[[], bool]] = None
    ) -> str:
        """
        Streams response from Ollama endpoint.
        Supports multimodal image inputs via base64 encoded strings in images list.
        """
        url = self.config.ollama_url
        model = self.config.ollama_model
        
        payload = {
            "model": model,
            "prompt": prompt,
            "system": system_prompt,
            "stream": True,
            "options": {
                "temperature": self.config.temperature,
                "num_predict": self.config.max_tokens
            }
        }
        # Only attach raw image tensors if the model architecture natively supports vision
        model_lower = model.lower()
        supports_vision = any(v in model_lower for v in ["vision", "llava", "moondream", "minicpm", "bakllava"])
        if images and supports_vision:
            payload["images"] = images
        
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
        
        full_response = []
        try:
            with urllib.request.urlopen(req, timeout=45) as response:
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
            except:
                pass
            if "does not support images" in err_body.lower() or "image" in err_body.lower():
                err_msg = f"⚠️ [Vision Error]: The selected model '{model}' is a text-only model and cannot analyze images directly.\n\nTo analyze screenshots, switch the model dropdown to a vision-capable model (like 'llava' or 'llama3.2-vision') in Ollama:\n`ollama pull llava`"
            else:
                err_msg = f"[Ollama Error {e.code}]: {e.reason}\n{err_body}"
            if on_token:
                on_token(err_msg)
            return err_msg
        except urllib.error.URLError as e:
            err_msg = f"[LLM Offline] Could not connect to Ollama at {url}.\nPlease ensure Ollama is running (`ollama run {model}`).\n\nError: {e}"
            if on_token:
                on_token(err_msg)
            return err_msg
        except Exception as e:
            err_msg = f"[LLM Error] {e}"
            if on_token:
                on_token(err_msg)
            return err_msg
        except urllib.error.URLError as e:
            err_msg = f"[LLM Offline] Could not connect to Ollama at {url}.\nPlease ensure Ollama is running (`ollama run {model}`).\n\nError: {e}"
            if on_token:
                on_token(err_msg)
            return err_msg
        except Exception as e:
            err_msg = f"[LLM Error] {e}"
            if on_token:
                on_token(err_msg)
            return err_msg

    def generate_sync(self, prompt: str, system_prompt: str = "") -> str:
        return self.generate_stream(prompt, system_prompt=system_prompt)
