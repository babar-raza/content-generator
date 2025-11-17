"""
MCP Traffic Logger for monitoring and debugging inter-agent communication.

Logs all MCP protocol messages (requests and responses) with minimal overhead.
Stores traffic in SQLite with configurable retention and provides filtering/export.
"""

import json
import sqlite3
import logging
import time
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from threading import Lock

logger = logging.getLogger(__name__)


@dataclass
class MCPMessage:
    """Represents an MCP message (request/response pair)."""
    id: str
    timestamp: str
    message_type: str  # invoke, query, response
    from_agent: str
    to_agent: str
    request: Dict[str, Any]
    response: Optional[Dict[str, Any]] = None
    status: Optional[str] = None  # success, error, timeout
    duration_ms: Optional[float] = None
    error: Optional[str] = None


class MCPTrafficLogger:
    """Logs and stores MCP traffic for monitoring and debugging."""
    
    def __init__(self, db_path: str = ".mcp_traffic.db", retention_days: int = 7):
        """Initialize the traffic logger.
        
        Args:
            db_path: Path to SQLite database
            retention_days: Number of days to retain traffic data
        """
        self.db_path = db_path
        self.retention_days = retention_days
        self._lock = Lock()
        self._init_db()
    
    def _init_db(self):
        """Initialize SQLite database for traffic storage."""
        try:
            conn = sqlite3.connect(self.db_path, check_same_thread=False)
            cursor = conn.cursor()
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS mcp_traffic (
                    id TEXT PRIMARY KEY,
                    timestamp TEXT NOT NULL,
                    message_type TEXT NOT NULL,
                    from_agent TEXT NOT NULL,
                    to_agent TEXT NOT NULL,
                    request TEXT NOT NULL,
                    response TEXT,
                    status TEXT,
                    duration_ms REAL,
                    error TEXT
                )
            ''')
            
            # Create indexes for efficient querying
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_timestamp ON mcp_traffic(timestamp)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_from_agent ON mcp_traffic(from_agent)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_to_agent ON mcp_traffic(to_agent)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_status ON mcp_traffic(status)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_message_type ON mcp_traffic(message_type)')
            
            conn.commit()
            conn.close()
            logger.info(f"MCP traffic logger initialized: db={self.db_path}, retention={self.retention_days} days")
        except Exception as e:
            logger.error(f"Failed to initialize MCP traffic database: {e}")
    
    def log_request(
        self,
        message_id: str,
        message_type: str,
        from_agent: str,
        to_agent: str,
        request: Dict[str, Any]
    ) -> None:
        """Log MCP request.
        
        Args:
            message_id: Unique message identifier
            message_type: Type of message (invoke, query, etc.)
            from_agent: Source agent ID
            to_agent: Target agent ID
            request: Request payload
        """
        try:
            with self._lock:
                message = MCPMessage(
                    id=message_id,
                    timestamp=datetime.now().isoformat(),
                    message_type=message_type,
                    from_agent=from_agent,
                    to_agent=to_agent,
                    request=request
                )
                
                conn = sqlite3.connect(self.db_path, check_same_thread=False)
                cursor = conn.cursor()
                
                cursor.execute('''
                    INSERT INTO mcp_traffic 
                    (id, timestamp, message_type, from_agent, to_agent, request)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    message.id,
                    message.timestamp,
                    message.message_type,
                    message.from_agent,
                    message.to_agent,
                    json.dumps(message.request)
                ))
                
                conn.commit()
                conn.close()
        except Exception as e:
            logger.error(f"Failed to log MCP request: {e}")
    
    def log_response(
        self,
        message_id: str,
        response: Dict[str, Any],
        status: str,
        duration_ms: float,
        error: Optional[str] = None
    ) -> None:
        """Log MCP response.
        
        Args:
            message_id: Message identifier matching the request
            response: Response payload
            status: Response status (success, error, timeout)
            duration_ms: Request duration in milliseconds
            error: Error message if status is error
        """
        try:
            with self._lock:
                conn = sqlite3.connect(self.db_path, check_same_thread=False)
                cursor = conn.cursor()
                
                cursor.execute('''
                    UPDATE mcp_traffic
                    SET response = ?, status = ?, duration_ms = ?, error = ?
                    WHERE id = ?
                ''', (
                    json.dumps(response),
                    status,
                    duration_ms,
                    error,
                    message_id
                ))
                
                conn.commit()
                conn.close()
        except Exception as e:
            logger.error(f"Failed to log MCP response: {e}")
    
    def get_traffic(
        self,
        limit: int = 100,
        offset: int = 0,
        agent_id: Optional[str] = None,
        message_type: Optional[str] = None,
        status: Optional[str] = None,
        after: Optional[datetime] = None,
        before: Optional[datetime] = None
    ) -> List[MCPMessage]:
        """Retrieve traffic with filtering.
        
        Args:
            limit: Maximum number of messages to return
            offset: Number of messages to skip
            agent_id: Filter by agent ID (matches from_agent or to_agent)
            message_type: Filter by message type
            status: Filter by status
            after: Filter messages after this timestamp
            before: Filter messages before this timestamp
            
        Returns:
            List of MCP messages
        """
        try:
            conn = sqlite3.connect(self.db_path, check_same_thread=False)
            cursor = conn.cursor()
            
            query = 'SELECT * FROM mcp_traffic WHERE 1=1'
            params = []
            
            if agent_id:
                query += ' AND (from_agent = ? OR to_agent = ?)'
                params.extend([agent_id, agent_id])
            
            if message_type:
                query += ' AND message_type = ?'
                params.append(message_type)
            
            if status:
                query += ' AND status = ?'
                params.append(status)
            
            if after:
                query += ' AND timestamp >= ?'
                params.append(after.isoformat())
            
            if before:
                query += ' AND timestamp <= ?'
                params.append(before.isoformat())
            
            query += ' ORDER BY timestamp DESC LIMIT ? OFFSET ?'
            params.extend([limit, offset])
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            conn.close()
            
            messages = []
            for row in rows:
                messages.append(MCPMessage(
                    id=row[0],
                    timestamp=row[1],
                    message_type=row[2],
                    from_agent=row[3],
                    to_agent=row[4],
                    request=json.loads(row[5]) if row[5] else {},
                    response=json.loads(row[6]) if row[6] else None,
                    status=row[7],
                    duration_ms=row[8],
                    error=row[9]
                ))
            
            return messages
        except Exception as e:
            logger.error(f"Failed to retrieve MCP traffic: {e}")
            return []
    
    def get_message(self, message_id: str) -> Optional[MCPMessage]:
        """Get a specific message by ID.
        
        Args:
            message_id: Message identifier
            
        Returns:
            MCPMessage or None if not found
        """
        try:
            conn = sqlite3.connect(self.db_path, check_same_thread=False)
            cursor = conn.cursor()
            
            cursor.execute('SELECT * FROM mcp_traffic WHERE id = ?', (message_id,))
            row = cursor.fetchone()
            conn.close()
            
            if row:
                return MCPMessage(
                    id=row[0],
                    timestamp=row[1],
                    message_type=row[2],
                    from_agent=row[3],
                    to_agent=row[4],
                    request=json.loads(row[5]) if row[5] else {},
                    response=json.loads(row[6]) if row[6] else None,
                    status=row[7],
                    duration_ms=row[8],
                    error=row[9]
                )
            return None
        except Exception as e:
            logger.error(f"Failed to get message {message_id}: {e}")
            return None
    
    def get_metrics(
        self,
        after: Optional[datetime] = None,
        before: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Get traffic metrics.
        
        Args:
            after: Calculate metrics after this timestamp
            before: Calculate metrics before this timestamp
            
        Returns:
            Dictionary of metrics
        """
        try:
            conn = sqlite3.connect(self.db_path, check_same_thread=False)
            cursor = conn.cursor()
            
            where_clause = ''
            params = []
            
            if after or before:
                conditions = []
                if after:
                    conditions.append('timestamp >= ?')
                    params.append(after.isoformat())
                if before:
                    conditions.append('timestamp <= ?')
                    params.append(before.isoformat())
                where_clause = ' WHERE ' + ' AND '.join(conditions)
            
            # Total messages
            cursor.execute(f'SELECT COUNT(*) FROM mcp_traffic{where_clause}', params)
            total_messages = cursor.fetchone()[0]
            
            # Average latency
            cursor.execute(
                f'SELECT AVG(duration_ms) FROM mcp_traffic{where_clause} AND duration_ms IS NOT NULL',
                params
            )
            avg_latency = cursor.fetchone()[0] or 0
            
            # Error rate
            error_params = params + ['error']
            cursor.execute(
                f"SELECT COUNT(*) FROM mcp_traffic{where_clause}{' AND' if where_clause else ' WHERE'} status = ?",
                error_params
            )
            error_count = cursor.fetchone()[0]
            error_rate = (error_count / total_messages * 100) if total_messages > 0 else 0
            
            # Messages by agent
            cursor.execute(f'''
                SELECT from_agent, COUNT(*) 
                FROM mcp_traffic{where_clause}
                GROUP BY from_agent
                ORDER BY COUNT(*) DESC
                LIMIT 10
            ''', params)
            top_agents = dict(cursor.fetchall())
            
            # Messages by type
            cursor.execute(f'''
                SELECT message_type, COUNT(*) 
                FROM mcp_traffic{where_clause}
                GROUP BY message_type
            ''', params)
            by_type = dict(cursor.fetchall())
            
            conn.close()
            
            return {
                'total_messages': total_messages,
                'avg_latency_ms': round(avg_latency, 2),
                'error_rate': round(error_rate, 2),
                'error_count': error_count,
                'top_agents': top_agents,
                'by_type': by_type
            }
        except Exception as e:
            logger.error(f"Failed to get MCP metrics: {e}")
            return {
                'total_messages': 0,
                'avg_latency_ms': 0,
                'error_rate': 0,
                'error_count': 0,
                'top_agents': {},
                'by_type': {}
            }
    
    def cleanup_old(self) -> int:
        """Remove traffic older than retention period.
        
        Returns:
            Number of records deleted
        """
        try:
            cutoff = datetime.now() - timedelta(days=self.retention_days)
            
            with self._lock:
                conn = sqlite3.connect(self.db_path, check_same_thread=False)
                cursor = conn.cursor()
                
                cursor.execute(
                    'DELETE FROM mcp_traffic WHERE timestamp < ?',
                    (cutoff.isoformat(),)
                )
                
                deleted = cursor.rowcount
                conn.commit()
                conn.close()
                
                if deleted > 0:
                    logger.info(f"Cleaned up {deleted} old MCP traffic records")
                return deleted
        except Exception as e:
            logger.error(f"Failed to cleanup old traffic: {e}")
            return 0
    
    def export_traffic(
        self,
        format: str = 'json',
        **filters
    ) -> str:
        """Export traffic to JSON or CSV.
        
        Args:
            format: Export format ('json' or 'csv')
            **filters: Filters to apply (passed to get_traffic)
            
        Returns:
            Exported data as string
        """
        try:
            messages = self.get_traffic(limit=10000, **filters)
            
            if format == 'json':
                return json.dumps([asdict(m) for m in messages], indent=2)
            
            elif format == 'csv':
                import csv
                import io
                
                output = io.StringIO()
                writer = csv.DictWriter(
                    output,
                    fieldnames=['id', 'timestamp', 'from_agent', 'to_agent', 
                               'message_type', 'status', 'duration_ms', 'error']
                )
                writer.writeheader()
                for msg in messages:
                    writer.writerow({
                        'id': msg.id,
                        'timestamp': msg.timestamp,
                        'from_agent': msg.from_agent,
                        'to_agent': msg.to_agent,
                        'message_type': msg.message_type,
                        'status': msg.status or '',
                        'duration_ms': msg.duration_ms or '',
                        'error': msg.error or ''
                    })
                
                return output.getvalue()
            
            else:
                raise ValueError(f"Unsupported format: {format}")
        except Exception as e:
            logger.error(f"Failed to export traffic: {e}")
            return ""


# Global logger instance
_traffic_logger: Optional[MCPTrafficLogger] = None
_logger_lock = Lock()


def get_traffic_logger() -> MCPTrafficLogger:
    """Get global traffic logger instance (singleton).
    
    Returns:
        MCPTrafficLogger instance
    """
    global _traffic_logger
    with _logger_lock:
        if _traffic_logger is None:
            try:
                from src.core.config import Config
                config = Config.load()
                retention_days = config.get('mcp.traffic_retention_days', 7)
                _traffic_logger = MCPTrafficLogger(retention_days=retention_days)
            except Exception as e:
                logger.warning(f"Failed to load config for traffic logger, using defaults: {e}")
                _traffic_logger = MCPTrafficLogger()
        return _traffic_logger


def set_traffic_logger(logger_instance: MCPTrafficLogger) -> None:
    """Set global traffic logger instance (for testing).
    
    Args:
        logger_instance: MCPTrafficLogger instance
    """
    global _traffic_logger
    with _logger_lock:
        _traffic_logger = logger_instance
