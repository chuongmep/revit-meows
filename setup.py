from setuptools import setup, find_packages

setup(
    name="revit_meows",
    version="0.1.1",
    author="chuongmep",
    author_email="chuongpqvn@gmail.com",
    description="A tool for extracting data from Revit ACC",
    long_description=open("Readme.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/chuongmep/revit-meows",
    packages=find_packages(exclude=["revit*", "aps*",'revit_meows*,aps-toolkit']),
    include_package_data=True,
    install_requires=[
        "pandas>=2.1.4",
        "numpy>=1.26.0",
        "requests>=2.0",
        "aps-toolkit"
    ],
    python_requires=">=3.9",
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
