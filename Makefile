# Crie um arquivo .make.env com:
#   VM_USER=ubuntu
#   VM_HOST=201.23.16.17
-include .make.env

VM_DIR=~/lista-compras
SSH=ssh $(VM_USER)@$(VM_HOST)

# ── Deploy ────────────────────────────────────────────────────────────────────

deploy: ## Envia o código e reinicia os containers na VM
	@echo "→ Enviando código para a VM..."
	rsync -avz --exclude='.git' --exclude='node_modules' --exclude='__pycache__' \
		--exclude='.env' --exclude='backups' \
		./ $(VM_USER)@$(VM_HOST):$(VM_DIR)/
	@echo "→ Subindo containers..."
	$(SSH) "cd $(VM_DIR) && docker compose up --build -d && docker system prune -f"
	@echo "✓ Deploy concluído! http://$(VM_HOST)"

# ── Utilitários ───────────────────────────────────────────────────────────────

logs: ## Ver logs da API em tempo real
	$(SSH) "cd $(VM_DIR) && docker compose logs -f api"

status: ## Ver status dos containers na VM
	$(SSH) "cd $(VM_DIR) && docker compose ps"

ssh: ## Abre terminal na VM
	$(SSH)

health: ## Verifica health da API
	curl -s http://$(VM_HOST):8000/health | python3 -m json.tool

restart: ## Reinicia os containers sem rebuild
	$(SSH) "cd $(VM_DIR) && docker compose restart"

# ── Setup inicial (primeira vez) ─────────────────────────────────────────────

setup: ## Configura a VM pela primeira vez (instala Docker)
	$(SSH) "curl -fsSL https://get.docker.com | sudo sh && sudo usermod -aG docker $(VM_USER)"
	@echo "✓ Docker instalado. Reconecte ao SSH para aplicar o grupo."

.PHONY: deploy logs status ssh health restart setup
.DEFAULT_GOAL := help

help: ## Lista os comandos disponíveis
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'
