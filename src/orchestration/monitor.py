# monitor.py
"""Real-time monitoring dashboard for agent mesh execution.

Shows live progress, event flow, and agent states.
"""

from rich.console import Console
from rich.live import Live
from rich.layout import Layout
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.tree import Tree
from rich.text import Text
import json
import time
from pathlib import Path
from datetime import datetime
from collections import defaultdict, deque
from typing import Dict, List, Optional
import threading

console = Console()


class AgentMeshMonitor:
    """Real-time monitor for agent mesh execution."""
    
    def __init__(self, log_dir: Path):
        self.log_dir = log_dir
        self.event_log = log_dir / "events.jsonl"
        self.app_log = log_dir / "app.log"
        
        # State tracking
        self.events: List[Dict] = []
        self.agent_states: Dict[str, Dict] = defaultdict(lambda: {
            'last_seen': None,
            'status': 'idle',
            'current_task': None,
            'success_count': 0,
            'error_count': 0
        })
        self.correlation_state: Dict[str, Dict] = {}
        self.recent_events = deque(maxlen=20)
        self.event_counts = defaultdict(int)
        
        self.running = True
        self.last_position = 0
    
    def load_events(self):
        """Load new events from log."""
        if not self.event_log.exists():
            return
        
        try:
            with open(self.event_log, 'r') as f:
                f.seek(self.last_position)
                
                for line in f:
                    try:
                        event = json.loads(line)
                        self.events.append(event)
                        self.recent_events.append(event)
                        self.event_counts[event['event_type']] += 1
                        self._update_agent_state(event)
                        self._update_correlation_state(event)
                    except json.JSONDecodeError:
                        continue
                
                self.last_position = f.tell()
        except Exception as e:
            console.print(f"[red]Error loading events: {e}[/red]")
    
    def _update_agent_state(self, event: Dict):
        """Update agent state from event."""
        source = event.get('source_agent', 'unknown')
        event_type = event.get('event_type', '')
        
        self.agent_states[source]['last_seen'] = event.get('timestamp')
        
        # Track execution states
        if 'AGENT_RECV' in event_type or event_type.startswith('execute_'):
            self.agent_states[source]['status'] = 'executing'
            self.agent_states[source]['current_task'] = event_type
        elif 'AGENT_EXEC_SUCCESS' in event_type or event_type.endswith('_written') or event_type.endswith('_generated'):
            self.agent_states[source]['status'] = 'success'
            self.agent_states[source]['success_count'] += 1
            self.agent_states[source]['current_task'] = None
        elif 'AGENT_ERROR' in event_type or 'AGENT_TIMEOUT' in event_type or event_type.endswith('_failed'):
            self.agent_states[source]['status'] = 'error'
            self.agent_states[source]['error_count'] += 1
        elif 'EXEC_START' in event_type:
            self.agent_states[source]['status'] = 'planning'
    
    def _update_correlation_state(self, event: Dict):
        """Track correlation state."""
        cid = event.get('correlation_id')
        if not cid:
            return
        
        if cid not in self.correlation_state:
            self.correlation_state[cid] = {
                'start_time': event.get('timestamp'),
                'events': [],
                'completed': set(),
                'current_topic': None,
                'status': 'running'
            }
        
        state = self.correlation_state[cid]
        state['events'].append(event)
        
        # Track completed capabilities
        data = event.get('data', {})
        if 'completed' in data:
            state['completed'] = set(data['completed'])
        
        if 'topic_slug' in data:
            state['current_topic'] = data['topic_slug']
        
        if event['event_type'] == 'blog_post_complete':
            state['status'] = 'complete'
    
    def create_layout(self) -> Layout:
        """Create dashboard layout."""
        layout = Layout()
        
        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="main"),
            Layout(name="footer", size=8)
        )
        
        layout["main"].split_row(
            Layout(name="left"),
            Layout(name="right")
        )
        
        return layout
    
    def render_header(self) -> Panel:
        """Render header panel."""
        text = Text()
        text.append("🤖 Agent Mesh Monitor", style="bold cyan")
        text.append(" | ", style="dim")
        text.append(f"Events: {len(self.events)}", style="green")
        text.append(" | ", style="dim")
        text.append(f"Agents: {len(self.agent_states)}", style="yellow")
        text.append(" | ", style="dim")
        text.append(f"Active: {sum(1 for s in self.agent_states.values() if s['status'] == 'executing')}", style="magenta")
        
        return Panel(text, style="bold white on blue")
    
    def render_agent_table(self) -> Panel:
        """Render agent status table."""
        table = Table(title="Agent States", expand=True)
        table.add_column("Agent", style="cyan")
        table.add_column("Status", style="yellow")
        table.add_column("Current Task", style="white")
        table.add_column("✓", justify="right", style="green")
        table.add_column("✗", justify="right", style="red")
        
        for agent_id, state in sorted(self.agent_states.items()):
            status_style = {
                'executing': 'yellow',
                'success': 'green',
                'error': 'red',
                'idle': 'dim',
                'planning': 'cyan'
            }.get(state['status'], 'white')
            
            status_emoji = {
                'executing': '⚙️',
                'success': '✅',
                'error': '❌',
                'idle': '💤',
                'planning': '🧠'
            }.get(state['status'], '❓')
            
            task = state['current_task'] or '-'
            if len(task) > 30:
                task = task[:27] + '...'
            
            table.add_row(
                agent_id[:25],
                f"{status_emoji} {state['status']}",
                task,
                str(state['success_count']),
                str(state['error_count'])
            )
        
        return Panel(table, border_style=status_style)
    
    def render_event_flow(self) -> Panel:
        """Render recent event flow."""
        tree = Tree("📊 Recent Events")
        
        for event in list(self.recent_events)[-10:]:
            event_type = event['event_type']
            source = event['source_agent'][:20]
            timestamp = event['timestamp'].split('T')[1][:8]
            
            # Color code by type
            if 'error' in event_type.lower() or 'fail' in event_type.lower():
                style = "red"
                icon = "❌"
            elif 'success' in event_type.lower() or event_type.endswith('_written') or event_type.endswith('_generated'):
                style = "green"
                icon = "✅"
            elif event_type.startswith('execute_'):
                style = "yellow"
                icon = "⚙️"
            else:
                style = "cyan"
                icon = "📝"
            
            tree.add(f"[{style}]{icon} [{timestamp}] {source} → {event_type}[/{style}]")
        
        return Panel(tree, title="Event Flow", border_style="cyan")
    
    def render_pipeline_progress(self) -> Panel:
        """Render pipeline progress."""
        # Get active correlation
        active_cid = None
        for cid, state in self.correlation_state.items():
            if state['status'] == 'running':
                active_cid = cid
                break
        
        if not active_cid:
            return Panel("No active pipeline", border_style="dim")
        
        state = self.correlation_state[active_cid]
        
        # Pipeline stages
        stages = [
            "ingest_kb", "identify_blog_topics", "check_duplication",
            "gather_rag_kb", "create_outline", "write_introduction",
            "write_sections", "write_conclusion", "generate_supplementary",
            "assemble_content", "generate_code", "validate_code",
            "generate_seo", "inject_keywords", "add_frontmatter", "write_file"
        ]
        
        table = Table(title=f"Pipeline Progress - {state['current_topic'] or 'Starting...'}", expand=True)
        table.add_column("Stage", style="cyan")
        table.add_column("Status", style="yellow")
        
        completed = state['completed']
        
        for stage in stages:
            if stage in completed:
                status = "✅ Complete"
                style = "green"
            else:
                status = "⏳ Pending"
                style = "dim"
            
            table.add_row(stage, f"[{style}]{status}[/{style}]")
        
        progress_pct = int((len(completed) / len(stages)) * 100)
        
        return Panel(table, subtitle=f"Progress: {progress_pct}%", border_style="yellow")
    
    def render_footer(self) -> Panel:
        """Render footer with stats."""
        table = Table.grid(expand=True)
        table.add_column(justify="left")
        table.add_column(justify="center")
        table.add_column(justify="right")
        
        # Top event types
        top_events = sorted(self.event_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        top_events_str = " | ".join([f"{et}: {count}" for et, count in top_events])
        
        table.add_row(
            f"📈 Top Events: {top_events_str}",
            f"⏱️  Runtime: {self._get_runtime()}",
            f"🔄 Refresh: Auto (1s)"
        )
        
        return Panel(table, style="dim")
    
    def _get_runtime(self) -> str:
        """Calculate runtime from first event."""
        if not self.events:
            return "0s"
        
        try:
            start = datetime.fromisoformat(self.events[0]['timestamp'].replace('Z', '+00:00'))
            now = datetime.now(start.tzinfo)
            delta = now - start
            
            hours = int(delta.total_seconds() // 3600)
            minutes = int((delta.total_seconds() % 3600) // 60)
            seconds = int(delta.total_seconds() % 60)
            
            if hours > 0:
                return f"{hours}h {minutes}m {seconds}s"
            elif minutes > 0:
                return f"{minutes}m {seconds}s"
            else:
                return f"{seconds}s"
        except:
            return "N/A"
    
    def render(self) -> Layout:
        """Render full dashboard."""
        layout = self.create_layout()
        
        layout["header"].update(self.render_header())
        layout["left"].update(self.render_agent_table())
        layout["right"].split_column(
            Layout(self.render_event_flow()),
            Layout(self.render_pipeline_progress())
        )
        layout["footer"].update(self.render_footer())
        
        return layout
    
    def run(self):
        """Run live monitor."""
        console.print("[bold green]Starting Agent Mesh Monitor...[/bold green]")
        console.print(f"[dim]Watching: {self.event_log}[/dim]\n")
        
        with Live(self.render(), refresh_per_second=1, console=console) as live:
            while self.running:
                self.load_events()
                live.update(self.render())
                time.sleep(1)
    
    def stop(self):
        """Stop monitor."""
        self.running = False


def main():
    """Main entry point."""
    import sys
    from pathlib import Path
    
    log_dir = Path("./logs")
    
    if len(sys.argv) > 1:
        log_dir = Path(sys.argv[1])
    
    if not log_dir.exists():
        console.print(f"[red]Log directory not found: {log_dir}[/red]")
        console.print("[yellow]Usage: python monitor.py [log_dir][/yellow]")
        return
    
    monitor = AgentMeshMonitor(log_dir)
    
    try:
        monitor.run()
    except KeyboardInterrupt:
        console.print("\n[yellow]Stopping monitor...[/yellow]")
        monitor.stop()


if __name__ == "__main__":
    main()