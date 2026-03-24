"""
Setup configuration for PKOS backend.
"""

from setuptools import setup, find_packages

setup(
    name="pkos",
    version="1.0.0-alpha",
    description="Personal Knowledge OS - A unified semantic knowledge management system",
    author="Piyush Nawani",
    author_email="piyush@example.com",
    python_requires=">=3.9",
    packages=find_packages(),
    install_requires=[
        "fastapi==0.104.1",
        "uvicorn[standard]==0.24.0",
        "pydantic==2.5.0",
        "pydantic-settings==2.1.0",
        "sqlalchemy==2.0.23",
        "psycopg2-binary==2.9.9",
        "pgvector==0.2.1",
        "sentence-transformers==2.2.2",
        "pypdf==3.17.1",
        "pdfplumber==0.10.3",
        "python-jose[cryptography]==3.3.0",
        "passlib[bcrypt]==1.7.4",
        "python-multipart==0.0.6",
    ],
    extras_require={
        "dev": [
            "pytest==7.4.3",
            "pytest-asyncio==0.21.1",
            "black==23.12.0",
            "flake8==6.1.0",
            "mypy==1.7.1",
        ],
        "ocr": ["pytesseract==0.3.10", "Pillow==10.1.0"],
        "graph": ["neo4j==5.14.1"],
    },
)
