Contributing to `frequenz-channels`
===================================


Build
=====

You can use `build` to simply build the source and binary distribution:

```sh
python -m pip install build
python -m build
```

Local development
=================

You can use editable installs to develop the project locally (it will install
all the dependencies too):

```sh
python -m pip install -e .
```

You can also use `nox` to run the tests and other checks:

```sh
python -m pip install nox
nox
```
