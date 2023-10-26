# Frequenz channels

[![Build Status](https://github.com/frequenz-floss/frequenz-channels-python/actions/workflows/ci.yaml/badge.svg)](https://github.com/frequenz-floss/frequenz-channels-python/actions/workflows/ci.yaml)
[![PyPI Package](https://img.shields.io/pypi/v/frequenz-channels)](https://pypi.org/project/frequenz-channels/)
[![Docs](https://img.shields.io/badge/docs-latest-informational)](https://frequenz-floss.github.io/frequenz-channels-python/)

## Introduction

Frequenz Channels is a *channels* implementation for Python.

According to [Wikipedia](https://en.wikipedia.org/wiki/Channel_(programming)):

> A channel is a model for interprocess communication and synchronization via
> message passing. A message may be sent over a channel, and another process or
> thread is able to receive messages sent over a channel it has a reference to,
> as a stream. Different implementations of channels may be buffered or not,
> and either synchronous or asynchronous.

Frequenz Channels are mostly designed after [Go
channels](https://tour.golang.org/concurrency/2) but it also borrows ideas from
[Rust channels](https://doc.rust-lang.org/book/ch16-02-message-passing.html).

## Supported Platforms

The following platforms are officially supported (tested):

- **Python:** 3.11
- **Operating System:** Ubuntu Linux 20.04
- **Architectures:** amd64, arm64

## Quick Start

We assume you are on a system with Python available. If that is not the case,
please [download and install Python](https://www.python.org/downloads/) first.

To install Frequenz Channels, you probably want to create a new virtual
environment first. For example, if you use a `sh` compatible shell, you can do
this:

```sh
python3 -m venv .venv
. .venv/bin/activate
```

Then, just install using `pip`:

```sh
python3 -m pip install frequenz-channels
```

## Documentation

For more information, please visit the [documentation
website](https://frequenz-floss.github.io/frequenz-channels-python/).

## Contributing

If you want to know how to build this project and contribute to it, please
check out the [Contributing Guide](CONTRIBUTING.md).
