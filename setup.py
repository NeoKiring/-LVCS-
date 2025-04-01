from setuptools import setup, find_packages

setup(
    name="lvcs",
    version="1.0.0",
    description="ローカルバージョン管理システム",
    author="LVCS Developer",
    author_email="developer@example.com",
    packages=find_packages(),
    entry_points={
        "console_scripts": [
            "lvcs=cli:main",
            "lvcs-gui=gui:main",
        ],
    },
    install_requires=[
        "tkinter",  # Windowsでは通常Pythonにバンドルされています
    ],
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: Console",
        "Environment :: Win32 (MS Windows)",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: Microsoft :: Windows",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Software Development :: Version Control",
    ],
    python_requires=">=3.8",
)
