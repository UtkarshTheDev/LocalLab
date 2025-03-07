import os
import logging
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig
from typing import Optional, Generator, Dict, Any, List, Union, Callable, AsyncGenerator
from fastapi import HTTPException
import time
from .config import (
    MODEL_REGISTRY, DEFAULT_MODEL, DEFAULT_MAX_LENGTH, DEFAULT_TEMPERATURE, DEFAULT_TOP_P,
    ENABLE_ATTENTION_SLICING, ENABLE_CPU_OFFLOADING, ENABLE_FLASH_ATTENTION,
    ENABLE_BETTERTRANSFORMER, ENABLE_QUANTIZATION, QUANTIZATION_TYPE, UNLOAD_UNUSED_MODELS, MODEL_TIMEOUT,
)
from .logger.logger import logger, log_model_loaded, log_model_unloaded
from .utils import check_resource_availability, get_device, format_model_size
import gc
from colorama import Fore, Style
import asyncio
import re
import zipfile
import tempfile
import json

QUANTIZATION_SETTINGS = {
    "fp16": {
        "load_in_8bit": False,
        "load_in_4bit": False,
        "torch_dtype": torch.float16,
        "device_map": "auto"
    },
    "int8": {
        "load_in_8bit": True,
        "load_in_4bit": False,
        "device_map": "auto"
    },
    "int4": {
        "load_in_8bit": False,
        "load_in_4bit": True,
        "device_map": "auto"
    }
}


