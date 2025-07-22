from setuptools import setup, find_packages
import platform

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

# Base requirements
install_requires = [
    "fastapi>=0.95.0,<1.0.0",
    "uvicorn>=0.21.1,<1.0.0",
    "pydantic>=2.0.0,<3.0.0",
    "python-dotenv>=0.21.0,<1.0.0",
    "python-multipart>=0.0.5",
    "dataclasses-json>=0.5.7,<1.0.0",
    "torch>=2.0.0,<3.0.0",
    "transformers>=4.49.0,<5.0.0",
    "accelerate>=0.18.0,<1.0.0",
    "click>=8.1.3,<9.0.0",
    "rich>=13.3.4,<14.0.0",
    "pyngrok>=6.0.0,<7.0.0",
    "requests>=2.28.2,<3.0.0",
    "httpx>=0.24.0",
    "colorama>=0.4.4",
    "websockets>=10.0",
    "psutil>=5.8.0",
    "nest-asyncio>=1.5.1",
    "fastapi-cache2>=0.2.1",
    "huggingface_hub>=0.20.0",
    "typing_extensions>=4.0.0",
    "questionary>=1.10.0",
]

# Platform-specific dependencies
if platform.system() == "Windows":
    install_requires.extend([
        "bitsandbytes-windows>=0.37.2",
        "llama-cpp-python>=0.1.77",
    ])
else:
    install_requires.extend([
        "bitsandbytes>=0.38.0,<1.0.0",
        "llama-cpp-python>=0.1.74,<1.0.0",
        "netifaces>=0.11.0",
        "nvidia-ml-py3>=7.352.0",
        "pynvml>=11.0.0",
    ])

setup(
    name="locallab",
    version="0.11.2",
    packages=find_packages(include=["locallab", "locallab.*"]),
    install_requires=install_requires,
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-asyncio>=0.15.0",
            "pytest-cov>=4.0.0",
        ],
    },
    author="Utkarsh Tiwari",
    author_email="utkarshweb2023@gmail.com",
    description="LocalLab: A lightweight AI inference server for running LLMs locally or in Google Colab with a friendly API.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/UtkarshTheDev/LocalLab",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: Apache Software License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Operating System :: Microsoft :: Windows",
        "Operating System :: POSIX :: Linux",
        "Operating System :: MacOS",
    ],
    python_requires=">=3.9",
    entry_points={
        "console_scripts": [
            "locallab=locallab.server:cli",
        ],
    },
    package_data={
        "locallab": ["py.typed"],
    },
)
