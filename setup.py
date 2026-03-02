from setuptools import setup, find_packages

setup(
    name="companion-bridge",
    version="1.0.0",
    description="AI companion identity profile generator",
    py_modules=["main", "app", "routes", "models", "simple_processor"],
    packages=[],  # No packages, only modules
    include_package_data=False,
    zip_safe=False,
    install_requires=[
        "flask>=3.1.1",
        "flask-sqlalchemy>=3.1.1", 
        "gunicorn>=23.0.0",
        "psycopg2-binary>=2.9.10",
        "spacy>=3.8.7",
        "sqlalchemy>=2.0.42",
        "werkzeug>=3.1.3",
    ],
    python_requires=">=3.11",
)