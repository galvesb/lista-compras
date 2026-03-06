---
name: deploy-magalucloud-docker
description: >
  Guia completo de deploy em VM MagaluCloud (ou qualquer VPS Linux) usando Docker Compose,
  Makefile e variaveis de ambiente seguras. Use quando o usuario pedir para:
  fazer deploy de uma aplicacao, configurar uma VM, criar um Makefile de deploy,
  configurar .env para producao, fazer deploy no MagaluCloud, configurar firewall/Security Groups,
  ou qualquer tarefa relacionada a CI/CD manual com rsync + docker compose.
  Inclui: estrutura de .env, .make.env, Makefile, docker-compose.yml, configuracao de firewall,
  instalacao de Docker na VM, e fluxo completo de primeiro deploy ao deploy continuo.
---

# Skill: Deploy em MagaluCloud com Docker Compose + Makefile

## Conceito central

O deploy funciona com 3 arquivos locais + 1 na VM:

```
LOCAL                           VM (ex: 201.23.16.17)
─────────────────────           ─────────────────────
Makefile         ─── rsync ──▶  ~/meu-projeto/
docker-compose.yml              docker-compose.yml
.env.example                    .env  (criado manualmente na VM)
.make.env  ← NÃO vai ao git
```

O `.make.env` fica local e fora do git — contém IP e usuário da VM.
O `.env` fica APENAS na VM — contém secrets de producao.

---

## 1. Arquivos de variáveis de ambiente

### `.env.example` (vai ao git, sem valores reais)

```bash
# ── Banco de dados ────────────────────────────────────────────────────
MONGO_USER=admin
MONGO_PASSWORD=change_me_strong_password
MONGO_DB=meu_banco
MONGO_HOST=mongodb
MONGO_PORT=27017

# ── Autenticacao JWT ──────────────────────────────────────────────────
# Gere com: python -c "import secrets; print(secrets.token_hex(32))"
JWT_SECRET_KEY=change_me_generate_a_256bit_secret_here
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=15

# ── API ───────────────────────────────────────────────────────────────
ALLOWED_ORIGINS=["http://localhost","http://localhost:80"]
API_PREFIX=/api/v1
DEBUG=false
```

### `.env` (criado na VM, NUNCA vai ao git)

```bash
# Copie de .env.example e preencha os valores reais:
# ssh usuario@IP "nano ~/meu-projeto/.env"

MONGO_USER=admin
MONGO_PASSWORD=MinhaS3nhaF0rte!
MONGO_DB=meu_banco
MONGO_HOST=mongodb
MONGO_PORT=27017

JWT_SECRET_KEY=a1b2c3d4e5f6...  # gerado com secrets.token_hex(32)
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=15

ALLOWED_ORIGINS=["http://201.23.16.17","http://meudominio.com"]
API_PREFIX=/api/v1
DEBUG=false
```

### `.make.env` (local, NUNCA vai ao git)

```bash
VM_USER=ubuntu
VM_HOST=201.23.16.17
```

### `.gitignore` — entradas obrigatórias

```gitignore
.env
.make.env
backups/
```

---

## 2. Makefile completo

