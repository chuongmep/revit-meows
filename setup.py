from setuptools import setup, find_packages

setup(
    name="revit_meows",
    version="0.1.0",
    author="chuongmep",
    author_email="chuongpqvn@gmail.com",
    description="A tool for extracting data from Revit ACC",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/chuongmep/aps-revit",
    packages=find_packages(exclude=["tests*", "venv*"]),
    include_package_data=True,
    install_requires=[
        "pandas>=2.1.4",
        "numpy>=1.26.0",
        "requests>=2.0",
        "aps-toolkit"
    ],
    python_requires=">=3.8", 
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: OS Independent",
    ],
    entry_points={
        "console_scripts": [
            # Define command-line scripts here if needed
        ],
    },
)
