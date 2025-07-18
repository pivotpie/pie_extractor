from setuptools import setup, find_packages

setup(
    name="openrouter_manager",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "requests>=2.25.1",
        "python-dotenv>=0.19.0",
        "pydantic>=1.8.2",
        "sqlalchemy>=1.4.23",
    ],
    python_requires=">=3.8",
    author="Your Name",
    author_email="your.email@example.com",
    description="A Python client for managing OpenRouter API keys and instances",
    long_description=open("README.md", "r", encoding="utf-8").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/openrouter-manager",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)
