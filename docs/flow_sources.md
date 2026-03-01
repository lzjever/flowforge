# Where Flows Come From

Routilux flows can be created and discovered in several ways. This document explains the sources so you know why a flow appears (or does not appear) in the API and in Overseer.

## 1. DSL files (server load)

When you start the Routilux server with `--flows-dir` (e.g. `routilux server start --flows-dir ./flows`), the server loads flow definitions from YAML/JSON files in that directory. These flows are registered in the global **FlowRegistry** when the server starts (and on hot reload if enabled). They are **not** automatically visible to the HTTP API until you sync (see below).

## 2. Programmatic (FlowRegistry)

When you create a `Flow` in Python and register it (e.g. via `FlowRegistry.get_instance().register(flow)` or by using the flow in the same process as the server), that flow lives in the global **FlowRegistry**. The HTTP API does not see it until discovery/sync is used.

## 3. Created via API

Flows created through the HTTP API (e.g. `POST /api/v1/flows`) are stored in the API’s flow store and are immediately visible to the API and to Overseer when you list flows.

## 4. “Sync from registry” in Overseer

In **Routilux Overseer**, the **Sync from registry** action (on the Flows page) calls the server’s discovery endpoint (`POST /api/v1/discovery/flows/sync`). That endpoint:

- Reads all flows from the server’s **FlowRegistry** (flows from DSL files and programmatic registration).
- Makes them available to the API’s flow store so they appear in `GET /api/v1/flows` and in the Overseer flows list.

So:

- **Empty flows list?** Ensure the server has flows (e.g. start with `--flows-dir` or register flows in code), then click **Sync from registry** in Overseer.
- **Flow created in code or from DSL?** Use **Sync from registry** once (or after adding new flows) so they show up in the UI.

## Summary

| Source              | Where it lives        | Visible to API after        |
|---------------------|-----------------------|-----------------------------|
| DSL (--flows-dir)   | FlowRegistry          | Sync from registry          |
| Programmatic        | FlowRegistry          | Sync from registry          |
| API (POST /flows)   | API flow store        | Immediately                 |
