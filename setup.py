"""
Setup configuration for OEFO package.

Enables installation via pip and provides console entry point.
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read version from __init__.py
init_file = Path(__file__).parent / 'oefo' / '__init__.py'
for line in init_file.read_text().split('\n'):
    if line.startswith('__version__'):
        version = line.split('=')[1].strip().strip('"\'')
        break
else:
    version = '0.1.0'

# Read README if it exists
readme_file = Path(__file__).parent / 'README.md'
long_description = ''
if readme_file.exists():
    long_description = readme_file.read_text()

setup(
    name='oefo',
    version=version,
    description='Open Energy Finance Observatory - Energy finance data toolkit',
    long_description=long_description,
    long_description_content_type='text/markdown',
    author='ET Finance',
    url='https://github.com/et-finance/oefo',
    packages=find_packages(),
    python_requires='>=3.8',
    install_requires=[
        'pandas>=2.0',
        'pydantic>=2.0',
        'pyarrow>=12.0',
        'pdfplumber>=0.9',
        'pymupdf>=1.22',
        'pdf2image>=1.16',
        'pytesseract>=0.3',
        'Pillow>=10.0',
        'opencv-python-headless>=4.8',
        'anthropic>=0.25',
        'requests>=2.31',
        'beautifulsoup4>=4.12',
        'lxml>=4.9',
        'openpyxl>=3.1',
        'matplotlib>=3.7',
        'python-dateutil>=2.8',
    ],
    extras_require={
        'dev': [
            'pytest>=7.0',
            'pytest-cov>=4.0',
            'black>=23.0',
            'flake8>=6.0',
            'mypy>=1.0',
        ],
        'openai': ['openai>=1.0'],
        'google': ['google-generativeai>=0.5'],
    },
    entry_points={
        'console_scripts': [
            'oefo=oefo.cli:main',
        ],
    },
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Intended Audience :: Science/Research',
        'Topic :: Office/Business :: News/Diary',
        'Topic :: Scientific/Engineering :: Information Analysis',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
    ],
    keywords='energy finance wacc renewable solar wind hydro',
)
