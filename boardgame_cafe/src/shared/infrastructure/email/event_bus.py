# Event bus som håndterer publisering av domenehendelser og distribuerer dem til registrerte event handlers.

class EventBus:
    """Simple synchronous event bus for domain events."""
    
    def __init__(self):
        self._handlers = {}
    
    def subscribe(self, event_type, handler):
        """Subscribe a handler to an event type."""
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)
    
    def publish(self, event):
        """Publish an event to all subscribed handlers."""
        event_type = type(event)
        if event_type in self._handlers:
            for handler in self._handlers[event_type]:
                try:
                    handler(event)
                except Exception as e:
                    # Log error but don't stop other handlers
                    print(f"Error in event handler for {event_type.__name__}: {e}")