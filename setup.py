from setuptools import setup


setup(
    name='cldfbench_chaomozhizhen',
    py_modules=['cldfbench_chaomozhizhen'],
    include_package_data=True,
    zip_safe=False,
    entry_points={
        'cldfbench.dataset': [
            'chaomozhizhen=cldfbench_chaomozhizhen:Dataset',
        ]
    },
    install_requires=[
        'cldfbench',
        'pylexibank',
        'pillow',
    ],
    extras_require={
        'test': [
            'pytest-cldf',
        ],
    },
)
