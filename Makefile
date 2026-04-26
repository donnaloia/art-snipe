MOCKUP ?= mockups/gameplay.png
SERVICE ?= artpipe-cli

HOST_DIRS := mockups workspace/analysis workspace/manifests workspace/references workspace/generated workspace/approved workspace/rejected workspace/logs game_assets models

.PHONY: _dirs up down logs shell run analyze manifest segment generate variants validate review export clean zip

_dirs:
	@mkdir -p $(HOST_DIRS)

up: | _dirs
	docker compose up -d

down:
	docker compose down

logs:
	docker compose logs -f

shell: | _dirs
	docker compose run --rm $(SERVICE) bash

run: | _dirs
	docker compose run --rm $(SERVICE) artpipe run --mockup $(MOCKUP)

analyze: | _dirs
	docker compose run --rm $(SERVICE) artpipe analyze --mockup $(MOCKUP)

manifest: | _dirs
	docker compose run --rm $(SERVICE) artpipe manifest

segment: | _dirs
	docker compose run --rm $(SERVICE) artpipe segment

generate: | _dirs
	docker compose run --rm $(SERVICE) artpipe generate

variants: | _dirs
	docker compose run --rm $(SERVICE) artpipe variants

validate: | _dirs
	docker compose run --rm $(SERVICE) artpipe validate

review: | _dirs
	docker compose up review-ui

export: | _dirs
	docker compose run --rm $(SERVICE) artpipe export

clean:
	rm -rf workspace/analysis/* workspace/references/* workspace/generated/* workspace/approved/* workspace/rejected/* workspace/logs/*

zip:
	cd .. && zip -r artpipe.zip art-snipe -x 'art-snipe/models/*' -x 'art-snipe/.git/*'
