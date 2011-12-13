#!/usr/bin/env python

from distutils.core import setup
import os

setup(
        name='amazons3',
        version='0.1',
        description='Django Storage Backend for Amazon S3.',
        author='com4',
        author_email='amazons3@zzq.org',
        url='https://github.com/com4/amazons3',
        package_dir={
            'amazons3': os.path.join('src', 'amazons3'),
            os.path.join('amazons3', 'django'): os.path.join('src', 'amazons3', 'django'),
        },
        packages=['amazons3', os.path.join('amazons3', 'django')],
)