```makefile
# Crie .make.env com:
#   VM_USER=ubuntu
#   VM_HOST=<ip-da-vm>
-include .make.env

VM_DIR=~/meu-projeto
SSH=ssh $(VM_USER)@$(VM_HOST)

# ── Deploy ─────────────────────────────────────────────────────────────

deploy: ## Envia o codigo e reinicia os containers na VM
	@echo "→ Enviando código para a VM..."
	rsync -avz --exclude='.git' --exclude='node_modules' --exclude='__pycache__' \
		--exclude='.env' --exclude='backups' \
		./ $(VM_USER)@$(VM_HOST):$(VM_DIR)/
	@echo "→ Subindo containers..."
	$(SSH) "cd $(VM_DIR) && docker compose up --build -d && docker system prune -f"
	@echo "✓ Deploy concluído! http://$(VM_HOST)"

# ── Utilitários ────────────────────────────────────────────────────────

logs: ## Ver logs da API em tempo real
	$(SSH) "cd $(VM_DIR) && docker compose logs -f api"

logs-all: ## Ver logs de todos os containers
	$(SSH) "cd $(VM_DIR) && docker compose logs -f"

status: ## Ver status dos containers na VM
	$(SSH) "cd $(VM_DIR) && docker compose ps"

ssh: ## Abre terminal na VM
	$(SSH)

health: ## Verifica health da API
	curl -s http://$(VM_HOST):8000/health | python3 -m json.tool

restart: ## Reinicia os containers sem rebuild
	$(SSH) "cd $(VM_DIR) && docker compose restart"

stop: ## Para todos os containers
	$(SSH) "cd $(VM_DIR) && docker compose down"

# ── Setup inicial (primeira vez) ───────────────────────────────────────

setup: ## Instala Docker na VM (rodar apenas uma vez)
	$(SSH) "curl -fsSL https://get.docker.com | sudo sh && sudo usermod -aG docker $(VM_USER)"
	@echo "✓ Docker instalado. Reconecte ao SSH para aplicar o grupo docker."

.PHONY: deploy logs logs-all status ssh health restart stop setup help
.DEFAULT_GOAL := help

help: ## Lista os comandos disponíveis
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'
```

---

## 3. `docker-compose.yml` (padrao com MongoDB interno)

```yaml
version: "3.9"

services:
  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    ports:
      - "80:8080"
    networks:
      - public
    depends_on:
      - api
    restart: unless-stopped

  api:
    build:
      context: ./backend
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    networks:
      - public
      - internal
    env_file:
      - .env
    depends_on:
      mongodb:
        condition: service_healthy
    restart: unless-stopped

  mongodb:
    image: mongo:7-jammy
    networks:
      - internal        # MongoDB NAO exposto ao publico
    volumes:
      - mongo_data:/data/db
    environment:
      MONGO_INITDB_ROOT_USERNAME: ${MONGO_USER}
      MONGO_INITDB_ROOT_PASSWORD: ${MONGO_PASSWORD}
      MONGO_INITDB_DATABASE: ${MONGO_DB}
    healthcheck:
      test: ["CMD", "mongosh", "--eval", "db.adminCommand('ping')"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 20s
    restart: unless-stopped

networks:
  public: {}
  internal:
    internal: true    # Rede interna: containers se falam, mundo externo nao acessa

volumes:
  mongo_data: {}
```

---

## 4. Fluxo completo de deploy — passo a passo

### Primeiro deploy (configuracao inicial)

```bash
# 1. Criar VM no MagaluCloud (Ubuntu 22.04 LTS, mínimo 1 vCPU / 1GB RAM)

# 2. Configurar Security Groups (Firewall) no painel MagaluCloud:
#    Entrada SSH (22):    seu_ip/32     — SÓ seu IP, nunca "0.0.0.0/0"
#    Entrada HTTP (80):   0.0.0.0/0    — Acesso público para o frontend
#    Entrada API (8000):  0.0.0.0/0    — Acesso público para a API
#    BLOQUEAR:  27017 (MongoDB), 3389 (RDP), qualquer outra porta

# 3. Descobrir seu IP atual (rodar na sua máquina local):
curl ifconfig.me

# 4. Conectar na VM pela primeira vez:
ssh ubuntu@<IP_DA_VM>

# 5. Instalar Docker na VM (ou usar o Makefile):
make setup
# Se nao funcionar, conectar e rodar manualmente:
# ssh ubuntu@<IP> "curl -fsSL https://get.docker.com | sudo sh && sudo usermod -aG docker ubuntu"
# Depois reconectar ao SSH para aplicar o grupo docker

# 6. Criar .make.env local (nunca commitar):
echo "VM_USER=ubuntu" > .make.env
echo "VM_HOST=<IP_DA_VM>" >> .make.env

# 7. Primeiro envio do codigo:
make deploy

# 8. Criar o .env de producao NA VM (nunca copiar do local):
ssh ubuntu@<IP_DA_VM> "cp ~/meu-projeto/.env.example ~/meu-projeto/.env && nano ~/meu-projeto/.env"
# Preencher todos os valores reais no editor nano

# 9. Gerar JWT_SECRET_KEY seguro:
python3 -c "import secrets; print(secrets.token_hex(32))"

# 10. Subir os containers:
ssh ubuntu@<IP_DA_VM> "cd ~/meu-projeto && docker compose up --build -d"

# 11. Verificar se esta funcionando:
make health
make status
```

