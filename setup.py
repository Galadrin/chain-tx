from setuptools import setup

setup(
    name='cosmos_spam',
    version='0.1',
    packages=['cosmos_spam',],
    url='http://cros-nest.com',
    license='MIT',
    author='galadrin',
    author_email='chainmaster@cros-nest.com',
    description='This script spam transaction for transferring coins',
    install_requires=[
        "requests",
        "dnspython",
    ],
    scripts=['transaction.py'],
)
