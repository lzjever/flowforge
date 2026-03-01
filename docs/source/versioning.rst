Versioning Policy
=================

Routilux uses semantic versioning in the form **x.y.z** (major.minor.patch).

Version structure
-----------------

- **x (major)**: Reserved for breaking changes to the public API or runtime behavior.
- **y (minor)**: New features and improvements. API and behavior remain compatible within the same minor line.
- **z (patch)**: Bug fixes and documentation only. No API or behavior changes.

Coupling with routilux-overseer
-------------------------------

- **routilux** and **routilux-overseer** are released as separate packages.
- **routilux-overseer** depends on the Routilux server API (HTTP + WebSocket).
- The **x.y** part of the version is **coupled**: for a given overseer release, it is designed to work with routilux **x.y.\*** (same major and minor). Example: overseer ``1.2.0`` targets routilux ``1.2.z``.
- **z (patch)** can be updated independently in each repo. Patch releases must not introduce any API or behavioral breaks.

API contract
------------

The contract between the server (routilux) and the client (routilux-overseer) is the **OpenAPI specification** exposed at ``/openapi.json``. See :doc:`api/contract` for details.

Summary
-------

- **x.y**: Released together; overseer x.y must match routilux x.y.
- **z**: Each repo may bump z independently; no API/behavior breaks.
