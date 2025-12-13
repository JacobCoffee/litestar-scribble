.. _api-reference:

=============
API Reference
=============

Complete API documentation for scribbl-py, organized by functional area.
All public APIs are documented with type hints, examples, and cross-references.


Quick Reference
===============

The most commonly used classes and functions:

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Task
     - API
   * - Litestar plugin
     - :class:`~scribbl_py.ScribblPlugin`, :class:`~scribbl_py.ScribblConfig`
   * - Domain models
     - :class:`~scribbl_py.Canvas`, :class:`~scribbl_py.Element`, :class:`~scribbl_py.Stroke`
   * - Storage
     - :class:`~scribbl_py.StorageProtocol`, :class:`~scribbl_py.InMemoryStorage`
   * - Services
     - :class:`~scribbl_py.CanvasService`
   * - WebSocket
     - :class:`~scribbl_py.CanvasWebSocketHandler`, :class:`~scribbl_py.ConnectionManager`
   * - Authentication
     - :class:`~scribbl_py.AuthService`, :class:`~scribbl_py.User`, :class:`~scribbl_py.Session`


Usage Examples
==============

Basic Plugin Setup
------------------

.. code-block:: python

   from litestar import Litestar
   from scribbl_py import ScribblPlugin, ScribblConfig

   app = Litestar(
       plugins=[ScribblPlugin(ScribblConfig())],
   )


Custom Configuration
--------------------

.. code-block:: python

   from scribbl_py import (
       ScribblPlugin,
       ScribblConfig,
       InMemoryStorage,
   )

   config = ScribblConfig(
       storage=InMemoryStorage(),
       api_path="/api/v1",
       enable_websocket=True,
   )

   app = Litestar(plugins=[ScribblPlugin(config)])


Creating a Canvas Programmatically
----------------------------------

.. code-block:: python

   from scribbl_py import Canvas, Stroke, Point, ElementStyle

   # Create a canvas
   canvas = Canvas(
       name="My Drawing",
       width=800,
       height=600,
   )

   # Create a stroke
   stroke = Stroke(
       points=[Point(x=10, y=10), Point(x=100, y=100)],
       style=ElementStyle(stroke_color="#000000", stroke_width=2),
   )


API Modules
===========

The API is organized into the following modules:

.. toctree::
   :maxdepth: 2
   :caption: API Documentation

   plugin
   core
   storage
   services
   realtime
   auth
   web
   game


Module Overview
---------------

Plugin (:mod:`scribbl_py.plugin`)
    The Litestar plugin and configuration classes for integrating scribbl-py
    into your application. See :doc:`plugin`.

Core (:mod:`scribbl_py.core`)
    Domain models including Canvas, Element, Stroke, Shape, Text, and Point.
    Also includes type enums and styling classes. See :doc:`core`.

Storage (:mod:`scribbl_py.storage`)
    Storage backends for persisting canvas data. Includes the StorageProtocol
    interface, InMemoryStorage, and optional DatabaseStorage. See :doc:`storage`.

Services (:mod:`scribbl_py.services`)
    Business logic services including CanvasService, ExportService, and
    TelemetryService. See :doc:`services`.

Realtime (:mod:`scribbl_py.realtime`)
    WebSocket handlers for real-time collaboration including the
    CanvasWebSocketHandler and ConnectionManager. See :doc:`realtime`.

Auth (:mod:`scribbl_py.auth`)
    OAuth authentication with support for Google, Discord, and GitHub.
    Includes User, Session, and UserStats models. See :doc:`auth`.

Web (:mod:`scribbl_py.web`)
    HTTP controllers and routes including CanvasController, ElementController,
    and the UIController for the web interface. See :doc:`web`.

Game (:mod:`scribbl_py.game`)
    Canvas Clash game logic including Room, Player, Round models and the
    word bank system. See :doc:`game`.


Indices and Tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
