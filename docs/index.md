# Frequenz Channels for Python

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

## Installation

First, you need to make sure you have Python installed (at least version 3.11):

```console
$ python3 --version
Python 3.11.4
```

!!! note

    These instructions assume you are using a [POSIX compatible
    `sh`](https://pubs.opengroup.org/onlinepubs/9699919799/utilities/sh.html)
    shell.

If that command doesn't print a version newer than 3.11.0, you'll need to
[download and install Python](https://www.python.org/downloads/) first.

To install Frequenz Channels, you probably want to create a new virtual
environment first:

```sh
mkdir my-channels-project
cd my-channels-project
python3 -m venv .venv
. .venv/bin/activate
```

!!! tip

    Using [`direnv`](https://direnv.net/) can greatly simplify this process as
    it automates the creation, activation, and deactivation of the virtual
    environment. The first time you enable `direnv`, the virtual environment
    will be created, and each time you enter or leave a subdirectory, it will be
    activated and deactivated, respectively.

    ```sh
    sudo apt install direnv # if you use Debian/Ubuntu
    mkdir my-channels-project
    cd my-channels-project
    echo "layout python python3" > .envrc
    direnv allow
    ```

    This will create the virtual environment and activate it automatically for you.

Now you can install Frequenz Channels by using `pip`:

```sh
python3 -m pip install frequenz-channels
```

To verify that the installation worked, you can invoke the Python interpreter and
import the `frequenz.channels` module:

```console
$ python3
Python 3.11.4 (main, Jun  7 2023, 10:13:09) [GCC 12.2.0] on linux
Type "help", "copyright", "credits" or "license" for more information.
>>> import frequenz.channels
>>> 
```
