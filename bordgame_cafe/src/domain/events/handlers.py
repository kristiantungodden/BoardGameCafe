"""Domain event handlers.

This module contains handlers for domain events. These are typically
called by the message bus or event publisher.
"""

from typing import Callable, Dict, Type
from .domain_event import DomainEvent


# Type alias for event handlers
EventHandler = Callable[[DomainEvent], None]


class EventHandlerRegistry:
    """Registry for event handlers."""
    
    def __init__(self) -> None:
        self._handlers: Dict[Type[DomainEvent], list[EventHandler]] = {}
    
    def register(self, event_type: Type[DomainEvent], handler: EventHandler) -> None:
        """Register a handler for an event type."""
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)
    
    def get_handlers(self, event_type: Type[DomainEvent]) -> list[EventHandler]:
        """Get handlers for an event type."""
        return self._handlers.get(event_type, [])
    
    def handle(self, event: DomainEvent) -> None:
        """Handle an event by calling all registered handlers."""
        handlers = self.get_handlers(type(event))
        for handler in handlers:
            handler(event)


# Global event handler registry
event_registry = EventHandlerRegistry()
