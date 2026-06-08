# Makefile — pain-free install for the memlog CLI.
#
# The plugin's read-half (auto-injecting prior lessons) works the moment you
# install the plugin, because its hooks call scripts by absolute path. The
# write-half (`memlog add` / `memlog search`) needs the `memlog` CLI on your
# PATH — that's what this Makefile sets up.
#
#   make install     symlink memlog into a bin dir on PATH, then verify
#   make doctor      report install/PATH/python health (no changes)
#   make uninstall   remove the symlink
#
# A symlink (not a copy) means `git pull` updates the CLI in place — no stale
# copies. Override the target dir with: make install BINDIR=/usr/local/bin

# Where the symlink lands. ~/.local/bin is on PATH for most shells.
BINDIR ?= $(HOME)/.local/bin

# Absolute path to this repo, resolved from the Makefile's own location so it
# is correct no matter the cwd or where the repo gets moved later.
REPO_DIR := $(patsubst %/,%,$(dir $(abspath $(lastword $(MAKEFILE_LIST)))))
SRC := $(REPO_DIR)/memlog
DEST := $(BINDIR)/memlog

.PHONY: install uninstall doctor

install:
	@command -v python3 >/dev/null 2>&1 || { echo "✗ python3 not found — memlog needs Python 3.8+"; exit 1; }
	@test -f "$(SRC)" || { echo "✗ $(SRC) missing — run make from inside the repo"; exit 1; }
	@chmod +x "$(SRC)"
	@mkdir -p "$(BINDIR)"
	@ln -sf "$(SRC)" "$(DEST)"
	@echo "✓ linked $(DEST) -> $(SRC)"
	@"$(DEST)" --help >/dev/null 2>&1 && echo "✓ memlog runs" || { echo "✗ memlog failed to run"; exit 1; }
	@case ":$$PATH:" in \
	  *":$(BINDIR):"*) echo "✓ $(BINDIR) is on your PATH — you're done." ;; \
	  *) echo "⚠ $(BINDIR) is NOT on your PATH. Add this to ~/.zshrc or ~/.bashrc:"; \
	     echo "    export PATH=\"$(BINDIR):\$$PATH\""; \
	     echo "  then restart your shell." ;; \
	esac
	@echo "→ sanity check: memlog list --reverse --limit 3"

uninstall:
	@if [ -L "$(DEST)" ]; then rm -f "$(DEST)"; echo "✓ removed $(DEST)"; \
	else echo "nothing to remove: $(DEST) is not a symlink"; fi

doctor:
	@echo "repo:      $(REPO_DIR)"
	@if [ -x "$(SRC)" ]; then echo "script:    $(SRC) (ok)"; \
	else echo "script:    $(SRC) (MISSING or not executable)"; fi
	@if [ -L "$(DEST)" ]; then \
	  if [ -e "$(DEST)" ]; then echo "symlink:   $(DEST) -> $$(readlink "$(DEST)") (ok)"; \
	  else echo "symlink:   $(DEST) -> $$(readlink "$(DEST)") (DANGLING — run 'make install')"; fi; \
	elif [ -e "$(DEST)" ]; then echo "symlink:   $(DEST) exists but is not a symlink"; \
	else echo "symlink:   not installed (run 'make install')"; fi
	@case ":$$PATH:" in \
	  *":$(BINDIR):"*) echo "PATH:      $(BINDIR) on PATH (ok)" ;; \
	  *) echo "PATH:      $(BINDIR) NOT on PATH" ;; \
	esac
	@if command -v memlog >/dev/null 2>&1; then echo "resolves:  $$(command -v memlog) (ok)"; \
	else echo "resolves:  memlog not found on PATH"; fi
	@if command -v python3 >/dev/null 2>&1; then echo "python3:   $$(python3 --version 2>&1) (ok)"; \
	else echo "python3:   MISSING — install Python 3.8+"; fi
