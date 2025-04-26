import os
from distutils.core import setup


def parse_requirements() -> list[str]:
    requirements = []
    with open(
        os.path.join(
            os.path.dirname(os.path.realpath(__file__)),
            "requirements.txt",
        ),
        "r",
    ) as f:
        requirements.append(f.readline().strip())
    return requirements


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
    install_rquires=parse_requirements(),
)
