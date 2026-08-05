from setuptools import setup, find_packages

setup(
    name="land-scanner",
    version="1.0.0",
    packages=find_packages(),
    install_requires=[
        "numpy>=1.21.0,<2.0",
        "FastAPI==0.104.1",
        "uvicorn==0.24.0",
        "Pydantic==2.4.2",
        "requests==2.31.0",
        "shapely==2.0.4",
        "pyproj==3.6.1",
        "pytest==7.4.3",
        "hypothesis==6.88.1",
        "gunicorn==21.2.0",
    ],
    python_requires=">=3.11",
)
