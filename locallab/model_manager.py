# Import early configuration module first to set up logging and environment variables
# This ensures Hugging Face's progress bars are displayed correctly
from .utils.early_config import configure_hf_progress_bars, StdoutRedirector

from .config import HF_TOKEN_ENV, get_env_var, set_env_var
import os
import logging
import torch
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

# Enable Hugging Face progress bars with native display
# This ensures we see the visually appealing progress bars from HuggingFace
configure_hf_progress_bars()

# Import transformers after configuring logging to ensure proper display
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig

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
        self.model = None
        self.tokenizer = None
        self.current_model = None
        self._loading = False
        self._last_use = time.time()  # Initialize _last_use
        self.response_cache = {}  # Add cache dictionary
        self.model_config = {}  # Initialize model_config
        self.device = get_device()  # Initialize device

    @property
    def last_used(self) -> float:
        """Get the timestamp of last model use"""
        return self._last_use

    @last_used.setter
    def last_used(self, value: float):
        """Set the timestamp of last model use"""
        self._last_use = value

    def _get_safe_device_map(self) -> str:
        """Get a safe device mapping strategy that avoids disk offloading"""
        if torch.cuda.is_available():
            # Check available GPU memory
            try:
                gpu_memory = torch.cuda.get_device_properties(0).total_memory / (1024**3)  # GB
                logger.info(f"Available GPU memory: {gpu_memory:.1f} GB")

                # If we have sufficient GPU memory (>4GB), use GPU
                if gpu_memory > 4.0:
                    return "cuda:0"
                else:
                    logger.warning(f"Limited GPU memory ({gpu_memory:.1f} GB), using CPU to avoid disk offloading")
                    return "cpu"
            except Exception as e:
                logger.warning(f"Could not determine GPU memory: {e}, using CPU")
                return "cpu"
        else:
            return "cpu"

    def _get_quantization_config(self) -> Optional[Dict[str, Any]]:
        """Get quantization configuration based on settings"""
        # Check if quantization is explicitly disabled (not just False but also '0', 'none', '')
        # Use the config system to get the value, which checks environment variables and config file
        from .cli.config import get_config_value

        # Get safe device mapping
        safe_device_map = self._get_safe_device_map()

        # First check if CUDA is available - if not, we can't use bitsandbytes quantization
        if not torch.cuda.is_available():
            logger.info("GPU not detected - running in CPU mode with optimized settings")
            logger.info("💡 For faster inference, consider using a system with CUDA-compatible GPU")
            return {
                "torch_dtype": torch.float32,
                "device_map": safe_device_map
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
                "device_map": safe_device_map
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
                    "device_map": safe_device_map,
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
                    "device_map": safe_device_map,
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
                    "device_map": safe_device_map
                }

        except ImportError:
            logger.warning(
                "bitsandbytes package not found or incompatible. "
                "Falling back to fp16. Please install bitsandbytes>=0.41.1 for quantization support."
            )
            return {
                "torch_dtype": torch.float16 if torch.cuda.is_available() else torch.float32,
                "device_map": safe_device_map
            }

    def _apply_optimizations(self, model: AutoModelForCausalLM) -> AutoModelForCausalLM:
        """Apply various optimizations to the model with graceful fallbacks"""
        optimization_results = []

        try:
            # Import the config system
            from .cli.config import get_config_value

            # Only apply attention slicing if explicitly enabled and not empty
            enable_attention_slicing = get_config_value('enable_attention_slicing', ENABLE_ATTENTION_SLICING)
            if isinstance(enable_attention_slicing, str):
                enable_attention_slicing = enable_attention_slicing.lower() not in ('false', '0', 'none', '')

            if enable_attention_slicing:
                try:
                    if hasattr(model, 'enable_attention_slicing'):
                        # Use more aggressive slicing for faster inference
                        model.enable_attention_slicing("max")
                        logger.info("Attention slicing enabled with max setting")
                        optimization_results.append("✓ Attention slicing")
                    else:
                        logger.info("Attention slicing not available for this model")
                        optimization_results.append("- Attention slicing (not supported)")
                except Exception as e:
                    logger.debug(f"Attention slicing failed: {str(e)}")
                    optimization_results.append("- Attention slicing (failed)")

            # Only apply CPU offloading if explicitly enabled and not empty
            enable_cpu_offloading = get_config_value('enable_cpu_offloading', ENABLE_CPU_OFFLOADING)
            if isinstance(enable_cpu_offloading, str):
                enable_cpu_offloading = enable_cpu_offloading.lower() not in ('false', '0', 'none', '')

            if enable_cpu_offloading:
                try:
                    if hasattr(model, "enable_cpu_offload"):
                        model.enable_cpu_offload()
                        logger.info("CPU offloading enabled")
                        optimization_results.append("✓ CPU offloading")
                    else:
                        logger.info("CPU offloading not available for this model")
                        optimization_results.append("- CPU offloading (not supported)")
                except Exception as e:
                    logger.debug(f"CPU offloading failed: {str(e)}")
                    optimization_results.append("- CPU offloading (failed)")

            # Only apply BetterTransformer if explicitly enabled and not empty
            enable_bettertransformer = get_config_value('enable_better_transformer', ENABLE_BETTERTRANSFORMER)
            if isinstance(enable_bettertransformer, str):
                enable_bettertransformer = enable_bettertransformer.lower() not in ('false', '0', 'none', '')

            if enable_bettertransformer:
                try:
                    # Check transformers version compatibility
                    import transformers
                    from packaging import version

                    transformers_version = version.parse(transformers.__version__)
                    if transformers_version >= version.parse("4.49.0"):
                        logger.info("BetterTransformer is deprecated for transformers>=4.49.0, using native optimizations instead")
                        # Use native PyTorch optimizations instead
                        try:
                            if hasattr(model, "to_bettertransformer"):
                                # Some models still support the native method
                                model = model.to_bettertransformer()
                                logger.info("Applied native BetterTransformer optimization")
                                optimization_results.append("✓ Native BetterTransformer")
                            else:
                                logger.info("Using default PyTorch optimizations (BetterTransformer not needed)")
                                optimization_results.append("✓ Default PyTorch optimizations")
                        except Exception as e:
                            logger.debug(f"Native BetterTransformer not available: {str(e)}")
                            optimization_results.append("✓ Default PyTorch optimizations")
                    else:
                        # Use optimum BetterTransformer for older transformers versions
                        from optimum.bettertransformer import BetterTransformer
                        model = BetterTransformer.transform(model)
                        logger.info("BetterTransformer optimization applied via optimum")
                        optimization_results.append("✓ BetterTransformer (optimum)")
                except ImportError:
                    logger.info("BetterTransformer not available - using default PyTorch optimizations")
                    optimization_results.append("✓ Default PyTorch optimizations")
                except Exception as e:
                    logger.debug(f"BetterTransformer optimization skipped: {str(e)}")
                    optimization_results.append("- BetterTransformer (failed)")

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
                        optimization_results.append("✓ Flash Attention 2")
                    # For older models, try the flash_attn module
                    else:
                        import flash_attn
                        logger.info("Flash Attention enabled via module")
                        optimization_results.append("✓ Flash Attention")
                except ImportError:
                    logger.info(
                        "Flash Attention not available - using standard attention (install 'flash-attn' for faster inference)")
                    optimization_results.append("- Flash Attention (not installed)")
                except Exception as e:
                    logger.debug(f"Flash Attention optimization skipped: {str(e)}")
                    optimization_results.append("- Flash Attention (failed)")

            # Enable memory efficient attention if available
            try:
                if hasattr(model, "enable_xformers_memory_efficient_attention"):
                    model.enable_xformers_memory_efficient_attention()
                    logger.info("XFormers memory efficient attention enabled")
                    optimization_results.append("✓ XFormers memory efficient attention")
                else:
                    optimization_results.append("- XFormers (not supported)")
            except Exception as e:
                logger.debug(f"XFormers memory efficient attention not available: {str(e)}")
                optimization_results.append("- XFormers (not available)")

            # Enable gradient checkpointing for memory efficiency if available
            try:
                if hasattr(model, "gradient_checkpointing_enable"):
                    model.gradient_checkpointing_enable()
                    logger.info("Gradient checkpointing enabled for memory efficiency")
                    optimization_results.append("✓ Gradient checkpointing")
                else:
                    optimization_results.append("- Gradient checkpointing (not supported)")
            except Exception as e:
                logger.debug(f"Gradient checkpointing not available: {str(e)}")
                optimization_results.append("- Gradient checkpointing (failed)")

            # Set model to evaluation mode for faster inference
            model.eval()
            logger.info("Model set to evaluation mode for faster inference")
            optimization_results.append("✓ Evaluation mode")

            # Log optimization summary
            if optimization_results:
                logger.info(f"Applied optimizations: {', '.join(optimization_results)}")

            return model
        except Exception as e:
            logger.warning(f"Some optimizations could not be applied: {str(e)}")
            return model

    async def _load_model_with_optimizations(self, model_id: str):
        """Load and optimize a model with all configured optimizations"""
        try:
            # Get HF token
            from .config import get_hf_token
            hf_token = get_hf_token(interactive=False)

            # Apply quantization settings
            quant_config = self._get_quantization_config()

            # Log model loading start
            logger.info(f"Starting download and loading of model: {model_id}")
            print(f"\n{Fore.GREEN}Downloading model: {model_id}{Style.RESET_ALL}")
            print(f"{Fore.CYAN}This may take a while depending on your internet speed...{Style.RESET_ALL}")
            # Add an empty line to separate from HuggingFace progress bars
            print("")

            # Add an empty line before progress bars start
            print(f"\n{Fore.CYAN}Starting model download - native progress bars will appear below{Style.RESET_ALL}\n")

            # Enable Hugging Face progress bars again to ensure they're properly configured
            # Set environment variables directly for maximum compatibility
            os.environ["HF_HUB_DISABLE_PROGRESS_BARS"] = "0"
            os.environ["TRANSFORMERS_NO_PROGRESS_BAR"] = "0"
            configure_hf_progress_bars()

            # Use a context manager to ensure proper display of Hugging Face progress bars
            with StdoutRedirector(disable_logging=True):
                # Load tokenizer/processor first
                logger.info(f"Loading tokenizer for {model_id}...")

                # For vision-language models, try processor first
                processor_loaded = False
                if "vl" in model_id.lower() or "vision" in model_id.lower() or "qwen2.5-vl" in model_id.lower():
                    try:
                        from transformers import AutoProcessor
                        self.tokenizer = AutoProcessor.from_pretrained(
                            model_id,
                            token=hf_token if hf_token else None,
                            trust_remote_code=True
                        )
                        processor_loaded = True
                        logger.info(f"Loaded {model_id} processor successfully")
                    except Exception as e:
                        logger.info(f"Failed to load as processor, trying tokenizer: {e}")

                # If processor loading fails or not a VL model, try tokenizer
                if not processor_loaded:
                    self.tokenizer = AutoTokenizer.from_pretrained(
                        model_id,
                        token=hf_token if hf_token else None,
                        trust_remote_code=True
                    )
                    logger.info(f"Loaded {model_id} tokenizer successfully")
                logger.info(f"Tokenizer loaded successfully")

                # Load model with optimizations
                logger.info(f"Loading model weights for {model_id}...")

                # This is the critical part where we want to see nice progress bars
                # We'll temporarily disable our logger's handlers to prevent interference
                root_logger = logging.getLogger()
                original_handlers = root_logger.handlers.copy()
                root_logger.handlers = []

                try:
                    # Load the model with Hugging Face's native progress bars
                    # Try different model classes based on model type
                    model_loaded = False

                    # First try AutoModelForCausalLM (most common)
                    try:
                        self.model = AutoModelForCausalLM.from_pretrained(
                            model_id,
                            token=hf_token if hf_token else None,
                            trust_remote_code=True,  # Allow custom model code
                            **quant_config
                        )
                        model_loaded = True
                    except ValueError as e:
                        if "Unrecognized configuration class" in str(e):
                            logger.info(f"Model {model_id} is not a causal LM, trying other model types...")
                        else:
                            raise
                    except Exception as e:
                        # Handle disk offloading errors
                        if "disk_offload" in str(e).lower() or "offload the whole model" in str(e).lower():
                            logger.info("Retrying AutoModelForCausalLM with CPU-only configuration...")
                            try:
                                cpu_config = {
                                    "torch_dtype": torch.float32,
                                    "device_map": "cpu"
                                }
                                self.model = AutoModelForCausalLM.from_pretrained(
                                    model_id,
                                    token=hf_token if hf_token else None,
                                    trust_remote_code=True,
                                    **cpu_config
                                )
                                model_loaded = True
                                logger.info(f"Loaded {model_id} as AutoModelForCausalLM (CPU-only)")
                            except Exception as cpu_e:
                                logger.warning(f"CPU-only retry also failed: {cpu_e}")
                        else:
                            logger.warning(f"Failed to load as AutoModelForCausalLM: {e}")

                    # If that fails, try AutoModel (generic)
                    if not model_loaded:
                        try:
                            from transformers import AutoModel
                            self.model = AutoModel.from_pretrained(
                                model_id,
                                token=hf_token if hf_token else None,
                                trust_remote_code=True,
                                **quant_config
                            )
                            model_loaded = True
                            logger.info(f"Loaded {model_id} as AutoModel")
                        except Exception as e:
                            logger.warning(f"Failed to load as AutoModel: {e}")

                    # If that fails, try Qwen2_5_VLForConditionalGeneration (for Qwen2.5-VL models)
                    if not model_loaded:
                        try:
                            from transformers import Qwen2_5_VLForConditionalGeneration
                            self.model = Qwen2_5_VLForConditionalGeneration.from_pretrained(
                                model_id,
                                token=hf_token if hf_token else None,
                                trust_remote_code=True,
                                **quant_config
                            )
                            model_loaded = True
                            logger.info(f"Loaded {model_id} as Qwen2_5_VLForConditionalGeneration")
                        except Exception as e:
                            logger.warning(f"Failed to load as Qwen2_5_VLForConditionalGeneration: {e}")

                            # If it's a disk offloading error, try with CPU-only configuration
                            if "disk_offload" in str(e).lower() or "offload the whole model" in str(e).lower():
                                logger.info("Retrying Qwen2_5_VLForConditionalGeneration with CPU-only configuration...")
                                try:
                                    cpu_config = {
                                        "torch_dtype": torch.float32,
                                        "device_map": "cpu"
                                    }
                                    self.model = Qwen2_5_VLForConditionalGeneration.from_pretrained(
                                        model_id,
                                        token=hf_token if hf_token else None,
                                        trust_remote_code=True,
                                        **cpu_config
                                    )
                                    model_loaded = True
                                    logger.info(f"Loaded {model_id} as Qwen2_5_VLForConditionalGeneration (CPU-only)")
                                except Exception as cpu_e:
                                    logger.warning(f"CPU-only retry also failed: {cpu_e}")

                    # If that fails, try AutoModelForVision2Seq (for other vision models)
                    if not model_loaded:
                        try:
                            from transformers import AutoModelForVision2Seq
                            self.model = AutoModelForVision2Seq.from_pretrained(
                                model_id,
                                token=hf_token if hf_token else None,
                                trust_remote_code=True,
                                **quant_config
                            )
                            model_loaded = True
                            logger.info(f"Loaded {model_id} as AutoModelForVision2Seq")
                        except Exception as e:
                            logger.warning(f"Failed to load as AutoModelForVision2Seq: {e}")

                    # If all else fails, raise the original error
                    if not model_loaded:
                        logger.error(f"Could not load model {model_id} with any supported model class")
                        raise RuntimeError(f"Unsupported model type for {model_id}. This model may require specific handling or newer transformers version.")

                finally:
                    # Restore our logger's handlers
                    root_logger.handlers = original_handlers
            # Reset the downloading flag
            try:
                # Access the module's global variable
                import locallab.utils.progress
                locallab.utils.progress.is_downloading = False
            except:
                # Fallback if import fails
                pass

            # Add an empty line and a clear success message
            print(f"\n{Fore.GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{Style.RESET_ALL}")
            print(f"{Fore.GREEN}✅ Model {model_id} downloaded successfully!{Style.RESET_ALL}")
            print(f"{Fore.GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{Style.RESET_ALL}")
            logger.info(f"Model weights loaded successfully")

            # Apply additional optimizations
            logger.info(f"Applying optimizations to model...")
            self.model = self._apply_optimizations(self.model)

            # Set model to evaluation mode
            self.model.eval()
            logger.info(f"Model ready for inference")

            return self.model

        except Exception as e:
            logger.error(f"Error loading model: {str(e)}")
            raise

    async def load_model(self, model_id: str) -> None:
        """Load a model but don't persist it to config"""
        if self._loading:
            raise RuntimeError("Another model is currently loading")

        self._loading = True

        try:
            # Unload current model if any
            if self.model:
                self.unload_model()

            # Load the new model
            logger.info(f"Loading model: {model_id}")
            start_time = time.time()

            # Check if model is in registry first
            from .config import MODEL_REGISTRY
            if model_id in MODEL_REGISTRY:
                # Apply optimizations based on config for registry models
                self.model = await self._load_model_with_optimizations(model_id)
                self.current_model = model_id
                self.model_config = MODEL_REGISTRY[model_id]
            else:
                # Try to load as custom model if not in registry
                logger.info(f"Model {model_id} not found in registry, attempting to load as custom model")
                success = await self.load_custom_model(model_id, fallback_model=None)
                if not success:
                    raise RuntimeError(f"Failed to load custom model {model_id}")
                # load_custom_model sets self.current_model, but we need to ensure it matches the requested model_id
                self.current_model = model_id

            load_time = time.time() - start_time
            logger.info(f"Model loaded in {load_time:.2f} seconds")

            # Log the model load but don't persist to config
            log_model_loaded(model_id, load_time)

        except Exception as e:
            logger.error(f"Error loading model: {str(e)}")
            raise
        finally:
            self._loading = False

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
        system_instructions: Optional[str] = None,
        do_sample: bool = True,
        max_time: Optional[float] = None
    ) -> str:
        """Generate text from the model"""
        # Check model timeout
        self.check_model_timeout()

        if not self.model or not self.tokenizer:
            raise HTTPException(
                status_code=400,
                detail="No model is currently loaded. Please load a model first using the /models/load endpoint."
            )

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

            # Set optimized defaults for high-quality responses
            if not max_length and not max_new_tokens:
                # Use a higher default max_length for more complete, high-quality responses
                # Don't limit it too much to ensure complete responses
                gen_params["max_length"] = min(gen_params.get("max_length", DEFAULT_MAX_LENGTH), 4096)

            if not temperature:
                # Use a balanced temperature for high-quality responses
                gen_params["temperature"] = gen_params.get("temperature", DEFAULT_TEMPERATURE)

            if not top_k:
                # Use a higher top_k for better quality sampling
                gen_params["top_k"] = 80  # Increased from 50 to 80 for better quality

            if not top_p:
                # Use a higher top_p for better quality
                gen_params["top_p"] = 0.92  # Increased for better quality

            if not repetition_penalty:
                # Use a higher repetition_penalty for better quality
                gen_params["repetition_penalty"] = 1.15  # Increased from 1.1 to 1.15

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
                    # Generate parameters optimized for high-quality responses
                    generate_params = {
                        **inputs,
                        "max_new_tokens": gen_params["max_length"],
                        "temperature": gen_params["temperature"],
                        "top_p": gen_params["top_p"],
                        "top_k": gen_params.get("top_k", 80),  # Default to 80 for better quality
                        "do_sample": gen_params.get("do_sample", True),
                        "pad_token_id": self.tokenizer.eos_token_id,
                        # Fix the early stopping warning by setting num_beams explicitly
                        "num_beams": 1,
                        # Add repetition penalty for better quality
                        "repetition_penalty": gen_params.get("repetition_penalty", 1.15)  # Increased from 1.1 to 1.15
                    }

                    # Set a reasonable max time for generation to prevent hanging
                    # Use the provided max_time or a default value of 180 seconds
                    if not stream:
                        if max_time is not None:
                            generate_params["max_time"] = max_time
                        elif "max_time" not in generate_params:
                            # Default to 180 seconds (3 minutes) if not specified
                            generate_params["max_time"] = 180.0  # Default max time in seconds

                    # Define comprehensive stop sequences for proper termination
                    stop_sequences = [
                        "</s>", "<|endoftext|>", "<|im_end|>",
                        "<eos>", "<end>", "<|end|>", "<|EOS|>",
                        "###", "Assistant:", "Human:", "User:"
                    ]

                    # Add stop sequences to generation parameters if supported by the model
                    if hasattr(self.model.config, "stop_token_ids") or hasattr(self.model.generation_config, "stopping_criteria"):
                        # Convert stop sequences to token IDs
                        stop_token_ids = []
                        for seq in stop_sequences:
                            try:
                                ids = self.tokenizer.encode(seq, add_special_tokens=False)
                                if ids:
                                    stop_token_ids.extend(ids)
                            except:
                                pass

                        # Add stop token IDs to generation parameters if supported
                        if hasattr(self.model.config, "stop_token_ids"):
                            self.model.config.stop_token_ids = stop_token_ids

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

            # Decode the raw response without any formatting
            response = self.tokenizer.decode(
                outputs[0][len(inputs["input_ids"][0]):], skip_special_tokens=True)

            # Clean up response by removing conversation markers and everything after them
            conversation_end_markers = ["</|assistant|>", "<|user|>", "<|human|>", "<|reserved_special_token"]
            for end_marker in conversation_end_markers:
                if end_marker in response:
                    logger.info(f"Conversation end marker '{end_marker}' detected in response, truncating")
                    # Remove the end marker and everything after it
                    marker_pos = response.find(end_marker)
                    if marker_pos > 0:
                        response = response[:marker_pos]
                    break

            # Additional cleanup for any remaining special tokens using regex
            special_token_pattern = r'<\|[a-zA-Z0-9_]+\|>'
            response = re.sub(special_token_pattern, '', response)

            # Check for repetition patterns that indicate the model is stuck
            if len(response) > 200:
                # Look for repeating patterns of 20+ characters that repeat 3+ times
                for pattern_len in range(20, 40):
                    if pattern_len < len(response) // 3:
                        for i in range(len(response) - pattern_len * 3):
                            pattern = response[i:i+pattern_len]
                            if pattern and not pattern.isspace():
                                if response[i:].count(pattern) >= 3:
                                    # Found a repeating pattern, truncate at the second occurrence
                                    second_pos = response.find(pattern, i + pattern_len)
                                    if second_pos > 0:
                                        logger.info(f"Detected repetition pattern, truncating response")
                                        response = response[:second_pos + pattern_len]
                                        break

            # Cache the cleaned response if we have a cache key
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
        """Stream generate text from the model with optimizations for high-quality responses"""
        try:
            # If gen_params is provided, use it instead of individual parameters
            if gen_params is not None:
                max_length = gen_params.get("max_length", DEFAULT_MAX_LENGTH)
                temperature = gen_params.get(
                    "temperature", DEFAULT_TEMPERATURE)
                top_p = gen_params.get("top_p", DEFAULT_TOP_P)
                top_k = gen_params.get("top_k", 80)  # Increased from 40 to 80 for better quality
                repetition_penalty = gen_params.get("repetition_penalty", 1.15)  # Increased from 1.1 to 1.15
            else:
                # Use provided individual parameters or defaults
                max_length = max_length or DEFAULT_MAX_LENGTH  # Use the full default max length
                temperature = temperature or 0.7  # Use same temperature as non-streaming
                top_p = top_p or DEFAULT_TOP_P
                top_k = 80  # Increased from 40 to 80 for better quality
                repetition_penalty = 1.15  # Increased from 1.1 to 1.15

            # For balanced performance and quality, use a reasonable max_length
            # but not limit it too much to ensure complete responses
            if max_length > 2048:
                logger.info(f"Limiting max_length from {max_length} to 2048 for better performance while maintaining quality")
                max_length = 2048

            # Get the actual device of the model
            model_device = next(self.model.parameters()).device

            # Ensure inputs are on the same device as the model
            for key in inputs:
                if inputs[key].device != model_device:
                    inputs[key] = inputs[key].to(model_device)

            # Generate tokens in larger batches for better quality and efficiency
            # This balances memory usage with generation quality
            tokens_to_generate_per_step = 8  # Increased from 4 to 8 for better quality and efficiency

            # Track generated text for quality control
            generated_text = ""

            # Define comprehensive stop sequences for proper termination
            # Include all common end markers used by different models
            stop_sequences = [
                "</s>", "<|endoftext|>", "<|im_end|>",
                "<eos>", "<end>", "<|end|>", "<|EOS|>",
                "###", "Assistant:", "Human:", "User:"
            ]

            # Memory monitoring variables - reduced frequency to avoid interrupting generation
            last_memory_check = time.time()
            memory_check_interval = 10.0  # Increased from 5.0 to 10.0 seconds to reduce interruptions

            # Get input IDs and attention mask
            input_ids = inputs["input_ids"]
            attention_mask = inputs["attention_mask"]

            with torch.no_grad():
                for step in range(0, max_length, tokens_to_generate_per_step):
                    # Periodically check memory usage and clear cache if needed
                    current_time = time.time()
                    if current_time - last_memory_check > memory_check_interval:
                        last_memory_check = current_time
                        if torch.cuda.is_available():
                            current_mem = torch.cuda.memory_allocated() / (1024 * 1024 * 1024)  # GB
                            total_mem = torch.cuda.get_device_properties(0).total_memory / (1024 * 1024 * 1024)  # GB
                            if current_mem > 0.9 * total_mem:  # Only clear if using >90% of GPU memory (increased from 85%)
                                torch.cuda.empty_cache()
                                logger.info("Cleared CUDA cache during streaming to prevent OOM")

                    # Generate parameters - optimized for high-quality responses
                    generate_params = {
                        "input_ids": input_ids,
                        "attention_mask": attention_mask,
                        "max_new_tokens": tokens_to_generate_per_step,
                        "temperature": temperature,
                        "top_p": top_p,
                        "top_k": top_k,
                        "do_sample": gen_params.get("do_sample", True) if gen_params else True,
                        "pad_token_id": self.tokenizer.eos_token_id,
                        "repetition_penalty": repetition_penalty,
                        "num_beams": 1  # Explicitly set to 1 to avoid warnings
                    }

                    # Use efficient attention if available, but only on CUDA devices
                    if torch.cuda.is_available() and hasattr(self.model.config, "attn_implementation"):
                        generate_params["attn_implementation"] = "flash_attention_2"

                    try:
                        # Generate tokens
                        outputs = self.model.generate(**generate_params)

                        # Get the new tokens (skip the input tokens)
                        new_tokens = outputs[0][len(input_ids[0]):]

                        # Decode the new token
                        new_text = self.tokenizer.decode(new_tokens, skip_special_tokens=True)

                        # If no new text was generated or it's just whitespace, skip this token but continue generation
                        if not new_text or new_text.isspace():
                            continue

                        # Add to generated text for quality control
                        generated_text += new_text

                        # Enhanced stop sequence detection - check for both definitive end markers and conversation markers
                        should_stop = False

                        # Definitive end markers
                        for stop_seq in stop_sequences:
                            if stop_seq in new_text:  # Only check in the new text, not the entire generated text
                                # We've reached a stop sequence, stop generation
                                logger.info(f"Stop sequence '{stop_seq}' detected, stopping generation")
                                should_stop = True
                                break

                        # Check for conversation markers that indicate the end of assistant's response
                        conversation_end_markers = ["</|assistant|>", "<|user|>", "<|human|>", "<|reserved_special_token"]
                        for end_marker in conversation_end_markers:
                            if end_marker in new_text:
                                logger.info(f"Conversation end marker '{end_marker}' detected, stopping generation")
                                # Remove the end marker and everything after it from the generated text
                                marker_pos = new_text.find(end_marker)
                                if marker_pos > 0:
                                    new_text = new_text[:marker_pos]
                                should_stop = True
                                break

                        # Modified repetition detection - only stop for extreme repetition
                        # This allows for legitimate repetition in responses
                        if len(generated_text) > 150:  # Increased from 100 to 150 to allow more context
                            # Check for repeating patterns of 15+ characters that repeat 4+ times
                            # Increased thresholds to be less aggressive in stopping generation
                            last_150_chars = generated_text[-150:]
                            for pattern_len in range(15, 25):  # Increased from 10-20 to 15-25
                                if pattern_len < len(last_150_chars) // 4:  # Increased from 3 to 4
                                    pattern = last_150_chars[-pattern_len:]
                                    # Check if pattern appears 4 or more times (increased from 3)
                                    if last_150_chars.count(pattern) >= 4:
                                        logger.warning("Detected extreme repetition in streaming generation, stopping")
                                        should_stop = True
                                        break

                        # Yield the new text
                        yield new_text

                        # Stop if needed
                        if should_stop:
                            break

                        # Update input_ids for next iteration
                        input_ids = outputs
                        attention_mask = torch.ones_like(input_ids)

                        # Ensure the updated inputs are on the correct device
                        if input_ids.device != model_device:
                            input_ids = input_ids.to(model_device)
                        if attention_mask.device != model_device:
                            attention_mask = attention_mask.to(model_device)

                    except RuntimeError as e:
                        error_msg = str(e)
                        if "CUDA out of memory" in error_msg or "DefaultCPUAllocator: can't allocate memory" in error_msg:
                            # If we run out of memory, clear cache and try to recover
                            if torch.cuda.is_available():
                                torch.cuda.empty_cache()

                            logger.warning(f"Memory error during streaming: {error_msg}. Attempting to recover...")

                            # Wait a moment to let memory clear
                            time.sleep(0.5)

                            try:
                                # Try again with minimal parameters but still generate tokens
                                minimal_params = {
                                    "input_ids": input_ids,
                                    "attention_mask": attention_mask,
                                    "max_new_tokens": 1,  # Generate just one token
                                    "do_sample": True,  # Keep sampling on for better quality
                                    "temperature": 0.7,  # Use a balanced temperature
                                    "top_k": 40,  # Use a reasonable top_k
                                    "pad_token_id": self.tokenizer.eos_token_id,
                                    "num_beams": 1
                                }
                                outputs = self.model.generate(**minimal_params)

                                # Continue as before
                                new_tokens = outputs[0][len(input_ids[0]):]
                                new_text = self.tokenizer.decode(new_tokens, skip_special_tokens=True)

                                if new_text and not new_text.isspace():
                                    generated_text += new_text
                                    yield new_text

                                    input_ids = outputs
                                    attention_mask = torch.ones_like(input_ids)

                                    # Reduce tokens_to_generate_per_step to prevent future OOM
                                    tokens_to_generate_per_step = 2  # Increased from 1 to 2 for better quality
                                    logger.info("Reduced generation batch size to 2 tokens at a time after OOM recovery")
                                else:
                                    # If recovery didn't produce valid text, try one more time with different settings
                                    logger.warning("First recovery attempt didn't produce valid text, trying again with different settings")

                                    # Try with different temperature
                                    minimal_params["temperature"] = 0.9
                                    minimal_params["top_p"] = 0.95  # Increase top_p for more diversity
                                    outputs = self.model.generate(**minimal_params)

                                    new_tokens = outputs[0][len(input_ids[0]):]
                                    new_text = self.tokenizer.decode(new_tokens, skip_special_tokens=True)

                                    if new_text and not new_text.isspace():
                                        generated_text += new_text
                                        yield new_text

                                        input_ids = outputs
                                        attention_mask = torch.ones_like(input_ids)
                                        tokens_to_generate_per_step = 2  # Use 2 tokens for better quality
                                    else:
                                        # If still no valid text, stop generation
                                        logger.warning("Recovery attempts failed to produce valid text, stopping generation")
                                        break
                            except Exception as recovery_error:
                                # If recovery fails, yield an error message and stop
                                logger.error(f"Recovery failed: {str(recovery_error)}")
                                yield "\nError: Out of memory. Try a shorter response or reduce model parameters."
                                break
                        else:
                            # For other errors, log and yield error message
                            logger.error(f"Error during streaming: {error_msg}")
                            yield f"\nError: {error_msg}"
                            break

        except Exception as e:
            logger.error(f"Streaming generation failed: {str(e)}")
            # Instead of raising an exception, yield the error as text
            # This allows the client to display the error message
            yield f"\nError: {str(e)}"

    async def async_stream_generate(self, inputs: Dict[str, torch.Tensor] = None, gen_params: Dict[str, Any] = None, prompt: str = None, system_prompt: Optional[str] = None, **kwargs):
        """Convert the synchronous stream generator to an async generator with optimizations for high-quality responses.

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

            # Set optimized defaults for streaming with high-quality responses
            if not kwargs.get("max_length") and not kwargs.get("max_new_tokens"):
                # Use a balanced default max_length that ensures quality while being efficient
                gen_params["max_length"] = min(gen_params.get("max_length", DEFAULT_MAX_LENGTH), 2048)

            if not kwargs.get("temperature"):
                # Use a balanced temperature for quality responses
                gen_params["temperature"] = gen_params.get("temperature", DEFAULT_TEMPERATURE)

            if not kwargs.get("top_k"):
                # Add top_k for better quality
                gen_params["top_k"] = 80  # Increased from 40 to 80 for better quality

            if not kwargs.get("repetition_penalty"):
                # Add repetition penalty to avoid loops but allow natural repetition
                gen_params["repetition_penalty"] = 1.15  # Increased from 1.1 to 1.15

            # Update with provided kwargs
            for key, value in kwargs.items():
                if key in ["max_length", "temperature", "top_p", "top_k", "repetition_penalty", "max_time"]:
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

        # Check if we need to clear memory before generation
        if torch.cuda.is_available():
            # Only clear cache if memory usage is high to avoid unnecessary interruptions
            current_mem = torch.cuda.memory_allocated() / (1024 * 1024 * 1024)  # GB
            total_mem = torch.cuda.get_device_properties(0).total_memory / (1024 * 1024 * 1024)  # GB
            if current_mem > 0.8 * total_mem:  # Only clear if using >80% of GPU memory
                torch.cuda.empty_cache()
                logger.info("Cleared CUDA cache before streaming generation to ensure optimal performance")

        # Create a token-level streaming generator optimized for high-quality responses
        async def token_level_stream_generator():
            # Define comprehensive stop sequences for proper termination
            # Include all common end markers used by different models
            stop_sequences = [
                "</s>", "<|endoftext|>", "<|im_end|>",
                "<eos>", "<end>", "<|end|>", "<|EOS|>",
                "###", "Assistant:", "Human:", "User:"
            ]
            accumulated_text = ""
            token_buffer = ""
            last_yield_time = time.time()
            error_reported = False

            try:
                # Use the optimized _stream_generate method
                for token in self._stream_generate(inputs, gen_params=gen_params):
                    # Check if this is an error message
                    if token.startswith("\nError:"):
                        if not error_reported:
                            yield token
                            error_reported = True
                        break

                    # Skip empty tokens
                    if not token or token.isspace():
                        continue

                    # Clean token of any special tokens before adding to buffer
                    cleaned_token = token

                    # Check for special tokens and remove them
                    special_token_pattern = r'<\|[a-zA-Z0-9_]+\|>'
                    matches = re.finditer(special_token_pattern, cleaned_token)
                    for match in matches:
                        cleaned_token = cleaned_token.replace(match.group(0), "")

                    # Add cleaned token to buffer
                    token_buffer += cleaned_token
                    accumulated_text += cleaned_token

                    # Enhanced stop sequence detection - check for both definitive end markers and conversation markers
                    should_stop = False

                    # Check for definitive end markers
                    for stop_seq in stop_sequences:
                        if stop_seq in token:
                            # Log the stop sequence detection
                            logger.info(f"Stop sequence '{stop_seq}' detected in async streaming, stopping")
                            # Don't truncate the text - just stop generating more
                            should_stop = True
                            break

                    # Check for conversation markers that indicate the end of assistant's response
                    conversation_end_markers = ["</|assistant|>", "<|user|>", "<|human|>", "<|reserved_special_token"]
                    for end_marker in conversation_end_markers:
                        if end_marker in token:
                            logger.info(f"Conversation end marker '{end_marker}' detected in async streaming, stopping")
                            # Remove the end marker and everything after it from the token
                            marker_pos = token.find(end_marker)
                            if marker_pos > 0:
                                # Update token buffer with truncated token
                                token_buffer = token_buffer[:-(len(token) - marker_pos)]
                                token = token[:marker_pos]
                            should_stop = True
                            break

                    # Determine if we should yield the buffer now
                    current_time = time.time()
                    time_since_last_yield = current_time - last_yield_time

                    # Enhanced yielding logic for smoother streaming:
                    # 1. Buffer contains complete word (ends with space)
                    # 2. Buffer contains punctuation
                    # 3. It's been more than 30ms since last yield (reduced from 50ms for smoother streaming)
                    # 4. Buffer is getting large (>4 chars) (reduced from 5 for more frequent updates)
                    should_yield = (
                        token.endswith(" ") or
                        any(p in token for p in ".,!?;:") or
                        time_since_last_yield > 0.03 or  # Reduced from 0.05 to 0.03 for smoother streaming
                        len(token_buffer) > 4  # Reduced from 5 to 4 for more frequent updates
                    )

                    if should_yield and token_buffer:
                        # Yield the raw token buffer without any formatting
                        yield token_buffer
                        last_yield_time = current_time
                        token_buffer = ""

                    # Stop if we've reached a stop sequence
                    if should_stop:
                        break

                    # Increase the maximum length limit to ensure complete responses
                    # Only stop if we've generated an extremely long response
                    max_length_multiplier = 10  # Increased from 8 to 10 for more complete responses
                    if len(accumulated_text) > gen_params.get("max_length", 512) * max_length_multiplier:
                        logger.warning(f"Stream generation exceeded maximum length ({gen_params.get('max_length', 512) * max_length_multiplier} chars) - stopping")
                        break

                    # Yield control to allow other async tasks to run
                    # Use a shorter sleep time for more responsive streaming
                    await asyncio.sleep(0)

                # Yield any remaining text in the buffer
                if token_buffer and not error_reported:
                    # Yield the raw token buffer without any formatting
                    yield token_buffer

            except Exception as e:
                logger.error(f"Error in token-level stream generation: {str(e)}")
                # Send error message to client if not already reported
                if not error_reported:
                    yield f"\nError: {str(e)}"

        # Use the token-level streaming generator
        async for token in token_level_stream_generator():
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

        # Get optimization settings from config
        from .cli.config import get_config_value
        from .config import ENABLE_QUANTIZATION, QUANTIZATION_TYPE, ENABLE_ATTENTION_SLICING, ENABLE_FLASH_ATTENTION, ENABLE_BETTERTRANSFORMER

        # Get values from config with defaults from constants
        enable_quantization = get_config_value('enable_quantization', ENABLE_QUANTIZATION)
        if isinstance(enable_quantization, str):
            enable_quantization = enable_quantization.lower() not in ('false', '0', 'none', '')

        quantization_type = get_config_value('quantization_type', QUANTIZATION_TYPE) if enable_quantization else "None"

        # If quantization is disabled or type is empty, set to "None"
        if not enable_quantization or not quantization_type or quantization_type.lower() in ('none', ''):
            quantization_type = "None"

        # Get other optimization settings
        enable_attention_slicing = get_config_value('enable_attention_slicing', ENABLE_ATTENTION_SLICING)
        if isinstance(enable_attention_slicing, str):
            enable_attention_slicing = enable_attention_slicing.lower() not in ('false', '0', 'none', '')

        enable_flash_attention = get_config_value('enable_flash_attention', ENABLE_FLASH_ATTENTION)
        if isinstance(enable_flash_attention, str):
            enable_flash_attention = enable_flash_attention.lower() not in ('false', '0', 'none', '')

        enable_bettertransformer = get_config_value('enable_bettertransformer', ENABLE_BETTERTRANSFORMER)
        if isinstance(enable_bettertransformer, str):
            enable_bettertransformer = enable_bettertransformer.lower() not in ('false', '0', 'none', '')

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
                "attention_slicing": enable_attention_slicing,
                "flash_attention": enable_flash_attention,
                "better_transformer": enable_bettertransformer
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

    async def load_custom_model(self, model_name: str, fallback_model: Optional[str] = None) -> bool:
        """Load a custom model from Hugging Face Hub with resource checks"""
        try:
            from huggingface_hub import model_info

            # Get HF token
            from .config import get_hf_token
            hf_token = get_hf_token(interactive=False)

            logger.info(f"Fetching model info for custom model: {model_name}")
            info = model_info(model_name, token=hf_token if hf_token else None)

            # Get model size from siblings if available
            estimated_ram = 0
            try:
                if hasattr(info, 'siblings') and info.siblings and len(info.siblings) > 0:
                    for sibling in info.siblings:
                        if hasattr(sibling, 'size') and sibling.size is not None:
                            estimated_ram = max(estimated_ram, sibling.size / (1024 * 1024))
                            break

                # If no size found from siblings, try safetensors
                if estimated_ram == 0 and hasattr(info, 'safetensors') and info.safetensors:
                    if hasattr(info.safetensors, 'total') and info.safetensors.total:
                        estimated_ram = info.safetensors.total / (1024 * 1024)

                # If still no size, use fallback estimation based on model name patterns
                if estimated_ram == 0:
                    if "3b" in model_name.lower():
                        estimated_ram = 6000  # 6GB for 3B models
                    elif "7b" in model_name.lower():
                        estimated_ram = 14000  # 14GB for 7B models
                    elif "1b" in model_name.lower():
                        estimated_ram = 2000  # 2GB for 1B models
                    else:
                        estimated_ram = 4000  # Default 4GB
            except Exception as e:
                logger.warning(f"Could not estimate model size: {e}. Using default estimation.")
                if "3b" in model_name.lower():
                    estimated_ram = 6000  # 6GB for 3B models
                elif "7b" in model_name.lower():
                    estimated_ram = 14000  # 14GB for 7B models
                elif "1b" in model_name.lower():
                    estimated_ram = 2000  # 2GB for 1B models
                else:
                    estimated_ram = 4000  # Default 4GB

            estimated_vram = estimated_ram * 1.5

            # Safely get description and tags
            description = "No description available"
            tags = []
            try:
                if hasattr(info, 'cardData') and info.cardData and hasattr(info.cardData, 'get'):
                    description = info.cardData.get('description', description)
                elif hasattr(info, 'description') and info.description:
                    description = info.description
            except:
                pass

            try:
                if hasattr(info, 'tags') and info.tags:
                    tags = info.tags
            except:
                pass

            temp_config = {
                "name": model_name,
                "ram": estimated_ram,
                "vram": estimated_vram,
                "max_length": 2048,
                "fallback": fallback_model,
                "description": f"Custom model: {description}",
                "quantization": "int8",
                "tags": tags
            }

            # Skip resource check for now to allow loading - user can configure optimizations
            # if not check_resource_availability(temp_config["ram"]):
            #     if fallback_model:
            #         logger.warning(
            #             f"Insufficient resources for {model_name} "
            #             f"(Requires ~{format_model_size(temp_config['ram'])} RAM), "
            #             f"falling back to {fallback_model}"
            #         )
            #         return await self.load_model(fallback_model)
            #     raise HTTPException(
            #         status_code=400,
            #         detail=f"Insufficient resources. Model requires ~{format_model_size(temp_config['ram'])} RAM"
            #     )

            if self.model:
                del self.model
                torch.cuda.empty_cache()

            logger.info(f"Loading custom model: {model_name}")

            # Use the same optimized loading approach as regular models
            # Get HF token
            from .config import get_hf_token
            hf_token = get_hf_token(interactive=False)

            # Apply quantization settings
            quant_config = self._get_quantization_config()

            # Log model loading start
            logger.info(f"Starting download and loading of custom model: {model_name}")
            print(f"\n{Fore.GREEN}Downloading custom model: {model_name}{Style.RESET_ALL}")
            print(f"{Fore.CYAN}This may take a while depending on your internet speed...{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}Estimated size: ~{estimated_ram/1024:.1f}GB{Style.RESET_ALL}")
            # Add an empty line to separate from HuggingFace progress bars
            print("")

            # Add an empty line before progress bars start
            print(f"\n{Fore.CYAN}Starting custom model download - native progress bars will appear below{Style.RESET_ALL}\n")

            # Enable Hugging Face progress bars again to ensure they're properly configured
            # Set environment variables directly for maximum compatibility
            os.environ["HF_HUB_DISABLE_PROGRESS_BARS"] = "0"
            os.environ["TRANSFORMERS_NO_PROGRESS_BAR"] = "0"
            configure_hf_progress_bars()

            # Use a context manager to ensure proper display of Hugging Face progress bars
            with StdoutRedirector(disable_logging=True):
                # Load tokenizer first
                logger.info(f"Loading tokenizer for custom model {model_name}...")

                # This is the critical part where we want to see nice progress bars
                # We'll temporarily disable our logger's handlers to prevent interference
                root_logger = logging.getLogger()
                original_handlers = root_logger.handlers.copy()
                root_logger.handlers = []

                try:
                    # Load tokenizer/processor with Hugging Face's native progress bars
                    logger.info(f"Attempting to load tokenizer for {model_name}")

                    # For vision-language models, try processor first
                    processor_loaded = False
                    if "vl" in model_name.lower() or "vision" in model_name.lower() or "qwen2.5-vl" in model_name.lower():
                        try:
                            from transformers import AutoProcessor
                            self.tokenizer = AutoProcessor.from_pretrained(
                                model_name,
                                token=hf_token if hf_token else None,
                                trust_remote_code=True
                            )
                            processor_loaded = True
                            logger.info(f"Loaded {model_name} processor successfully")
                        except Exception as e:
                            logger.info(f"Failed to load as processor, trying tokenizer: {e}")

                    # If processor loading fails or not a VL model, try tokenizer
                    if not processor_loaded:
                        self.tokenizer = AutoTokenizer.from_pretrained(
                            model_name,
                            token=hf_token if hf_token else None,
                            trust_remote_code=True  # Allow custom tokenizers
                        )
                        logger.info(f"Tokenizer loaded successfully")

                    # Load model with optimizations
                    logger.info(f"Loading model weights for custom model {model_name}...")

                    # Load the model with Hugging Face's native progress bars
                    # Try different model classes based on model type
                    model_loaded = False

                    # First try AutoModelForCausalLM (most common)
                    try:
                        self.model = AutoModelForCausalLM.from_pretrained(
                            model_name,
                            token=hf_token if hf_token else None,
                            trust_remote_code=True,  # Allow custom model code
                            **quant_config
                        )
                        model_loaded = True
                    except ValueError as e:
                        if "Unrecognized configuration class" in str(e):
                            logger.info(f"Model {model_name} is not a causal LM, trying other model types...")
                        else:
                            raise
                    except Exception as e:
                        # Handle disk offloading errors
                        if "disk_offload" in str(e).lower() or "offload the whole model" in str(e).lower():
                            logger.info("Retrying AutoModelForCausalLM with CPU-only configuration...")
                            try:
                                cpu_config = {
                                    "torch_dtype": torch.float32,
                                    "device_map": "cpu"
                                }
                                self.model = AutoModelForCausalLM.from_pretrained(
                                    model_name,
                                    token=hf_token if hf_token else None,
                                    trust_remote_code=True,
                                    **cpu_config
                                )
                                model_loaded = True
                                logger.info(f"Loaded {model_name} as AutoModelForCausalLM (CPU-only)")
                            except Exception as cpu_e:
                                logger.warning(f"CPU-only retry also failed: {cpu_e}")
                        else:
                            logger.warning(f"Failed to load as AutoModelForCausalLM: {e}")

                    # If that fails, try AutoModel (generic)
                    if not model_loaded:
                        try:
                            from transformers import AutoModel
                            self.model = AutoModel.from_pretrained(
                                model_name,
                                token=hf_token if hf_token else None,
                                trust_remote_code=True,
                                **quant_config
                            )
                            model_loaded = True
                            logger.info(f"Loaded {model_name} as AutoModel")
                        except Exception as e:
                            logger.warning(f"Failed to load as AutoModel: {e}")

                    # If that fails, try Qwen2_5_VLForConditionalGeneration (for Qwen2.5-VL models)
                    if not model_loaded:
                        try:
                            from transformers import Qwen2_5_VLForConditionalGeneration
                            self.model = Qwen2_5_VLForConditionalGeneration.from_pretrained(
                                model_name,
                                token=hf_token if hf_token else None,
                                trust_remote_code=True,
                                **quant_config
                            )
                            model_loaded = True
                            logger.info(f"Loaded {model_name} as Qwen2_5_VLForConditionalGeneration")
                        except Exception as e:
                            logger.warning(f"Failed to load as Qwen2_5_VLForConditionalGeneration: {e}")

                            # If it's a disk offloading error, try with CPU-only configuration
                            if "disk_offload" in str(e).lower() or "offload the whole model" in str(e).lower():
                                logger.info("Retrying Qwen2_5_VLForConditionalGeneration with CPU-only configuration...")
                                try:
                                    cpu_config = {
                                        "torch_dtype": torch.float32,
                                        "device_map": "cpu"
                                    }
                                    self.model = Qwen2_5_VLForConditionalGeneration.from_pretrained(
                                        model_name,
                                        token=hf_token if hf_token else None,
                                        trust_remote_code=True,
                                        **cpu_config
                                    )
                                    model_loaded = True
                                    logger.info(f"Loaded {model_name} as Qwen2_5_VLForConditionalGeneration (CPU-only)")
                                except Exception as cpu_e:
                                    logger.warning(f"CPU-only retry also failed: {cpu_e}")

                    # If that fails, try AutoModelForVision2Seq (for other vision models)
                    if not model_loaded:
                        try:
                            from transformers import AutoModelForVision2Seq
                            self.model = AutoModelForVision2Seq.from_pretrained(
                                model_name,
                                token=hf_token if hf_token else None,
                                trust_remote_code=True,
                                **quant_config
                            )
                            model_loaded = True
                            logger.info(f"Loaded {model_name} as AutoModelForVision2Seq")
                        except Exception as e:
                            logger.warning(f"Failed to load as AutoModelForVision2Seq: {e}")

                    # If all else fails, raise the original error
                    if not model_loaded:
                        logger.error(f"Could not load model {model_name} with any supported model class")
                        raise RuntimeError(f"Unsupported model type for {model_name}. This model may require specific handling or newer transformers version.")
                    logger.info(f"Model weights loaded successfully")

                except Exception as e:
                    # Restore handlers before logging error
                    root_logger.handlers = original_handlers
                    logger.error(f"Error during model loading: {str(e)}")

                    # Check for common authentication errors
                    if "401" in str(e) or "Unauthorized" in str(e):
                        logger.error("Authentication failed. Please check your HuggingFace token.")
                        logger.info("You can update your token using: locallab config")
                    elif "404" in str(e) or "not found" in str(e).lower():
                        logger.error(f"Model {model_name} not found on HuggingFace Hub.")
                        logger.info("Please check the model name and ensure it exists.")
                    elif "trust_remote_code" in str(e):
                        logger.error("This model requires trust_remote_code=True but failed to load.")
                        logger.info("This might be a security restriction or model compatibility issue.")

                    raise
                finally:
                    # Restore our logger's handlers
                    root_logger.handlers = original_handlers
            # Reset the downloading flag
            try:
                # Access the module's global variable
                import locallab.utils.progress
                locallab.utils.progress.is_downloading = False
            except:
                # Fallback if import fails
                pass

            # Add an empty line and a clear success message
            print(f"\n{Fore.GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{Style.RESET_ALL}")
            print(f"{Fore.GREEN}✅ Custom model {model_name} downloaded successfully!{Style.RESET_ALL}")
            print(f"{Fore.GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{Style.RESET_ALL}")
            logger.info(f"Model weights loaded successfully")

            # Apply additional optimizations
            logger.info(f"Applying optimizations to custom model...")
            self.model = self._apply_optimizations(self.model)

            # Set model to evaluation mode
            self.model.eval()
            logger.info(f"Custom model ready for inference")

            # Set current model to the exact model name requested (not prefixed with "custom/")
            self.current_model = model_name
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
            # Don't raise HTTPException here since this might be called from load_model
            # Just re-raise the original exception
            raise

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