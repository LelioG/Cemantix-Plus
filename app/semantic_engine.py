"""Couche de compatibilité historique.

Le moteur principal vit désormais dans `app.services.semantic`.
"""

from .services.semantic import SemanticService

__all__ = ["SemanticService"]
