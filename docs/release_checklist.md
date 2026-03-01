# Release Checklist

Use this checklist when releasing a new **x.y** (coupled) or **z** (patch) version. For the **x.y** coupling with routilux-overseer, see `VERSIONING.md` and coordinate with the overseer repo (same x.y; overseer regenerates API client from this server).

## Pre-release (both repos when doing x.y)

1. **Version**
   - Bump `__version__` in `routilux/__init__.py` (routilux) and `version` in `package.json` (overseer) to the same **x.y.z** (for a coupled release) or bump only **z** in one repo (patch).
2. **Changelog**
   - Add a new `## [x.y.z] - YYYY-MM-DD` section in `CHANGELOG.md` (routilux). Overseer may maintain its own changelog.
3. **Contract**
   - For **x.y** release: ensure routilux-overseer has regenerated its API client from the routilux server that will be released (`npm run regenerate-api` against the routilux server), and commit `lib/api/generated` and `openapi.json` if changed.
4. **Tests**
   - Routilux: `make test` (or `uv run pytest tests/ routilux/builtin_routines/ -n auto -v`).
   - Overseer: `npm run test:run`, `npm run build`, optionally E2E against the target routilux server.
5. **Lint / format**
   - Routilux: `make lint`, `make format-check`.
   - Overseer: `npm run lint`, `npm run format:check`.

## Release (routilux)

1. Tag: `git tag vx.y.z`
2. Push tag: `git push origin vx.y.z`
3. CI will build, run tests, create GitHub Release, and optionally publish to PyPI if `PYPI_API_TOKEN` is set.

## Release (routilux-overseer)

1. Tag: `git tag vx.y.z`
2. Push tag (or create GitHub Release manually with the same version).
3. For patch-only (**z**) releases, no need to regenerate API if routilux x.y is unchanged.

## Rules

- **x.y**: Release routilux and routilux-overseer together; overseer x.y must match routilux x.y.
- **z**: Each repo may release patches independently; no API or behavior breaks.
