SITE_URL = "https://crypto-factory-studios.cryptofactorystudios.workers.dev"

# Pages whose canonical + OpenGraph URL are validated directly.
SEO_PAGES = {
    "index.html": "/",
}

# Focused public discovery surface while first-party games are hidden.
# Prompt product pages are appended dynamically by the Cloudflare Worker.
SITEMAP_PATHS = {
    "/",
    "/prompt-factory",
    "/bitshelf",
}

FORBIDDEN_SEO_HOSTS = {
    "https://crypto-factory-studios.cesargp9712.workers.dev",
    "https://crypto-factory-studios.onrender.com",
}
