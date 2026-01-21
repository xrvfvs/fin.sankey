# Deployment Guide - fin.sankey

Ten przewodnik opisuje różne opcje deploymentu aplikacji fin.sankey.

## Spis treści

1. [Wymagania wstępne](#wymagania-wstępne)
2. [Streamlit Cloud (Zalecane)](#streamlit-cloud-zalecane)
3. [Railway](#railway)
4. [Render](#render)
5. [Fly.io](#flyio)
6. [Heroku](#heroku)
7. [VPS / Docker Compose](#vps--docker-compose)
8. [Zmienne środowiskowe](#zmienne-środowiskowe)

---

## Wymagania wstępne

Przed deploymentem upewnij się, że masz:

- [ ] Konto Supabase z utworzonym projektem
- [ ] Klucz API Perplexity (dla raportów AI)
- [ ] Konfiguracja email (SendGrid/Resend/SMTP) - dla powiadomień
- [ ] Repozytorium na GitHub

### Konfiguracja Supabase

1. Utwórz projekt na [supabase.com](https://supabase.com)
2. Wykonaj migrację bazy danych (schemat w `supabase/schema.sql` jeśli istnieje)
3. Skopiuj `SUPABASE_URL` i `SUPABASE_KEY` z Settings → API

---

## Streamlit Cloud (Zalecane)

**Koszt:** Darmowy | **Trudność:** Łatwa | **URL:** [share.streamlit.io](https://share.streamlit.io)

### Zalety
- Natywne wsparcie dla Streamlit
- Automatyczne deploymenty z GitHub
- Wbudowane zarządzanie sekretami
- Darmowy plan dla publicznych repozytoriów

### Kroki

1. **Zaloguj się** na [share.streamlit.io](https://share.streamlit.io) kontem GitHub

2. **Utwórz nową aplikację:**
   - Repository: `twój-użytkownik/fin.sankey`
   - Branch: `main`
   - Main file path: `app.py`

3. **Skonfiguruj sekrety:**

   W ustawieniach aplikacji → Secrets, wklej:
   ```toml
   [api]
   perplexity_key = "pplx-xxx"

   [supabase]
   url = "https://xxx.supabase.co"
   key = "eyJxxx"

   [email]
   provider = "sendgrid"  # lub "resend", "smtp"
   sendgrid_api_key = "SG.xxx"
   from_address = "alerts@your-domain.com"
   from_name = "fin.sankey Alerts"

   [redis]
   url = ""  # opcjonalne - Streamlit Cloud nie wymaga Redis
   ```

4. **Deploy** - kliknij "Deploy!"

### Ograniczenia
- Brak Redis (sesje nie są persistentne między restartami)
- Ograniczone zasoby na darmowym planie
- Publiczne repo dla darmowego planu

---

## Railway

**Koszt:** ~$5/mies | **Trudność:** Łatwa | **URL:** [railway.app](https://railway.app)

### Zalety
- Pełne wsparcie Docker
- Wbudowany Redis
- Prosty UI
- Automatyczne HTTPS

### Kroki

1. **Zainstaluj Railway CLI:**
   ```bash
   npm install -g @railway/cli
   railway login
   ```

2. **Utwórz projekt:**
   ```bash
   cd fin.sankey
   railway init
   ```

3. **Dodaj Redis:**
   ```bash
   railway add --plugin redis
   ```

4. **Skonfiguruj zmienne środowiskowe:**
   ```bash
   railway variables set PERPLEXITY_API_KEY=pplx-xxx
   railway variables set SUPABASE_URL=https://xxx.supabase.co
   railway variables set SUPABASE_KEY=eyJxxx
   railway variables set SENDGRID_API_KEY=SG.xxx
   railway variables set EMAIL_FROM=alerts@your-domain.com
   ```

5. **Deploy:**
   ```bash
   railway up
   ```

### Konfiguracja
Plik `railway.toml` jest już przygotowany w repozytorium.

---

## Render

**Koszt:** Darmowy tier | **Trudność:** Łatwa | **URL:** [render.com](https://render.com)

### Zalety
- Darmowy tier
- Managed Redis
- Blueprint dla łatwego setupu
- Automatyczne deploymenty

### Kroki

1. **Zaloguj się** na [render.com](https://render.com)

2. **Użyj Blueprint:**
   - New → Blueprint
   - Połącz repozytorium GitHub
   - Render automatycznie wykryje `render.yaml`

3. **Lub ręcznie:**

   **Web Service:**
   - New → Web Service
   - Połącz repozytorium
   - Runtime: Docker
   - Dockerfile Path: `./Dockerfile`

   **Redis:**
   - New → Redis
   - Plan: Free
   - Skopiuj Internal URL do zmiennej `REDIS_URL`

4. **Skonfiguruj zmienne środowiskowe** w dashboardzie

5. **Deploy** - automatycznie po push do main

---

## Fly.io

**Koszt:** Pay-as-you-go | **Trudność:** Średnia | **URL:** [fly.io](https://fly.io)

### Zalety
- Globalny edge
- Dobre skalowanie
- Niskie opóźnienia

### Kroki

1. **Zainstaluj Fly CLI:**
   ```bash
   curl -L https://fly.io/install.sh | sh
   fly auth login
   ```

2. **Utwórz aplikację:**
   ```bash
   cd fin.sankey
   fly launch --no-deploy
   ```

   Fly wykryje `fly.toml` i użyje go.

3. **Dodaj Redis (opcjonalnie):**
   ```bash
   fly redis create
   ```

4. **Skonfiguruj sekrety:**
   ```bash
   fly secrets set PERPLEXITY_API_KEY=pplx-xxx
   fly secrets set SUPABASE_URL=https://xxx.supabase.co
   fly secrets set SUPABASE_KEY=eyJxxx
   fly secrets set SENDGRID_API_KEY=SG.xxx
   ```

5. **Deploy:**
   ```bash
   fly deploy
   ```

### Monitoring
```bash
fly status
fly logs
```

---

## Heroku

**Koszt:** ~$7/mies | **Trudność:** Łatwa | **URL:** [heroku.com](https://heroku.com)

### Kroki

1. **Zainstaluj Heroku CLI:**
   ```bash
   curl https://cli-assets.heroku.com/install.sh | sh
   heroku login
   ```

2. **Utwórz aplikację:**
   ```bash
   cd fin.sankey
   heroku create fin-sankey-app
   ```

3. **Dodaj Redis:**
   ```bash
   heroku addons:create heroku-redis:mini
   ```

4. **Skonfiguruj zmienne:**
   ```bash
   heroku config:set PERPLEXITY_API_KEY=pplx-xxx
   heroku config:set SUPABASE_URL=https://xxx.supabase.co
   heroku config:set SUPABASE_KEY=eyJxxx
   ```

5. **Deploy:**
   ```bash
   git push heroku main
   ```

Plik `Procfile` jest już przygotowany.

---

## VPS / Docker Compose

**Koszt:** ~$5/mies (DigitalOcean/Hetzner) | **Trudność:** Średnia

### Wymagania
- VPS z Ubuntu 22.04+
- Docker i Docker Compose zainstalowane
- Domena (opcjonalnie)

### Kroki

1. **Połącz się z serwerem:**
   ```bash
   ssh root@your-server-ip
   ```

2. **Zainstaluj Docker:**
   ```bash
   curl -fsSL https://get.docker.com | sh
   apt install docker-compose-plugin
   ```

3. **Sklonuj repozytorium:**
   ```bash
   git clone https://github.com/twój-user/fin.sankey.git
   cd fin.sankey
   ```

4. **Skonfiguruj sekrety:**
   ```bash
   mkdir -p .streamlit
   cp .streamlit/secrets.toml.example .streamlit/secrets.toml
   nano .streamlit/secrets.toml  # edytuj wartości
   ```

5. **Uruchom:**
   ```bash
   docker compose up -d
   ```

6. **Sprawdź status:**
   ```bash
   docker compose ps
   docker compose logs -f fin-sankey
   ```

### Reverse Proxy (Nginx + SSL)

Dla produkcji zalecany jest reverse proxy z SSL:

```bash
apt install nginx certbot python3-certbot-nginx
```

Konfiguracja Nginx (`/etc/nginx/sites-available/fin-sankey`):
```nginx
server {
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:8501;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_read_timeout 86400;
    }
}
```

Włącz i uzyskaj certyfikat SSL:
```bash
ln -s /etc/nginx/sites-available/fin-sankey /etc/nginx/sites-enabled/
certbot --nginx -d your-domain.com
systemctl restart nginx
```

---

## Zmienne środowiskowe

| Zmienna | Wymagana | Opis |
|---------|----------|------|
| `PERPLEXITY_API_KEY` | Tak* | Klucz API dla raportów AI |
| `SUPABASE_URL` | Tak | URL projektu Supabase |
| `SUPABASE_KEY` | Tak | Klucz anon Supabase |
| `SENDGRID_API_KEY` | Nie | Klucz SendGrid (email) |
| `RESEND_API_KEY` | Nie | Alternatywnie: Resend |
| `SMTP_SERVER` | Nie | Alternatywnie: SMTP |
| `SMTP_PORT` | Nie | Port SMTP (587) |
| `SMTP_USER` | Nie | Użytkownik SMTP |
| `SMTP_PASSWORD` | Nie | Hasło SMTP |
| `REDIS_URL` | Nie | URL Redis dla cache |
| `EMAIL_FROM` | Nie | Adres nadawcy email |
| `EMAIL_FROM_NAME` | Nie | Nazwa nadawcy |

*Wymagane dla funkcji raportów AI

---

## Porównanie platform

| Platforma | Koszt | Redis | Auto-deploy | SSL | Trudność |
|-----------|-------|-------|-------------|-----|----------|
| Streamlit Cloud | Darmowy | - | Tak | Tak | Łatwa |
| Railway | ~$5 | Tak | Tak | Tak | Łatwa |
| Render | Darmowy+ | Tak | Tak | Tak | Łatwa |
| Fly.io | Pay-go | Tak | Tak | Tak | Średnia |
| Heroku | ~$7 | Tak | Tak | Tak | Łatwa |
| VPS | ~$5 | Tak | Nie | Manual | Średnia |

---

## Troubleshooting

### Aplikacja nie startuje
```bash
# Sprawdź logi
docker compose logs fin-sankey

# Sprawdź zmienne środowiskowe
docker compose exec fin-sankey env | grep -E 'SUPABASE|PERPLEXITY'
```

### Błędy połączenia z Supabase
- Sprawdź czy `SUPABASE_URL` zawiera `https://`
- Upewnij się, że używasz klucza `anon`, nie `service_role`

### Redis nie działa
```bash
# Test połączenia
docker compose exec redis redis-cli ping
# Powinno zwrócić: PONG
```

### Health check fails
- Poczekaj 30-60 sekund po starcie
- Sprawdź czy port 8501 jest dostępny
- Sprawdź logi: `docker compose logs -f`

---

## Wsparcie

W razie problemów:
1. Sprawdź logi aplikacji
2. Zweryfikuj zmienne środowiskowe
3. Upewnij się, że wszystkie zewnętrzne usługi (Supabase, API) działają
