Installation
============

Requirements
------------

* **Python 3.8 or higher** (supports up to 3.14)
* Operating system: Linux, macOS, or Windows

.. note:: **Python Version Support**

   Routilux supports Python 3.8 through 3.14. If you're using Python 3.7 or earlier,
   you'll need to upgrade to use Routilux.

Basic Installation
------------------

Install Routilux from PyPI using pip:

.. code-block:: bash

   pip install routilux

This installs the core Routilux package with minimal dependencies.

Installation with Optional Features
------------------------------------

API Server (FastAPI)
~~~~~~~~~~~~~~~~~~~~

For HTTP API and WebSocket support (monitoring, debugging, flow builder):

.. code-block:: bash

   pip install routilux[api]

This installs:

* `fastapi` - Web framework
* `uvicorn[standard]` - ASGI server
* `slowapi` - Rate limiting

.. warning:: **Production Deployment**

   When deploying the API server in production, **always enable API key authentication**.
   See the :doc:`HTTP API <http_api>` section for security configuration.

Development Installation
------------------------

For development with all dependencies (testing, documentation, API):

.. code-block:: bash

   pip install routilux[dev]

This includes:

* pytest - Testing framework
* pytest-cov - Coverage reporting
* sphinx - Documentation generation
* ruff - Linting and formatting
* mypy - Type checking
* All API dependencies

Installing from Source
-----------------------

Clone the repository and install in development mode:

.. code-block:: bash

   git clone https://github.com/lzjever/routilux.git
   cd routilux
   pip install -e .

For development with all dependencies:

.. code-block:: bash

   pip install -e ".[dev]"

Using UV (Recommended)
----------------------

`uv` is a fast Python package installer written in Rust. It's significantly faster than pip.

Install uv:

.. code-block:: bash

   curl -LsSf https://astral.sh/uv/install.sh | sh

Then install Routilux:

.. code-block:: bash

   # Basic installation
   uv pip install routilux

   # With API support
   uv pip install "routilux[api]"

   # Development mode (from source)
   uv pip install -e ".[dev]"

Core Dependencies
-----------------

Routilux has minimal core dependencies:

* **serilux >= 0.3.1** - Serialization framework

All other dependencies are optional or development-only.

Verifying Installation
-----------------------

After installation, verify that Routilux is working:

.. code-block:: python

   from routilux import Routine, Flow, Runtime
   print(f"Routilux version: {Routine.__module__}")
   print("Installation successful!")

If you installed with API support, you can also verify the FastAPI app:

.. code-block:: python

   from routilux.api import app
   print("API module loaded successfully!")

.. note:: **ImportError for API Module**

   If you get an ImportError when importing the API module, make sure you installed
   the API extras: `pip install routilux[api]`

Environment Variables
----------------------

The API server (when installed) supports several environment variables for configuration:

.. list-table::
   :widths: 25 75
   :header-rows: 1

   * - Variable
     - Description
   * - ``ROUTILUX_API_HOST``
     - API server host (default: ``0.0.0.0``)
   * - ``ROUTILUX_API_PORT``
     - API server port (default: ``20555``)
   * - ``ROUTILUX_API_RELOAD``
     - Enable auto-reload (default: ``true``)
   * - ``ROUTILUX_API_KEY_ENABLED``
     - Enable API key authentication (default: ``false``)
   * - ``ROUTILUX_API_KEY``
     - Single API key for authentication
   * - ``ROUTILUX_API_KEYS``
     - Comma-separated list of API keys
   * - ``ROUTILUX_CORS_ORIGINS``
     - CORS allowed origins (default: localhost only)
   * - ``ROUTILUX_RATE_LIMIT_ENABLED``
     - Enable rate limiting (default: ``false``)
   * - ``ROUTILUX_RATE_LIMIT_PER_MINUTE``
     - Rate limit per minute (default: ``60``)

.. warning:: **Security: API Key Authentication**

   **Always enable API key authentication in production** by setting
   ``ROUTILUX_API_KEY_ENABLED=true`` and providing a strong API key via
   ``ROUTILUX_API_KEY`` or ``ROUTILUX_API_KEYS``. See :doc:`http_api` for details.

Running the API Server
----------------------

To start the API server:

.. code-block:: bash

   # Using python
   python -m routilux.api.main

   # Using uvicorn directly
   uvicorn routilux.api.main:app --host 0.0.0.0 --port 20555 --reload

The API will be available at:

* HTTP API: ``http://localhost:20555/api``
* Interactive docs (Swagger UI): ``http://localhost:20555/docs``
* Alternative docs (ReDoc): ``http://localhost:20555/redoc``

Troubleshooting
---------------

Import Errors
~~~~~~~~~~~~~

If you encounter import errors:

.. code-block:: bash

   # Reinstall with all dependencies
   pip install --force-reinstall routilux[api]

   # Or upgrade pip first
   pip install --upgrade pip
   pip install routilux

API Server Won't Start
~~~~~~~~~~~~~~~~~~~~~~~

If the API server fails to start:

1. Make sure you installed API extras: ``pip install routilux[api]``
2. Check if port 20555 is available, or use a different port:
   ``ROUTILUX_API_PORT=8080 python -m routilux.api.main``
3. Check the error message for missing dependencies and install them

Python Version Issues
~~~~~~~~~~~~~~~~~~~~~

If you're using Python 3.7 or earlier:

.. code-block:: bash

   # Upgrade to Python 3.8+
   # On Ubuntu/Debian:
   sudo apt update && sudo apt install python3.8

   # On macOS with pyenv:
   pyenv install 3.8.18
   pyenv global 3.8.18

   # Then reinstall routilux
   pip install routilux

Next Steps
----------

After installation, check out:

* :doc:`quickstart` - Get started in 5 minutes
* :doc:`http_api` - HTTP API and security configuration
* :doc:`user_guide/index` - Comprehensive user guide
* :doc:`examples/index` - Real-world examples
