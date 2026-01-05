# Minimal makefile for Sphinx documentation
SPHINXOPTS    =
SOURCEDIR    = source
BUILDDIR     = build

# Auto-detect sphinx-build: prefer uv run if available, otherwise use python -m sphinx
# Check if uv command exists and use it, otherwise fall back to python -m sphinx
# Allow override via SPHINXBUILD environment variable
SPHINXBUILD ?= $(shell command -v uv >/dev/null 2>&1 && echo "uv run sphinx-build" || echo "python -m sphinx")

# Put it first so that "make" without argument is like "make help".
help:
	@$(SPHINXBUILD) -M help "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)

.PHONY: help Makefile

# Catch-all target: route all unknown targets to Sphinx using the new
# "make mode" option.  $(O) is meant as a shortcut for $(SPHINXOPTS).
%: Makefile
	@$(SPHINXBUILD) -M $@ "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)

