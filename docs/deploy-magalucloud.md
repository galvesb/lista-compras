# Deploy no MagaluCloud — Guia Completo

Stack: Docker Compose + Makefile + rsync | VM Ubuntu 22.04

---

## Visão geral

```
Sua máquina (local)          VM MagaluCloud
────────────────────         ─────────────────────────────────
código-fonte                 ~/lista-compras/
Makefile          ─rsync──▶  docker-compose.yml
docker-compose.yml           Dockerfile(s)
.env.example                 .env  ← criado MANUALMENTE na VM
.make.env  (oculto)          containers: frontend, api, mongodb
```

---

## Passo 1 — Criar a VM no MagaluCloud

1. Acesse o painel MagaluCloud → **Computação → Virtual Machines**
2. Clique em **Criar VM**
3. Configurações mínimas recomendadas:

| Campo | Valor |
|---|---|
| Imagem | Ubuntu 22.04 LTS |
| Flavor | 1 vCPU / 1 GB RAM (ou maior) |
| Região | brasil-se-1 (ou a mais próxima) |
| Par de chaves SSH | Selecione ou crie um par (obrigatório) |

4. Anote o **IP público** da VM após criação (ex: `201.23.16.17`)

---

## Passo 2 — Configurar Security Groups (Firewall)

Acesse **Rede → Security Groups** no painel. Configure as **regras de entrada (ingress)**:

| Protocolo | Porta | Origem | Motivo |
|---|---|---|---|
| TCP | 22 | `seu_ip/32` | SSH — somente sua máquina |
| TCP | 80 | `0.0.0.0/0` | Frontend (acesso público) |
| TCP | 8000 | `0.0.0.0/0` | API (acesso público) |
| ~~TCP~~ | ~~27017~~ | ~~Bloqueado~~ | MongoDB — nunca expor |
| ~~TCP~~ | ~~3389~~ | ~~Bloqueado~~ | RDP — desnecessário |

**Como descobrir seu IP atual:**
```bash
# Rodar na sua máquina local (não na VM):
curl ifconfig.me
```

> **Importante:** Use `x.x.x.x/32` (barra 32) para restringir SSH apenas ao seu IP.
> Nunca use `0.0.0.0/0` para SSH — isso expõe a VM para ataques de força bruta.

---

## Passo 3 — Conectar na VM pela primeira vez

```bash
# Conectar via SSH com a chave criada no painel
ssh ubuntu@201.23.16.17

# Verificar se conectou
whoami  # deve retornar: ubuntu
```

---

## Passo 4 — Instalar Docker na VM

```bash
# Na VM, rodar o script oficial do Docker
curl -fsSL https://get.docker.com | sudo sh

# Adicionar o usuario ubuntu ao grupo docker (sem precisar de sudo)
sudo usermod -aG docker ubuntu

# Sair e reconectar para aplicar o grupo
exit
ssh ubuntu@201.23.16.17

# Verificar instalação
docker --version
docker compose version
```

Ou usar o Makefile (após configurar `.make.env` localmente):
```bash
make setup
# Depois reconectar ao SSH para aplicar o grupo docker
```

---

## Passo 5 — Configurar arquivos locais

### 5.1 Criar `.make.env` (nunca vai ao git)

```bash
# Na sua máquina local, na raiz do projeto:
cat > .make.env << 'EOF'
VM_USER=ubuntu
VM_HOST=201.23.16.17
EOF
```

Verifique que está no `.gitignore`:
```bash
grep ".make.env" .gitignore  # deve aparecer na lista
```

### 5.2 Verificar `.gitignore`

Deve conter no mínimo:
```gitignore
.env
.make.env
backups/
node_modules/
__pycache__/
```

---

## Passo 6 — Primeiro deploy (enviar o código)

```bash
# Na sua máquina local:
make deploy

# O que este comando faz:
# 1. rsync: envia o código para a VM (excluindo .env, node_modules, .git)
# 2. docker compose up --build -d: builda e sobe os containers
# 3. docker system prune -f: limpa imagens antigas
```

---

## Passo 7 — Configurar o `.env` de produção NA VM

