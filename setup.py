import os.path
from setuptools import setup, find_packages


def read_file(fn):
    with open(os.path.join(os.path.dirname(__file__), fn)) as f:
        return f.read()


setup(
    name="argparse_helper",
    version="0.9.0",
    description="Yet another argparse helper: complex subcommand trees made simple",
    long_description=read_file("README.md"),
    author="jang",
    author_email="argparse_helper@ioctl.org",
    license="Apache License 2.0",
    packages=find_packages(exclude=["test.*, *.test", "test*"]),

    install_requires=[],

    tests_require=[
        "pytest",
    ],
)
