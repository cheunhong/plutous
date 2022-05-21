import setuptools
import plutous


setuptools.setup(
    name = 'plutous',
    packages = setuptools.find_packages(),
    include_package_data = True,
    version = plutous.__version__,
    python_requires = '>=3.7.*',
    description = 'Personal Finance & Portfolio Tracker',
    author = 'cheunhong',
    author_email = 'chlin6755@gmail.com',
    url = 'https://github.com/cheunhong/plutous',
    install_requires = [
        'SQLAlchemy<=1.4.35',
        'PyPortfolioOpt',
        'vectorbt[full]',
        'quantstats',
        'pandas_ta',
        'sqlmodel',
        'asyncmy',
        'PyMySQL',
        'alembic',
        'inflect',
        'TA-Lib',
        'pandas',
        'babel',
        'ccxt',
    ],
    license = 'MIT',
    classifiers = [
        'Programming Language :: Python :: 3.7',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
)
