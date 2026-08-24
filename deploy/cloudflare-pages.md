# Cloudflare split deployment

Use Cloudflare Pages for `frontend/` only. Keep the API on a Python host and large creator game assets in object storage/CDN. Do not upload third-party game archives directly into Pages. A production deployment should use a distinct game-content origin (for example `games.example.com`) from the authenticated portal origin.
