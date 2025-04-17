"""
Dual-mode functionality for the LocalLab client.

This module provides the infrastructure for methods that can be used both
synchronously and asynchronously.
"""

import asyncio
import functools
import inspect
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable, Dict, Optional, TypeVar, cast

# Type variables for better type hints
T = TypeVar('T')
AsyncFunc = Callable[..., asyncio.Future[T]]
SyncFunc = Callable[..., T]


class ThreadManager:
    """
    Manages a dedicated thread with an event loop for running async code synchronously.
    
    This class is responsible for:
    1. Creating and managing a dedicated thread with an event loop
    2. Running coroutines in that event loop and returning results
    3. Properly cleaning up resources when no longer needed
    """
    
    _instance: Optional['ThreadManager'] = None
    _lock = threading.RLock()
    
    @classmethod
    def get_instance(cls) -> 'ThreadManager':
        """Get or create the singleton instance of ThreadManager."""
        with cls._lock:
            if cls._instance is None:
                cls._instance = ThreadManager()
            return cls._instance
    
    def __init__(self):
        """Initialize the thread manager."""
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._thread: Optional[threading.Thread] = None
        self._executor = ThreadPoolExecutor(max_workers=4)
        self._running = False
        self._last_activity = time.time()
        self._clients_count = 0
        self._initialize()
    
    def _initialize(self):
        """Initialize the event loop thread."""
        with self._lock:
            if self._thread is None or not self._thread.is_alive():
                self._loop = asyncio.new_event_loop()
                self._running = True
                
                def run_event_loop():
                    """Run the event loop in a separate thread."""
                    asyncio.set_event_loop(self._loop)
                    self._loop.run_forever()
                
                self._thread = threading.Thread(target=run_event_loop, daemon=True)
                self._thread.start()
    
    def register_client(self):
        """Register a new client using this thread manager."""
        with self._lock:
            self._clients_count += 1
            self._last_activity = time.time()
    
    def unregister_client(self):
        """Unregister a client from this thread manager."""
        with self._lock:
            self._clients_count -= 1
            if self._clients_count <= 0:
                self._clients_count = 0
                # Schedule cleanup after a delay if no clients remain
                if self._loop:
                    self._loop.call_later(60, self._cleanup_if_inactive)
    
    def _cleanup_if_inactive(self):
        """Clean up resources if no activity for a while and no clients."""
        with self._lock:
            if self._clients_count <= 0 and time.time() - self._last_activity > 60:
                self.shutdown()
    
    def shutdown(self):
        """Shut down the thread manager and clean up resources."""
        with self._lock:
            if self._running and self._loop and self._thread and self._thread.is_alive():
                # Stop the event loop
                self._running = False
                self._loop.call_soon_threadsafe(self._loop.stop)
                
                # Wait for the thread to finish
                self._thread.join(timeout=1)
                
                # Clean up
                self._loop = None
                self._thread = None
            
            # Shutdown the executor
            self._executor.shutdown(wait=False)
    
    def run_coroutine(self, coro) -> Any:
        """
        Run a coroutine in the event loop thread and return the result.
        
        Args:
            coro: The coroutine to run
            
        Returns:
            The result of the coroutine
            
        Raises:
            Any exception raised by the coroutine
        """
        self._last_activity = time.time()
        
        if not self._loop or not self._thread or not self._thread.is_alive():
            self._initialize()
        
        if not self._loop:
            raise RuntimeError("Failed to initialize event loop")
        
        # Run the coroutine in the event loop and wait for the result
        future = asyncio.run_coroutine_threadsafe(coro, self._loop)
        
        try:
            # Wait for the result with a timeout
            return future.result(timeout=300)  # 5 minutes timeout
        except Exception as e:
            # If the future was cancelled or raised an exception, propagate it
            if future.cancelled():
                raise asyncio.CancelledError("Operation was cancelled") from e
            raise


class DualModeMethod:
    """
    A method wrapper that can be used both synchronously and asynchronously.
    
    When awaited, it runs the original async method.
    When called directly, it runs the async method in a background thread and returns the result.
    """
    
    def __init__(self, async_method: AsyncFunc, instance: Any):
        """
        Initialize the dual-mode method.
        
        Args:
            async_method: The original async method
            instance: The instance the method is bound to
        """
        self.async_method = async_method
        self.instance = instance
        self.thread_manager = ThreadManager.get_instance()
        
        # Copy metadata from the original method
        functools.update_wrapper(self, async_method)
    
    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        """
        Call the method synchronously.
        
        This runs the async method in a background thread and returns the result directly.
        
        Args:
            *args: Positional arguments to pass to the method
            **kwargs: Keyword arguments to pass to the method
            
        Returns:
            The result of the method
        """
        # Create the coroutine
        coro = self.async_method(self.instance, *args, **kwargs)
        
        # Run it in the background thread and return the result
        return self.thread_manager.run_coroutine(coro)
    
    def __await__(self):
        """
        Allow the method to be awaited.
        
        This returns the original async method's awaitable.
        
        Returns:
            An awaitable that will resolve to the method's result
        """
        # Just return the awaitable from the original method
        return self.async_method(self.instance).__await__()


def dual_mode(cls):
    """
    Class decorator that makes all async methods of a class dual-mode.
    
    This allows the methods to be used both with and without await.
    
    Args:
        cls: The class to modify
        
    Returns:
        The modified class
    """
    # Find all async methods in the class
    for name, method in inspect.getmembers(cls, inspect.iscoroutinefunction):
        # Skip special methods
        if name.startswith('__') and name.endswith('__'):
            continue
        
        # Create a property that returns a DualModeMethod when accessed
        setattr(cls, name, _create_dual_mode_property(name, method))
    
    # Add a reference to the thread manager
    original_init = cls.__init__
    
    @functools.wraps(original_init)
    def new_init(self, *args, **kwargs):
        # Call the original __init__
        original_init(self, *args, **kwargs)
        
        # Register with the thread manager
        self._thread_manager = ThreadManager.get_instance()
        self._thread_manager.register_client()
    
    # Replace the __init__ method
    cls.__init__ = new_init
    
    # Add a __del__ method to unregister from the thread manager
    original_del = getattr(cls, '__del__', lambda self: None)
    
    @functools.wraps(original_del)
    def new_del(self):
        # Unregister from the thread manager
        if hasattr(self, '_thread_manager'):
            self._thread_manager.unregister_client()
        
        # Call the original __del__
        original_del(self)
    
    # Replace the __del__ method
    cls.__del__ = new_del
    
    return cls


def _create_dual_mode_property(name, method):
    """
    Create a property that returns a DualModeMethod when accessed.
    
    Args:
        name: The name of the method
        method: The original async method
        
    Returns:
        A property that returns a DualModeMethod
    """
    # Store the original method
    method_name = f"_async_{name}"
    
    # Create the property
    def getter(self):
        # Store the async method on the instance if not already there
        if not hasattr(self, method_name):
            setattr(self, method_name, method)
        
        # Return a DualModeMethod that wraps the async method
        return DualModeMethod(getattr(self, method_name), self)
    
    # Return the property
    return property(getter)
