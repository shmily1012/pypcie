from setuptools import find_packages, setup


with open("README.md", "r") as handle:
    long_description = handle.read()


setup(
    name="pcispace",
    version="0.1.0",
    description="PCI config and BAR access via sysfs",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Alex Z",
    license="MIT",
    python_requires=">=3.6",
    packages=find_packages(exclude=("tests",)),
    entry_points={"console_scripts": ["pcispace=pcispace.cli:main"]},
    classifiers=[
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
    ],
)
