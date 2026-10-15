"""Serve the built frontend (frontend/dist) in production."""

from starlette.responses import Response
from starlette.staticfiles import StaticFiles
from starlette.types import Scope

# Must always be revalidated so tablets pick up new deploys promptly.
NO_CACHE = {"index.html", "sw.js", "registerSW.js", "manifest.webmanifest"}


class FrontendFiles(StaticFiles):
    """StaticFiles with cache headers suited to a Vite + service-worker build."""

    async def get_response(self, path: str, scope: Scope) -> Response:
        response = await super().get_response(path, scope)
        name = path.rsplit("/", 1)[-1] or "index.html"
        if path.startswith("assets/"):
            # Vite puts a content hash in these filenames, so they never change.
            response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
        elif name in NO_CACHE or path in ("", "."):
            response.headers["Cache-Control"] = "no-cache"
        return response
