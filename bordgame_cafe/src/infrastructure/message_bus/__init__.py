"""Message bus for publishing and subscribing to domain events."""

from typing import Callable, List, Dict, Type
from domain.events import DomainEvent


class MessageBus:
    """Simple message bus for event publishing."""
    
    def __init__(self):
        self._handlers: Dict[Type[DomainEvent], List[Callable]] = {}
    
    def subscribe(self, event_type: Type[DomainEvent], handler: Callable) -> None:
        """Subscribe a handler to an event type."""
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)
    
    def unsubscribe(self, event_type: Type[DomainEvent], handler: Callable) -> None:
        """Unsubscribe a handler from an event type."""
        if event_type in self._handlers:
            self._handlers[event_type].remove(handler)
    
    def publish(self, event: DomainEvent) -> None:
        """Publish an event to all registered handlers."""
        event_type = type(event)
        if event_type in self._handlers:
            for handler in self._handlers[event_type]:
                handler(event)
    
    async def publish_async(self, event: DomainEvent) -> None:
        """Publish an event asynchronously to all registered handlers."""
        event_type = type(event)
        if event_type in self._handlers:
            for handler in self._handlers[event_type]:
                if hasattr(handler, '__await__'):
                    await handler(event)
                else:
                    handler(event)


# Global message bus instance
message_bus = MessageBus()
