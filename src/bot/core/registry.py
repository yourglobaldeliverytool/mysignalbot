"""Registry system for plugins."""

from typing import Type, Dict, Any, Optional, TypeVar, Callable
from abc import ABC


T = TypeVar('T', bound=ABC)


class Registry:
    """Registry for plugins."""
    
    def __init__(self, name: str):
        """Initialize registry."""
        self.name = name
        self._items: Dict[str, Type[T]] = {}
    
    def register(self, name: str) -> Callable:
        """Decorator to register a plugin."""
        def decorator(cls: Type[T]) -> Type[T]:
            self._items[name] = cls
            return cls
        return decorator
    
    def get(self, name: str) -> Optional[Type[T]]:
        """Get a registered plugin by name."""
        return self._items.get(name)
    
    def create(self, name: str, *args, **kwargs) -> Optional[T]:
        """Create an instance of a registered plugin."""
        cls = self.get(name)
        if cls is None:
            return None
        try:
            return cls(*args, **kwargs)
        except Exception as e:
            from bot.core.logger import get_logger
            logger = get_logger(f"{self.name}.{name}")
            logger.error(f"Failed to create instance: {e}")
            return None
    
    def list(self) -> list:
        """List all registered plugins."""
        return list(self._items.keys())
    
    def has(self, name: str) -> bool:
        """Check if a plugin is registered."""
        return name in self._items


class RegistryManager:
    """Manager for multiple registries."""
    
    def __init__(self):
        """Initialize registry manager."""
        self._registries: Dict[str, Registry] = {}
    
    def create_registry(self, name: str) -> Registry:
        """Create a new registry."""
        if name in self._registries:
            return self._registries[name]
        registry = Registry(name)
        self._registries[name] = registry
        return registry
    
    def get_registry(self, name: str) -> Optional[Registry]:
        """Get a registry by name."""
        return self._registries.get(name)
    
    def list_registries(self) -> list:
        """List all registries."""
        return list(self._registries.keys())


# Global registry manager instance
_registry_manager: Optional[RegistryManager] = None


def get_registry_manager() -> RegistryManager:
    """Get global registry manager instance."""
    global _registry_manager
    if _registry_manager is None:
        _registry_manager = RegistryManager()
    return _registry_manager