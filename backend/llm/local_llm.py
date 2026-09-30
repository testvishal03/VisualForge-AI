"""One small Transformers model on CPU; no hosted inference client."""
import os
from pathlib import Path
import time
from typing import Callable

MODEL_NAME = "Qwen/Qwen2.5-1.5B-Instruct"
MODEL_REVISION = "989aa7980e4cf806f80c7fef2b1adb7bc71aa306"
MODEL_DIRECTORY = Path(__file__).resolve().parents[1] / ".cache" / "qwen2.5-1.5b-instruct"
SEED = 42


class LocalLLM:
    def __init__(self, model_name: str = MODEL_NAME, *, offline: bool = False, threads: int = 2, on_progress: Callable[[str], None] | None = None):
        if model_name != MODEL_NAME:
            raise ValueError(f"This CPU profile supports the pinned primary model {MODEL_NAME}.")
        if not 1 <= threads <= 8:
            raise ValueError("CPU threads must be between 1 and 8.")
        self.model_name = model_name
        self.offline = offline
        self.threads = threads
        self.on_progress = on_progress
        self.model = None
        self.tokenizer = None
        self.load_seconds = 0.0
        self.last_generation_seconds = 0.0
        self.last_token_count = 0

    def _load(self):
        if self.model is not None:
            return
        os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")
        os.environ.setdefault("HF_HUB_DISABLE_XET", "1")
        os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
        started = time.perf_counter()
        try:
            import torch
            from huggingface_hub import snapshot_download
            from transformers import AutoModelForCausalLM, AutoTokenizer
            # local_dir avoids duplicate symlink/blob storage on Windows.
            required = ["config.json", "tokenizer.json", "tokenizer_config.json", "model.safetensors", ".revision"]
            cached = all((MODEL_DIRECTORY / name).is_file() for name in required)
            cached = cached and (MODEL_DIRECTORY / ".revision").read_text().strip() == MODEL_REVISION
            if not cached:
                if self.offline:
                    raise OSError("Pinned model/tokenizer is not cached. Run once without --offline while connected to download it.")
                snapshot_download(
                    repo_id=self.model_name, revision=MODEL_REVISION, local_dir=MODEL_DIRECTORY,
                    allow_patterns=["*.json", "*.safetensors", "merges.txt", "vocab.json", "LICENSE", "README.md"],
                    max_workers=2, token=False,
                )
                (MODEL_DIRECTORY / ".revision").write_text(MODEL_REVISION, encoding="utf-8")
            torch.set_num_threads(self.threads)
            torch.manual_seed(SEED)
            if self.on_progress:
                self.on_progress("Loading the cached checkpoint on CPU...")
            self.tokenizer = AutoTokenizer.from_pretrained(MODEL_DIRECTORY, local_files_only=True, trust_remote_code=False)
            self.model = AutoModelForCausalLM.from_pretrained(
                MODEL_DIRECTORY, local_files_only=True, trust_remote_code=False,
                use_safetensors=True, dtype=torch.float32, attn_implementation="sdpa",
            ).to("cpu").eval()
            self.model.requires_grad_(False)
            if self.on_progress:
                self.on_progress(f"Using CPU precision: {self.model.dtype}.")
            self.load_seconds = time.perf_counter() - started
            if self.on_progress:
                self.on_progress(f"CPU model ready in {self.load_seconds:.1f}s; generating text...")
        except (MemoryError, RuntimeError) as exc:
            self.model = None
            raise RuntimeError(f"Could not load the CPU model. Close memory-heavy apps; this CPU profile uses about 7 GB RAM, with a temporary loading peak near 10 GB. Details: {exc}") from exc
        except Exception as exc:
            raise RuntimeError(f"Local model/tokenizer setup failed. First use needs internet and about 3.1 GB free disk for weights; use --offline only after caching. Details: {exc}") from exc

    def generate(self, prompt: str, max_new_tokens: int = 1800, temperature: float = 0.0) -> str:
        if not 128 <= max_new_tokens <= 3000:
            raise ValueError("max_new_tokens must be between 128 and 3000.")
        if not 0 <= temperature <= 1:
            raise ValueError("temperature must be between 0 and 1; zero uses greedy decoding.")
        self._load()
        import torch
        from transformers import GenerationConfig
        from backend.llm.prompts import SYSTEM_PROMPT
        messages = [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": prompt}]
        text = self.tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        inputs = self.tokenizer(text, return_tensors="pt")
        prompt_length = inputs["input_ids"].shape[-1]
        if prompt_length > 6000:
            raise ValueError("Prompt exceeds the local profile's 6000-token input limit.")
        config = GenerationConfig(
            max_new_tokens=max_new_tokens, do_sample=temperature > 0,
            temperature=temperature if temperature > 0 else 1.0,
            eos_token_id=self.model.generation_config.eos_token_id,
            pad_token_id=self.tokenizer.pad_token_id or self.tokenizer.eos_token_id,
            use_cache=True,
        )
        torch.manual_seed(SEED)
        started = time.perf_counter()
        try:
            with torch.inference_mode():
                tokens = self.model.generate(**inputs, generation_config=config)[0, prompt_length:]
            self.last_generation_seconds = time.perf_counter() - started
            self.last_token_count = len(tokens)
            result = self.tokenizer.decode(tokens, skip_special_tokens=True).strip()
            if not result:
                raise ValueError("The model generated no text.")
            return result
        except Exception as exc:
            raise RuntimeError(f"Local text generation failed. Reduce token limits or close memory-heavy apps. Details: {exc}") from exc
