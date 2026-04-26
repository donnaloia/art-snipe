MOCKUP ?= mockups/gameplay.png
SERVICE ?= artpipe-cli

.PHONY: init up down logs shell run analyze manifest segment generate variants validate review export clean zip

init:
	mkdir -p mockups workspace/analysis workspace/manifests workspace/references workspace/generated workspace/approved workspace/rejected workspace/logs godot_project/assets/{ui,cards,icons,enemies,backgrounds} models

up:
	docker compose up -d

down:
	docker compose down

logs:
	docker compose logs -f

shell:
	docker compose run --rm $(SERVICE) bash

run:
	docker compose run --rm $(SERVICE) artpipe run --mockup $(MOCKUP)

analyze:
	docker compose run --rm $(SERVICE) artpipe analyze --mockup $(MOCKUP)

manifest:
	docker compose run --rm $(SERVICE) artpipe manifest

segment:
	docker compose run --rm $(SERVICE) artpipe segment

generate:
	docker compose run --rm $(SERVICE) artpipe generate

variants:
	docker compose run --rm $(SERVICE) artpipe variants

validate:
	docker compose run --rm $(SERVICE) artpipe validate

review:
	docker compose up review-ui

export:
	docker compose run --rm $(SERVICE) artpipe export

clean:
	rm -rf workspace/analysis/* workspace/references/* workspace/generated/* workspace/approved/* workspace/rejected/* workspace/logs/*

zip:
	cd .. && zip -r artpipe-godot-ai.zip artpipe-godot-ai -x 'artpipe-godot-ai/models/*' -x 'artpipe-godot-ai/.git/*'
