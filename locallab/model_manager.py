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
from .logger import logger
from .utils import check_resource_availability, get_device, format_model_size
import gc

# Define quantization settings here since it's model manager specific
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
        
        # Initialize optimizations
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
                # Fallback to fp16 if bitsandbytes version is too old
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
        
        # Default to FP16
        return {
            "torch_dtype": torch.float16,
            "device_map": "auto"
        }
    
    def _apply_optimizations(self, model: AutoModelForCausalLM) -> AutoModelForCausalLM:
        """Apply various optimizations to the model"""
        if ENABLE_ATTENTION_SLICING:
            model.enable_attention_slicing(1)
            
        if ENABLE_CPU_OFFLOADING and hasattr(model, "enable_cpu_offload"):
            model.enable_cpu_offload()
            
        if ENABLE_BETTERTRANSFORMER:
            try:
                from optimum.bettertransformer import BetterTransformer
                model = BetterTransformer.transform(model)
                logger.info("BetterTransformer optimization applied")
            except ImportError:
                logger.warning("BetterTransformer not available")
                
        return model
    
    async def load_model(self, model_id: str) -> bool:
        """Load a model from HuggingFace Hub"""
        try:
            # Clean up previous model if exists
            if self.model is not None:
                del self.model
                self.model = None
                torch.cuda.empty_cache()
                gc.collect()
            
            logger.info(f"Loading model: {model_id}")
            
            # Get quantization config
            config = self._get_quantization_config()
            if config:
                logger.info(f"Using quantization config: {QUANTIZATION_TYPE}")
            
            try:
                # Load tokenizer and model
                self.tokenizer = AutoTokenizer.from_pretrained(
                    model_id,
                    trust_remote_code=True
                )
                
                self.model = AutoModelForCausalLM.from_pretrained(
                    model_id,
                    trust_remote_code=True,
                    **config
                )
                
                # Apply optimizations if supported
                if ENABLE_FLASH_ATTENTION:
                    try:
                        self.model.config.use_flash_attention = True
                        logger.info("Flash Attention enabled")
                    except Exception as e:
                        logger.warning(f"Flash Attention not available: {str(e)}")
                
                if ENABLE_ATTENTION_SLICING:
                    try:
                        if hasattr(self.model, 'enable_attention_slicing'):
                            self.model.enable_attention_slicing()
                            logger.info("Attention slicing enabled")
                        else:
                            logger.warning("Attention slicing not supported by this model")
                    except Exception as e:
                        logger.warning(f"Failed to enable attention slicing: {str(e)}")
                
                if ENABLE_CPU_OFFLOADING:
                    try:
                        if hasattr(self.model, 'enable_cpu_offload'):
                            self.model.enable_cpu_offload()
                            logger.info("CPU offloading enabled")
                        else:
                            logger.warning("CPU offloading not supported by this model")
                    except Exception as e:
                        logger.warning(f"Failed to enable CPU offloading: {str(e)}")
                
                if ENABLE_BETTERTRANSFORMER:
                    try:
                        from optimum.bettertransformer import BetterTransformer
                        self.model = BetterTransformer.transform(self.model)
                        logger.info("BetterTransformer enabled")
                    except Exception as e:
                        logger.warning(f"BetterTransformer not available: {str(e)}")
                
                self.current_model = model_id
                if model_id in MODEL_REGISTRY:
                    self.model_config = MODEL_REGISTRY[model_id]
                else:
                    self.model_config = {"max_length": DEFAULT_MAX_LENGTH}
                
                # Move model to device
                device = "cuda" if torch.cuda.is_available() else "cpu"
                self.model = self.model.to(device)
                logger.info(f"Model loaded successfully on {device}")
                
                return True
                
            except Exception as e:
                logger.error(f"Error loading model components: {str(e)}")
                if self.model is not None:
                    del self.model
                    self.model = None
                    torch.cuda.empty_cache()
                    gc.collect()
                
                # Attempt fallback if available
                fallback_model = None
                if self.model_config and self.model_config.get("fallback") and self.model_config.get("fallback") != model_id:
                    fallback_model = self.model_config.get("fallback")
                
                if fallback_model:
                    logger.warning(f"Attempting to load fallback model: {fallback_model}")
                    return await self.load_model(fallback_model)
                else:
                    raise HTTPException(
                        status_code=500,
                        detail=f"Failed to load model: {str(e)}"
                    )
                
        except Exception as e:
            logger.error(f"Failed to load model {model_id}: {str(e)}")
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
            del self.model
            self.model = None
            self.current_model = None
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
    
    async def generate(
        self,
        prompt: str,
        stream: bool = False,
        max_length: Optional[int] = None,
        temperature: float = DEFAULT_TEMPERATURE,
        top_p: float = DEFAULT_TOP_P
    ) -> str:
        """Generate text from the model"""
        # Check model timeout
        self.check_model_timeout()
        
        if not self.model or not self.tokenizer:
            await self.load_model(DEFAULT_MODEL)
        
        self.last_used = time.time()
        max_length = max_length or (self.model_config.get("max_length", DEFAULT_MAX_LENGTH) if self.model_config else DEFAULT_MAX_LENGTH)
        
        try:
            inputs = self.tokenizer(prompt, return_tensors="pt")
            for key in inputs:
                inputs[key] = inputs[key].to(self.device)
            
            if stream:
                return self._stream_generate(inputs, max_length, temperature, top_p)
            
            with torch.no_grad():
                outputs = self.model.generate(
                    **inputs,
                    max_new_tokens=max_length,
                    temperature=temperature,
                    top_p=top_p,
                    do_sample=True,
                    pad_token_id=self.tokenizer.eos_token_id
                )
            
            return self.tokenizer.decode(outputs[0][len(inputs["input_ids"][0]):], skip_special_tokens=True)
            
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
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the currently loaded model"""
        if not self.current_model:
            return {"status": "No model loaded"}
        
        memory_used = 0
        if self.model:
            memory_used = sum(p.numel() * p.element_size() for p in self.model.parameters())
        
        # Safely retrieve model config values
        model_name = self.model_config.get("name", self.current_model) if isinstance(self.model_config, dict) else self.current_model
        max_length = self.model_config.get("max_length", DEFAULT_MAX_LENGTH) if isinstance(self.model_config, dict) else DEFAULT_MAX_LENGTH
        ram_required = self.model_config.get("ram", "Unknown") if isinstance(self.model_config, dict) else "Unknown"
        vram_required = self.model_config.get("vram", "Unknown") if isinstance(self.model_config, dict) else "Unknown"
        
        return {
            "model_id": self.current_model,
            "model_name": model_name,
            "device": self.device,
            "max_length": max_length,
            "ram_required": ram_required,
            "vram_required": vram_required,
            "memory_used": f"{memory_used / (1024 * 1024):.2f} MB",
            "quantization": QUANTIZATION_TYPE,
            "optimizations": {
                "attention_slicing": ENABLE_ATTENTION_SLICING,
                "flash_attention": ENABLE_FLASH_ATTENTION,
                "better_transformer": ENABLE_BETTERTRANSFORMER
            }
        }

    async def load_custom_model(self, model_name: str, fallback_model: Optional[str] = "qwen-0.5b") -> bool:
        """Load a custom model from Hugging Face Hub with resource checks"""
        try:
            # First, try to get model info from Hugging Face
            from huggingface_hub import model_info
            info = model_info(model_name)
            
            # Estimate resource requirements (rough estimation)
            estimated_ram = info.siblings[0].size / (1024 * 1024)  # Convert to MB
            estimated_vram = estimated_ram * 1.5  # Rough VRAM estimate
            
            # Create temporary model config
            temp_config = {
                "name": model_name,
                "ram": estimated_ram,
                "vram": estimated_vram,
                "max_length": 2048,  # Default max length
                "fallback": fallback_model,
                "description": f"Custom model: {info.description}",
                "quantization": "int8",  # Default to int8 quantization for custom models
                "tags": info.tags
            }
            
            # Check resource availability
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
            
            # Clean up previous model
            if self.model:
                del self.model
                torch.cuda.empty_cache()
            
            logger.info(f"Loading custom model: {model_name}")
            
            # Get quantization config
            quant_config = BitsAndBytesConfig(
                load_in_8bit=True,
                llm_int8_threshold=6.0
            )
            
            # Try to load the model
            self.tokenizer = AutoTokenizer.from_pretrained(model_name)
            self.model = AutoModelForCausalLM.from_pretrained(
                model_name,
                torch_dtype=torch.float16,
                device_map="auto",
                quantization_config=quant_config
            )
            
            # Apply optimizations
            self.model = self._apply_optimizations(self.model)
            
            # Update model info
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
