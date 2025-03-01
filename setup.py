from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="locallab",
    version="0.1.9",
    packages=find_packages(include=["locallab", "locallab.*"]),
    install_requires=[
        "fastapi>=0.68.0,<1.0.0",
        "uvicorn>=0.15.0,<1.0.0",
        "python-multipart>=0.0.5",
        "transformers>=4.0.0",
        "accelerate>=0.12.0",
        "pyngrok>=5.1.0",
        "nest-asyncio>=1.5.1",
        "psutil>=5.8.0",
        "nvidia-ml-py3>=7.352.0",
        "fastapi-cache2>=0.1.8",
        "colorama>=0.4.4",
        "pydantic>=2.0.0",
        "typing-extensions>=4.0.0",  # Added for better type support
        "torch>=2.0.0",
        "websockets>=10.0",
        "huggingface-hub>=0.19.0",
        "optimum>=1.16.0",
        "bitsandbytes>=0.41.1",
        "packaging>=21.0",
        "rich>=13.0.0",
        "termcolor>=2.3.0",
        "tqdm>=4.65.0",
        "requests>=2.31.0",
    ],
    author="Utkarsh",
    author_email="utkarshweb2023@gmail.com",
    description="A lightweight AI inference server for running models locally or in Google Colab",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/Developer-Utkarsh/LocalLab",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
    ],
    python_requires=">=3.8",
    entry_points={
        "console_scripts": [
            "locallab=locallab.main:start_server",
        ],
    },
    package_data={
        "locallab": ["py.typed"],
    },
)
