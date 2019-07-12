#!/usr/bin/env python3

from setuptools import setup


if __name__ == '__main__':
    setup(
        name='pyserp',
        version='0.1',
        description='Annotation based injector',
        author='Stanislav Ananyev',
        author_email='ctacyok@yandex.ru',
        packages=['pyserp'],
        classifiers=[
            'Development Status :: 3 - Alpha',
            'Framework :: AsyncIO',
            'Intended Audience :: Developers',
            'License :: OSI Approved :: MIT License',
            'Operating System :: OS Independent',
            'Programming Language :: Python :: 3.6',
            'Programming Language :: Python :: 3.7',
            'Programming Language :: Python :: 3.8',
            'Typing :: Typed',
        ],
        setup_requires=[
            'pytest-runner',
        ],
        tests_require=[
            'pytest',
        ],
        test_suite='tests',
    )
