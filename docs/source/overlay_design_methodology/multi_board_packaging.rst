.. Copyright (C) 2026 Advanced Micro Devices, Inc.
.. SPDX-License-Identifier: BSD-3-Clause

.. _multi-board-packaging:

Packaging Overlays for Multiple Boards
======================================

An overlay is usually built for several boards. This page describes a package
layout that ships the bitstreams of all boards in one release and installs the
one that matches the target board. On a PYNQ.remote host the same package can
be installed for several board types, and one Python session can then drive
boards of different types.

The layout is the one used by the StrathSDR overlays, for example
`rfsoc_qpsk <https://github.com/strath-sdr/rfsoc_qpsk>`_. Notebooks are
registered with a ``pynq.notebooks`` entry point (see
:ref:`pynq-python-packaging`) instead of being copied by ``setup.py`` or by a
``__main__`` installer such as ``python -m rfsoc_qpsk install``.

Repository Layout
-----------------

Each board has a folder under ``boards/`` with the bitstream built for it. The
folder name is the board name: ``BOARD`` selects the folder when the package is
built, and the same name must be the ``device.name`` of the board, because PYNQ
uses ``device.name`` to pick the bitstream at run time. Spell it exactly as the
board reports it, for example ``RFSoC4x2``, ``ZCU208`` or ``AUP-ZU3``.
``pynq.Device.active_device.name`` gives the name of a board.

.. code-block:: console

   my_overlay/
   ├── boards/
   │   ├── RFSoC4x2/
   │   │   └── my_overlay/
   │   │       └── bitstream/
   │   │           ├── my_overlay.bit
   │   │           └── my_overlay.hwh
   │   └── ZCU208/
   │       └── my_overlay/
   │           └── bitstream/
   │               ├── my_overlay.bit
   │               └── my_overlay.hwh
   ├── my_overlay/
   │   ├── __init__.py
   │   ├── overlay.py
   │   └── notebooks/
   │       ├── __init__.py
   │       └── my_overlay.ipynb
   └── setup.py

The bitstream and hardware handoff file have the same names for every board, so
the driver loads them by one name whatever the board.

setup.py
--------

``setup.py`` reads the board name from the ``BOARD`` environment variable and
stops if there is no folder for it. It replaces ``my_overlay/bitstream`` with a
copy of that board's ``bitstream`` folder, so no file from an earlier build for
another board is left in it. The build picks the folder up as package data:

.. code-block:: python

   import os
   import shutil

   from setuptools import find_packages, setup

   NAME = "my_overlay"

   board = os.environ.get("BOARD", "")
   source = os.path.join("boards", board, NAME, "bitstream")
   if not board or not os.path.isdir(source):
       raise ValueError(f"Board {board!r} is not supported")
   dest = os.path.join(NAME, "bitstream")
   shutil.rmtree(dest, ignore_errors=True)
   shutil.copytree(source, dest)

   setup(
       name=NAME,
       version="1.0.0",
       packages=find_packages(),
       package_data={NAME: ["bitstream/*", "notebooks/**/*"]},
       install_requires=["pynq"],
       entry_points={
           "pynq.notebooks": ["my-overlay = my_overlay.notebooks"],
       },
   )

The entry point registers ``my_overlay/notebooks`` with ``pynq get-notebooks``
as ``my-overlay``. ``setup.py`` does not copy notebooks and the package has no
``__main__`` installer, so the build does not need ``PYNQ_JUPYTER_NOTEBOOKS``.

Overlay Driver
--------------

The driver subclasses ``Overlay`` and loads the bitstream installed with the
package unless it is given another one. Everything else, including the
``device`` argument, goes to ``Overlay`` through ``**kwargs``:

.. code-block:: python

   import os

   from pynq import Overlay

   ADC_TILE = {"RFSoC4x2": 2, "ZCU208": 1}


   class MyOverlay(Overlay):
       def __init__(self, bitfile_name=None, **kwargs):
           if bitfile_name is None:
               bitfile_name = os.path.join(
                   os.path.dirname(__file__), "bitstream", "my_overlay.bit"
               )
           super().__init__(bitfile_name, **kwargs)
           rf = self.usp_rf_data_converter_0
           self.adc_tile = rf.adc_tiles[ADC_TILE[self.device.name]]

Choose board-specific settings from ``self.device.name``, not from
``os.environ["BOARD"]``. ``BOARD`` selects the installation target and holds
one name per process; creating a remote overlay does not change it.
``self.device`` is always the board of this overlay.

Notebooks
---------

Notebooks do not name a board. They create the overlay through the driver,
which finds the bitstream for the board it runs on:

.. code-block:: python

   from my_overlay.overlay import MyOverlay

   overlay = MyOverlay()

The same notebook runs on every board the package supports. On a PYNQ.remote
host, set ``PYNQ_REMOTE_DEVICES`` before the import, as shown in
:ref:`quickstart`.

Releasing
---------

Build the bitstream and HWH file for each supported board and place them in
that board's folder, as shown above. Publish a source archive containing the
Python package, notebooks and all of these board folders.

Use a fresh checkout for the release build. Remove any temporary ``build/``
folder before creating the archive, so it cannot include files from an earlier
package build. From the directory containing the project, run:

.. code-block:: bash

   tar -czf my_overlay.tar.gz --exclude=.git my_overlay

Users install this archive and select the board they need.

Installing
----------

On a Board
~~~~~~~~~~

On a PYNQ board, omit ``--board``. The command reads the local board name
and installs the package and notebooks for it:

.. code-block:: bash

   pynq install <tarball>

Notebooks go to ``PYNQ_JUPYTER_NOTEBOOKS``, or ``./pynq-notebooks`` if it is
unset. Use ``--path`` to choose another directory. The package's bitstreams
stay in their original locations.

``<tarball>`` is the URL of the release asset or a local path.

On a PYNQ.remote Host
~~~~~~~~~~~~~~~~~~~~~

Run ``pynq install`` once for each board type:

.. code-block:: bash

   pynq install <tarball> --board RFSoC4x2
   pynq install <tarball> --board ZCU208

Each run adds the board's bitstream to the installed package and delivers its
notebooks to ``pynq-notebooks/<BOARD>/my-overlay/``. Do not use plain
``pip install`` on the host: it needs ``BOARD`` set, ``pip`` can reuse a cached
wheel built for another board, and it leaves plain bitstream files, which take
precedence over the per-board files of every board. See :ref:`pynq-cli` for the
options.

Using Several Remote Boards in One Session
-----------------------------------------

This example runs on a PYNQ.remote host, not in a local session on a classic
PYNQ image. Install the package for each board type, then create one overlay
per remote board and pass its ``device``:

.. code-block:: python

   import os
   os.environ["PYNQ_REMOTE_DEVICES"] = "192.168.2.99,192.168.2.100"

   import pynq
   from my_overlay.overlay import MyOverlay

   a, b = pynq.Device.devices
   overlay_a = MyOverlay(device=a)
   overlay_b = MyOverlay(device=b)

   mmio = pynq.MMIO(0xA0000000, 0x1000, device=a)
   buffer = pynq.allocate(1024, target=b)

Each overlay takes the bitstream for its own ``device.name``, so ``a`` and ``b``
can be different board types. See :ref:`remote_device` for what a session
shares between boards.
