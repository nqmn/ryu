**PLEASE READ: RYU NOT CURRENTLY MAINTAINED**

    * The Ryu project needs new maintainers - please file an issue if you are able to assist.
    * see OpenStack's os-ken (`<https://github.com/openstack/os-ken>`_) for a maintained Ryu alternative.

What's Ryu
==========
Ryu is a component-based software defined networking framework.

Ryu provides software components with well defined API's that make it
easy for developers to create new network management and control
applications. Ryu supports various protocols for managing network
devices, such as OpenFlow, Netconf, OF-config, etc. About OpenFlow,
Ryu supports fully 1.0, 1.2, 1.3, 1.4, 1.5 and Nicira Extensions.

All of the code is freely available under the Apache 2.0 license. Ryu
is fully written in Python.

**Python Version Requirements**
-------------------------------
This modernized version of Ryu requires Python 3.8 or later. The codebase has been
updated to use modern Python features and remove Python 2 compatibility code.


Quick Start
===========
**Requirements**: Python 3.8 or later

Installing Ryu is quite easy::

   % pip install ryu

If you prefer to install Ryu from the source code::

   % git clone https://github.com/faucetsdn/ryu.git
   % cd ryu; pip install .

If you want to write your Ryu application, have a look at
`Writing ryu application <http://ryu.readthedocs.io/en/latest/writing_ryu_app.html>`_ document.
After writing your application, just type::

   % ryu-manager yourapp.py


Optional Requirements
=====================

Some functions of ryu require extra packages:

- OF-Config requires lxml and ncclient
- NETCONF requires paramiko
- BGP speaker (SSH console) requires paramiko
- Zebra protocol service (database) requires SQLAlchemy

If you want to use these functions, please install the requirements::

    % pip install -r tools/optional-requires

Please refer to tools/optional-requires for details.


Prerequisites
=============
If you got some error messages at the installation stage, please confirm
dependencies for building the required Python packages.

On Ubuntu(18.04 LTS or later)::

  % apt install gcc python3-dev libffi-dev libssl-dev libxml2-dev libxslt1-dev zlib1g-dev

**Development and Testing**
---------------------------
For development and testing, install additional dependencies::

  % pip install -e .[dev]

Run tests using pytest::

  % pytest ryu/tests/unit/

**Modernization Changes**
-------------------------
This version has been modernized with the following improvements:

- **Python 3.8+ Support**: Dropped support for Python 3.7 and earlier
- **Dependency Updates**: All dependencies updated to latest stable versions
- **Code Modernization**: Removed six library, updated string formatting to f-strings
- **Testing Framework**: Migrated from nose to pytest
- **Type Hints**: Added type hints to core modules
- **Project Structure**: Migrated from setup.py to modern pyproject.toml


Support
=======
Ryu Official site is `<https://ryu-sdn.org/>`_.

If you have any
questions, suggestions, and patches, the mailing list is available at
`ryu-devel ML
<https://lists.sourceforge.net/lists/listinfo/ryu-devel>`_.
`The ML archive at Gmane <http://dir.gmane.org/gmane.network.ryu.devel>`_
is also available.