```bash
# Conectar na VM
ssh ubuntu@ip

# Copiar o .env.example como base
cp ~/lista-compras/.env.example ~/lista-compras/.env

# Editar com os valores reais
nano ~/lista-compras/.env
```

Preencha todos os valores. Para gerar o `JWT_SECRET_KEY`:
```bash
# Na VM ou localmente:
python3 -c "import secrets; print(secrets.token_hex(32))"
```

Exemplo de `.env` de produção preenchido:
```bash
MONGO_USER=admin
MONGO_PASSWORD=MinhaS3nhaF0rte!
MONGO_DB=nome-banco
MONGO_HOST=mongodb
MONGO_PORT=27017

JWT_SECRET_KEY=a1b2c3d4e5f6789abc...  # gerado acima
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=15

ALLOWED_ORIGINS=["http://ip","http://meudominio.com"]
API_PREFIX=/api/v1
DEBUG=false
```

---

## Passo 8 — Subir os containers com o .env correto

```bash
# Na VM (após editar o .env):
cd ~/lista-compras
docker compose up --build -d

# Ou da sua máquina local (faz deploy + build):
make deploy
```

---

## Passo 9 — Verificar se está funcionando

```bash
# Status dos containers (devem estar todos "Up")
make status

# Health check da API
make health
# Esperado: { "status": "ok", "mongodb": "ok" }

# Ver logs da API
make logs

# Acessar no browser:
# Frontend: http://ip
# API docs: http://ip:8000/docs
```

---

## Fluxo de deploy contínuo (atualizações)

Após qualquer mudança no código:

```bash
# 1. Verificar .make.env
cat .make.env

# 2. Deploy (rsync + rebuild)
make deploy

# 3. Acompanhar os logs
make logs

# 4. Verificar health
make health
```

---

## Referência de comandos Makefile

```bash
make deploy      # Envia código + rebuild containers
make logs        # Logs da API em tempo real
make logs-all    # Logs de todos os containers
make status      # Status dos containers
make ssh         # Abre terminal SSH na VM
make health      # Testa o endpoint /health
make restart     # Reinicia sem rebuild (rápido)
make stop        # Para todos os containers
make setup       # Instala Docker na VM (apenas 1x)
make help        # Lista todos os comandos
```

---

## Solução de problemas

### Container não sobe
```bash
make ssh
cd ~/lista-compras
docker compose logs api        # ver erro da API
docker compose logs mongodb    # ver erro do MongoDB
docker compose ps              # ver status de todos
```

### MongoDB não conecta
```bash
make ssh
cd ~/lista-compras
docker compose exec api env | grep MONGO    # ver variáveis carregadas
cat .env                                     # confirmar valores
```

### Porta 80 não responde
```bash
make status      # verificar se frontend está "Up"
# Verificar Security Groups no painel — porta 80 deve estar liberada
```

### Espaço em disco esgotado
```bash
make ssh
docker system prune -af        # remove imagens e containers não usados
df -h                          # verificar espaço disponível
```

### Rebuild forçado (sem cache)
```bash
make ssh
cd ~/lista-compras
docker compose build --no-cache
docker compose up -d
```

### Perdi acesso SSH (IP mudou)
```bash
# 1. Descobrir novo IP: curl ifconfig.me
# 2. No painel MagaluCloud → Security Groups
# 3. Editar regra de entrada SSH (porta 22)
# 4. Atualizar o IP de origem para seu novo IP/32
```

---

## Checklist de segurança

```
[ ] SSH (porta 22) restrito ao seu IP no Security Group
[ ] MongoDB (27017) BLOQUEADO no Security Group
[ ] RDP (3389) BLOQUEADO no Security Group
[ ] .env no .gitignore (nunca commitado)
[ ] .make.env no .gitignore (nunca commitado)
[ ] JWT_SECRET_KEY gerado com secrets.token_hex(32)
[ ] MongoDB na rede internal do Docker (sem porta exposta)
[ ] Autenticacao SSH por chave (nao por senha)
[ ] DEBUG=false no .env de producao
```
