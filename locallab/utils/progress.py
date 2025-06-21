"""
Progress bar utilities for LocalLab
"""

import os
import sys
import threading
import time
from typing import Optional, Dict, Any, List, Tuple, Callable
import logging
from tqdm import tqdm
from huggingface_hub.utils import (
    HfHubHTTPError,
    RepositoryNotFoundError,
    RevisionNotFoundError,
    hf_raise_for_status,
)

# Get logger
logger = logging.getLogger("locallab.utils.progress")

# Global lock for progress bar output
progress_lock = threading.Lock()

# Store active progress bars
active_progress_bars: Dict[str, Any] = {}

# Flag to indicate if we're currently downloading a model
# This is used to suppress other logging during downloads
is_downloading = False

class SequentialProgressBar:
    """
    A progress bar that ensures sequential display of multiple download progress bars.
    This prevents interleaving of progress bars in the console output.
    """

    def __init__(self, total: int, desc: str, file_name: str = ""):
        """
        Initialize a sequential progress bar

        Args:
            total: Total size in bytes
            desc: Description of the progress bar
            file_name: Name of the file being downloaded
        """
        global is_downloading

        self.total = total
        self.desc = desc
        self.file_name = file_name
        self.n = 0
        self.pbar = None
        self.closed = False
        self.id = f"{desc}_{file_name}"

        # Set downloading flag to suppress other logging
        is_downloading = True

        # Store in global dict
        with progress_lock:
            active_progress_bars[self.id] = self

            # Create the progress bar
            self.pbar = tqdm(
                total=total,
                desc=desc,
                unit="B",
                unit_scale=True,
                unit_divisor=1024,
                file=sys.stdout,
                leave=True,
                position=len(active_progress_bars) - 1,
                dynamic_ncols=True,
                miniters=1  # Update at least once per iteration
            )

    def update(self, n: int) -> None:
        """Update the progress bar"""
        if self.closed:
            return

        with progress_lock:
            self.n += n
            if self.pbar:
                self.pbar.update(n)

    def close(self) -> None:
        """Close the progress bar"""
        global is_downloading

        if self.closed:
            return

        with progress_lock:
            if self.pbar:
                self.pbar.close()
            self.closed = True

            # Remove from global dict
            if self.id in active_progress_bars:
                del active_progress_bars[self.id]

                # Reposition remaining progress bars
                for i, (_, pbar) in enumerate(active_progress_bars.items()):
                    if pbar.pbar:
                        pbar.pbar.position = i

            # If no more active progress bars, reset downloading flag
            if not active_progress_bars:
                is_downloading = False
                # Print a newline to ensure clean separation after progress bars
                print("")

def custom_progress_callback(
    current: int, total: int, desc: str, file_name: str = ""
) -> None:
    """
    Custom progress callback for HuggingFace Hub downloads

    Args:
        current: Current size in bytes
        total: Total size in bytes
        desc: Description of the progress bar
        file_name: Name of the file being downloaded
    """
    global is_downloading

    # Create a unique ID for this download
    bar_id = f"{desc}_{file_name}"

    # Create a new progress bar if needed
    if bar_id not in active_progress_bars:
        # Clean up the description to make it more readable
        clean_desc = desc
        if file_name:
            # Extract just the filename without path
            short_name = os.path.basename(file_name)
            clean_desc = f"Downloading {short_name}"

        # Create the progress bar
        active_progress_bars[bar_id] = SequentialProgressBar(total, clean_desc, file_name)

    # Get the progress bar
    pbar = active_progress_bars[bar_id]

    # Update or close the progress bar
    if current < total:
        # Calculate the increment
        increment = current - pbar.n
        if increment > 0:
            pbar.update(increment)
    else:
        # Download complete
        pbar.close()

def configure_hf_hub_progress():
    """
    Configure HuggingFace Hub to use its native progress bars for model downloads.
    This completely bypasses our custom logger for HuggingFace download progress.
    """
    try:
        # 1. Enable HuggingFace's native progress bars
        from huggingface_hub.utils import logging as hf_logging
        hf_logging.enable_progress_bars()

        # 2. Enable HF Transfer for better download experience (only if available)
        try:
            import hf_transfer
            from huggingface_hub import constants
            constants.HF_HUB_ENABLE_HF_TRANSFER = True
        except ImportError:
            # hf_transfer not available, skip enabling it
            pass

        # 3. Make sure we're NOT overriding HuggingFace's progress callback
        # This is critical - we want to use their native implementation
        from huggingface_hub import file_download
        if hasattr(file_download, "_tqdm_callback"):
            # Reset to default - we don't want any custom callback
            file_download._tqdm_callback = None

        # 4. Ensure HuggingFace Hub's own logging is properly configured
        # This ensures HF's own progress bars are displayed correctly
        import huggingface_hub
        if hasattr(huggingface_hub, "enable_progress_bars"):
            huggingface_hub.enable_progress_bars()

        # 5. Configure tqdm directly to ensure proper display
        import tqdm
        tqdm.tqdm.monitor_interval = 0  # Disable monitor thread which can cause issues

        # 6. Ensure we're not capturing tqdm output in our logger
        # This is critical for allowing tqdm to directly write to stdout
        import logging
        tqdm_logger = logging.getLogger("tqdm")
        tqdm_logger.setLevel(logging.WARNING)  # Only show warnings and errors from tqdm

        # 7. Set a flag to indicate we're using HuggingFace's native progress bars
        global is_downloading
        is_downloading = True

        logger.debug("Configured HuggingFace Hub to use its native progress bars")
    except ImportError:
        logger.warning("Failed to configure HuggingFace Hub progress bars")
    except Exception as e:
        logger.warning(f"Error configuring HuggingFace Hub progress: {str(e)}")

# Function to check if we're currently downloading
def is_model_downloading():
    """
    Check if a model is currently being downloaded.

    This function now checks for active HuggingFace downloads by looking
    for tqdm progress bars in sys.stdout that contain model file patterns.
    """
    # First check our global flag
    if is_downloading:
        return True

    # Also check if there are any active HuggingFace downloads
    # by looking for specific patterns in the output
    try:
        # Check if there are any tqdm instances in sys.stdout
        if hasattr(sys.stdout, '_instances') and sys.stdout._instances:
            for instance in sys.stdout._instances:
                if hasattr(instance, 'desc') and isinstance(instance.desc, str):
                    # Look for common model file patterns in the description
                    if any(pattern in instance.desc.lower() for pattern in
                          ['model', 'weight', 'safetensors', 'bin', 'pytorch_model']):
                        return True
    except:
        # If anything goes wrong with the check, default to False
        pass

    return False
