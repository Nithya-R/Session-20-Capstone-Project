import os
import time
import asyncio
import json
import yaml
from datetime import datetime, timedelta
from pathlib import Path
from google import genai
from google.genai.errors import ServerError
from dotenv import load_dotenv
from huggingface_hub import InferenceClient

ROOT = Path(__file__).parent.parent
load_dotenv(ROOT / ".env")
MODELS_JSON = ROOT / "config" / "models.json"
PROFILE_YAML = ROOT / "config" / "profiles.yaml"
RATE_LIMIT_STATE_FILE = ROOT / "config" / "rate_limit_state.json"

# ---------------------------------------------------------------------------
# Rate-limit fallback registry
# Persists { "model_name": "ISO-datetime-until-which-it-is-blocked" }
# ---------------------------------------------------------------------------

def _load_rate_limit_state() -> dict:
    if RATE_LIMIT_STATE_FILE.exists():
        try:
            return json.loads(RATE_LIMIT_STATE_FILE.read_text())
        except Exception:
            pass
    return {}

def _save_rate_limit_state(state: dict):
    RATE_LIMIT_STATE_FILE.write_text(json.dumps(state, indent=2))

def is_model_rate_limited(model_name: str) -> bool:
    state = _load_rate_limit_state()
    until_str = state.get(model_name)
    if not until_str:
        return False
    until = datetime.fromisoformat(until_str)
    if datetime.now() < until:
        return True
    # Expired — clear the entry
    state.pop(model_name, None)
    _save_rate_limit_state(state)
    return False

def mark_model_rate_limited(model_name: str, hours: float = 1.0):
    state = _load_rate_limit_state()
    reset_at = datetime.now() + timedelta(hours=hours)
    state[model_name] = reset_at.isoformat()
    _save_rate_limit_state(state)
    print(f"[RateLimit] {model_name} marked as rate-limited until {reset_at.strftime('%H:%M:%S')}")

