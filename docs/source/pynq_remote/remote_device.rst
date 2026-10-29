.. _remote_device:

The RemoteDevice Class
======================

The ``RemoteDevice`` class enables controlling PYNQ boards over network connections using gRPC. It provides a complete remote access solution including bitstream downloading, memory allocation, MMIO operations, and other PYNQ functionalities through remote procedure calls. 

This module includes classes for remote memory management (``RemoteBuffer``), memory-mapped I/O (``RemoteMMIO``), bitstream handling, and communication channel management. The implementation handles multiple bitstream formats (.bit, .bin, .xsa), metadata parsing, and caching while maintaining compatibility with the local PYNQ API. 

Remote devices can be configured through the ``PYNQ_REMOTE_DEVICES`` environment
variable, which should contain a comma-separated list of IP addresses for target
devices. Alternatively, construct a ``RemoteDevice`` directly and pass it to
``Overlay``:

.. code-block:: python

   from pynq import Overlay
   from pynq.pl_server.remote_device import RemoteDevice

   dev = RemoteDevice(0, "192.168.2.99")
   overlay = Overlay("design.bit", device=dev)

When ``PYNQ_REMOTE_DEVICES`` is set, ``Device.devices`` lists one
``RemoteDevice`` per address and ``Overlay`` uses the active device if no
``device`` argument is given.

``RemoteDevice`` returns a subclass that matches the board's SoC:
``RemoteZynqDevice``, ``RemoteZynqUltrascaleDevice`` or ``RemoteVersalDevice``.
Local devices share the same architecture classes from
:mod:`pynq.pl_server.arch`, so ``isinstance(dev, VersalArch)`` works for both.

Device tree overlays (``.dtbo``) shipped with a bitstream are applied on the
board. This needs a remote image built with the matching ``pynq-remote``
server; an older server reports that the remote image must be updated.

The ``RemoteDevice`` class is complemented by ``PYNQ.cpp`` which operates on the target device, providing a C++ implementation of the PYNQ API. For more details on the C++ implementation, see the :ref:`cppindex` module documentation.

Several Boards in One Session
-----------------------------

List every address in ``PYNQ_REMOTE_DEVICES`` and create one ``Overlay`` per
board, passing the board with ``device``. ``pynq.Device.devices`` holds one
``RemoteDevice`` per address, in order, and ``RemoteDevice(index, ip)`` creates
one directly. Set ``PYNQ_REMOTE_DEVICES`` before ``import pynq`` in both cases,
because that is what puts ``pynq`` in remote mode.

.. code-block:: python

   import os
   os.environ["PYNQ_REMOTE_DEVICES"] = "192.168.2.99,192.168.2.100"

   import pynq

   a, b = pynq.Device.devices
   overlay_a = pynq.Overlay("design_a.bit", device=a)
   overlay_b = pynq.Overlay("design_b.bit", device=b)

   mmio = pynq.MMIO(0xA0000000, 0x1000, device=a)
   buffer = pynq.allocate(1024, target=b)

Standalone objects name their board the same way: ``MMIO``, ``Register``,
``GPIO`` and ``Interrupt`` take ``device`` and ``allocate`` takes ``target``. Without them, they
use the active device (``pynq.Device.active_device``, the first board unless
you set it), which suits a single board only.

``from pynq import GPIO, Interrupt`` exports the same public classes whether
or not ``PYNQ_REMOTE_DEVICES`` is set. The target device selects the local or
remote implementation when an object is constructed. Existing objects retain
their target when the active device changes. GPIO lookup methods also accept
``device``:

.. code-block:: python

   pin = pynq.GPIO.get_gpio_pin(0, device=a)
   output = pynq.GPIO(pin, "out", device=a)
   irq = pynq.Interrupt("my_ip/interrupt", device=a)

Local GPIO wrappers share the local pin implementation. Remote GPIO wrappers
share a handle for the same pin and device instance; different device instances
have separate caches. As with local GPIO, releasing a shared pin unexports it
for the other wrappers too. Independent clients are not coordinated by this
Python cache.

Local interrupt controllers and UIO handles are cached per device. Interrupt
objects check their own device's overlay timestamp when waiting, so changing
another device's overlay does not invalidate them. Reloading an overlay while
a wait is already pending remains unsupported. Remote interrupt waiting is
still unimplemented and raises ``RuntimeError``.

Some lookups name no board. They are single-board conveniences and follow one
board:

``xrfclk``
   ``xrfclk`` calls without ``device`` act on the board of the most recently
   created overlay (on the active device before the first one).

``Clocks``
   The class-level ``Clocks`` acts on the board of the last overlay that was
   created or downloaded, and ``Clocks.set_device(device)`` selects another
   board. Each overlay programs the PL clocks of its own board when it is
   downloaded.

``PL``
   The class-level ``PL`` always describes ``pynq.Device.active_device``,
   whichever board the latest overlay was created on.

For several boards, keep one ``Overlay(..., device=dev)`` per board, read
``overlay.ip_dict`` rather than ``PL.ip_dict``, and pass ``device`` or
``target`` to every standalone ``MMIO``, ``Register``, ``GPIO`` and
``allocate``.

``pynq`` keeps the state of each remote board separately, in the
``pynq/pl_server`` folder of the installed package:
``global_pl_state_<ip>_<port>.json`` and ``_current_metadata_<ip>_<port>.pkl``,
where ``<port>`` is 7967 for the boards in ``PYNQ_REMOTE_DEVICES`` and any
character of ``<ip>`` other than a letter, digit, ``.``, ``-`` or ``_`` is
replaced by ``_``. Boards of the same type at different addresses have
separate files, and downloading an overlay to one board never rewrites the
files of another.

API Reference
-------------

.. automodule:: pynq.pl_server.remote_device
    :members:
    :undoc-members:
    :show-inheritance:
