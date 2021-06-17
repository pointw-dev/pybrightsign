# from glob import glob
from setuptools import setup

setup(
    name='pybrightsign',
    version='0.1.6',
    description='Python module to simplify using the BrightSign BSN/BSNEE API.',
    long_description=open('../README.md').read(),
    long_description_content_type='text/markdown',
    license='MIT',
    # https://pypi.org/classifiers/
    classifiers=[
        'Development Status :: 1 - Planning',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Operating System :: OS Independent',
        'Intended Audience :: Developers',
        'Topic :: Adaptive Technologies',
        'Topic :: Utilities'
    ],
    url='https://github.com/pointw-dev/pybrightsign',
    author='Michael Ottoson',
    author_email='michael@pointw.com',
    packages=['pybrightsign'],
    include_package_data=True,
    install_requires=[
        'requests',
        'oauthlib==2.1.0',
        'requests-oauthlib==1.1.0'   
    ],    
#    scripts=glob('bin/*'),
    zip_safe=False
)

