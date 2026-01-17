"""Client pool for managing reusable ClaudeSDKClient instances.

This module implements a fixed-size pool of ClaudeSDKClient instances to optimize
resource utilization and connection reuse across multiple sessions.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Callable, Optional

from claude_agent_sdk import ClaudeSDKClient

logger = logging.getLogger(__name__)


@dataclass
class PoolClient:
    """Wraps a ClaudeSDKClient with pool metadata.

    Attributes:
        client: The underlying ClaudeSDKClient instance
        index: Index of this client in the pool (for tracking/debugging)
        lock: Async lock for serializing access to this pool client
        current_session_id: Session currently using this client (None if available)
        acquisition_count: Total times this client has been acquired from the pool
    """
    client: ClaudeSDKClient
    index: int
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    current_session_id: Optional[str] = None
    acquisition_count: int = 0


class ClientPool:
    """Manages a fixed-size pool of reusable ClaudeSDKClient instances.

    The pool provides efficient client reuse by maintaining a set of pre-connected
    clients that can be acquired and released by sessions. This reduces connection
    overhead and limits resource usage.

    Usage:
        ```python
        pool = ClientPool(
            pool_size=5,
            client_factory=lambda: ClaudeSDKClient(options),
            acquire_timeout=30.0
        )
        await pool.initialize()

        # Acquire a client for a session
        pool_client = await pool.get_client(session_id="session-123")
        try:
            # Use the client
            response = await pool_client.client.send_message("Hello")
        finally:
            # Always release back to pool
            await pool.release_client(session_id="session-123")

        # Cleanup on shutdown
        await pool.cleanup()
        ```
    """

    def __init__(
        self,
        pool_size: int,
        client_factory: Callable[[], ClaudeSDKClient],
        acquire_timeout: float = 30.0
    ) -> None:
        """Initialize the client pool.

        Args:
            pool_size: Number of clients to maintain in the pool
            client_factory: Factory function to create new ClaudeSDKClient instances
            acquire_timeout: Maximum seconds to wait for an available client
        """
        if pool_size <= 0:
            raise ValueError(f"pool_size must be positive, got {pool_size}")

        if acquire_timeout <= 0:
            raise ValueError(f"acquire_timeout must be positive, got {acquire_timeout}")

        self._pool_size = pool_size
        self._client_factory = client_factory
        self._acquire_timeout = acquire_timeout

        self._clients: list[PoolClient] = []
        self._availability_event = asyncio.Event()
        self._total_acquisitions: int = 0
        self._initialized: bool = False

        logger.info(
            f"ClientPool created: pool_size={pool_size}, "
            f"acquire_timeout={acquire_timeout}s"
        )

    async def initialize(self) -> None:
        """Connect all pool clients at startup.

        Creates and connects all clients in the pool. This should be called
        once during application startup before using the pool.

        Raises:
            Exception: If any client fails to connect. All successfully
                connected clients will be disconnected before re-raising.
        """
        if self._initialized:
            logger.warning("ClientPool already initialized, skipping")
            return

        logger.info(f"Initializing client pool with {self._pool_size} clients...")
        connected_clients: list[PoolClient] = []

        try:
            for i in range(self._pool_size):
                client = self._client_factory()
                await client.connect()

                pool_client = PoolClient(client=client, index=i)
                self._clients.append(pool_client)
                connected_clients.append(pool_client)

                logger.debug(f"Connected pool client {i+1}/{self._pool_size}")

            self._initialized = True
            self._availability_event.set()  # All clients are initially available
            logger.info(f"ClientPool initialized successfully with {len(self._clients)} clients")

        except Exception as e:
            # Clean up any clients that were successfully connected
            logger.error(f"Failed to initialize pool: {e}. Cleaning up...")
            for pool_client in connected_clients:
                try:
                    await pool_client.client.disconnect()
                except Exception as disconnect_error:
                    logger.warning(
                        f"Failed to disconnect client during cleanup: {disconnect_error}"
                    )

            self._clients.clear()
            raise

    async def get_client(self, session_id: str) -> PoolClient:
        """Acquire an available client for the specified session.

        Waits until a client becomes available, then acquires it for the session.
        The client's lock is held until release_client() is called.

        Args:
            session_id: Session ID that will use this client

        Returns:
            PoolClient with the client's lock held

        Raises:
            TimeoutError: If no client becomes available within acquire_timeout
            RuntimeError: If pool is not initialized

        Example:
            ```python
            pool_client = await pool.get_client(session_id="my-session")
            try:
                # Use pool_client.client
                await pool_client.client.send_message("Hello")
            finally:
                await pool.release_client(session_id="my-session")
            ```
        """
        if not self._initialized:
            raise RuntimeError("ClientPool not initialized. Call initialize() first.")

        if not session_id:
            raise ValueError("session_id cannot be empty")

        logger.debug(f"Acquiring client for session: {session_id}")

        start_time = asyncio.get_event_loop().time()

        while True:
            # Check for timeout
            elapsed = asyncio.get_event_loop().time() - start_time
            if elapsed >= self._acquire_timeout:
                raise TimeoutError(
                    f"Timeout waiting for available client after {elapsed:.1f}s "
                    f"(session: {session_id})"
                )

            # Try to find an available client
            available_client: Optional[PoolClient] = None
            for pool_client in self._clients:
                if pool_client.current_session_id is None:
                    available_client = pool_client
                    break

            if available_client:
                # Acquire this client's lock
                await available_client.lock.acquire()
                available_client.current_session_id = session_id
                available_client.acquisition_count += 1
                self._total_acquisitions += 1

                logger.info(
                    f"Acquired client for session {session_id} "
                    f"(acquisition #{available_client.acquisition_count}, "
                    f"total pool acquisitions: {self._total_acquisitions})"
                )

                # Check if more clients are available
                if any(c.current_session_id is None for c in self._clients):
                    self._availability_event.set()
                else:
                    self._availability_event.clear()

                return available_client

            # Wait for a client to become available
            try:
                # Calculate remaining timeout
                remaining_timeout = self._acquire_timeout - elapsed
                await asyncio.wait_for(
                    self._availability_event.wait(),
                    timeout=remaining_timeout
                )
            except asyncio.TimeoutError:
                raise TimeoutError(
                    f"Timeout waiting for available client after {self._acquire_timeout}s "
                    f"(session: {session_id})"
                )

    async def release_client(self, session_id: str) -> bool:
        """Release a client back to the pool.

        Finds the client associated with the session and releases it,
        making it available for other sessions.

        Args:
            session_id: Session ID that was using the client

        Returns:
            True if client was found and released, False if session_id
            was not found in the pool

        Example:
            ```python
            try:
                pool_client = await pool.get_client(session_id="my-session")
                # ... use client ...
            finally:
                await pool.release_client(session_id="my-session")
            ```
        """
        if not session_id:
            logger.warning("Attempted to release client with empty session_id")
            return False

        logger.debug(f"Releasing client for session: {session_id}")

        for pool_client in self._clients:
            if pool_client.current_session_id == session_id:
                pool_client.current_session_id = None
                # Only release if the lock is currently held
                if pool_client.lock.locked():
                    pool_client.lock.release()

                # Signal that a client is now available
                self._availability_event.set()

                logger.info(f"Released client for session {session_id}")
                return True

        logger.warning(
            f"No client found for session {session_id} in pool "
            f"(may have already been released or never acquired)"
        )
        return False

    async def cleanup(self) -> None:
        """Disconnect all clients and cleanup pool resources.

        Should be called during application shutdown. Safely disconnects
        all clients even if some disconnections fail.
        """
        if not self._initialized:
            logger.debug("ClientPool not initialized, skipping cleanup")
            return

        logger.info("Cleaning up client pool...")

        # Clear availability event to prevent new acquisitions
        self._availability_event.clear()

        # Disconnect all clients
        for i, pool_client in enumerate(self._clients):
            try:
                # Release lock if held
                if pool_client.lock.locked():
                    pool_client.lock.release()

                await pool_client.client.disconnect()
                logger.debug(f"Disconnected pool client {i+1}/{len(self._clients)}")
            except Exception as e:
                logger.warning(
                    f"Failed to disconnect pool client {i+1}/{len(self._clients)}: {e}"
                )

        self._clients.clear()
        self._initialized = False

        logger.info("ClientPool cleanup complete")

    def get_stats(self) -> dict:
        """Get pool statistics for monitoring.

        Returns:
            Dictionary with pool statistics including:
            - pool_size: Total number of clients in pool
            - available_clients: Number of clients not currently in use
            - busy_clients: Number of clients currently in use
            - total_acquisitions: Total number of times clients have been acquired
            - initialized: Whether the pool has been initialized

        Example:
            ```python
            stats = pool.get_stats()
            print(f"Pool utilization: {stats['busy_clients']}/{stats['pool_size']}")
            ```
        """
        available = sum(1 for c in self._clients if c.current_session_id is None)
        busy = len(self._clients) - available

        return {
            "pool_size": self._pool_size,
            "available_clients": available,
            "busy_clients": busy,
            "total_acquisitions": self._total_acquisitions,
            "initialized": self._initialized,
        }

    def __len__(self) -> int:
        """Return the number of clients in the pool."""
        return len(self._clients)

    def __repr__(self) -> str:
        """Return string representation of the pool."""
        stats = self.get_stats()
        return (
            f"ClientPool(size={stats['pool_size']}, "
            f"available={stats['available_clients']}, "
            f"busy={stats['busy_clients']}, "
            f"initialized={stats['initialized']})"
        )
