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
        self.compiled_model: bool = False
        self.response_cache = {}  # Simple in-memory cache for responses

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
        # Use the config system to get the value, which checks environment variables and config file
        from .cli.config import get_config_value
        
        # First check if CUDA is available - if not, we can't use bitsandbytes quantization
        if not torch.cuda.is_available():
            logger.warning("CUDA not available - quantization with bitsandbytes requires CUDA")
            logger.info("Disabling quantization and using CPU-compatible settings")
            return {
                "torch_dtype": torch.float32,
                "device_map": "auto"
            }
        
        enable_quantization = get_config_value('enable_quantization', ENABLE_QUANTIZATION)
        # Convert string values to boolean if needed
        if isinstance(enable_quantization, str):
            enable_quantization = enable_quantization.lower() not in ('false', '0', 'none', '')
        
        quantization_type = get_config_value('quantization_type', QUANTIZATION_TYPE)
        
        if not enable_quantization:
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
            if not quantization_type or quantization_type.lower() in ('none', ''):
                logger.info(
                    "No quantization type specified, defaulting to fp16")
                return {
                    "torch_dtype": torch.float16 if torch.cuda.is_available() else torch.float32,
                    "device_map": "auto"
                }

            if quantization_type == "int8":
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
            elif quantization_type == "int4":
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
                logger.info(f"Unrecognized quantization type '{quantization_type}', defaulting to fp16")
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

    def _apply_optimizations(self, model: AutoModelForCausalLM) -> AutoModelForCausalLM:
        """Apply various optimizations to the model"""
        try:
            # Import the config system
            from .cli.config import get_config_value
            
            # Only apply attention slicing if explicitly enabled and not empty
            enable_attention_slicing = get_config_value('enable_attention_slicing', ENABLE_ATTENTION_SLICING)
            if isinstance(enable_attention_slicing, str):
                enable_attention_slicing = enable_attention_slicing.lower() not in ('false', '0', 'none', '')
            
            if enable_attention_slicing:
                if hasattr(model, 'enable_attention_slicing'):
                    # Use more aggressive slicing for faster inference
                    model.enable_attention_slicing("max")
                    logger.info("Attention slicing enabled with max setting")
                else:
                    logger.info(
                        "Attention slicing not available for this model")

            # Only apply CPU offloading if explicitly enabled and not empty
            enable_cpu_offloading = get_config_value('enable_cpu_offloading', ENABLE_CPU_OFFLOADING)
            if isinstance(enable_cpu_offloading, str):
                enable_cpu_offloading = enable_cpu_offloading.lower() not in ('false', '0', 'none', '')
            
            if enable_cpu_offloading:
                if hasattr(model, "enable_cpu_offload"):
                    model.enable_cpu_offload()
                    logger.info("CPU offloading enabled")
                else:
                    logger.info("CPU offloading not available for this model")

            # Only apply BetterTransformer if explicitly enabled and not empty
            enable_bettertransformer = get_config_value('enable_better_transformer', ENABLE_BETTERTRANSFORMER)
            if isinstance(enable_bettertransformer, str):
                enable_bettertransformer = enable_bettertransformer.lower() not in ('false', '0', 'none', '')
            
            if enable_bettertransformer:
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
            enable_flash_attention = get_config_value('enable_flash_attention', ENABLE_FLASH_ATTENTION)
            if isinstance(enable_flash_attention, str):
                enable_flash_attention = enable_flash_attention.lower() not in ('false', '0', 'none', '')
            
            if enable_flash_attention:
                try:
                    # Try to enable flash attention directly on the model config
                    if hasattr(model.config, "attn_implementation"):
                        model.config.attn_implementation = "flash_attention_2"
                        logger.info("Flash Attention 2 enabled via config")
                    # For older models, try the flash_attn module
                    else:
                        import flash_attn
                        logger.info("Flash Attention enabled via module")
                except ImportError:
                    logger.warning(
                        "Flash Attention not available - install 'flash-attn' for this feature")
                except Exception as e:
                    logger.warning(
                        f"Flash Attention optimization failed: {str(e)}")
            
            # Enable memory efficient attention if available
            try:
                if hasattr(model, "enable_xformers_memory_efficient_attention"):
                    model.enable_xformers_memory_efficient_attention()
                    logger.info("XFormers memory efficient attention enabled")
            except Exception as e:
                logger.info(f"XFormers memory efficient attention not available: {str(e)}")
            
            # Enable gradient checkpointing for memory efficiency if available
            try:
                if hasattr(model, "gradient_checkpointing_enable"):
                    model.gradient_checkpointing_enable()
                    logger.info("Gradient checkpointing enabled for memory efficiency")
            except Exception as e:
                logger.info(f"Gradient checkpointing not available: {str(e)}")
            
            # Set model to evaluation mode for faster inference
            model.eval()
            logger.info("Model set to evaluation mode for faster inference")

            return model
        except Exception as e:
            logger.warning(f"Some optimizations could not be applied: {str(e)}")
            return model

    async def load_model(self, model_id: str) -> bool:
        """Load a model from HuggingFace Hub"""
        try:
            start_time = time.time()
            logger.info(f"\n{Fore.CYAN}Loading model: {model_id}{Style.RESET_ALL}")
        
            from .config import get_hf_token
            hf_token = get_hf_token(interactive=True)

            if self.model is not None:
                prev_model = self.current_model
                logger.info(f"Unloading previous model: {prev_model}")
                del self.model
                self.model = None
                self.compiled_model = False
                self.response_cache.clear()  # Clear cache when changing models
                torch.cuda.empty_cache()
                gc.collect()
                log_model_unloaded(prev_model)

            # Set CUDA memory allocation configuration to avoid fragmentation
            os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "expandable_segments:True"   
            try:
                # First, try to get model config to check architecture
                from transformers import AutoConfig, BertLMHeadModel, AutoModelForCausalLM
                model_config = AutoConfig.from_pretrained(
                    model_id,
                    trust_remote_code=True,
                    token=hf_token
                )

                # First, try to get model config to check architecture
                from transformers import AutoConfig
                model_config = AutoConfig.from_pretrained(
                    model_id,
                    trust_remote_code=True,
                    token=hf_token
                )

                # Check if it's a BERT-based model
                is_bert_based = any(arch.lower().startswith('bert') for arch in model_config.architectures) if hasattr(model_config, 'architectures') else False

                # If it's BERT-based, set is_decoder=True
                if is_bert_based:
                    logger.info("Detected BERT-based model, configuring for generation...")
                    model_config.is_decoder = True
                    if hasattr(model_config, 'add_cross_attention'):
                        model_config.add_cross_attention = False

                # Load tokenizer first
                self.tokenizer = AutoTokenizer.from_pretrained(
                    model_id,
                    trust_remote_code=True,
                    token=hf_token
                )

                # Determine if we should use CPU offloading
                use_cpu_offload = not torch.cuda.is_available() or torch.cuda.get_device_properties(0).total_memory < 4 * 1024 * 1024 * 1024  # Less than 4GB VRAM

                if use_cpu_offload:
                    logger.info("Using CPU offloading due to limited GPU memory or CPU-only environment")
                    config["device_map"] = {
                        "": "cpu"
                    }
                    config["offload_folder"] = "offload"
                    if "torch_dtype" in config:
                        # Use lower precision for CPU to save memory
                        config["torch_dtype"] = torch.float32

                # Load the model with the modified config
                self.model = AutoModelForCausalLM.from_pretrained(
                    model_id,
                    config=model_config,
                    trust_remote_code=True,
                    token=hf_token,
                    low_cpu_mem_usage=True,  # Enable low memory usage
                    **config
                )
                
                logger.info(f"Model loaded with device_map='auto' for automatic placement")

                # Apply memory optimizations
                if use_cpu_offload:
                    # Enable gradient checkpointing for memory efficiency
                    if hasattr(self.model, "gradient_checkpointing_enable"):
                        self.model.gradient_checkpointing_enable()
                        logger.info("Enabled gradient checkpointing for memory efficiency")

                    # Enable CPU offloading if available
                    if hasattr(self.model, "enable_cpu_offload"):
                        self.model.enable_cpu_offload()
                        logger.info("Enabled CPU offloading")

                # Apply optimizations if needed
                self.model = self._apply_optimizations(self.model)
                
                # Set model to evaluation mode
                self.model.eval()
                
                # Clear any unused memory
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
                gc.collect()

                # Capture model parameters after loading
                model_architecture = self.model.config.architectures[0] if hasattr(self.model.config, 'architectures') else 'Unknown'
                memory_used = torch.cuda.memory_allocated() if torch.cuda.is_available() else 'N/A'
                logger.info(f"Model architecture: {model_architecture}")
                logger.info(f"Memory used: {memory_used}")

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
                    self.compiled_model = False
                    torch.cuda.empty_cache()
                    gc.collect()

                # Try to load a smaller fallback model
                fallback_model = "microsoft/phi-2"  # A smaller model that works well
                if model_id != fallback_model:
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
            
            # Check cache for non-streaming requests with default parameters
            cache_key = None
            if not stream and not any([max_length, max_new_tokens, temperature, top_p, top_k, repetition_penalty]):
                cache_key = f"{self.current_model}:{hash(formatted_prompt)}"
                if cache_key in self.response_cache:
                    logger.info(f"Cache hit for prompt: {prompt[:30]}...")
                    return self.response_cache[cache_key]

            # Get model-specific generation parameters
            from .config import get_model_generation_params
            gen_params = get_model_generation_params(self.current_model)
            
            # Set optimized defaults for faster generation
            if not max_length and not max_new_tokens:
                # Use a smaller default max_length for faster generation
                gen_params["max_length"] = min(gen_params.get("max_length", DEFAULT_MAX_LENGTH), 512)
            
            if not temperature:
                # Slightly lower temperature for faster and more focused generation
                gen_params["temperature"] = min(gen_params.get("temperature", DEFAULT_TEMPERATURE), 0.7)
            
            if not top_k:
                # Add top_k for faster sampling
                gen_params["top_k"] = 40

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
            
            # Get the actual device of the model
            model_device = next(self.model.parameters()).device
            
            # Move inputs to the same device as the model
            for key in inputs:
                inputs[key] = inputs[key].to(model_device)

            if stream:
                return self.async_stream_generate(inputs, gen_params)

            # Check if we need to clear CUDA cache before generation
            if torch.cuda.is_available():
                current_mem = torch.cuda.memory_allocated() / (1024 * 1024 * 1024)  # GB
                total_mem = torch.cuda.get_device_properties(0).total_memory / (1024 * 1024 * 1024)  # GB
                if current_mem > 0.8 * total_mem:  # If using >80% of GPU memory
                    # Clear cache to avoid OOM
                    torch.cuda.empty_cache()
                    logger.info("Cleared CUDA cache before generation to avoid out of memory error")

            with torch.no_grad():
                try:
                    generate_params = {
                        **inputs,
                        "max_new_tokens": gen_params["max_length"],
                        "temperature": gen_params["temperature"],
                        "top_p": gen_params["top_p"],
                        "do_sample": True,
                        "pad_token_id": self.tokenizer.eos_token_id,
                        # Fix the early stopping warning by setting num_beams explicitly
                        "num_beams": 1
                    }

                    # Add optional parameters if present in gen_params
                    if "top_k" in gen_params:
                        generate_params["top_k"] = gen_params["top_k"]
                    if "repetition_penalty" in gen_params:
                        generate_params["repetition_penalty"] = gen_params["repetition_penalty"]
                    
                    # Set a reasonable max time for generation to prevent hanging
                    if "max_time" not in generate_params and not stream:
                        generate_params["max_time"] = 30.0  # 30 seconds max for generation
                    
                    # Use efficient attention implementation if available
                    if hasattr(self.model.config, "attn_implementation"):
                        generate_params["attn_implementation"] = "flash_attention_2"

                    # Generate text
                    start_time = time.time()
                    outputs = self.model.generate(**generate_params)
                    generation_time = time.time() - start_time
                    logger.info(f"Generation completed in {generation_time:.2f} seconds")
                
                except RuntimeError as e:
                    if "CUDA out of memory" in str(e):
                        # If we run out of memory, clear cache and try again with smaller parameters
                        torch.cuda.empty_cache()
                        logger.warning("CUDA out of memory during generation. Cleared cache and reducing parameters.")
                        
                        # Reduce parameters for memory efficiency
                        generate_params["max_new_tokens"] = min(generate_params.get("max_new_tokens", 512), 256)
                        
                        # Try again with reduced parameters
                        outputs = self.model.generate(**generate_params)
                    else:
                        # For other errors, re-raise
                        raise

            response = self.tokenizer.decode(
                outputs[0][len(inputs["input_ids"][0]):], skip_special_tokens=True)
            # Clean up response by removing system and user prompts if they got repeated
            response = response.replace(
                str(instructions), "").replace(prompt, "").strip()
            
            # Cache the response if we have a cache key
            if cache_key:
                self.response_cache[cache_key] = response
                # Limit cache size to prevent memory issues
                if len(self.response_cache) > 100:
                    # Remove oldest entries
                    for _ in range(10):
                        self.response_cache.pop(next(iter(self.response_cache)), None)
            
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
                top_k = gen_params.get("top_k", 40)  # Default to 40 for better quality
                repetition_penalty = gen_params.get("repetition_penalty", 1.1)
            else:
                # Use provided individual parameters or defaults
                max_length = max_length or min(DEFAULT_MAX_LENGTH, 512)  # Limit default max_length
                temperature = temperature or 0.7  # Use same temperature as non-streaming
                top_p = top_p or DEFAULT_TOP_P
                top_k = 40  # Default to 40 for better quality
                repetition_penalty = 1.1

            # Get the actual device of the model
            model_device = next(self.model.parameters()).device
            
            # Ensure inputs are on the same device as the model
            for key in inputs:
                if inputs[key].device != model_device:
                    inputs[key] = inputs[key].to(model_device)

            # Use KV caching for faster generation
            past_key_values = None
            input_ids = inputs["input_ids"]
            attention_mask = inputs["attention_mask"]
            
            # Generate fewer tokens at once for more responsive streaming
            # Using smaller chunks makes it appear more interactive while maintaining quality
            tokens_to_generate_per_step = 2  # Reduced from 3 to 2 for better quality control
            
            # Track generated text for quality control
            generated_text = ""
            
            # Define stop sequences for proper termination
            stop_sequences = ["</s>", "<|endoftext|>", "<|im_end|>", "<|assistant|>"]
            
            with torch.no_grad():
                for step in range(0, max_length, tokens_to_generate_per_step):
                    # Calculate how many tokens to generate in this step
                    current_tokens_to_generate = min(tokens_to_generate_per_step, max_length - step)
                    
                    # Generate parameters - use the same high-quality parameters as non-streaming
                    generate_params = {
                        "input_ids": input_ids,
                        "attention_mask": attention_mask,
                        "max_new_tokens": current_tokens_to_generate,
                        "temperature": temperature,
                        "top_p": top_p,
                        "top_k": top_k,
                        "do_sample": True,
                        "pad_token_id": self.tokenizer.eos_token_id,
                        "repetition_penalty": repetition_penalty,
                        "num_beams": 1  # Explicitly set to 1 to avoid warnings
                    }
                    
                    # Use efficient attention if available
                    if hasattr(self.model.config, "attn_implementation"):
                        generate_params["attn_implementation"] = "flash_attention_2"
                    
                    try:
                        # Generate tokens
                        outputs = self.model.generate(**generate_params)
                        
                        # Get the new tokens (skip the input tokens)
                        new_tokens = outputs[0][len(input_ids[0]):]
                        
                        # Decode and yield each new token
                        new_text = self.tokenizer.decode(new_tokens, skip_special_tokens=True)
                        
                        # If no new text was generated or it's just whitespace, stop generation
                        if not new_text or new_text.isspace():
                            break
                        
                        # Add to generated text for quality control
                        generated_text += new_text
                        
                        # Check for stop sequences
                        should_stop = False
                        for stop_seq in stop_sequences:
                            if stop_seq in generated_text:
                                # We've reached a stop sequence, stop generation
                                should_stop = True
                                break
                                
                        # Check for repetition (a sign of poor quality)
                        if len(generated_text) > 50:
                            # Check for repeating patterns of 10+ characters
                            last_50_chars = generated_text[-50:]
                            for pattern_len in range(10, 20):
                                if pattern_len < len(last_50_chars) // 2:
                                    pattern = last_50_chars[-pattern_len:]
                                    if pattern in last_50_chars[:-pattern_len]:
                                        # Detected repetition, stop generation
                                        logger.warning("Detected repetition in streaming generation, stopping")
                                        should_stop = True
                                        break
                        
                        # Yield the new text
                        yield new_text
                        
                        # Stop if needed
                        if should_stop:
                            break
                        
                        # Update input_ids and attention_mask for next iteration
                        input_ids = outputs
                        attention_mask = torch.ones_like(input_ids)
                        
                        # Ensure the updated inputs are on the correct device
                        if input_ids.device != model_device:
                            input_ids = input_ids.to(model_device)
                        if attention_mask.device != model_device:
                            attention_mask = attention_mask.to(model_device)
                            
                        # Check if we're running out of memory and need to clear cache
                        if torch.cuda.is_available():
                            current_mem = torch.cuda.memory_allocated() / (1024 * 1024 * 1024)  # GB
                            total_mem = torch.cuda.get_device_properties(0).total_memory / (1024 * 1024 * 1024)  # GB
                            if current_mem > 0.9 * total_mem:  # If using >90% of GPU memory
                                # Clear cache to avoid OOM
                                torch.cuda.empty_cache()
                                logger.info("Cleared CUDA cache to avoid out of memory error")
                    
                    except RuntimeError as e:
                        if "CUDA out of memory" in str(e):
                            # If we run out of memory, clear cache and try again with smaller batch
                            torch.cuda.empty_cache()
                            logger.warning("CUDA out of memory during streaming. Cleared cache and reducing batch size.")
                            
                            # Reduce tokens per step for the rest of generation
                            tokens_to_generate_per_step = 1
                            current_tokens_to_generate = 1
                            
                            # Try again with smaller batch
                            generate_params["max_new_tokens"] = 1
                            outputs = self.model.generate(**generate_params)
                            
                            # Continue as before
                            new_tokens = outputs[0][len(input_ids[0]):]
                            new_text = self.tokenizer.decode(new_tokens, skip_special_tokens=True)
                            
                            if not new_text or new_text.isspace():
                                break
                                
                            generated_text += new_text
                            yield new_text
                            
                            input_ids = outputs
                            attention_mask = torch.ones_like(input_ids)
                        else:
                            # For other errors, re-raise
                            raise

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
            
            # Set optimized defaults for streaming that match non-streaming quality
            # Use the same parameters as non-streaming for consistency
            if not kwargs.get("max_length") and not kwargs.get("max_new_tokens"):
                # Use a reasonable default max_length
                gen_params["max_length"] = min(gen_params.get("max_length", DEFAULT_MAX_LENGTH), 512)
            
            if not kwargs.get("temperature"):
                # Use the same temperature as non-streaming
                gen_params["temperature"] = min(gen_params.get("temperature", DEFAULT_TEMPERATURE), 0.7)
            
            if not kwargs.get("top_k"):
                # Add top_k for better quality
                gen_params["top_k"] = 40
                
            if not kwargs.get("repetition_penalty"):
                # Add repetition penalty to avoid loops
                gen_params["repetition_penalty"] = 1.1

            # Update with provided kwargs
            for key, value in kwargs.items():
                if key in ["max_length", "temperature", "top_p", "top_k", "repetition_penalty"]:
                    gen_params[key] = value
                elif key == "max_new_tokens":
                    # Handle the max_new_tokens parameter by mapping to max_length
                    gen_params["max_length"] = value

            # Tokenize the prompt
            inputs = self.tokenizer(formatted_prompt, return_tensors="pt")
            
            # Get the actual device of the model
            model_device = next(self.model.parameters()).device
            
            # Move inputs to the same device as the model
            for key in inputs:
                inputs[key] = inputs[key].to(model_device)

        # Check if we need to clear CUDA cache before generation
        if torch.cuda.is_available():
            current_mem = torch.cuda.memory_allocated() / (1024 * 1024 * 1024)  # GB
            total_mem = torch.cuda.get_device_properties(0).total_memory / (1024 * 1024 * 1024)  # GB
            if current_mem > 0.8 * total_mem:  # If using >80% of GPU memory
                # Clear cache to avoid OOM
                torch.cuda.empty_cache()
                logger.info("Cleared CUDA cache before streaming generation to avoid out of memory error")

        # Create a custom stream generator with improved quality
        async def improved_stream_generator():
            # Use the same stopping conditions as non-streaming
            stop_sequences = ["</s>", "<|endoftext|>", "<|im_end|>", "<|assistant|>"]
            accumulated_text = ""
            
            # Use a generator that produces high-quality chunks
            try:
                for token_chunk in self._stream_generate(inputs, gen_params=gen_params):
                    accumulated_text += token_chunk
                    
                    # Check for stop sequences
                    should_stop = False
                    for stop_seq in stop_sequences:
                        if stop_seq in accumulated_text:
                            # Truncate at stop sequence
                            accumulated_text = accumulated_text.split(stop_seq)[0]
                            should_stop = True
                            break
                    
                    # Yield the token chunk
                    yield token_chunk
                    
                    # Stop if we've reached a stop sequence
                    if should_stop:
                        break
                    
                    # Also stop if we've generated too much text (safety measure)
                    if len(accumulated_text) > gen_params.get("max_length", 512) * 4:  # Character estimate
                        logger.warning("Stream generation exceeded maximum length - stopping")
                        break
                        
                    await asyncio.sleep(0)
            except Exception as e:
                logger.error(f"Error in stream generation: {str(e)}")
                # Don't propagate the error to avoid breaking the stream
                # Just stop generating
        
        # Use the improved generator
        async for token in improved_stream_generator():
            yield token

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

        # Check environment variables for optimization settings
        enable_quantization = os.environ.get('LOCALLAB_ENABLE_QUANTIZATION', '').lower() not in ('false', '0', 'none', '')
        quantization_type = os.environ.get('LOCALLAB_QUANTIZATION_TYPE', '') if enable_quantization else "None"
        
        # If quantization is disabled or type is empty, set to "None"
        if not enable_quantization or not quantization_type or quantization_type.lower() in ('none', ''):
            quantization_type = "None"

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
            "quantization": quantization_type,
            "optimizations": {
                "attention_slicing": os.environ.get('LOCALLAB_ENABLE_ATTENTION_SLICING', '').lower() not in ('false', '0', 'none', ''),
                "flash_attention": os.environ.get('LOCALLAB_ENABLE_FLASH_ATTENTION', '').lower() not in ('false', '0', 'none', ''),
                "better_transformer": os.environ.get('LOCALLAB_ENABLE_BETTERTRANSFORMER', '').lower() not in ('false', '0', 'none', '')
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
• Attention Slicing: {Fore.YELLOW}{str(model_info['optimizations']['attention_slicing'])}{Style.RESET_ALL}
• Flash Attention: {Fore.YELLOW}{str(model_info['optimizations']['flash_attention'])}{Style.RESET_ALL}
• Better Transformer: {Fore.YELLOW}{str(model_info['optimizations']['better_transformer'])}{Style.RESET_ALL}
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
