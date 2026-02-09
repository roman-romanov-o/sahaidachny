.PHONY: test test-clean

test-clean:
	@if command -v docker >/dev/null 2>&1; then \
		ids=$$(docker ps -aq --filter "name=testcontainers-ryuk"); \
		if [ -n "$$ids" ]; then \
			docker rm -f $$ids >/dev/null; \
		fi; \
	fi

test:
	@$(MAKE) test-clean
	uv run pytest
