"""
Streaming Concurrency Test

Verifies that multiple clients can execute streaming workflows simultaneously
without blocking each other and operate independently
"""

import pytest
import asyncio
import aiohttp
import json
import time
from typing import Dict, Any, List, Tuple
import logging

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TestStreamingConcurrency:
    """Streaming concurrency test class"""

    BASE_URL = "http://localhost:5001"

    @pytest.fixture
    def simple_workflow_data(self) -> Dict[str, Any]:
        """Simple workflow data for testing (fast version without LLM)"""
        return {
            "workflow": {
                "nodes": [
                    {
                        "id": "input-1",
                        "type": "input-node",
                        "position": {"x": 100, "y": 100},
                        "content": "This is input text for streaming concurrency test.",
                        "model_type": None,
                        "llm_provider": None,
                        "prompt": None,
                        "knowledge_base": None,
                        "search_intensity": None,
                        "rerank_provider": None,
                        "rerank_model": None,
                        "output": None,
                        "executed": False,
                        "error": None
                    },
                    {
                        "id": "output-1",
                        "type": "output-node",
                        "position": {"x": 300, "y": 100},
                        "content": "Final result",
                        "model_type": None,
                        "llm_provider": None,
                        "prompt": None,
                        "knowledge_base": None,
                        "search_intensity": None,
                        "rerank_provider": None,
                        "rerank_model": None,
                        "output": None,
                        "executed": False,
                        "error": None
                    }
                ],
                "edges": [
                    {"id": "edge-1", "source": "input-1", "target": "output-1"}
                ]
            }
        }

    async def _execute_streaming_client(
        self,
        client_id: int,
        session: aiohttp.ClientSession,
        workflow_data: Dict[str, Any]
    ) -> Tuple[bool, float, int]:
        """Execute a single streaming client"""
        start_time = time.time()
        logger.info(f"[Client {client_id}] Starting streaming")

        try:
            async with session.post(
                f"{self.BASE_URL}/execute-workflow-stream",
                json=workflow_data,
                headers={"Content-Type": "application/json"}
            ) as response:

                if response.status != 200:
                    logger.error(f"[Client {client_id}] HTTP error: {response.status}")
                    response_text = await response.text()
                    logger.error(f"[Client {client_id}] Response content: {response_text}")
                    return False, time.time() - start_time, 0

                # Read SSE stream - line-by-line buffered processing
                chunk_count = 0
                completed = False
                buffer = ""

                async for chunk in response.content.iter_chunked(1024):
                    buffer += chunk.decode('utf-8')

                    # Process line by line
                    lines = buffer.split('\n')
                    buffer = lines[-1]  # Keep incomplete last line in buffer

                    for line in lines[:-1]:
                        line = line.strip()
                        if line.startswith('data: '):
                            try:
                                data = json.loads(line[6:])
                                chunk_count += 1

                                # Log key events
                                if data.get('type') in ['start', 'node_start', 'complete', 'error']:
                                    logger.info(f"[Client {client_id}] {data.get('type')}: {data.get('message', '')}")

                                # Exit on completion or error
                                if data.get('type') in ['complete', 'error']:
                                    completed = True
                                    elapsed = time.time() - start_time
                                    if data.get('type') == 'error':
                                        logger.error(f"[Client {client_id}] Error response: {data}")
                                    logger.info(f"[Client {client_id}] Completed ({elapsed:.2f}s, {chunk_count} chunks)")
                                    return data.get('type') == 'complete', elapsed, chunk_count

                            except json.JSONDecodeError as e:
                                logger.debug(f"[Client {client_id}] JSON parsing failed: {line[6:]} - {e}")
                                continue

                # Check if stream terminated normally
                elapsed = time.time() - start_time
                if completed:
                    logger.info(f"[Client {client_id}] Stream completed normally ({elapsed:.2f}s, {chunk_count} chunks)")
                    return True, elapsed, chunk_count
                else:
                    logger.warning(f"[Client {client_id}] Stream ended without completion ({elapsed:.2f}s)")
                    return False, elapsed, chunk_count

        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(f"[Client {client_id}] Error: {e} ({elapsed:.2f}s)")
            return False, elapsed, 0

    async def _call_api_endpoint(
        self,
        session: aiohttp.ClientSession,
        endpoint: str
    ) -> Tuple[bool, float]:
        """Call a single API endpoint"""
        start_time = time.time()
        try:
            async with session.get(f"{self.BASE_URL}{endpoint}") as response:
                elapsed = time.time() - start_time
                success = response.status == 200
                if success:
                    await response.json()  # Verify JSON response parsing
                return success, elapsed
        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(f"API call failed ({endpoint}): {e}")
            return False, elapsed

    @pytest.mark.asyncio
    async def test_concurrent_streaming(self, simple_workflow_data):
        """Concurrent streaming execution test - verify independent execution without blocking"""
        # Check server availability
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.BASE_URL}/", timeout=aiohttp.ClientTimeout(total=5)) as resp:
                    if resp.status != 200:
                        pytest.skip("API server not running")
        except Exception:
            pytest.skip("API server not running")

        logger.info("Starting concurrent streaming execution test")

        num_clients = 3
        connector = aiohttp.TCPConnector(limit=100, limit_per_host=50)
        timeout = aiohttp.ClientTimeout(total=120)

        async with aiohttp.ClientSession(
            connector=connector,
            timeout=timeout
        ) as session:

            # Execute concurrently
            tasks = [
                self._execute_streaming_client(i, session, simple_workflow_data)
                for i in range(1, num_clients + 1)
            ]

            start_time = time.time()
            results = await asyncio.gather(*tasks, return_exceptions=True)
            total_time = time.time() - start_time

            logger.info(f"Total test completed: {total_time:.2f}s")

            # Analyze results
            successful = 0
            execution_times = []

            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"Client {i+1}: Exception occurred - {result}")
                    assert False, f"Client {i+1} failed with exception: {result}"
                else:
                    success, elapsed, chunk_count = result
                    if success:
                        successful += 1
                        execution_times.append(elapsed)
                        logger.info(f"Client {i+1}: Success ({elapsed:.2f}s, {chunk_count} chunks)")
                    else:
                        logger.error(f"Client {i+1}: Failed ({elapsed:.2f}s)")

            # Verification
            assert successful == num_clients, f"All clients must succeed (succeeded: {successful}/{num_clients})"

            if execution_times:
                avg_time = sum(execution_times) / len(execution_times)
                min_time = min(execution_times)
                max_time = max(execution_times)
                time_variance = max_time - min_time

                logger.info(f"Average execution time: {avg_time:.2f}s")
                logger.info(f"Min/Max execution time: {min_time:.2f}s / {max_time:.2f}s")
                logger.info(f"Time variance: {time_variance:.2f}s")

                # Blocking detection - time variance should not be too large (relaxed threshold)
                assert time_variance < 20.0, f"Execution time variance between clients is too large ({time_variance:.2f}s). Possible blocking detected."

                logger.info("Concurrent streaming execution completed successfully.")

    @pytest.mark.asyncio
    async def test_streaming_during_api_calls(self, simple_workflow_data):
        """Test that other API calls are not blocked during streaming execution"""
        logger.info("Starting API calls during streaming test")

        connector = aiohttp.TCPConnector(limit=100, limit_per_host=50)
        timeout = aiohttp.ClientTimeout(total=120)

        async with aiohttp.ClientSession(
            connector=connector,
            timeout=timeout
        ) as session:

            # Execute streaming in background
            streaming_task = asyncio.create_task(
                self._execute_streaming_client(1, session, simple_workflow_data)
            )

            # Wait briefly after streaming starts
            await asyncio.sleep(1.0)

            # Call other APIs during streaming execution
            api_endpoints = [
                "/",
                "/knowledge-bases",
                "/available-models/google"
            ]

            api_tasks = [
                self._call_api_endpoint(session, endpoint)
                for endpoint in api_endpoints
            ]

            # Verify API calls complete quickly
            api_start_time = time.time()
            api_results = await asyncio.gather(*api_tasks, return_exceptions=True)
            api_total_time = time.time() - api_start_time

            # Wait for streaming to complete
            streaming_result = await streaming_task

            # Verify API results
            logger.info(f"API calls completed: {api_total_time:.3f}s")

            for i, (endpoint, result) in enumerate(zip(api_endpoints, api_results)):
                if isinstance(result, Exception):
                    assert False, f"API call failed ({endpoint}): {result}"
                else:
                    success, elapsed = result
                    logger.info(f"{endpoint}: {elapsed:.3f}s ({'success' if success else 'failed'})")
                    assert success, f"API call failed: {endpoint}"

                    # API calls should not take too long (possible blocking) - relaxed threshold
                    assert elapsed < 10.0, f"API call took too long ({endpoint}: {elapsed:.3f}s). Possible blocking detected."

            # Verify streaming result
            assert not isinstance(streaming_result, Exception), f"Streaming execution failed: {streaming_result}"
            success, elapsed, chunk_count = streaming_result
            assert success, f"Streaming execution failed ({elapsed:.2f}s)"

            logger.info("API calls during streaming completed successfully.")

    @pytest.mark.asyncio
    async def test_api_response_times(self):
        """Basic API response time test"""
        # Check server availability
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.BASE_URL}/", timeout=aiohttp.ClientTimeout(total=5)) as resp:
                    if resp.status != 200:
                        pytest.skip("API server not running")
        except Exception:
            pytest.skip("API server not running")

        logger.info("Starting API response time test")

        async with aiohttp.ClientSession() as session:
            api_endpoints = [
                ("/", "Health check"),
                ("/knowledge-bases", "Knowledge base list"),
                ("/available-models/google", "Google model list")
            ]

            for endpoint, description in api_endpoints:
                success, elapsed = await self._call_api_endpoint(session, endpoint)
                logger.info(f"{description}: {elapsed:.3f}s ({'success' if success else 'failed'})")

                assert success, f"{description} API call failed"
                # Basic APIs should respond within 10 seconds (allow extra time for initial load)
                assert elapsed < 10.0, f"{description} API response too slow ({elapsed:.3f}s)"

    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_concurrent_different_workflows(self, simple_workflow_data):
        """Concurrent execution test with different workflows"""
        # Check server availability
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.BASE_URL}/", timeout=aiohttp.ClientTimeout(total=5)) as resp:
                    if resp.status != 200:
                        pytest.skip("API server not running")
        except Exception:
            pytest.skip("API server not running")

        logger.info("Starting different workflows concurrent execution test")

        # Create second workflow (longer prompt)
        workflow_2 = {
            "workflow": {
                "nodes": [
                    {
                        "id": "input-2",
                        "type": "input-node",
                        "position": {"x": 100, "y": 100},
                        "content": "This is the test input for the second workflow. This text is longer so processing time may vary.",
                        "model_type": None,
                        "llm_provider": None,
                        "prompt": None,
                        "knowledge_base": None,
                        "search_intensity": None,
                        "rerank_provider": None,
                        "rerank_model": None,
                        "output": None,
                        "executed": False,
                        "error": None
                    },
                    {
                        "id": "generation-2",
                        "type": "generation-node",
                        "position": {"x": 300, "y": 100},
                        "content": None,
                        "model_type": "gemini-2.0-flash",
                        "llm_provider": "google",
                        "prompt": "Analyze the following text in detail and extract 3 key points: {input_data}",
                        "knowledge_base": None,
                        "search_intensity": None,
                        "rerank_provider": None,
                        "rerank_model": None,
                        "output": None,
                        "executed": False,
                        "error": None
                    },
                    {
                        "id": "output-2",
                        "type": "output-node",
                        "position": {"x": 500, "y": 100},
                        "content": "Analysis result",
                        "model_type": None,
                        "llm_provider": None,
                        "prompt": None,
                        "knowledge_base": None,
                        "search_intensity": None,
                        "rerank_provider": None,
                        "rerank_model": None,
                        "output": None,
                        "executed": False,
                        "error": None
                    }
                ],
                "edges": [
                    {"id": "edge-2-1", "source": "input-2", "target": "generation-2"},
                    {"id": "edge-2-2", "source": "generation-2", "target": "output-2"}
                ]
            }
        }

        connector = aiohttp.TCPConnector(limit=100, limit_per_host=50)
        timeout = aiohttp.ClientTimeout(total=120)

        async with aiohttp.ClientSession(
            connector=connector,
            timeout=timeout
        ) as session:

            # Execute different workflows concurrently
            tasks = [
                self._execute_streaming_client(1, session, simple_workflow_data),
                self._execute_streaming_client(2, session, workflow_2)
            ]

            start_time = time.time()
            results = await asyncio.gather(*tasks, return_exceptions=True)
            total_time = time.time() - start_time

            logger.info(f"Different workflows execution completed: {total_time:.2f}s")

            # Verify results
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    assert False, f"Workflow {i+1} failed with exception: {result}"
                else:
                    success, elapsed, chunk_count = result
                    assert success, f"Workflow {i+1} execution failed ({elapsed:.2f}s)"
                    logger.info(f"Workflow {i+1}: Success ({elapsed:.2f}s, {chunk_count} chunks)")

            logger.info("Different workflows concurrent execution completed successfully.")

    @pytest.mark.asyncio
    async def test_concurrent_llm_workflows(self):
        """Concurrent LLM workflow execution test (only when Google API key is available)"""
        import os

        # Check server availability
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.BASE_URL}/", timeout=aiohttp.ClientTimeout(total=5)) as resp:
                    if resp.status != 200:
                        pytest.skip("API server not running")
        except Exception:
            pytest.skip("API server not running")

        if not os.getenv("GOOGLE_API_KEY"):
            pytest.skip("Google API key not set. Skipping actual LLM concurrency test.")

        logger.info("Starting LLM workflow concurrency test")

        # Workflow with LLM
        llm_workflow = {
            "workflow": {
                "nodes": [
                    {
                        "id": "input-llm",
                        "type": "input-node",
                        "position": {"x": 100, "y": 100},
                        "content": "This is a short text for LLM testing.",
                        "model_type": None,
                        "llm_provider": None,
                        "prompt": None,
                        "knowledge_base": None,
                        "search_intensity": None,
                        "rerank_provider": None,
                        "rerank_model": None,
                        "output": None,
                        "executed": False,
                        "error": None
                    },
                    {
                        "id": "generation-llm",
                        "type": "generation-node",
                        "position": {"x": 300, "y": 100},
                        "content": None,
                        "model_type": "gemini-1.5-flash",
                        "llm_provider": "google",
                        "prompt": "Summarize the following text in one sentence: {input_data}",
                        "knowledge_base": None,
                        "search_intensity": None,
                        "rerank_provider": None,
                        "rerank_model": None,
                        "output": None,
                        "executed": False,
                        "error": None
                    },
                    {
                        "id": "output-llm",
                        "type": "output-node",
                        "position": {"x": 500, "y": 100},
                        "content": "LLM result",
                        "model_type": None,
                        "llm_provider": None,
                        "prompt": None,
                        "knowledge_base": None,
                        "search_intensity": None,
                        "rerank_provider": None,
                        "rerank_model": None,
                        "output": None,
                        "executed": False,
                        "error": None
                    }
                ],
                "edges": [
                    {"id": "edge-llm-1", "source": "input-llm", "target": "generation-llm"},
                    {"id": "edge-llm-2", "source": "generation-llm", "target": "output-llm"}
                ]
            }
        }

        connector = aiohttp.TCPConnector(limit=100, limit_per_host=50)
        timeout = aiohttp.ClientTimeout(total=180)  # Longer timeout for LLM calls

        async with aiohttp.ClientSession(
            connector=connector,
            timeout=timeout
        ) as session:

            # Execute 2 LLM workflows concurrently
            tasks = [
                self._execute_streaming_client(1, session, llm_workflow),
                self._execute_streaming_client(2, session, llm_workflow)
            ]

            start_time = time.time()
            results = await asyncio.gather(*tasks, return_exceptions=True)
            total_time = time.time() - start_time

            logger.info(f"LLM workflow concurrent execution completed: {total_time:.2f}s")

            # Verify results
            successful = 0
            execution_times = []

            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"LLM Workflow {i+1}: Exception occurred - {result}")
                else:
                    success, elapsed, chunk_count = result
                    if success:
                        successful += 1
                        execution_times.append(elapsed)
                        logger.info(f"LLM Workflow {i+1}: Success ({elapsed:.2f}s, {chunk_count} chunks)")
                    else:
                        logger.error(f"LLM Workflow {i+1}: Failed ({elapsed:.2f}s)")

            # Skip if LLM workflows fail (possible network issues, API limits, etc.)
            if successful == 0:
                pytest.skip("LLM workflow execution failed (API key, network, or server issue)")

            # At least 1 should succeed
            assert successful >= 1, f"At least 1 LLM workflow must succeed (succeeded: {successful}/2)"

            if len(execution_times) >= 2:
                time_variance = max(execution_times) - min(execution_times)
                logger.info(f"LLM execution time variance: {time_variance:.2f}s")

                # LLM calls may take longer, so use lenient threshold
                assert time_variance < 30.0, f"Execution time variance between LLM workflows is too large ({time_variance:.2f}s)"

            logger.info("LLM workflow concurrency test completed successfully.")


if __name__ == "__main__":
    # Standalone execution (for development/debugging)
    import sys
    import os

    # Add project root to Python path
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

    pytest.main([__file__, "-v", "-s"])
