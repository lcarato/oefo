"""
OEFO Dashboard Streaming Server

Lightweight HTTP + Server-Sent Events (SSE) server that:
  1. Serves the dashboard HTML on GET /
  2. Streams live pipeline snapshots on GET /stream (text/event-stream)
  3. Serves the latest snapshot on GET /api/snapshot (JSON, for initial load)

The SSE endpoint pushes a fresh snapshot every N seconds (configurable).
The dashboard connects via EventSource and re-renders charts in real time
without any page refresh.

Usage:
    # Default: http://localhost:8787
    python -m oefo.dashboard.server

    # Custom port and interval
    python -m oefo.dashboard.server --port 9000 --interval 10

    # Use sample data (no real pipeline directories needed)
    python -m oefo.dashboard.server --demo
"""

import argparse
import asyncio
import json
import logging
import os
import signal
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, Set

logger = logging.getLogger("oefo.dashboard.server")

# ---------------------------------------------------------------------------
# Snapshot collector — wraps PipelineTracker or demo generator
# ---------------------------------------------------------------------------

class SnapshotCollector:
    """
    Collects pipeline snapshots on a timer and notifies waiting SSE clients.

    In production mode it uses PipelineTracker.collect().
    In demo mode it uses generate_sample_snapshot() with a small random
    perturbation each tick so the dashboard visibly updates.
    """

    def __init__(self, demo: bool = False, base_dir: Optional[str] = None):
        self.demo = demo
        self.base_dir = base_dir
        self._latest: Optional[dict] = None
        self._subscribers: Set[asyncio.Queue] = set()
        self._tick = 0

    def subscribe(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue()
        self._subscribers.add(q)
        return q

    def unsubscribe(self, q: asyncio.Queue):
        self._subscribers.discard(q)

    @property
    def latest_snapshot(self) -> Optional[dict]:
        return self._latest

    async def run(self, interval: float = 5.0):
        """Collect a snapshot every `interval` seconds and push to subscribers."""
        while True:
            try:
                snapshot = self._collect()
                self._latest = snapshot
                payload = json.dumps(snapshot, default=str)
                dead = []
                for q in self._subscribers:
                    try:
                        q.put_nowait(payload)
                    except asyncio.QueueFull:
                        dead.append(q)
                for q in dead:
                    self._subscribers.discard(q)
            except Exception:
                logger.exception("Snapshot collection error")
            await asyncio.sleep(interval)

    def _collect(self) -> dict:
        self._tick += 1
        if self.demo:
            return self._collect_demo()
        return self._collect_real()

    def _collect_real(self) -> dict:
        try:
            from oefo.dashboard.tracker import PipelineTracker
            tracker = PipelineTracker(base_dir=self.base_dir)
            return tracker.collect()
        except Exception as exc:
            logger.warning("PipelineTracker failed, falling back to demo: %s", exc)
            return self._collect_demo()

    def _collect_demo(self) -> dict:
        """Generate sample data with small random perturbations each tick."""
        import random

        # Use a different seed each tick to vary the data
        random.seed(42 + self._tick)

        from oefo.dashboard.tracker import generate_sample_snapshot
        snapshot = generate_sample_snapshot()

        # Apply small perturbations so the dashboard visibly changes
        snapshot["generated_at"] = datetime.utcnow().isoformat() + "Z"
        snapshot["_tick"] = self._tick

        # Slightly vary scraping total
        delta = random.randint(-5, 15)
        snapshot["scraping"]["total_documents"] += self._tick * 2 + delta

        # Slightly vary observation counts
        obs_delta = random.randint(0, 8)
        snapshot["database"]["total_observations"] += self._tick + obs_delta
        snapshot["extraction"]["total_extractions"] += self._tick + obs_delta

        # Shift QC mean score slightly
        snapshot["qc"]["mean_score"] = round(
            snapshot["qc"]["mean_score"] + random.uniform(-0.01, 0.02), 3
        )

        return snapshot


# ---------------------------------------------------------------------------
# Async HTTP server using only the standard library (asyncio)
# ---------------------------------------------------------------------------

class DashboardServer:
    """
    Minimal async HTTP server that serves:
      GET /            → dashboard HTML
      GET /stream      → SSE text/event-stream
      GET /api/snapshot → latest JSON snapshot
      GET /health      → {"status": "ok"}
    """

    def __init__(self, collector: SnapshotCollector, host: str = "0.0.0.0",
                 port: int = 8787):
        self.collector = collector
        self.host = host
        self.port = port
        self._dashboard_html: Optional[str] = None

    def _load_dashboard_html(self) -> str:
        if self._dashboard_html:
            return self._dashboard_html
        html_path = Path(__file__).parent / "index.html"
        if html_path.exists():
            self._dashboard_html = html_path.read_text()
        else:
            self._dashboard_html = "<html><body><h1>Dashboard HTML not found</h1></body></html>"
        return self._dashboard_html

    async def handle_client(self, reader: asyncio.StreamReader,
                            writer: asyncio.StreamWriter):
        try:
            raw = await asyncio.wait_for(reader.readuntil(b"\r\n\r\n"), timeout=10)
            request_line = raw.split(b"\r\n")[0].decode("utf-8", errors="replace")
            parts = request_line.split(" ")
            method = parts[0] if len(parts) > 0 else "GET"
            path = parts[1] if len(parts) > 1 else "/"

            if path == "/stream" and method == "GET":
                await self._handle_sse(writer)
            elif path == "/api/snapshot" and method == "GET":
                await self._handle_json(writer)
            elif path == "/health" and method == "GET":
                await self._send_response(writer, 200, "application/json",
                                          '{"status":"ok"}')
            elif path == "/" and method == "GET":
                html = self._load_dashboard_html()
                await self._send_response(writer, 200, "text/html", html)
            else:
                await self._send_response(writer, 404, "text/plain", "Not Found")
        except (asyncio.TimeoutError, ConnectionResetError, BrokenPipeError):
            pass
        except Exception:
            logger.exception("Error handling request")
        finally:
            try:
                writer.close()
                await writer.wait_closed()
            except Exception:
                pass

    async def _send_response(self, writer: asyncio.StreamWriter,
                             status: int, content_type: str, body: str):
        body_bytes = body.encode("utf-8")
        status_text = {200: "OK", 404: "Not Found", 500: "Internal Server Error"}.get(status, "OK")
        header = (
            f"HTTP/1.1 {status} {status_text}\r\n"
            f"Content-Type: {content_type}; charset=utf-8\r\n"
            f"Content-Length: {len(body_bytes)}\r\n"
            f"Access-Control-Allow-Origin: *\r\n"
            f"Cache-Control: no-cache\r\n"
            f"Connection: close\r\n"
            f"\r\n"
        )
        writer.write(header.encode("utf-8") + body_bytes)
        await writer.drain()

    async def _handle_json(self, writer: asyncio.StreamWriter):
        snapshot = self.collector.latest_snapshot
        if snapshot is None:
            await self._send_response(writer, 200, "application/json",
                                      '{"status":"collecting"}')
            return
        body = json.dumps(snapshot, default=str)
        await self._send_response(writer, 200, "application/json", body)

    async def _handle_sse(self, writer: asyncio.StreamWriter):
        """Stream Server-Sent Events until the client disconnects."""
        header = (
            "HTTP/1.1 200 OK\r\n"
            "Content-Type: text/event-stream\r\n"
            "Cache-Control: no-cache\r\n"
            "Connection: keep-alive\r\n"
            "Access-Control-Allow-Origin: *\r\n"
            "X-Accel-Buffering: no\r\n"
            "\r\n"
        )
        writer.write(header.encode("utf-8"))
        await writer.drain()

        # Send latest snapshot immediately if available
        if self.collector.latest_snapshot:
            initial = json.dumps(self.collector.latest_snapshot, default=str)
            writer.write(f"event: snapshot\ndata: {initial}\n\n".encode("utf-8"))
            await writer.drain()

        # Subscribe to future updates
        queue = self.collector.subscribe()
        try:
            while True:
                try:
                    payload = await asyncio.wait_for(queue.get(), timeout=30)
                    writer.write(f"event: snapshot\ndata: {payload}\n\n".encode("utf-8"))
                    await writer.drain()
                except asyncio.TimeoutError:
                    # Send keepalive comment every 30s
                    writer.write(f": keepalive {datetime.utcnow().isoformat()}\n\n".encode("utf-8"))
                    await writer.drain()
        except (ConnectionResetError, BrokenPipeError, OSError):
            pass
        finally:
            self.collector.unsubscribe(queue)

    async def start(self):
        server = await asyncio.start_server(
            self.handle_client, self.host, self.port
        )
        addr = server.sockets[0].getsockname()
        logger.info("OEFO Dashboard server running at http://%s:%s", addr[0], addr[1])
        print(f"\n{'=' * 60}")
        print(f"  OEFO Pipeline Dashboard — Live Streaming")
        print(f"  http://localhost:{self.port}")
        print(f"  SSE stream:  http://localhost:{self.port}/stream")
        print(f"  JSON API:    http://localhost:{self.port}/api/snapshot")
        print(f"{'=' * 60}\n")
        async with server:
            await server.serve_forever()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="OEFO Dashboard Streaming Server")
    parser.add_argument("--port", type=int, default=8787,
                        help="HTTP port (default: 8787)")
    parser.add_argument("--host", type=str, default="0.0.0.0",
                        help="Bind address (default: 0.0.0.0)")
    parser.add_argument("--interval", type=float, default=5.0,
                        help="Snapshot refresh interval in seconds (default: 5)")
    parser.add_argument("--demo", action="store_true",
                        help="Use sample data (no real pipeline dirs needed)")
    parser.add_argument("--base-dir", type=str, default=None,
                        help="OEFO base directory override")
    parser.add_argument("--log-level", type=str, default="INFO",
                        choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    args = parser.parse_args()

    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )

    collector = SnapshotCollector(demo=args.demo, base_dir=args.base_dir)
    server = DashboardServer(collector, host=args.host, port=args.port)

    async def run():
        # Start collector and server concurrently
        collector_task = asyncio.create_task(collector.run(interval=args.interval))
        server_task = asyncio.create_task(server.start())
        await asyncio.gather(collector_task, server_task)

    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        print("\nShutting down dashboard server.")


if __name__ == "__main__":
    main()
