Storage
=======

The storage module provides backends for persisting canvas and element data.

StorageProtocol
---------------

The base protocol that all storage backends must implement:

.. autoclass:: scribbl_py.StorageProtocol
   :members:
   :undoc-members:
   :show-inheritance:

InMemoryStorage
---------------

A simple in-memory storage backend, useful for development and testing:

.. autoclass:: scribbl_py.InMemoryStorage
   :members:
   :undoc-members:
   :show-inheritance:


Database Storage (Optional)
---------------------------

Available with the ``[db]`` extra. Install with:

.. code-block:: bash

   uv add "scribbl-py[db]"

DatabaseStorage
~~~~~~~~~~~~~~~

.. autoclass:: scribbl_py.storage.db.DatabaseStorage
   :members:
   :undoc-members:
   :show-inheritance:
   :noindex:


SQLAlchemy Models
~~~~~~~~~~~~~~~~~

.. automodule:: scribbl_py.storage.db.models
   :members:
   :undoc-members:
   :show-inheritance:
   :noindex:
