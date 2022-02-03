from setuptools import setup, find_packages

with open("requirements.txt") as f:
	install_requires = f.read().strip().split("\n")

# get version from __version__ variable in senbagam_api/__init__.py
from senbagam_api import __version__ as version

setup(
	name="senbagam_api",
	version=version,
	description="Api for mobile app",
	author="Aerele Technologies",
	author_email="Aerele Technologies",
	packages=find_packages(),
	zip_safe=False,
	include_package_data=True,
	install_requires=install_requires
)
