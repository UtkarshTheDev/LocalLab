from setuptools import setup, find_packages

setup(
    name="locallab-client",
    version="1.0.5",
    author="Utkarsh",
    author_email="utkarshweb2023@gmail.com",
    description="Python client for LocalLab - A local LLM server",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/UtkarshTheDev/LocalLab",
    packages=find_packages(),
    install_requires=[
        "aiohttp>=3.8.0",
        "websockets>=10.0",
        "pydantic>=2.0.0",
        "asyncio>=3.4.3",
        "nest-asyncio>=1.5.1",
    ],
    python_requires=">=3.7",
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
    ],
)
