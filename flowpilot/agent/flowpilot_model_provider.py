from __future__ import annotations

from pathlib import Path
from typing import Optional

import torch
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
)


class FlowPilotModelProvider:
    """
    Local inference provider for the FlowPilot specialized model.

    No OpenAI.
    No Claude.
    No Ollama.

    The base model and FlowPilot LoRA adapter are loaded locally.
    """

    def __init__(
        self,
        base_model: str = "Qwen/Qwen2.5-Coder-3B-Instruct",
        adapter_path: str = "FlowPilot-GNURadio-3B",
    ) -> None:

        self.base_model = base_model
        self.adapter_path = Path(adapter_path)

        self.tokenizer = None
        self.model = None

    def load(self) -> None:
        """Load tokenizer, base model and FlowPilot adapter."""

        from peft import PeftModel

        self.tokenizer = AutoTokenizer.from_pretrained(
            self.base_model,
            trust_remote_code=True,
        )

        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = (
                self.tokenizer.eos_token
            )

        self.model = AutoModelForCausalLM.from_pretrained(
            self.base_model,
            torch_dtype=torch.float16,
            device_map="auto",
            trust_remote_code=True,
        )

        if self.adapter_path.exists():
            self.model = PeftModel.from_pretrained(
                self.model,
                str(self.adapter_path),
            )

        self.model.eval()

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_new_tokens: int = 512,
        temperature: float = 0.1,
    ) -> str:

        if self.model is None:
            self.load()

        messages = []

        if system_prompt:
            messages.append(
                {
                    "role": "system",
                    "content": system_prompt,
                }
            )

        messages.append(
            {
                "role": "user",
                "content": prompt,
            }
        )

        text = self.tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True,
        )

        inputs = self.tokenizer(
            text,
            return_tensors="pt",
        )

        inputs = {
            key: value.to(self.model.device)
            for key, value in inputs.items()
        }

        with torch.inference_mode():

            outputs = self.model.generate(
                **inputs,
                max_new_tokens=max_new_tokens,
                temperature=temperature,
                do_sample=temperature > 0,
                pad_token_id=self.tokenizer.pad_token_id,
                eos_token_id=self.tokenizer.eos_token_id,
            )

        generated = outputs[
            0
        ][
            inputs["input_ids"].shape[1]:
        ]

        answer = self.tokenizer.decode(
            generated,
            skip_special_tokens=True,
        )

        return answer.strip()


__all__ = [
    "FlowPilotModelProvider",
]