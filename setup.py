"""Setup."""

from setuptools import setup, find_packages

# Runtime requirements.
inst_reqs = ["rio-cogeo", "wget"]

setup(
    name="app",
    version="0.0.1",
    python_requires=">=3",
    packages=find_packages(exclude=["ez_setup", "examples", "tests"]),
    include_package_data=True,
    zip_safe=False,
    install_requires=inst_reqs,
)
