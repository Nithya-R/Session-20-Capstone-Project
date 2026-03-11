from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from services.news_service import get_user_sites, add_site, delete_site, get_articles

router = APIRouter(prefix="/news", tags=["news"])


class AddSiteRequest(BaseModel):
    state: str
    name: str
    url: str
    site_id: Optional[str] = None   # provided when re-adding a default


@router.get("/sites/{user_id}")
def news_get_sites(user_id: str):
    """Return user's saved sites, all defaults, and which defaults are still available to add."""
    try:
        return get_user_sites(user_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sites/{user_id}")
def news_add_site(user_id: str, req: AddSiteRequest):
    """Add a news site to the user's list (default or custom)."""
    try:
        return add_site(user_id, req.state, req.name, req.url, req.site_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/sites/{user_id}/{site_id}")
def news_delete_site(user_id: str, site_id: str):
    """Remove a site from the user's list."""
    try:
        return delete_site(user_id, site_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/articles/{site_id}")
async def news_get_articles(site_id: str, url: str, name: str):
    """
    Fetch top-10 political articles for a site (LLM-filtered + translated).
    Polls the site only if last poll was > 24 hours ago.
    """
    try:
        return await get_articles(site_id, url, name)
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
