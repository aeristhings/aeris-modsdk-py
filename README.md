# aeris-modsdk-py
This package is intended to provide both an SDK and CLI for common radio modules.

This is not production code. There is no formal support provided by Aeris for this SDK.


## Getting Started - Install Package

If you want to install and use the package rather than make changes to it, see:

https://github.com/aeristhings/aeris-modsdk-py/wiki

## Getting Started - Development

These instructions will get you a copy of the project up and running on your local machine for development and testing purposes.

### Prerequisites

What you need to develop and test.

What I'm using:

```
git --version = 2.17.1
python --version = 3.7.5
pip --version = 19.3.1
poetry --version = 1.0.0
See: https://github.com/python-poetry/poetry
```

### Installing

A step by step series of examples that tell you how to get a development env running

Step 1: Clone the source to your local machine

```
$ git clone https://github.com/aeristhings/aeris-modsdk-py.git

Cloning into 'aeris-modsdk-py'...
remote: Enumerating objects: 38, done.
remote: Counting objects: 100% (38/38), done.
remote: Compressing objects: 100% (36/36), done.
remote: Total 38 (delta 12), reused 14 (delta 0), pack-reused 0
Unpacking objects: 100% (38/38), done.
```

Step 2: Install dependencies

```
$ cd aeris-modsdk-py
$ poetry install

Updating dependencies
Resolving dependencies... (0.9s)

Writing lock file


Package operations: 18 installs, 0 updates, 0 removals

  - Installing more-itertools (8.1.0)
  - Installing zipp (1.0.0)
  - Installing importlib-metadata (1.4.0)
  - Installing pyparsing (2.4.6)
  - Installing six (1.13.0)
  - Installing attrs (19.3.0)
  - Installing certifi (2019.11.28)
  - Installing chardet (3.0.4)
  - Installing idna (2.8)
  - Installing packaging (20.0)
  - Installing pluggy (0.13.1)
  - Installing py (1.8.1)
  - Installing urllib3 (1.25.7)
  - Installing wcwidth (0.1.8)
  - Installing click (7.0)
  - Installing pathlib (1.0.1)
  - Installing pytest (5.3.2)
  - Installing requests (2.22.0)
```

Step 3: Verify development environment working

~~~
$ poetry run aeriscli --help

Usage: aeriscli [OPTIONS] COMMAND [ARGS]...

Options:
  -v, --verbose             Verbose output
  -cfg, --config-file TEXT  Path to config file.
  --help                    Show this message and exit.

Commands:
  config       Set up the configuration for using this tool
  edrx         eDRX commands
  interactive  Interactive mode
  modem        Modem information
  network      Network commands
  packet       Packet commands
  pi           pi commands
  psm          PSM commands
~~~


### Coding style tests

This project used pycodestyle to ensure adherence to PEP 8 coding style rules.

Running pycodestyle as below should return with no errors.

```
$ pycodestyle --max-line-length=120 aeris-modsdk-py/
```

### Integration tests



## Updating Version Number
Before you build and publish, you will need to make sure that the version is changed so that users can easily pick up the latest version.

You can easily do that via poetry. For example, to increment the patch-level version, issue the command:

```
$ poetry version patch
Bumping version from 0.1.4 to 0.1.5
```


## Building
You can use poetry to build the distribution that we will want to publish to pypi.org. Use the 'build' command.

I have not found a way to clean out the previous build distribution. You may have to manually 'rm -rf dist' to remove before running the build.

```
$ poetry build
Building aerismodsdk (0.1.1)
 - Building sdist
 - Built aerismodsdk-0.1.1.tar.gz

 - Building wheel
 - Built aerismodsdk-0.1.1-py3-none-any.whl
```

## Publishing
The publish command uploads to pypi.org so that users can install via 'pip install' or 'pip install --upgrade'.

```
$ poetry publish

Publishing aerismodsdk (0.1.3) to PyPI
Username: <myusername>
Password:
 - Uploading aerismodsdk-0.1.3-py3-none-any.whl 100%
 - Uploading aerismodsdk-0.1.3.tar.gz 100%
```

## Built With

* [Poetry](https://python-poetry.org/) - Python dependency management
* [Click](https://click.palletsprojects.com/en/7.x/) - Python package for creating beautiful command line interfaces
* [pytest](https://docs.pytest.org/en/latest/) - Python testing tool that helps you write better programs
* [pycodestyle](http://pycodestyle.pycqa.org/en/latest/index.html) -  A tool to check Python code against the style conventions in PEP 8

## Contributing

Please read [CONTRIBUTING.md] for details on our code of conduct, and the process for submitting pull requests to us.

## Versioning

We use [SemVer](http://semver.org/) for versioning. For the versions available, see the [tags on this repository](https://github.com/aerisiot/aeris-apisdk-py/tags). 

## Authors

* **Drew Johnson** - *Initial work*
* **Sundar Arunachalam** - *Initial work*

See also the list of [contributors](https://github.com/aerisiot/aeris-apisdk-py/contributors) who participated in this project.

## License

This project is licensed under the Apache 2.0 License - see the [LICENSE](LICENSE) file for details

## Acknowledgments

* Hat tip to anyone whose code was used
