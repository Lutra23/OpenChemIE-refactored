from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="openchemie",
    version="2.0.0",
    author="Lutra23",
    author_email="your.email@example.com",
    description="AI-powered chemical information extraction from scientific literature",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/Lutra23/OpenChemIE-refactored",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Topic :: Scientific/Engineering :: Chemistry",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=6.2.0",
            "pytest-cov>=2.12.0",
            "pytest-asyncio>=0.15.0",
            "flake8>=3.9.0",
            "black>=21.6.0",
            "isort>=5.9.0",
        ],
        "docs": [
            "sphinx>=4.0.0",
            "sphinx-rtd-theme>=0.5.0",
            "myst-parser>=0.15.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "openchemie=app.core.interface:main",
        ],
    },
    include_package_data=True,
    package_data={
        "app": ["web/dist/**/*"],
    },
)