class ModelManager:
    def __init__(self, model_name: str = None, provider: str = None):
        """
        Initialize ModelManager with flexible model specification.
        
        Args:
            model_name: The model to use. Can be:
                - A key from models.json (e.g., "gemini", "phi4")
                - An actual model name (e.g., "gemini-2.5-flash", "llama3:8b")
            provider: Optional explicit provider ("gemini" or "ollama").
                      If provided, bypasses models.json lookup.
        """
        self.config = json.loads(MODELS_JSON.read_text())
        try:
            self.profile = yaml.safe_load(PROFILE_YAML.read_text())
        except FileNotFoundError:
            self.profile = {}

        # Load settings for Ollama URL
        try:
            from config.settings_loader import settings
            self.ollama_base_url = settings.get("ollama", {}).get("base_url", "http://127.0.0.1:11434")
        except:
            self.ollama_base_url = "http://127.0.0.1:11434"

        # 🎯 NEW: Support explicit provider specification (from settings)
        if provider:
            self.model_type = provider
            self.text_model_key = model_name or "gemini-2.5-flash"
            
            if provider == "gemini":
                # Gemini: model_name is the actual Gemini model like "gemini-2.5-flash"
                self.model_info = {
                    "type": "gemini",
                    "model": self.text_model_key,
                    "api_key_env": "GEMINI_API_KEY"
                }
                api_key = os.getenv("GEMINI_API_KEY")
                self.client = genai.Client(api_key=api_key)
            elif provider == "huggingface":
                self.model_info = {
                    "type": "huggingface",
                    "model": self.text_model_key,
                }
                self.client = InferenceClient(api_key=os.getenv("HUGGINGFACE_API_TOKEN"))
            elif provider == "ollama":
                # Ollama: model_name is the Ollama model like "phi4" or "llama3:8b"
                self.model_info = {
                    "type": "ollama",
                    "model": self.text_model_key,
                    "url": {
                        "generate": f"{self.ollama_base_url}/api/generate",
                        "chat": f"{self.ollama_base_url}/api/chat"
                    }
                }
                self.client = None  # Ollama uses HTTP, no client needed
            else:
                raise ValueError(f"Unknown provider: {provider}")
        else:
            # 🔄 LEGACY: Lookup in models.json by key
            if model_name:
                self.text_model_key = model_name
            else:
                self.text_model_key = self.profile["llm"]["text_generation"]
            
            # Validate that the model exists in config
            if self.text_model_key not in self.config["models"]:
                available_models = list(self.config["models"].keys())
                raise ValueError(f"Model '{self.text_model_key}' not found in models.json. Available: {available_models}")
                
            self.model_info = self.config["models"][self.text_model_key]
            self.model_type = self.model_info["type"]

            # Initialize client based on model type
            if self.model_type == "gemini":
                api_key = os.getenv("GEMINI_API_KEY")
                self.client = genai.Client(api_key=api_key)
            # Ollama doesn't need a persistent client

    async def generate_text(self, prompt: str) -> str:
        """Generate text with automatic rate-limit fallback to HuggingFace."""
        # Check if the primary model is currently rate-limited
        if is_model_rate_limited(self.text_model_key):
            print(f"[RateLimit] {self.text_model_key} is rate-limited. Falling back to HuggingFace.")
            return await self._hf_generate(prompt)

        try:
            if self.model_type == "gemini":
                return await self._gemini_generate(prompt)
            elif self.model_type == "ollama":
                return await self._ollama_generate(prompt)
            elif self.model_type == "huggingface":
                return await self._hf_generate(prompt)
            raise NotImplementedError(f"Unsupported model type: {self.model_type}")

        except (RuntimeError, Exception) as e:
            err_str = str(e)
            if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str or "rate" in err_str.lower():
                mark_model_rate_limited(self.text_model_key, hours=1.0)
                print(f"[RateLimit] Falling back to HuggingFace for this request.")
                return await self._hf_generate(prompt)
            raise

    async def generate_content(self, contents: list) -> str:
        """Generate content with support for text and images.
        
        Contents can contain:
        - str: Text content
        - PIL.Image: Image to process (will be base64-encoded for Ollama)
        """
        if self.model_type == "gemini":
            await self._wait_for_rate_limit()
            return await self._gemini_generate_content(contents)
        elif self.model_type == "ollama":
            # Ollama multimodal: extract text and images separately
            return await self._ollama_generate_content(contents)
        
        raise NotImplementedError(f"Unsupported model type: {self.model_type}")

    async def _ollama_generate_content(self, contents: list) -> str:
        """Generate content with Ollama, supporting multimodal models like gemma3, llava, etc."""
        import base64
        import io
        from PIL import Image as PILImage
        
        text_parts = []
        images_base64 = []
        
        for content in contents:
            if isinstance(content, str):
                text_parts.append(content)
            elif hasattr(content, 'save'):  # PIL Image check
                # Convert PIL Image to base64
                try:
                    img = content
                    # Convert to RGB if necessary
                    if img.mode in ('RGBA', 'P'):
                        img = img.convert('RGB')
                    
                    # Resize if too large (Ollama has limits)
                    MAX_DIM = 1024
                    if img.width > MAX_DIM or img.height > MAX_DIM:
                        img.thumbnail((MAX_DIM, MAX_DIM), PILImage.Resampling.LANCZOS)
                    
                    # Encode to base64
                    buf = io.BytesIO()
                    img.save(buf, format="JPEG", quality=85)
                    encoded = base64.b64encode(buf.getvalue()).decode("utf-8")
                    images_base64.append(encoded)
                except Exception as e:
                    print(f"⚠️ Failed to encode image for Ollama: {e}")
        
        prompt = "\n".join(text_parts)
        
        if images_base64:
            # Use Ollama's multimodal format with images array
            return await self._ollama_generate_with_images(prompt, images_base64)
        else:
            # Text-only fallback
            return await self._ollama_generate(prompt)

    async def _ollama_generate_with_images(self, prompt: str, images: list) -> str:
        """Generate with Ollama using images (for multimodal models)."""
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.model_info["url"]["generate"],
                    json={
                        "model": self.model_info["model"],
                        "prompt": prompt,
                        "images": images,  # Base64 encoded images
                        "stream": False
                    }
                ) as response:
                    response.raise_for_status()
                    result = await response.json()
                    return result["response"].strip()
        except Exception as e:
            raise RuntimeError(f"Ollama multimodal generation failed: {str(e)}")

    # --- Rate Limiting Helper ---
    _last_call = 0
    _lock = asyncio.Lock()

    async def _wait_for_rate_limit(self):
        """Enforce ~15 RPM limit for Gemini (4s interval)"""
        async with ModelManager._lock:
            now = time.time()
            elapsed = now - ModelManager._last_call
            if elapsed < 4.5: # 4.5s buffer for safety
                sleep_time = 4.5 - elapsed
                # print(f"[Rate Limit] Sleeping for {sleep_time:.2f}s...")
                await asyncio.sleep(sleep_time)
            ModelManager._last_call = time.time()


    async def _gemini_generate(self, prompt: str) -> str:
        await self._wait_for_rate_limit()
        try:
            # ✅ CORRECT: Use synchronous SDK client in thread to bypass aiohttp/DNS issues common on macOS
            response = await asyncio.to_thread(
                self.client.models.generate_content,
                model=self.model_info["model"],
                contents=prompt
            )
            return response.text.strip()

        except ServerError as e:
            # ✅ FIXED: Raise the exception instead of returning it
            raise e
        except Exception as e:
            # ✅ Handle other potential errors
            raise RuntimeError(f"Gemini generation failed: {str(e)}")

    async def _gemini_generate_content(self, contents: list) -> str:
        """Generate content with support for text and images using Gemini SDK"""
        try:
            # ✅ Use synchronous SDK client in thread (text + images)
            response = await asyncio.to_thread(
                self.client.models.generate_content,
                model=self.model_info["model"],
                contents=contents
            )
            return response.text.strip()

        except ServerError as e:
            # ✅ FIXED: Raise the exception instead of returning it
            raise e
        except Exception as e:
            # ✅ Handle other potential errors
            raise RuntimeError(f"Gemini content generation failed: {str(e)}")

    async def _ollama_generate(self, prompt: str) -> str:
        try:
            # ✅ Use aiohttp for truly async requests
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.model_info["url"]["generate"],
                    json = {"model": self.model_info["model"], "prompt": prompt, "stream": False}
                ) as response:
                    response.raise_for_status()
                    result = await response.json()
                    return result["response"].strip()
        except Exception as e:
            raise RuntimeError(f"Ollama generation failed: {str(e)}")

    async def _hf_generate(self, prompt: str) -> str:
        """Fallback generator using HuggingFace Inference API."""
        hf_model = "Qwen/Qwen2.5-7B-Instruct"
        try:
            hf_token = os.getenv("HUGGINGFACE_API_TOKEN")
            hf_client = InferenceClient(api_key=hf_token)

            response = await asyncio.to_thread(
                hf_client.chat_completion,
                model=hf_model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=4096,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            raise RuntimeError(f"HuggingFace fallback generation failed: {str(e)}")
