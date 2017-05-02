import os
from setuptools import setup, find_packages

this_dir = os.path.abspath(os.path.dirname(__file__))

with open(os.path.join(this_dir, 'README.md'), 'r') as f:
    long_description = f.read()

setup(name='boa',
      version=open("websurvey/_version.py").readlines()[-1].split()[-1].strip("\"'"),
      author='Olivier Feys',
      # TODO Provide a support mailbox for our products
      author_email='olivier.feys@gmail.com',
      description="Websockets based webapp for making real time surveys",
      long_description=long_description,
      # TODO Package to artifactory and assert that bamboo will keep it up to date
      download_url='http://www.engie.com',
      classifiers=[
          "Development Status :: 3 - Alpha",
          "Intended Audience :: Developers"
          "Programming Language :: Python",
          "Programming Language :: Python :: 2",
          "Programming Language :: Python :: 2.7"
      ],
      keywords=[
          'survey',
          'tornado',
          'websockets'
      ],
      packages=find_packages(),
      install_requires=[
          'tornado'
      ]
      )
