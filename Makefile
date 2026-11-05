ARCHIVE ?= sincero.zip
DOWNLOADS ?= $(HOME)/Downloads

.PHONY: compress apply

compress:            ## zip the whole project, except .git/, .claude/, .githooks/, tasks.md, *brief.md and .ai-memory.toml: make compress [ARCHIVE=name.zip]
	rm -f $(ARCHIVE)
	zip -qr $(ARCHIVE) . -x '.git/*' '.claude/*' '.githooks/*' tasks.md '*brief.md' 'docs/plan' 'docs/future-features' .ai-memory.toml '*_changed_files.zip' '.venv/*' '*/.venv/*' CLAUDE.md

apply:               ## move the newest *changed_files.zip from Downloads here and overwrite the project with it
	@zip=$$(ls -t $(DOWNLOADS)/*changed_files.zip 2>/dev/null | head -n 1); \
	test -n "$$zip" || { echo "no *changed_files.zip in $(DOWNLOADS)"; exit 1; }; \
	tmp=$$(mktemp -d); trap 'rm -rf "$$tmp"' EXIT; \
	unzip -q "$$zip" -d "$$tmp" && test -d "$$tmp/files" && \
	cp -r "$$tmp/files/." . && mv "$$zip" . && echo "applied $$(basename "$$zip")"