class ModelManager:
    def __init__(self):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.current_model: Optional[str] = None
        self.model: Optional[AutoModelForCausalLM] = None
        self.tokenizer: Optional[AutoTokenizer] = None
        self.model_config: Optional[Dict[str, Any]] = None
        self.last_used: float = time.time()

        logger.info(f"Using device: {self.device}")

        # Only try to use Flash Attention if it's explicitly enabled and not empty
        if ENABLE_FLASH_ATTENTION and str(ENABLE_FLASH_ATTENTION).lower() not in ('false', '0', 'none', ''):
            try:
                import flash_attn
                logger.info("Flash Attention enabled - will accelerate transformer attention operations")
            except ImportError:
                logger.info("Flash Attention not available - this is an optional optimization and won't affect basic functionality")
                logger.info("To enable Flash Attention, install with: pip install flash-attn --no-build-isolation")

    def _get_quantization_config(self) -> Optional[Dict[str, Any]]:
        """Get quantization configuration based on settings"""
        # Check if quantization is explicitly disabled (not just False but also '0', 'none', '')
        if not ENABLE_QUANTIZATION or str(ENABLE_QUANTIZATION).lower() in ('false', '0', 'none', ''):
            logger.info("Quantization is disabled, using default precision")
            return {
                "torch_dtype": torch.float16 if torch.cuda.is_available() else torch.float32,
                "device_map": "auto"
            }

        try:
            import bitsandbytes as bnb
            from packaging import version

            if version.parse(bnb.__version__) < version.parse("0.41.1"):
                logger.warning(
                    f"bitsandbytes version {bnb.__version__} may not support all quantization features. "
                    "Please upgrade to version 0.41.1 or higher."
                )
                return {
                    "torch_dtype": torch.float16 if torch.cuda.is_available() else torch.float32,
                    "device_map": "auto"
                }

            # Check for empty quantization type
            if not QUANTIZATION_TYPE or QUANTIZATION_TYPE.lower() in ('none', ''):
                logger.info(
                    "No quantization type specified, defaulting to fp16")
                return {
                    "torch_dtype": torch.float16 if torch.cuda.is_available() else torch.float32,
                    "device_map": "auto"
                }

            if QUANTIZATION_TYPE == "int8":
                logger.info("Using INT8 quantization")
                return {
                    "device_map": "auto",
                    "quantization_config": BitsAndBytesConfig(
                        load_in_8bit=True,
                        llm_int8_threshold=6.0,
                        bnb_8bit_compute_dtype=torch.float16,
                        bnb_8bit_use_double_quant=True
                    )
                }
            elif QUANTIZATION_TYPE == "int4":
                logger.info("Using INT4 quantization")
                return {
                    "device_map": "auto",
                    "quantization_config": BitsAndBytesConfig(
                        load_in_4bit=True,
                        bnb_4bit_compute_dtype=torch.float16,
                        bnb_4bit_use_double_quant=True,
                        bnb_4bit_quant_type="nf4"
                    )
                }
            else:
                logger.info(f"Unrecognized quantization type '{QUANTIZATION_TYPE}', defaulting to fp16")
                return {
                    "torch_dtype": torch.float16 if torch.cuda.is_available() else torch.float32,
                    "device_map": "auto"
                }

        except ImportError:
            logger.warning(
                "bitsandbytes package not found or incompatible. "
                "Falling back to fp16. Please install bitsandbytes>=0.41.1 for quantization support."
            )
            return {
                "torch_dtype": torch.float16 if torch.cuda.is_available() else torch.float32,
                "device_map": "auto"
            }
        except Exception as e:
            logger.warning(f"Error configuring quantization: {str(e)}. Falling back to fp16.")
            return {
                "torch_dtype": torch.float16 if torch.cuda.is_available() else torch.float32,
                "device_map": "auto"
            }

        return {
            "torch_dtype": torch.float16,
            "device_map": "auto"
        }

    def _apply_optimizations(self, model: AutoModelForCausalLM) -> AutoModelForCausalLM:
        """Apply various optimizations to the model"""
        try:
            # Only apply attention slicing if explicitly enabled and not empty
            if os.environ.get('LOCALLAB_ENABLE_ATTENTION_SLICING', '').lower() not in ('false', '0', 'none', ''):
                if hasattr(model, 'enable_attention_slicing'):
                    model.enable_attention_slicing(1)
                    logger.info("Attention slicing enabled")
                else:
                    logger.info(
                        "Attention slicing not available for this model")

            # Only apply CPU offloading if explicitly enabled and not empty
            if os.environ.get('LOCALLAB_ENABLE_CPU_OFFLOADING', '').lower() not in ('false', '0', 'none', ''):
                if hasattr(model, "enable_cpu_offload"):
                    model.enable_cpu_offload()
                    logger.info("CPU offloading enabled")
                else:
                    logger.info("CPU offloading not available for this model")

            # Only apply BetterTransformer if explicitly enabled and not empty
            if os.environ.get('LOCALLAB_ENABLE_BETTERTRANSFORMER', '').lower() not in ('false', '0', 'none', ''):
                try:
                    from optimum.bettertransformer import BetterTransformer
                    model = BetterTransformer.transform(model)
                    logger.info("BetterTransformer optimization applied")
                except ImportError:
                    logger.warning(
                        "BetterTransformer not available - install 'optimum' for this feature")
                except Exception as e:
                    logger.warning(
                        f"BetterTransformer optimization failed: {str(e)}")

            # Only apply Flash Attention if explicitly enabled and not empty
            if os.environ.get('LOCALLAB_ENABLE_FLASH_ATTENTION', '').lower() not in ('false', '0', 'none', ''):
                try:
                    from flash_attn import FlashAttention
                    model = FlashAttention(model)
                    logger.info("Flash Attention optimization applied")
                except ImportError:
                    logger.warning(
                        "Flash Attention not available - install 'flash-attn' for this feature")
                except Exception as e:
                    logger.warning(
                        f"Flash Attention optimization failed: {str(e)}")

            return model
        except Exception as e:
            logger.warning(f"Some optimizations could not be applied: {str(e)}")
            return model

    async def load_model(self, model_id: str) -> bool:
        """Load a model from HuggingFace Hub"""
        try:
            start_time = time.time()
            logger.info(f"\n{Fore.CYAN}Loading model: {model_id}{Style.RESET_ALL}")

            if self.model is not None:
                prev_model = self.current_model
                logger.info(f"Unloading previous model: {prev_model}")
                del self.model
                self.model = None
                torch.cuda.empty_cache()
                gc.collect()
                log_model_unloaded(prev_model)

            hf_token = os.getenv("HF_TOKEN")
            config = self._get_quantization_config()

            if config and config.get("quantization_config"):
                logger.info(f"Using quantization config: {QUANTIZATION_TYPE}")
            else:
                precision = "fp16" if torch.cuda.is_available() else "fp32"
                logger.info(f"Using {precision} precision (no quantization)")

            try:
                self.tokenizer = AutoTokenizer.from_pretrained(
                    model_id,
                    trust_remote_code=True,
                    token=hf_token
                )

                self.model = AutoModelForCausalLM.from_pretrained(
                    model_id,
                    trust_remote_code=True,
                    token=hf_token,
                    **config
                )

                # Move model only if quantization is disabled
                if not ENABLE_QUANTIZATION or str(ENABLE_QUANTIZATION).lower() in ('false', '0', 'none', ''):
                    device = "cuda" if torch.cuda.is_available() else "cpu"
                    logger.info(f"Moving model to {device}")
                    self.model = AutoModelForCausalLM.from_pretrained(
                        model_id,
                        trust_remote_code=True,
                        token=hf_token,               
                        device_map="auto"
                    )
                else:
                    logger.info("Skipping device move for quantized model - using device_map='auto'")

                # Capture model parameters after loading
                model_architecture = self.model.config.architectures[0] if hasattr(self.model.config, 'architectures') else 'Unknown'
                memory_used = torch.cuda.memory_allocated() if torch.cuda.is_available() else 'N/A'
                logger.info(f"Model architecture: {model_architecture}")
                logger.info(f"Memory used: {memory_used}")

                self.model = self._apply_optimizations(self.model)

                self.current_model = model_id
                if model_id in MODEL_REGISTRY:
                    self.model_config = MODEL_REGISTRY[model_id]
                else:
                    self.model_config = {"max_length": DEFAULT_MAX_LENGTH}

                load_time = time.time() - start_time
                log_model_loaded(model_id, load_time)
                logger.info(f"{Fore.GREEN}✓ Model '{model_id}' loaded successfully in {load_time:.2f} seconds{Style.RESET_ALL}")
                return True

            except Exception as e:
                logger.error(f"{Fore.RED}✗ Error loading model {model_id}: {str(e)}{Style.RESET_ALL}")
                if self.model is not None:
                    del self.model
                    self.model = None
                    torch.cuda.empty_cache()
                    gc.collect()

                fallback_model = None
                if self.model_config and self.model_config.get("fallback") and self.model_config.get("fallback") != model_id:
                    fallback_model = self.model_config.get("fallback")

                if fallback_model:
                    logger.warning(f"{Fore.YELLOW}! Attempting to load fallback model: {fallback_model}{Style.RESET_ALL}")
                    return await self.load_model(fallback_model)
                else:
                    raise HTTPException(
                        status_code=500,
                        detail=f"Failed to load model: {str(e)}"
                    )

        except Exception as e:
            logger.error(f"{Fore.RED}✗ Failed to load model {model_id}: {str(e)}{Style.RESET_ALL}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to load model: {str(e)}"
            )

    def check_model_timeout(self):
        """Check if model should be unloaded due to inactivity"""
        if not UNLOAD_UNUSED_MODELS or not self.model:
            return

        if time.time() - self.last_used > MODEL_TIMEOUT:
            logger.info(f"Unloading model {self.current_model} due to inactivity")
            model_id = self.current_model
            del self.model
            self.model = None
            self.current_model = None
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            log_model_unloaded(model_id)

    async def generate(
        self,
        prompt: str,
        stream: bool = False,
        max_length: Optional[int] = None,
        max_new_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
        top_k: Optional[int] = None,
        repetition_penalty: Optional[float] = None,
        system_instructions: Optional[str] = None
    ) -> str:
        """Generate text from the model"""
        # Check model timeout
        self.check_model_timeout()

        if not self.model or not self.tokenizer:
            await self.load_model(DEFAULT_MODEL)

        self.last_used = time.time()

        try:
            # Get appropriate system instructions
            from .config import system_instructions
            instructions = str(system_instructions.get_instructions(
                self.current_model)) if not system_instructions else str(system_instructions)

            # Format prompt with system instructions
            formatted_prompt = f"""<|system|>{instructions}</|system|>\n<|user|>{prompt}</|user|>\n<|assistant|>"""

            # Get model-specific generation parameters
            from .config import get_model_generation_params
            gen_params = get_model_generation_params(self.current_model)

            # Handle max_new_tokens parameter (map to max_length)
            if max_new_tokens is not None:
                max_length = max_new_tokens

            # Override with user-provided parameters if specified
            if max_length is not None:
                try:
                    gen_params["max_length"] = int(max_length)
                except (ValueError, TypeError):
                    logger.warning(f"Invalid max_length value: {max_length}. Using model default.")
            if temperature is not None:
                try:
                    gen_params["temperature"] = float(temperature)
                except (ValueError, TypeError):
                    logger.warning(f"Invalid temperature value: {temperature}. Using model default.")
            if top_p is not None:
                try:
                    gen_params["top_p"] = float(top_p)
                except (ValueError, TypeError):
                    logger.warning(f"Invalid top_p value: {top_p}. Using model default.")
            if top_k is not None:
                try:
                    gen_params["top_k"] = int(top_k)
                except (ValueError, TypeError):
                    logger.warning(f"Invalid top_k value: {top_k}. Using model default.")
            if repetition_penalty is not None:
                try:
                    gen_params["repetition_penalty"] = float(
                        repetition_penalty)
                except (ValueError, TypeError):
                    logger.warning(f"Invalid repetition_penalty value: {repetition_penalty}. Using model default.")

            inputs = self.tokenizer(formatted_prompt, return_tensors="pt")
            for key in inputs:
                inputs[key] = inputs[key].to(self.device)

            if stream:
                return self.async_stream_generate(inputs, gen_params)

            with torch.no_grad():
                generate_params = {
                    **inputs,
                    "max_new_tokens": gen_params["max_length"],
                    "temperature": gen_params["temperature"],
                    "top_p": gen_params["top_p"],
                    "do_sample": True,
                    "pad_token_id": self.tokenizer.eos_token_id
                }

                # Add optional parameters if present in gen_params
                if "top_k" in gen_params:
                    generate_params["top_k"] = gen_params["top_k"]
                if "repetition_penalty" in gen_params:
                    generate_params["repetition_penalty"] = gen_params["repetition_penalty"]

                outputs = self.model.generate(**generate_params)

            response = self.tokenizer.decode(
                outputs[0][len(inputs["input_ids"][0]):], skip_special_tokens=True)
            # Clean up response by removing system and user prompts if they got repeated
            response = response.replace(
                str(instructions), "").replace(prompt, "").strip()
            return response

        except Exception as e:
            logger.error(f"Generation failed: {str(e)}")
            raise HTTPException(
                status_code=500, detail=f"Generation failed: {str(e)}")

    def _stream_generate(
        self,
        inputs: Dict[str, torch.Tensor],
        max_length: int = None,
        temperature: float = None,
        top_p: float = None,
        gen_params: Optional[Dict[str, Any]] = None
    ) -> Generator[str, None, None]:
        """Stream generate text from the model"""
        try:
            # If gen_params is provided, use it instead of individual parameters
            if gen_params is not None:
                max_length = gen_params.get("max_length", DEFAULT_MAX_LENGTH)
                temperature = gen_params.get(
                    "temperature", DEFAULT_TEMPERATURE)
                top_p = gen_params.get("top_p", DEFAULT_TOP_P)
                top_k = gen_params.get("top_k", 50)
                repetition_penalty = gen_params.get("repetition_penalty", 1.1)
            else:
                # Use provided individual parameters or defaults
                max_length = max_length or DEFAULT_MAX_LENGTH
                temperature = temperature or DEFAULT_TEMPERATURE
                top_p = top_p or DEFAULT_TOP_P
                top_k = 50
                repetition_penalty = 1.1

            with torch.no_grad():
                for _ in range(max_length):
                    generate_params = {
                        **inputs,
                        "max_new_tokens": 1,
                        "temperature": temperature,
                        "top_p": top_p,
                        "do_sample": True,
                        "pad_token_id": self.tokenizer.eos_token_id
                    }

                    # Add optional parameters if available
                    if top_k is not None:
                        generate_params["top_k"] = top_k
                    if repetition_penalty is not None:
                        generate_params["repetition_penalty"] = repetition_penalty

                    outputs = self.model.generate(**generate_params)

                    new_token = self.tokenizer.decode(
                        outputs[0][-1:], skip_special_tokens=True)
                    if not new_token or new_token.isspace():
                        break

                    yield new_token
                    inputs = {"input_ids": outputs,
                              "attention_mask": torch.ones_like(outputs)}

        except Exception as e:
            logger.error(f"Streaming generation failed: {str(e)}")
            raise HTTPException(
                status_code=500, detail=f"Streaming generation failed: {str(e)}")

    async def async_stream_generate(self, inputs: Dict[str, torch.Tensor] = None, gen_params: Dict[str, Any] = None, prompt: str = None, system_prompt: Optional[str] = None, **kwargs):
        """Convert the synchronous stream generator to an async generator.

        This can be called either with:
        1. inputs and gen_params directly (internal use)
        2. prompt, system_prompt and other kwargs (from generate_stream adapter)
        """
        # If called with prompt, prepare inputs and parameters
        if prompt is not None:
            # Get appropriate system instructions
            from .config import system_instructions
            instructions = str(system_instructions.get_instructions(
                self.current_model)) if not system_prompt else str(system_prompt)

            # Format prompt with system instructions
            formatted_prompt = f"""<|system|>{instructions}</|system|>\n<|user|>{prompt}</|user|>\n<|assistant|>"""

            # Get model-specific generation parameters
            from .config import get_model_generation_params
            gen_params = get_model_generation_params(self.current_model)

            # Update with provided kwargs
            for key, value in kwargs.items():
                if key in ["max_length", "temperature", "top_p", "top_k", "repetition_penalty"]:
                    gen_params[key] = value
                elif key == "max_new_tokens":
                    # Handle the max_new_tokens parameter by mapping to max_length
                    gen_params["max_length"] = value

            # Tokenize the prompt
            inputs = self.tokenizer(formatted_prompt, return_tensors="pt")
            for key in inputs:
                inputs[key] = inputs[key].to(self.device)

        # Now stream tokens using the prepared inputs and parameters
        for token in self._stream_generate(inputs, gen_params=gen_params):
            yield token
            await asyncio.sleep(0)

    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the currently loaded model"""
        if not self.current_model:
            return {"status": "No model loaded"}

        memory_used = 0
        if self.model:
            memory_used = sum(p.numel() * p.element_size()
                              for p in self.model.parameters())
            num_parameters = sum(p.numel() for p in self.model.parameters())

        model_name = self.model_config.get("name", self.current_model) if isinstance(
            self.model_config, dict) else self.current_model
        max_length = self.model_config.get("max_length", DEFAULT_MAX_LENGTH) if isinstance(
            self.model_config, dict) else DEFAULT_MAX_LENGTH
        ram_required = self.model_config.get("ram", "Unknown") if isinstance(
            self.model_config, dict) else "Unknown"
        vram_required = self.model_config.get("vram", "Unknown") if isinstance(
            self.model_config, dict) else "Unknown"

        model_info = {
            "model_id": self.current_model,
            "model_name": model_name,
            "parameters": f"{num_parameters/1e6:.1f}M",
            "architecture": self.model.__class__.__name__ if self.model else "Unknown",
            "device": self.device,
            "max_length": max_length,
            "ram_required": ram_required,
            "vram_required": vram_required,
            "memory_used": f"{memory_used / (1024 * 1024):.2f} MB",
            "quantization": QUANTIZATION_TYPE if ENABLE_QUANTIZATION else "None",
            "optimizations": {
                "attention_slicing": ENABLE_ATTENTION_SLICING,
                "flash_attention": ENABLE_FLASH_ATTENTION,
                "better_transformer": ENABLE_BETTERTRANSFORMER
            }
        }

        # Log detailed model information
        logger.info(f"""
{Fore.CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{Style.RESET_ALL}
{Fore.GREEN}📊 Model Information{Style.RESET_ALL}
{Fore.CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{Style.RESET_ALL}

• Model: {Fore.YELLOW}{model_name}{Style.RESET_ALL}
• Parameters: {Fore.YELLOW}{model_info['parameters']}{Style.RESET_ALL}
• Architecture: {Fore.YELLOW}{model_info['architecture']}{Style.RESET_ALL}
• Device: {Fore.YELLOW}{self.device}{Style.RESET_ALL}
• Memory Used: {Fore.YELLOW}{model_info['memory_used']}{Style.RESET_ALL}
• Quantization: {Fore.YELLOW}{model_info['quantization']}{Style.RESET_ALL}

{Fore.GREEN}🔧 Optimizations{Style.RESET_ALL}
• Attention Slicing: {Fore.YELLOW}{str(ENABLE_ATTENTION_SLICING)}{Style.RESET_ALL}
• Flash Attention: {Fore.YELLOW}{str(ENABLE_FLASH_ATTENTION)}{Style.RESET_ALL}
• Better Transformer: {Fore.YELLOW}{str(ENABLE_BETTERTRANSFORMER)}{Style.RESET_ALL}
""")

        return model_info

    async def load_custom_model(self, model_name: str, fallback_model: Optional[str] = "qwen-0.5b") -> bool:
        """Load a custom model from Hugging Face Hub with resource checks"""
        try:
            from huggingface_hub import model_info
            info = model_info(model_name)

            estimated_ram = info.siblings[0].size / (1024 * 1024)
            estimated_vram = estimated_ram * 1.5

            temp_config = {
                "name": model_name,
                "ram": estimated_ram,
                "vram": estimated_vram,
                "max_length": 2048,
                "fallback": fallback_model,
                "description": f"Custom model: {info.description}",
                "quantization": "int8",
                "tags": info.tags
            }

            if not check_resource_availability(temp_config["ram"]):
                if fallback_model:
                    logger.warning(
                        f"Insufficient resources for {model_name} "
                        f"(Requires ~{format_model_size(temp_config['ram'])} RAM), "
                        f"falling back to {fallback_model}"
                    )
                    raise HTTPException(
                        status_code=400,
                        detail=f"Insufficient resources. Model requires ~{format_model_size(temp_config['ram'])} RAM"
                    )
                raise HTTPException(
                    status_code=400,
                    detail=f"Insufficient resources. Model requires ~{format_model_size(temp_config['ram'])} RAM"
                )

            if self.model:
                del self.model
                torch.cuda.empty_cache()

            logger.info(f"Loading custom model: {model_name}")

            quant_config = BitsAndBytesConfig(
                load_in_8bit=True,
                llm_int8_threshold=6.0
            )

            self.tokenizer = AutoTokenizer.from_pretrained(model_name)
            self.model = AutoModelForCausalLM.from_pretrained(
                model_name,
                torch_dtype=torch.float16,
                device_map="auto",
                quantization_config=quant_config
            )

            self.model = self._apply_optimizations(self.model)

            self.current_model = f"custom/{model_name}"
            self.model_config = temp_config
            self.last_used = time.time()

            model_size = sum(p.numel() * p.element_size()
                             for p in self.model.parameters())
            logger.info(f"Custom model loaded successfully. Size: {format_model_size(model_size)}")

            return True

        except Exception as e:
            logger.error(f"Failed to load custom model {model_name}: {str(e)}")
            if fallback_model:
                logger.warning(f"Attempting to load fallback model: {fallback_model}")
                return await self.load_model(fallback_model)
            raise HTTPException(
                status_code=500,
                detail=f"Failed to load model: {str(e)}"
            )

    # Add adapter methods to match the interface expected by the routes
    async def generate_text(self, prompt: str, system_prompt: Optional[str] = None, **kwargs) -> str:
        """
        Adapter method that calls the generate method.
        This is used to maintain compatibility with routes that call generate_text.
        """
        # Make sure we're not streaming when generating text
        kwargs["stream"] = False

        # Handle max_new_tokens parameter by mapping to max_length if needed
        if "max_new_tokens" in kwargs and "max_length" not in kwargs:
            kwargs["max_length"] = kwargs.pop("max_new_tokens")

        # Directly await the generate method to return the string result
        return await self.generate(prompt=prompt, system_instructions=system_prompt, **kwargs)

    async def generate_stream(self, prompt: str, system_prompt: Optional[str] = None, **kwargs) -> AsyncGenerator[str, None]:
        """Adapter method for streaming text generation.
        Calls the async_stream_generate method with proper parameters."""
        # Ensure streaming is enabled
        kwargs["stream"] = True

        # Handle max_new_tokens parameter by mapping to max_length
        if "max_new_tokens" in kwargs and "max_length" not in kwargs:
            kwargs["max_length"] = kwargs.pop("max_new_tokens")

        # Call async_stream_generate with the prompt and parameters
        async for token in self.async_stream_generate(prompt=prompt, system_prompt=system_prompt, **kwargs):
            yield token

    def is_model_loaded(self, model_id: str) -> bool:
        """Check if a specific model is loaded.

        Args:
            model_id: The ID of the model to check

        Returns:
            True if the model is loaded, False otherwise
        """
        return (self.model is not None) and (self.current_model == model_id)

    def unload_model(self) -> None:
        """Unload the current model to free memory resources.

        This method removes the current model from memory and clears
        the tokenizer and model references.
        """
        if self.model is not None:
            # Log which model is being unloaded
            model_id = self.current_model

            # Clear model and tokenizer
            self.model = None
            self.tokenizer = None
            self.current_model = None

            # Clean up memory
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            gc.collect()

            # Log model unloading
            log_model_unloaded(model_id)

            logger.info(f"Model {model_id} unloaded successfully")
