# setup.py
from setuptools import setup, find_packages

setup(
    name="specopt-server",
    version="1.0.0",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        "mcp>=1.0.0",
        "langchain-core>=0.1.0",
        "langchain-openai>=0.1.0",
        "dspy>=2.4.0",
        "anyio>=4.0.0",
        "pytest>=8.0.0"
    ],
    entry_points={
        "console_scripts": [
            # 🚀 This defines the terminal command and hooks it to your main function
            "specopt-server=core.server:main",
        ],
    },
)
