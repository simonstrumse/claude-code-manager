"""
Setup configuration for MCP Server Manager
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="mcp-server-manager",
    version="1.0.0",
    author="Kalin Yorgov",
    author_email="kalinyorgov@gmail.com",
    description="A CLI tool to manage MCP servers in Claude Code",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/kalinyorgov/mcp-server-manager",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Build Tools",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Operating System :: OS Independent",
        "Environment :: Console",
    ],
    python_requires=">=3.6",
    py_modules=["mcp_manager"],
    entry_points={
        "console_scripts": [
            "mcp-manager=mcp_manager:main",
            "mcpm=mcp_manager:main",  # Short alias
        ],
    },
    install_requires=[
        # No external dependencies required!
        # Uses only Python standard library
    ],
    extras_require={
        "dev": [
            "pytest>=6.0",
            "black>=22.0",
            "flake8>=4.0",
            "mypy>=0.900",
        ],
    },
    project_urls={
        "Bug Reports": "https://github.com/kalinyorgov/mcp-server-manager/issues",
        "Source": "https://github.com/kalinyorgov/mcp-server-manager",
        "Documentation": "https://github.com/kalinyorgov/mcp-server-manager#readme",
    },
    keywords="claude-code mcp server management cli tool anthropic",
    include_package_data=True,
    zip_safe=False,
)