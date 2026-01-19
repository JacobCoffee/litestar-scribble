Installation
============

This guide covers different ways to install and run scribbl-py.


Requirements
------------

- **Python 3.10+** (3.12 or 3.13 recommended)
- **uv** - Fast Python package manager
- **Bun** - JavaScript runtime for frontend builds


Installing uv
-------------

uv is a fast Python package manager. Install it with:

.. code-block:: bash

   # macOS/Linux
   curl -LsSf https://astral.sh/uv/install.sh | sh

   # Or with the Makefile
   make install-uv


Installing Bun
--------------

Bun is used to build the frontend assets. Install it with:

.. code-block:: bash

   # macOS/Linux
   curl -fsSL https://bun.sh/install | bash

   # macOS with Homebrew
   brew install bun


Development Installation
------------------------

Clone and install for local development:

.. code-block:: bash

   # Clone the repository
   git clone https://github.com/JacobCoffee/scribbl-py.git
   cd scribbl-py

   # Install Python dependencies
   make dev

   # Install frontend dependencies
   make frontend-install

   # Build frontend assets
   make frontend-build

   # Run the application
   make serve

The application will be available at:

- **UI**: http://127.0.0.1:8000/ui/
- **Canvas Clash**: http://127.0.0.1:8000/canvas-clash/
- **API Docs**: http://127.0.0.1:8000/schema/


Optional Dependencies
---------------------

scribbl-py has optional extras for additional functionality:

Database Support
~~~~~~~~~~~~~~~~

For SQLAlchemy database persistence:

.. code-block:: bash

   uv add "scribbl-py[db]"

This installs:

- ``advanced-alchemy`` - Database utilities
- ``aiosqlite`` - Async SQLite support
- ``alembic`` - Database migrations
- ``asyncpg`` - PostgreSQL support


Authentication
~~~~~~~~~~~~~~

For OAuth authentication:

.. code-block:: bash

   uv add "scribbl-py[auth]"

This installs:

- ``authlib`` - OAuth library
- ``itsdangerous`` - Session signing
- ``httpx`` - HTTP client


Redis Support
~~~~~~~~~~~~~

For Redis-backed features:

.. code-block:: bash

   uv add "scribbl-py[redis]"


Task Queue
~~~~~~~~~~

For background task processing:

.. code-block:: bash

   uv add "scribbl-py[tasks]"


All Extras
~~~~~~~~~~

Install everything:

.. code-block:: bash

   uv add "scribbl-py[all]"


Docker Installation
-------------------

Run scribbl-py with Docker:

.. code-block:: bash

   # Build and run
   docker compose up -d

   # View logs
   docker compose logs -f

The application will be available at http://localhost:8000.

See :doc:`/guides/deployment` for production Docker configuration.


Verifying Installation
----------------------

After installation, verify everything is working:

.. code-block:: bash

   # Check Python package
   python -c "import scribbl_py; print(scribbl_py.__version__)"

   # Run tests
   make test

   # Build documentation
   make docs