### Deploy contínuo (após mudancas no codigo)

```bash
# Verificar se .make.env existe com IP correto
cat .make.env

# Fazer o deploy (rsync + docker compose up --build)
make deploy

# Acompanhar os logs
make logs

# Se algo der errado, ver todos os containers
make status
make logs-all
```

---

## 5. Comandos de operacao

```bash
# Ver status dos containers
make status

# Ver logs da API em tempo real
make logs

# Ver logs de todos os servicos
make logs-all

# Abrir terminal SSH na VM
make ssh

# Verificar endpoint /health
make health

# Reiniciar sem rebuild (rapido)
make restart

# Parar tudo
make stop

# Ver todos os comandos disponíveis
make help
```

---

## 6. Seguranca — checklist

```
Security Groups (Firewall MagaluCloud):
  [ ] SSH (22):   Somente seu IP (x.x.x.x/32) — NUNCA 0.0.0.0/0
  [ ] HTTP (80):  0.0.0.0/0  (frontend público)
  [ ] 8000:       0.0.0.0/0  (API pública)
  [ ] 27017:      BLOQUEADO   (MongoDB interno)
  [ ] 3389:       BLOQUEADO   (RDP desnecessário)

Arquivos:
  [ ] .env nao commitado (no .gitignore)
  [ ] .make.env nao commitado (no .gitignore)
  [ ] .env.example commitado SEM valores reais
  [ ] JWT_SECRET_KEY gerado com secrets.token_hex(32)
  [ ] MongoDB na rede internal do Docker (nao exposto)

SSH:
  [ ] Autenticacao por chave (nao por senha)
  [ ] Seu IP restrito no Security Group
```

---

## 7. Solucao de problemas comuns

```bash
# Container nao sobe — ver logs de erro
ssh ubuntu@<IP> "cd ~/meu-projeto && docker compose logs api"

# Porta 80 nao responde — verificar se container frontend subiu
ssh ubuntu@<IP> "docker compose ps"

# MongoDB nao conecta — verificar variaveis no .env
ssh ubuntu@<IP> "cd ~/meu-projeto && docker compose exec api env | grep MONGO"

# Fazer rebuild forçado sem cache
ssh ubuntu@<IP> "cd ~/meu-projeto && docker compose build --no-cache && docker compose up -d"

# Espaço em disco esgotado — limpar imagens antigas
ssh ubuntu@<IP> "docker system prune -af"

# Ver uso de recursos
ssh ubuntu@<IP> "docker stats --no-stream"

# Reiniciar apenas a API sem afetar o frontend
ssh ubuntu@<IP> "cd ~/meu-projeto && docker compose restart api"
```

---

## 8. Adaptacao para outros projetos

Para usar este padrao em um novo projeto, copie:

1. `Makefile` — altere `VM_DIR` e os nomes dos servicos em `logs`
2. `.env.example` — adapte as variaveis do seu projeto
3. `docker-compose.yml` — adapte os servicos
4. Crie `.make.env` localmente com `VM_USER` e `VM_HOST`
5. Adicione `.env` e `.make.env` ao `.gitignore`

O fluxo de deploy (`rsync` + `docker compose up --build`) funciona para qualquer projeto que tenha `docker-compose.yml` na raiz.
