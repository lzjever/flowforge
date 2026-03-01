API Contract
============

The Routilux server exposes a REST and WebSocket API. **routilux-overseer** consumes this API. The formal contract is the **OpenAPI 3.x** specification.

Contract source
---------------

- **Live**: When the server is running, the spec is available at ``GET /openapi.json``.
- **Version**: The server includes its package version in ``GET /`` (root) and in the OpenAPI ``info.version`` field. This version follows the same x.y.z policy as the package.

Compatibility rules
-------------------

- **Same x.y**: An overseer build for routilux **x.y** is compatible with any routilux **x.y.z** (e.g. 1.0.0, 1.0.1).
- **Patch (z)**: Routilux patch releases must not remove or change existing request/response shapes or semantics. Optional new fields are allowed.
- **Breaking changes**: Any change that breaks the existing OpenAPI contract (removed endpoints, changed required fields, changed types) must be released as a new **x** or **y** with clear migration notes.

Regenerating the client (overseer)
----------------------------------

routilux-overseer generates its TypeScript client from the OpenAPI spec:

1. Start the routilux server (e.g. ``routilux server`` or ``uv run routilux server``).
2. Run the overseer script: ``npm run regenerate-api`` (or pass the server URL, e.g. ``http://localhost:20555/openapi.json``).
3. Commit updated ``lib/api/generated`` and ``openapi.json`` when upgrading to a new routilux **x.y** (or when the spec has changed).

This ensures the overseer client stays in sync with the server contract for the targeted routilux x.y.
