from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="locallab-client",
    version="1.0.0",
    author="Utkarsh Tiwari",
    author_email="utkarshweb2023@gmail.com",
    description="Official Python client for LocalLab - A local LLM server",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/UtkarshTheDev/LocalLab",
    packages=find_packages(include=["locallab", "locallab.*"]),
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
    ],
    python_requires=">=3.7",
    install_requires=[
        "aiohttp>=3.8.0",
        "typing-extensions>=4.0.0",
        "pydantic>=2.0.0",
    ],
    extras_require={
        "dev": [
            "pytest>=6.0",
            "pytest-asyncio>=0.15.0",
            "pytest-cov>=2.0",
            "black>=22.0",
            "isort>=5.0",
            "mypy>=0.900",
            "flake8>=3.9",
        ],
    },
    project_urls={
        "Bug Tracker": "https://github.com/UtkarshTheDev/LocalLab/issues",
        "Documentation": "https://github.com/UtkarshTheDev/LocalLab#readme",
        "Source Code": "https://github.com/UtkarshTheDev/LocalLab",
    },
)
