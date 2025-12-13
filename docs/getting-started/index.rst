Getting Started
===============

Welcome to scribbl-py! This guide will help you get the application running locally.

.. toctree::
   :maxdepth: 2

   installation
   quickstart


What is scribbl-py?
-------------------

scribbl-py is a collaborative drawing and whiteboard application built with Litestar.
It includes:

- **Canvas Editor** - A full-featured drawing tool with pen, shapes, text, and more
- **Canvas Clash** - A Pictionary-style multiplayer drawing game
- **Real-time Collaboration** - WebSocket-based synchronization
- **OAuth Authentication** - Sign in with Google, Discord, or GitHub


Prerequisites
-------------

Before you begin, ensure you have:

- **Python 3.10+** (3.12 or 3.13 recommended)
- **uv** - Fast Python package manager (`install <https://docs.astral.sh/uv/getting-started/installation/>`_)
- **Bun** - JavaScript runtime for frontend builds (`install <https://bun.sh/>`_)
- **Git** - Version control


Quick Start
-----------

.. code-block:: bash

   # Clone the repository
   git clone https://github.com/JacobCoffee/scribbl-py.git
   cd scribbl-py

   # Install dependencies
   make dev
   make frontend-install
   make frontend-build

   # Run the application
   make serve

Open http://127.0.0.1:8000 in your browser to access the application.


Next Steps
----------

- :doc:`installation` - Detailed installation instructions
- :doc:`quickstart` - Your first canvas and game
- :doc:`/guides/configuration` - Environment variables and OAuth setup
- :doc:`/guides/development` - Contributing and local development
