from setuptools import setup, find_packages

setup(name='ABCD_ML',
      version='1.2',
      description='Python based Machine Learning library, for tabular ' +
                  'Neuroimaging data, specifically geared towards the' +
                  ' ABCD dataset.',
      url='http://github.com/sahahn/ABCD_ML',
      author='Sage Hahn',
      author_email='sahahn@euvm.edu',
      license='MIT',
      packages=find_packages(),
      install_requires=[
          'scikit-learn>=0.23.1',
          'numpy>=1.18',
          'scipy>=1.2',
          'pandas>=0.25',
          'matplotlib>=3.2.2',
          'seaborn>=0.9',
          'deslib',
          'scikit-image>=0.16',
          'tqdm>=4',
          'nevergrad==0.4.0',
          'Ipython',
          'joblib>=0.14',
          'python-docx',
      ],
      test_suite='nose.collector',
      tests_require=['nose', 'coverage'],
      zip_safe=False)
