"""
Node execution engine - Dependency resolution and parallel execution based on project_reference.md
"""

import asyncio
import time
import logging
from typing import Dict, List, Set, Optional, AsyncGenerator
from collections import defaultdict, deque

from ..models import (
    WorkflowDefinition, WorkflowNode, WorkflowEdge, NodeType,
    NodeExecutionResult, WorkflowExecutionResponse
)
from ..api.node_executors import NodeExecutor
from ..config import NODE_EXECUTION_CONFIG


# Logger setup
logger = logging.getLogger(__name__)

class NodeExecutionEngine:
    """
    Node-based workflow execution engine

    Execution algorithm from project_reference.md:
    1. Find all input-nodes and add to execution queue
    2. Execute nodes in parallel if they have no pre-nodes or all pre-nodes are completed
    3. Register post-nodes of completed nodes to the queue
    4. Repeat until queue is empty
    """
    
    def __init__(self):
        self.execution_queue: Set[str] = set()
        self.completed_nodes: Set[str] = set()
        self.node_outputs: Dict[str, str] = {}
        self.execution_results: List[NodeExecutionResult] = []
        self.execution_order: List[str] = []  # Track execution order
        self.is_stopping: bool = False  # Stop flag
        self.stop_logged: bool = False  # Flag to prevent duplicate stop logs

        # Create node executor
        self.node_executor = NodeExecutor()
    
    async def _collect_stream_output(self, stream_queue: asyncio.Queue, expected_completions: int) -> List[Dict]:
        """Helper method to collect streaming output"""
        outputs = []
        completed_count = 0
        
        while completed_count < expected_completions:
            try:
                chunk = await asyncio.wait_for(
                    stream_queue.get(), 
                    timeout=NODE_EXECUTION_CONFIG["stream_timeout"]
                )
                
                if chunk["type"] == "_stream_complete":
                    break
                    
                outputs.append(chunk)
                
                if chunk["type"] == "node_complete":
                    completed_count += 1
                    
            except asyncio.TimeoutError:
                # Log timeout and continue
                logger.warning(f"Stream timeout waiting for completion ({completed_count}/{expected_completions})")
                break
        
        return outputs
    
    async def _execute_single_node_stream(
        self,
        node: WorkflowNode,
        workflow: WorkflowDefinition,
        stream_queue: asyncio.Queue
    ):
        """Execute a single node and send streaming output to queue in real-time"""
        
        accumulated_output = ""
        final_result = None
        try:
            # Process streaming output
            async for chunk in self._execute_node_stream(node, workflow):
                if chunk["type"] == "stream":
                    accumulated_output += chunk["content"]
                    # Send streaming output immediately
                    await stream_queue.put({
                        "type": "stream",
                        "node_id": node.id,
                        "content": chunk["content"]
                    })
                elif chunk["type"] == "result":
                    final_result = chunk
                elif chunk["type"] == "parsed_result":
                    final_result = chunk

            # Process node execution result
            if final_result and final_result.get("success") != False:
                # Success case
                if "output" in final_result:
                    output_value = final_result.get("output")
                elif "result" in final_result:
                    output_value = final_result.get("result")
                else:
                    output_value = accumulated_output
                    
                # Use accumulated_output if output_value is None
                if output_value is None:
                    output_value = accumulated_output
                    
                description_value = final_result.get("description", "") or accumulated_output
                    
                self.node_outputs[node.id] = output_value
                self.execution_results.append(NodeExecutionResult(
                    node_id=node.id,
                    success=True,
                    output=output_value,
                    description=description_value,
                    raw_response=accumulated_output or final_result.get("description", ""),
                    execution_time=final_result.get("execution_time", 0.0)
                ))
                
                # Send completion notification immediately
                await stream_queue.put({
                    "type": "node_complete",
                    "node_id": node.id,
                    "success": True,
                    "description": description_value,
                    "execution_time": final_result.get("execution_time", 0.0),
                    "message": f"{node.type} node execution completed"
                })
            else:
                # Failure case
                error_msg = final_result.get("error", "Unknown error") if final_result else "No result"
                description = final_result.get("description", str(error_msg)) if final_result else str(error_msg)
                
                self.execution_results.append(NodeExecutionResult(
                    node_id=node.id,
                    success=False,
                    output=None,
                    description=description,
                    error=error_msg,
                    raw_response=accumulated_output,
                    execution_time=final_result.get("execution_time", 0.0) if final_result else 0.0
                ))
                
                # Send failure notification immediately
                await stream_queue.put({
                    "type": "node_complete",
                    "node_id": node.id,
                    "success": False,
                    "error": error_msg,
                    "description": description,
                    "execution_time": final_result.get("execution_time", 0.0) if final_result else 0.0
                })
 
        except Exception as e:
            # Handle exception
            await stream_queue.put({
                "type": "node_complete",
                "node_id": node.id,
                "success": False,
                "error": str(e),
                "execution_time": 0.0
            })
    
    async def execute_workflow(
        self,
        workflow: WorkflowDefinition
    ) -> WorkflowExecutionResponse:
        """Execute entire workflow (non-streaming)"""

        # Use streaming execution but only collect results
        results = []
        async for event in self.execute_workflow_stream(workflow):
            if event["type"] == "final_result":
                return event["result"]
        
        # Fallback (normally unreachable)
        return WorkflowExecutionResponse(
            success=False,
            results=[],
            error="Workflow execution completed without final result"
        )
    
    def _reset_state(self):
        """Reset execution state"""
        self.execution_queue.clear()
        self.completed_nodes.clear()
        self.node_outputs.clear()
        self.execution_results.clear()
        self.execution_order.clear()  # Reset execution order
        self.workflow_nodes = []  # Reset workflow nodes
    
    def _build_dependency_graph(self, workflow: WorkflowDefinition) -> Dict[str, List[str]]:
        """Build dependency graph (map each node's pre-nodes)"""
        pre_nodes_map = defaultdict(list)
        
        for edge in workflow.edges:
            pre_nodes_map[edge.target].append(edge.source)
        
        # Create empty list for all nodes
        for node in workflow.nodes:
            if node.id not in pre_nodes_map:
                pre_nodes_map[node.id] = []
        return dict(pre_nodes_map)
    
    def _build_post_nodes_map(self, workflow: WorkflowDefinition) -> Dict[str, List[str]]:
        """Map each node's post-nodes"""
        post_nodes_map = defaultdict(list)
        
        for edge in workflow.edges:
            post_nodes_map[edge.source].append(edge.target)
        
        return dict(post_nodes_map)
    
    def _find_ready_nodes(self, pre_nodes_map: Dict[str, List[str]]) -> List[str]:
        """Find nodes ready for execution (all pre-nodes completed)"""
        ready_nodes = []
        
        logger.info(f"Finding ready nodes from queue: {list(self.execution_queue)}")
        logger.info(f"Completed nodes: {list(self.completed_nodes)}")
        
        for node_id in self.execution_queue:
            pre_nodes = pre_nodes_map.get(node_id, [])
            logger.info(f"Node {node_id} has pre_nodes: {pre_nodes}")
            
            # Ready if no pre-nodes or all pre-nodes are completed
            if not pre_nodes or all(pre_id in self.completed_nodes for pre_id in pre_nodes):
                ready_nodes.append(node_id)
                logger.info(f"Node {node_id} is ready for execution")
            else:
                missing_pre_nodes = [pre_id for pre_id in pre_nodes if pre_id not in self.completed_nodes]
                logger.info(f"Node {node_id} waiting for pre_nodes: {missing_pre_nodes}")
        
        return ready_nodes
    
    def _get_final_output(self, workflow: WorkflowDefinition) -> Optional[str]:
        """Get final output result (from output-node)"""
        output_nodes = [node for node in workflow.nodes if node.type == "output-node"]
        
        if output_nodes:
            output_node_id = output_nodes[0].id
            return self.node_outputs.get(output_node_id)
        
        return None
    
    async def execute_workflow_stream(
        self,
        workflow: WorkflowDefinition
    ):
        """Event-based parallel streaming workflow execution - proceed to next step as soon as each node completes"""

        start_time = time.time()

        try:
            # Initialize
            self._reset_state()

            # Store workflow nodes (for context-node distinction)
            self.workflow_nodes = workflow.nodes

            # Streaming start notification
            yield {
                "type": "start",
                "message": "Starting event-based workflow execution.",
                "total_nodes": len(workflow.nodes)
            }

            # Build dependency graph
            pre_nodes_map = self._build_dependency_graph(workflow)
            node_lookup = {node.id: node for node in workflow.nodes}

            # Queue for overall streaming output
            global_stream_queue = asyncio.Queue()

            # Track active node tasks
            active_tasks = {}

            # Start input-nodes first
            for node in workflow.nodes:
                if node.type == "input-node":
                    # Send node start notification first
                    yield {
                        "type": "node_start",
                        "node_id": node.id,
                        "node_type": node.type,
                        "message": f"{node.type} node execution started"
                    }
                    
                    task = asyncio.create_task(
                        self._execute_single_node_stream(
                            node, workflow, global_stream_queue
                        )
                    )
                    active_tasks[node.id] = task
            
            # Track total node completions
            total_completed = 0
            total_nodes = len(workflow.nodes)

            # Event-based execution loop
            while total_completed < total_nodes:
                # Check stop request - verify immediately at loop start
                if self.is_stopping:
                    if not self.stop_logged:
                        logger.info("Workflow execution stopped by user request")
                        self.stop_logged = True
                        yield {
                            "type": "stop_requested",
                            "message": "Workflow stop requested. Will stop after currently running nodes complete."
                        }

                    # Stop immediately if no active tasks
                    if not active_tasks:
                        logger.info("Workflow execution stopping - no active tasks")
                        break
                
                # Process streaming output
                try:
                    chunk = await asyncio.wait_for(global_stream_queue.get(), timeout=0.1)
                    yield chunk
                    
                    # Handle node completion event
                    if chunk["type"] == "node_complete" and chunk["success"]:
                        completed_node_id = chunk["node_id"]
                        total_completed += 1

                        # Add completed node to completed_nodes
                        self.completed_nodes.add(completed_node_id)
                        self.execution_order.append(completed_node_id)

                        # Remove completed node from active_tasks
                        if completed_node_id in active_tasks:
                            del active_tasks[completed_node_id]

                        # If stop requested, don't start new nodes and continue loop
                        if self.is_stopping:
                            if not active_tasks:
                                logger.info("Workflow execution stopping - all active tasks completed")
                                break
                            continue  # Continue loop without starting new nodes

                        # Check post-nodes immediately and start ready nodes
                        for edge in workflow.edges:
                            if edge.source == completed_node_id:
                                target_node_id = edge.target

                                # Skip if already running or completed
                                if (target_node_id in active_tasks or
                                    target_node_id in self.completed_nodes):
                                    continue

                                # Dependency check: verify all pre-nodes are completed
                                pre_nodes = set(pre_nodes_map.get(target_node_id, []))
                                if pre_nodes.issubset(self.completed_nodes):
                                    target_node = node_lookup[target_node_id]

                                    # Send node start notification first (minimize delay)
                                    yield {
                                        "type": "node_start",
                                        "node_id": target_node_id,
                                        "node_type": target_node.type,
                                        "message": f"{target_node.type} node execution started"
                                    }

                                    # Start node execution immediately
                                    task = asyncio.create_task(
                                        self._execute_single_node_stream(
                                            target_node, workflow, global_stream_queue
                                        )
                                    )
                                    active_tasks[target_node_id] = task
                    
                    elif chunk["type"] == "node_complete" and not chunk["success"]:
                        # Remove failed node from active_tasks
                        failed_node_id = chunk.get("node_id")
                        if failed_node_id and failed_node_id in active_tasks:
                            del active_tasks[failed_node_id]

                        # Stop entire workflow if a node fails
                        yield {
                            "type": "error",
                            "message": f"Node execution failed: {chunk['node_id']}"
                        }
                        # Cancel all active tasks
                        for task in active_tasks.values():
                            task.cancel()
                        return
                        
                except asyncio.TimeoutError:
                    # Timeout is normal - continue
                    continue

            # Wait for all active tasks to complete
            if active_tasks:
                await asyncio.gather(*active_tasks.values(), return_exceptions=True)
            
            # Final result
            total_time = time.time() - start_time
            final_output = self._get_final_output(workflow)

            # Distinguish between stopped and normal completion
            was_stopped = self.is_stopping
            success_status = True  # Treat as success by default (stop is also considered successful termination)

            # Completion event for streaming
            yield {
                "type": "complete",
                "success": success_status,
                "final_output": final_output,
                "total_execution_time": total_time,
                "execution_order": self.execution_order,
                "results": [result.__dict__ for result in self.execution_results],
                "was_stopped": was_stopped  # Add stop status info
            }

            # Final result event for non-streaming
            yield {
                "type": "final_result",
                "result": WorkflowExecutionResponse(
                    success=True,
                    results=self.execution_results,
                    final_output=final_output,
                    total_execution_time=total_time,
                    execution_order=self.execution_order
                )
            }
            
        except Exception as e:
            logger.error(f"Error during workflow execution: {str(e)}")
            total_time = time.time() - start_time

            # Error event for streaming
            yield {
                "type": "error",
                "message": f"Workflow execution error: {str(e)}"
            }

            # Final result event for non-streaming
            yield {
                "type": "final_result",
                "result": WorkflowExecutionResponse(
                    success=False,
                    results=self.execution_results,
                    error=f"Workflow execution failed: {str(e)}",
                    total_execution_time=total_time,
                    execution_order=self.execution_order
                )
            }
    
    async def _execute_node_stream(
        self,
        node: WorkflowNode,
        workflow: WorkflowDefinition
    ):
        """Execute individual node with streaming"""
        
        start_time = time.time()
        
        try:
            # Streaming execution
            accumulated_output = ""
            parsed_result = None

            final_result = None

            # Separate pre-nodes into context-nodes and regular nodes
            context_node_ids = []
            regular_pre_node_ids = []

            for edge in workflow.edges:
                if edge.target == node.id and edge.source in self.node_outputs:
                    # Find source node in workflow nodes
                    source_node = None
                    for wf_node in workflow.nodes:
                        if wf_node.id == edge.source:
                            source_node = wf_node
                            break
                    
                    if source_node and source_node.type == "context-node":
                        context_node_ids.append(edge.source)
                    else:
                        regular_pre_node_ids.append(edge.source)
            
            # Collect outputs from each
            context_outputs = [self.node_outputs[ctx_id] for ctx_id in context_node_ids]
            pre_outputs = [self.node_outputs[pre_id] for pre_id in regular_pre_node_ids]

            # LLM nodes always use context-aware execution (needs separate processing even without context)
            if node.type in ["generation-node", "ensemble-node", "validation-node"]:
                # Context-aware streaming execution (OK even if context is empty)
                async for chunk in self.node_executor.execute_node_stream_with_context(node, pre_outputs, context_outputs):
                    if chunk["type"] == "stream":
                        accumulated_output += chunk["content"] 
                        yield chunk
                    elif chunk["type"] == "result":
                        final_result = chunk
                    elif chunk["type"] == "parsed_result":
                        final_result = chunk
                        parsed_result = chunk.get("output")
            else:
                # Text nodes execute in legacy way (combine all pre_outputs)
                all_pre_outputs = pre_outputs + context_outputs
                async for chunk in self.node_executor.execute_node_stream(node, all_pre_outputs):
                    if chunk["type"] == "stream":
                        accumulated_output += chunk["content"] 
                        yield chunk
                    elif chunk["type"] == "result":
                        final_result = chunk
                    elif chunk["type"] == "parsed_result":
                        final_result = chunk
                        parsed_result = chunk.get("output")
            
            # Return final result (use result already received from execute_node_stream)
            if final_result:
                yield final_result
            else:
                # Calculate execution time
                execution_time = time.time() - start_time
                yield {
                    "type": "result",
                    "success": True,
                    "output": parsed_result,
                    "raw_response": accumulated_output,
                    "execution_time": execution_time
                }
            
        except Exception as e:
            logger.error(f"Node stream execution failed: {str(e)}")
            yield {
                "type": "result",
                "success": False,
                "error": str(e)
            }
    
    def stop_execution(self):
        """Request workflow execution stop"""
        self.is_stopping = True
        logger.info("Workflow execution stop requested")
    
    def stop(self):
        """Request workflow execution stop (API compatibility alias)"""
        self.stop_execution()
    
    def reset_execution_state(self):
        """Reset execution state"""
        self.execution_queue.clear()
        self.completed_nodes.clear()
        self.node_outputs.clear()
        self.execution_results.clear()
        self.execution_order.clear()
        self.is_stopping = False
        self.stop_logged = False  # Reset stop log flag as well