import os
import logging
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig
from typing import Optional, Generator, Dict, Any, List
from fastapi import HTTPException
import time
from .config import (
    MODEL_REGISTRY, DEFAULT_MODEL, DEFAULT_MAX_LENGTH, DEFAULT_TEMPERATURE, DEFAULT_TOP_P,
    ENABLE_ATTENTION_SLICING, ENABLE_CPU_OFFLOADING, ENABLE_FLASH_ATTENTION,
    ENABLE_BETTERTRANSFORMER, ENABLE_QUANTIZATION, QUANTIZATION_TYPE, UNLOAD_UNUSED_MODELS, MODEL_TIMEOUT,
    ENABLE_COMPRESSION
)
from .logger.logger import logger, log_model_loaded, log_model_unloaded
from .utils import check_resource_availability, get_device, format_model_size
import gc
from colorama import Fore, Style
import asyncio

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
        
        if ENABLE_FLASH_ATTENTION:
            try:
                import flash_attn
                logger.info("Flash Attention enabled")
            except ImportError:
                logger.warning("Flash Attention not available")
    
    def _get_quantization_config(self) -> Optional[Dict[str, Any]]:
        """Get quantization configuration based on settings"""
        if not ENABLE_QUANTIZATION:
            return {
                "torch_dtype": torch.float16,
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
                    "torch_dtype": torch.float16,
                    "device_map": "auto"
                }
                
            if QUANTIZATION_TYPE == "int8":
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
                return {
                    "device_map": "auto",
                    "quantization_config": BitsAndBytesConfig(
                        load_in_4bit=True,
                        bnb_4bit_compute_dtype=torch.float16,
                        bnb_4bit_use_double_quant=True,
                        bnb_4bit_quant_type="nf4"
                    )
                }
            
        except ImportError:
            logger.warning(
                "bitsandbytes package not found or incompatible. "
                "Falling back to fp16. Please install bitsandbytes>=0.41.1 for quantization support."
            )
            return {
                "torch_dtype": torch.float16,
                "device_map": "auto"
            }
        except Exception as e:
            logger.warning(f"Error configuring quantization: {str(e)}. Falling back to fp16.")
            return {
                "torch_dtype": torch.float16,
                "device_map": "auto"
            }
        
        return {
            "torch_dtype": torch.float16,
            "device_map": "auto"
        }
    
    def _apply_optimizations(self, model: AutoModelForCausalLM) -> AutoModelForCausalLM:
        """Apply various optimizations to the model"""
        try:
            if ENABLE_ATTENTION_SLICING and hasattr(model, 'enable_attention_slicing'):
                model.enable_attention_slicing(1)
                logger.info("Attention slicing enabled")
                
            if ENABLE_CPU_OFFLOADING and hasattr(model, "enable_cpu_offload"):
                model.enable_cpu_offload()
                logger.info("CPU offloading enabled")
                
            if ENABLE_BETTERTRANSFORMER:
                try:
                    from optimum.bettertransformer import BetterTransformer
                    model = BetterTransformer.transform(model)
                    logger.info("BetterTransformer optimization applied")
                except ImportError:
                    logger.warning("BetterTransformer not available")
                    
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
            
            if config:
                logger.info(f"Using quantization config: {QUANTIZATION_TYPE}")
            
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
                
                if not ENABLE_QUANTIZATION:
                    device = "cuda" if torch.cuda.is_available() else "cpu"
                    self.model = self.model.to(device)
                
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
        temperature: float = DEFAULT_TEMPERATURE,
        top_p: float = DEFAULT_TOP_P,
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
            instructions = str(system_instructions.get_instructions(self.current_model)) if not system_instructions else str(system_instructions)
            
            # Format prompt with system instructions
            formatted_prompt = f"""<|system|>{instructions}</|system|>\n<|user|>{prompt}</|user|>\n<|assistant|>"""
            
            # Handle max_length properly
            try:
                if max_length is not None:
                    max_length = int(max_length)  # Convert to integer if provided
                else:
                    max_length = self.model_config.get("max_length", DEFAULT_MAX_LENGTH) if self.model_config else DEFAULT_MAX_LENGTH
                    max_length = int(max_length)  # Ensure it's an integer
            except (ValueError, TypeError) as e:
                logger.warning(f"Invalid max_length value: {max_length}. Using default: {DEFAULT_MAX_LENGTH}")
                max_length = DEFAULT_MAX_LENGTH
            
            inputs = self.tokenizer(formatted_prompt, return_tensors="pt")
            for key in inputs:
                inputs[key] = inputs[key].to(self.device)
            
            if stream:
                return self.async_stream_generate(inputs, max_length, temperature, top_p)
            
            with torch.no_grad():
                outputs = self.model.generate(
                    **inputs,
                    max_new_tokens=max_length,
                    temperature=temperature,
                    top_p=top_p,
                    do_sample=True,
                    pad_token_id=self.tokenizer.eos_token_id
                )
            
            response = self.tokenizer.decode(outputs[0][len(inputs["input_ids"][0]):], skip_special_tokens=True)
            # Clean up response by removing system and user prompts if they got repeated
            response = response.replace(str(instructions), "").replace(prompt, "").strip()
            return response
            
        except Exception as e:
            logger.error(f"Generation failed: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Generation failed: {str(e)}")
    
    def _stream_generate(
        self,
        inputs: Dict[str, torch.Tensor],
        max_length: int,
        temperature: float,
        top_p: float
    ) -> Generator[str, None, None]:
        """Stream generate text from the model"""
        try:
            with torch.no_grad():
                for _ in range(max_length):
                    outputs = self.model.generate(
                        **inputs,
                        max_new_tokens=1,
                        temperature=temperature,
                        top_p=top_p,
                        do_sample=True,
                        pad_token_id=self.tokenizer.eos_token_id
                    )
                    
                    new_token = self.tokenizer.decode(outputs[0][-1:], skip_special_tokens=True)
                    if not new_token or new_token.isspace():
                        break
                        
                    yield new_token
                    inputs = {"input_ids": outputs, "attention_mask": torch.ones_like(outputs)}
                    
        except Exception as e:
            logger.error(f"Streaming generation failed: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Streaming generation failed: {str(e)}")
    
    async def async_stream_generate(self, inputs: Dict[str, torch.Tensor], max_length: int, temperature: float, top_p: float):
        """Convert the synchronous stream generator to an async generator."""
        for token in self._stream_generate(inputs, max_length, temperature, top_p):
            yield token
            await asyncio.sleep(0)
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the currently loaded model"""
        if not self.current_model:
            return {"status": "No model loaded"}
        
        memory_used = 0
        if self.model:
            memory_used = sum(p.numel() * p.element_size() for p in self.model.parameters())
            num_parameters = sum(p.numel() for p in self.model.parameters())
        
        model_name = self.model_config.get("name", self.current_model) if isinstance(self.model_config, dict) else self.current_model
        max_length = self.model_config.get("max_length", DEFAULT_MAX_LENGTH) if isinstance(self.model_config, dict) else DEFAULT_MAX_LENGTH
        ram_required = self.model_config.get("ram", "Unknown") if isinstance(self.model_config, dict) else "Unknown"
        vram_required = self.model_config.get("vram", "Unknown") if isinstance(self.model_config, dict) else "Unknown"
        
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
                    return await self.load_model(fallback_model)
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
            
            model_size = sum(p.numel() * p.element_size() for p in self.model.parameters())
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
