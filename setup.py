import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="split_openfeature_provider",
    version="1.0.0",
    description="The official Python Split Provider for OpenFeature",
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=setuptools.find_packages(),
    license='Apache License 2.0',
    classifiers=[
        "Programming Language :: Python :: 3",
        'Topic :: Software Development :: Libraries'
    ],
    python_requires='>=3.9'
)
