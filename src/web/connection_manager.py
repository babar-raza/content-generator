"""WebSocket connection manager stub."""

import logging

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Simple connection manager for WebSocket connections."""
    
    def __init__(self):
        self.connections = []
    
    async def broadcast_agents(self, message):
        """Broadcast message to agent status clients."""
        logger.debug(f"Broadcasting to agents: {message}")
    
    async def broadcast_visual(self, message):
        """Broadcast message to visual clients."""
        logger.debug(f"Broadcasting to visual: {message}")


_connection_manager = None


def get_connection_manager():
    """Get or create the connection manager singleton."""
    global _connection_manager
    if _connection_manager is None:
        _connection_manager = ConnectionManager()
    return _connection_manager
