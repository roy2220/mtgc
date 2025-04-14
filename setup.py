from distutils.core import setup

setup(
    name="mtgc",
    version="0.0.1",
    description="Match-Transform-Generation Compiler",
    packages=["mtgc"],
    package_dir={"mtgc": "src"},
    entry_points={
        "console_scripts": [
            "mtgc=mtgc.compiler:main",
        ],
    },
    python_requires=">=3.12",
    install_rquires=[
        "sympy==1.13.3",
        "xlsxwriter==3.2.2",
        "jsonschema==4.23.0",
    ],
)
