from setuptools import setup

setup(
    name="quartermaster",
    version="0.1.0",
    py_modules=["quartermaster"],
    install_requires=[
        "Click",
    ],
    entry_points={
        "console_scripts": [
            "qm = quartermaster:cli",
        ],
    },
)
