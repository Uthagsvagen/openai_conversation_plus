"""Setup file for OpenAI Conversation Plus integration."""
from setuptools import find_packages, setup

with open("README.md", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="openai-conversation-plus",
    version="2025.81.1",
    author="jekalmin",
    description="OpenAI Conversation Plus integration for Home Assistant",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/Uthagsvagen/openai_conversation_plus",
    packages=find_packages(include=["custom_components", "custom_components.*"]),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Home Automation",
    ],
    python_requires=">=3.11",
    install_requires=[
        "openai~=1.76.2",
    ],
    extras_require={
        "test": [
            "pytest>=7.1.2",
            "pytest-homeassistant-custom-component>=0.13.0",
            "pytest-cov>=4.0.0",
            "pytest-asyncio>=0.21.0",
            "pytest-timeout>=2.1.0",
            "pre-commit>=3.3.3",
            "ruff>=0.1.0",
            "mypy>=1.5.0",
            "black>=23.0.0",
            "hassfest",
        ],
    },
)
