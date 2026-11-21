# Convenience targets. Everything here is a thin wrapper around ./fluidian.
.PHONY: help doctor test test-quick test-browser gallery showcase codegen docs screenshots toolchains clean dist

help:            ## List the targets
	@grep -E '^[a-z-]+: .*##' $(MAKEFILE_LIST) | sed -E 's/:.*## /\t/' | expand -t 16

doctor:          ## Check the environment and toolchains
	./fluidian doctor

test:            ## Run every automated test (SDKs without a toolchain are skipped)
	./fluidian test

test-quick:      ## Engine and runtime tests only (a few seconds)
	./fluidian test --quick

test-browser:    ## Everything, plus the headless-Chrome checks
	./fluidian test --browser

gallery:         ## Start the gallery of AI capabilities at http://127.0.0.1:8787
	./fluidian gallery --open

showcase:        ## Start the showcase of 85 complete screens at http://127.0.0.1:8787
	./fluidian showcase --open

codegen:         ## Regenerate SDK factories and specs from the registries
	./fluidian codegen

docs:            ## Regenerate the reference documentation
	./fluidian docs

screenshots:     ## Re-capture the documentation screenshots and the README collage (needs Chrome and Pillow)
	python3 tools/screenshots.py
	python3 tools/hero.py

toolchains:      ## Install the optional language toolchains (Ubuntu/Debian)
	scripts/install-toolchains.sh

clean:           ## Remove build output and caches
	rm -rf .fluidian sdks/csharp/*/bin sdks/csharp/*/obj sdks/csharp/examples/*/bin sdks/csharp/examples/*/obj sdks/rust/target sdks/rust/Cargo.lock sdks/typescript/dist sdks/dart/.dart_tool sdks/dart/pubspec.lock
	find . -name __pycache__ -type d -prune -exec rm -rf {} +

dist: clean      ## Build fluidian-<version>.zip next to the checkout
	cd .. && zip -qr fluidian-$$(cd fluidian && PYTHONDONTWRITEBYTECODE=1 ./fluidian version | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -1).zip fluidian \
		-x 'fluidian/.git/*' '*/__pycache__/*' 'fluidian/.fluidian/*' 'fluidian/converted/*' 'fluidian/native/*' 'fluidian/design-tokens/*'
