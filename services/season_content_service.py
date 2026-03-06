"""
Season content manifest service.
Provides scalable file activation for seasonal content packs.
"""

import json
import os
from services.season_gate import get_active_season_theme


SERVICE_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(SERVICE_DIR)
MANIFEST_PATH = os.path.join(BASE_DIR, "data", "season_content_manifest.json")


class SeasonContentService:
    def __init__(self):
        self._manifest_cache = None
        self._manifest_mtime = None

    def _load_manifest(self):
        if not os.path.exists(MANIFEST_PATH):
            return {}
        mtime = os.path.getmtime(MANIFEST_PATH)
        if self._manifest_cache is not None and self._manifest_mtime == mtime:
            return self._manifest_cache
        with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
            self._manifest_cache = json.load(f)
        self._manifest_mtime = mtime
        return self._manifest_cache

    def get_active_pack_key(self, session=None):
        manifest = self._load_manifest()
        packs = manifest.get("packs", {})
        active_theme = (get_active_season_theme(session=session) or "").strip().lower()
        for pack_key, pack_cfg in packs.items():
            match_theme = (
                pack_cfg.get("match", {}).get("theme", "")
                .strip()
                .lower()
            )
            if match_theme and match_theme == active_theme:
                return pack_key
        return None

    def get_runtime_signature(self, session=None):
        theme = get_active_season_theme(session=session) or ""
        pack = self.get_active_pack_key(session=session) or "base"
        return f"{theme.strip().lower()}::{pack}"

    def get_files(self, content_type, session=None):
        """
        Return active file list for a content type.
        Types: characters, abilities, mobs, bosses, dungeons, achievements
        """
        manifest = self._load_manifest()
        files = list(manifest.get("default", {}).get(content_type, []))
        pack_key = self.get_active_pack_key(session=session)
        if pack_key:
            pack_cfg = manifest.get("packs", {}).get(pack_key, {})
            files.extend(pack_cfg.get("append", {}).get(content_type, []))
        return files

    def get_enabled_achievement_categories(self, session=None):
        manifest = self._load_manifest()
        categories = list(manifest.get("default", {}).get("achievement_categories", []))
        pack_key = self.get_active_pack_key(session=session)
        if pack_key:
            pack_cfg = manifest.get("packs", {}).get(pack_key, {})
            categories.extend(pack_cfg.get("achievement_categories_add", []))
        # Stable order, unique
        out = []
        seen = set()
        for c in categories:
            cc = (c or "").strip()
            if not cc:
                continue
            if cc in seen:
                continue
            seen.add(cc)
            out.append(cc)
        return out

    def get_all_seasonal_achievement_categories(self):
        """Categories introduced by seasonal packs (not base categories)."""
        manifest = self._load_manifest()
        packs = manifest.get("packs", {})
        cats = []
        for _, pack_cfg in packs.items():
            cats.extend(pack_cfg.get("achievement_categories_add", []))
        return sorted({(c or "").strip().lower() for c in cats if (c or "").strip()})

    def get_inactive_seasonal_achievement_categories(self, session=None):
        """
        Seasonal categories that belong to packs not currently active.
        Achievements in these categories should be hidden.
        """
        manifest = self._load_manifest()
        active_pack = self.get_active_pack_key(session=session)
        packs = manifest.get("packs", {})
        inactive = []
        for pack_key, pack_cfg in packs.items():
            if pack_key == active_pack:
                continue
            inactive.extend(pack_cfg.get("achievement_categories_add", []))
        return sorted({(c or "").strip().lower() for c in inactive if (c or "").strip()})

    def get_active_ui_config(self, session=None):
        manifest = self._load_manifest()
        pack_key = self.get_active_pack_key(session=session)
        if not pack_key:
            return {}
        return manifest.get("packs", {}).get(pack_key, {}).get("ui", {}) or {}


_season_content_service = None


def get_season_content_service():
    global _season_content_service
    if _season_content_service is None:
        _season_content_service = SeasonContentService()
    return _season_content_service
