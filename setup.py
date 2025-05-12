import os

from setuptools import setup


def parse_requirements() -> list[str]:
    current_dir_name = os.path.dirname(os.path.realpath(__file__))
    requirements = []
    with open(os.path.join(current_dir_name, "requirements.txt"), "r") as f:
        for line in f:
            line = line.strip()
            if line == "" or line.startswith("#"):
                continue
            requirements.append(line)
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
    install_requires=parse_requirements(),
)
