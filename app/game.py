"""Couche de compatibilité historique.

Le moteur principal vit désormais dans `app.services.game_service`.
"""

from .services.game_service import GameService

__all__ = ["GameService"]
