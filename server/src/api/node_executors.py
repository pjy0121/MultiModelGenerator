"""
Node executor implementation - Simplified version
Maintains core functionality while removing unnecessary complexity
"""

import asyncio
import time
from typing import List, Any, AsyncGenerator

from ..models import WorkflowNode, NodeExecutionResult, SearchIntensity
from ..utils import ResultParser
from ..config import LLM_CONFIG
from ..services.llm_factory import LLMFactory
from ..services.vector_store_service import VectorStoreService


class NodeExecutor:
    """Node executor - Handles all node types"""

    def __init__(self):
        self.llm_factory = LLMFactory()
        self.result_parser = ResultParser()
        # Create VectorStoreService as needed to prevent blocking

    async def execute_node(self, node: WorkflowNode, pre_outputs: List[str]) -> NodeExecutionResult:
        """Execute node (legacy interface)"""
        return await self.execute_node_with_context(node, pre_outputs, [])

    async def execute_node_with_context(self, node: WorkflowNode, pre_outputs: List[str], context_outputs: List[str]) -> NodeExecutionResult:
        """Execute node - Process context-node output and regular pre-node output separately"""
        try:
            if self._is_text_node(node.type):
                # Text nodes use only regular pre_outputs
                return self._execute_text_node(node, pre_outputs)
            elif node.type == "context-node":
                return await self._execute_context_node(node, pre_outputs)
            else:
                # LLM nodes process context and input_data separately
                return await self._execute_llm_node_with_context(node, pre_outputs, context_outputs)
        except Exception as e:
            import traceback
            error_msg = f"Node execution failed: {str(e)}\nTraceback: {traceback.format_exc()}"
            print(f"[NodeExecutor] Error in node {node.id}: {error_msg}")  # Debug log
            return NodeExecutionResult(
                node_id=node.id,
                success=False,
                error=error_msg,
                execution_time=0.0
            )
    
    async def execute_node_stream(self, node: WorkflowNode, pre_outputs: List[str]):
        """Execute node with streaming (legacy interface)"""
        async for chunk in self.execute_node_stream_with_context(node, pre_outputs, []):
            yield chunk

    async def execute_node_stream_with_context(self, node: WorkflowNode, pre_outputs: List[str], context_outputs: List[str]):
        """Execute node with streaming - Process context-node output and regular pre-node output separately"""
        try:
            if self._is_text_node(node.type):
                # Text nodes return result immediately
                result = self._execute_text_node(node, pre_outputs)
                yield {
                    "type": "result",
                    "success": result.success,
                    "output": result.output,
                    "description": result.description,
                    "execution_time": result.execution_time,
                    "error": result.error
                }
            elif node.type == "context-node":
                # Context nodes return result immediately
                result = await self._execute_context_node(node, pre_outputs)
                yield {
                    "type": "result",
                    "success": result.success,
                    "output": result.output,
                    "description": result.description,
                    "execution_time": result.execution_time,
                    "error": result.error
                }
            else:
                # LLM nodes process context and input_data separately
                async for chunk in self._execute_llm_node_stream_with_context(node, pre_outputs, context_outputs):
                    yield chunk
        except Exception as e:
            import traceback
            error_msg = f"Node execution failed: {str(e)}\nTraceback: {traceback.format_exc()}"
            print(f"[NodeExecutor Stream] Error in node {node.id}: {error_msg}")  # Debug log
            yield {
                "type": "error",
                "message": error_msg
            }
    
    def _is_text_node(self, node_type: str) -> bool:
        """Check if node is a text node"""
        return node_type in ["input-node", "output-node"]
    
    def _execute_text_node(self, node: WorkflowNode, pre_outputs: List[str]) -> NodeExecutionResult:
        """Execute text node (Input/Output)"""
        if node.type == "input-node":
            content = node.content or "Input data not set."
        else:  # Output node
            if pre_outputs:
                # Check for <output> tag in pre_outputs and try parsing
                combined_content = "\n".join(pre_outputs)
                try:
                    # Try output parsing
                    parsed_result = self.result_parser.parse_node_output(combined_content)
                    content = parsed_result.output
                except:
                    # Use original if parsing fails
                    content = combined_content
            else:
                content = node.content or ""

        return NodeExecutionResult(
            node_id=node.id,
            success=True,
            description=content,
            output=content,
            execution_time=0.0
        )
    
    async def _execute_llm_node(self, node: WorkflowNode, pre_outputs: List[str]) -> NodeExecutionResult:
        """Execute LLM node (Generation/Ensemble/Validation)"""
        start_time = time.time()
        
        try:
            prompt = await self._prepare_prompt(node, pre_outputs)
            
            if not node.llm_provider or not node.model_type:
                raise ValueError(f"Node {node.id} missing LLM configuration")
            
            llm_client = self.llm_factory.get_client(node.llm_provider)
            response = await self._call_llm(llm_client, node.model_type, prompt)
            
            parsed_result = self.result_parser.parse_node_output(response)
            execution_time = time.time() - start_time
            
            return NodeExecutionResult(
                node_id=node.id,
                success=True,
                description=parsed_result.description,
                output=parsed_result.output,
                execution_time=execution_time
            )
        except Exception as e:
            execution_time = time.time() - start_time
            return NodeExecutionResult(
                node_id=node.id,
                success=False,
                error=f"LLM node execution failed: {str(e)}",
                execution_time=execution_time
            )

    async def _execute_llm_node_with_context(self, node: WorkflowNode, pre_outputs: List[str], context_outputs: List[str]) -> NodeExecutionResult:
        """Execute LLM node - Process context and input_data separately"""
        start_time = time.time()

        try:
            # input_data uses only regular pre-node outputs
            input_data = "\n".join(pre_outputs) if pre_outputs else ""
            # context uses context-node outputs
            context = "\n".join(context_outputs) if context_outputs else ""

            prompt_template = node.prompt or ""

            # Substitute prompt variables
            formatted_prompt = prompt_template.replace("{input_data}", input_data).replace("{context}", context)
            prompt = formatted_prompt if formatted_prompt.strip() else input_data
            
            if not node.llm_provider or not node.model_type:
                raise ValueError(f"Node {node.id} missing LLM configuration")
            
            llm_client = self.llm_factory.get_client(node.llm_provider)
            response = await self._call_llm(llm_client, node.model_type, prompt)
            
            parsed_result = self.result_parser.parse_node_output(response)
            execution_time = time.time() - start_time
            
            return NodeExecutionResult(
                node_id=node.id,
                success=True,
                description=parsed_result.description,
                output=parsed_result.output,
                execution_time=execution_time
            )
        except Exception as e:
            execution_time = time.time() - start_time
            return NodeExecutionResult(
                node_id=node.id,
                success=False,
                error=f"LLM node execution failed: {str(e)}",
                execution_time=execution_time
            )
    
    async def _execute_llm_node_stream(self, node: WorkflowNode, pre_outputs: List[str]):
        """Execute LLM node with streaming"""
        try:
            # LLM nodes don't perform knowledge base search (handled by context-node)
            input_data = "\n".join(pre_outputs) if pre_outputs else ""
            prompt_template = node.prompt or ""

            # context is empty string (provided by context-node)
            context = ""

            # LLM execution start notification
            yield {"type": "stream", "content": f"🤖 [{node.id}] Running {node.llm_provider}/{node.model_type} model...\n\n"}

            # Substitute prompt variables
            formatted_prompt = prompt_template.replace("{input_data}", input_data).replace("{context}", context)
            prompt = formatted_prompt if formatted_prompt.strip() else input_data

            if not node.llm_provider or not node.model_type:
                raise ValueError(f"Node {node.id} missing LLM configuration")
            
            client = self.llm_factory.get_client(node.llm_provider)
            if not client or not client.is_available():
                raise Exception(f"LLM client not available: {node.llm_provider}")
            
            full_response = ""
            
            # Use unified streaming interface
            async for chunk in client.generate_stream(
                prompt=prompt,
                model=node.model_type,
                temperature=LLM_CONFIG["default_temperature"]
            ):
                if chunk:
                    full_response += chunk
                    yield {"type": "stream", "content": chunk}
            
            # Parse result
            if full_response:
                parsed_result = self.result_parser.parse_node_output(full_response)
                yield {
                    "type": "parsed_result",
                    "success": True,
                    "description": parsed_result.description,
                    "output": parsed_result.output,
                    "execution_time": 0.0
                }
            else:
                raise Exception("Empty LLM response")
                
        except Exception as e:
            yield {
                "type": "result",
                "success": False,
                "error": str(e),
                "description": f"LLM execution error: {str(e)}",
                "output": None
            }
    
    async def _prepare_prompt(self, node: WorkflowNode, pre_outputs: List[str]) -> str:
        """Prepare prompt (non-streaming) - For LLM nodes, knowledge base search removed"""
        input_data = "\n".join(pre_outputs) if pre_outputs else ""
        prompt_template = node.prompt or ""

        # context is empty string (provided by context-node)
        context = ""

        # Substitute prompt variables
        formatted_prompt = prompt_template.replace("{input_data}", input_data).replace("{context}", context)
        return formatted_prompt if formatted_prompt.strip() else input_data

    async def _execute_context_node(self, node: WorkflowNode, pre_outputs: List[str]) -> NodeExecutionResult:
        """
        Execute context node - Search context from vector DB + add user-defined context
        If no knowledge base is set, only additional_context can be used
        """
        start_time = time.time()

        try:
            # Prepare input data (combine pre_outputs)
            input_data = " ".join(pre_outputs) if pre_outputs else ""

            # Check knowledge base and search intensity
            knowledge_base = node.knowledge_base
            search_intensity = node.search_intensity or SearchIntensity.get_default()
            additional_context = node.additional_context or ""

            context_parts = []
            total_chunks = 0
            found_chunks = 0
            kb_searched = False  # Whether knowledge base search was performed

            # Perform search if knowledge base is set and not "none"
            if knowledge_base and knowledge_base.lower() != "none":
                kb_searched = True
                if not input_data.strip():
                    return NodeExecutionResult(
                        node_id=node.id,
                        success=False,
                        error="Context search requires input data from pre-nodes",
                        execution_time=time.time() - start_time
                    )
                
                # Use context-node's own rerank settings
                rerank_info = None
                if (node.rerank_provider and node.rerank_provider not in ["none", None]):
                    from ..config import VECTOR_DB_CONFIG
                    rerank_info = {
                        "provider": "internal",
                        "model": VECTOR_DB_CONFIG.get("default_rerank_model")
                    }

                # Execute vector DB search
                vector_store_service = VectorStoreService()
                search_result = await vector_store_service.search(
                    kb_name=knowledge_base,
                    query=input_data,
                    search_intensity=search_intensity,
                    rerank_info=rerank_info
                )
                
                context_results = search_result["chunks"]
                total_chunks = search_result["total_chunks"]
                found_chunks = search_result["found_chunks"]
                
                if context_results:
                    # Add knowledge base name to output header (chunk count info in description)
                    kb_header = f"=== Knowledge Base: {knowledge_base} ==="
                    kb_content = "\n".join(context_results)
                    context_parts.append(f"{kb_header}\n{kb_content}")

            # Add additional context if available
            if additional_context.strip():
                context_parts.append(additional_context.strip())

            # Combine final context
            if not context_parts:
                context_content = "No context available."
                if kb_searched:
                    # Searched but no results
                    description = f"No context found from KB '{knowledge_base}' ({found_chunks}/{total_chunks} chunks found)"
                else:
                    description = "No knowledge base search performed and no additional context provided."
            else:
                context_content = "\n\n".join(context_parts)
                # Include chunk count info in description
                if kb_searched:
                    kb_info = f" from KB '{knowledge_base}' ({found_chunks}/{total_chunks} chunks found)"
                else:
                    kb_info = ""
                additional_info = " + user-defined context" if additional_context.strip() else ""
                description = f"Context prepared{kb_info}{additional_info}"
            
            return NodeExecutionResult(
                node_id=node.id,
                success=True,
                description=description,
                output=context_content,
                execution_time=time.time() - start_time
            )
            
        except Exception as e:
            return NodeExecutionResult(
                node_id=node.id,
                success=False,
                error=f"Context preparation failed: {str(e)}",
                execution_time=time.time() - start_time
            )
    
    async def _execute_context_node_stream(self, node: WorkflowNode, pre_outputs: List[str]):
        """
        Execute context node with streaming
        If no knowledge base is set, only additional_context can be used
        """
        try:
            # Prepare input data
            query = "\n".join(pre_outputs) if pre_outputs else ""
            knowledge_base = node.knowledge_base
            additional_context = node.additional_context or ""

            context_parts = []
            total_chunks = 0
            found_chunks = 0
            kb_searched = False  # Whether knowledge base search was performed

            # Perform search if knowledge base is set and not "none"
            if knowledge_base and knowledge_base.lower() != "none":
                kb_searched = True
                if not query.strip():
                    yield {"type": "result", "success": False, "error": "No input data for context search"}
                    return

                # Search start notification
                yield {"type": "stream", "content": f"🔍 [{node.id}] Searching knowledge base '{knowledge_base}'...\n"}

            # Set rerank info
            rerank_info = None
            if (node.rerank_provider and node.rerank_provider not in ["none", None]):
                from ..config import VECTOR_DB_CONFIG
                rerank_model = VECTOR_DB_CONFIG.get("default_rerank_model")
                rerank_info = {
                    "provider": "internal",
                    "model": rerank_model
                }
                yield {"type": "stream", "content": f"🔄 [{node.id}] Reranking enabled: {rerank_model}\n"}

            # Perform knowledge base search (if set and not "none")
            if kb_searched:
                # Search for related context from vector store
                vector_store_service = VectorStoreService()
                search_result = await vector_store_service.search(
                    kb_name=knowledge_base,
                    query=query,
                    search_intensity=node.search_intensity or SearchIntensity.get_default(),
                    rerank_info=rerank_info
                )
                
                context_results = search_result["chunks"]
                total_chunks = search_result["total_chunks"]
                found_chunks = search_result["found_chunks"]
                
                if context_results:
                    # Add knowledge base name to output header (chunk count info in description and stream message)
                    kb_header = f"=== Knowledge Base: {knowledge_base} ==="
                    kb_content = "\n".join(context_results)
                    context_parts.append(f"{kb_header}\n{kb_content}")
                    yield {"type": "stream", "content": f"✅ [{node.id}] Found {found_chunks} relevant contexts from {total_chunks} total chunks.\n"}
                else:
                    yield {"type": "stream", "content": f"⚠️ [{node.id}] No relevant context found from knowledge base ({total_chunks} total chunks).\n"}

            # Add additional context if available
            if additional_context.strip():
                additional_header = "=== Additional Context ==="
                context_parts.append(f"{additional_header}\n{additional_context.strip()}")
                yield {"type": "stream", "content": f"📝 [{node.id}] User-defined context added.\n"}

            # Combine final context
            if not context_parts:
                yield {"type": "stream", "content": f"⚠️ [{node.id}] No context available.\n"}
                if kb_searched:
                    description = f"No context found from KB '{knowledge_base}' ({found_chunks}/{total_chunks} chunks found)"
                else:
                    description = "No context available"
                yield {
                    "type": "parsed_result",
                    "success": True,
                    "description": description,
                    "output": "No context available.",
                    "execution_time": 0.0
                }
            else:
                context_content = "\n\n".join(context_parts)
                # Include chunk count info in description
                if kb_searched:
                    kb_info = f" from KB '{knowledge_base}' ({found_chunks}/{total_chunks} chunks)"
                else:
                    kb_info = ""
                additional_info = " + user-defined" if additional_context.strip() else ""
                description = f"Context prepared{kb_info}{additional_info}"
                
                yield {
                    "type": "parsed_result",
                    "success": True,
                    "description": description,
                    "output": context_content,
                    "execution_time": 0.0
                }
        except Exception as e:
            yield {"type": "result", "success": False, "error": f"Context search failed: {str(e)}"}
    
    async def _call_llm(self, llm_client: Any, model_type: str, prompt: str) -> str:
        """Call LLM - Collect full response using streaming interface"""
        try:
            # Collect full response via streaming
            full_response = ""
            async for chunk in llm_client.generate_stream(
                prompt=prompt,
                model=model_type,
                temperature=0.3
            ):
                if chunk:
                    full_response += chunk
            
            if not full_response.strip():
                raise Exception("Empty response from LLM")
                
            return full_response
        except Exception as e:
            raise Exception(f"LLM call failed: {str(e)}")
    
    async def _execute_llm_node_stream_with_context(self, node: WorkflowNode, pre_outputs: List[str], context_outputs: List[str]):
        """Execute LLM node with streaming - Process context and input_data separately"""
        try:
            # input_data uses only regular pre-node outputs
            input_data = "\n".join(pre_outputs) if pre_outputs else ""
            # context uses context-node outputs
            context = "\n".join(context_outputs) if context_outputs else ""

            prompt_template = node.prompt or ""

            # Streaming start notification
            yield {"type": "stream", "content": f"🤖 [{node.id}] Context-aware execution: {node.llm_provider}/{node.model_type}\n"}

            # Substitute prompt variables
            formatted_prompt = prompt_template.replace("{input_data}", input_data).replace("{context}", context)
            prompt = formatted_prompt if formatted_prompt.strip() else input_data

            if not node.llm_provider or not node.model_type:
                raise ValueError(f"Node {node.id} missing LLM configuration")
            
            client = self.llm_factory.get_client(node.llm_provider)
            if not client or not client.is_available():
                raise Exception(f"LLM client not available: {node.llm_provider}")
            
            full_response = ""
            
            # Use unified streaming interface
            async for chunk in client.generate_stream(
                prompt=prompt,
                model=node.model_type,
                temperature=LLM_CONFIG["default_temperature"]
            ):
                if chunk:
                    full_response += chunk
                    yield {"type": "stream", "content": chunk}
            
            # Parse result
            if full_response:
                parsed_result = self.result_parser.parse_node_output(full_response)
                yield {
                    "type": "parsed_result",
                    "success": True,
                    "description": parsed_result.description,
                    "output": parsed_result.output,
                    "execution_time": 0.0
                }
            else:
                yield {"type": "result", "success": False, "error": "No response received"}
                
        except Exception as e:
            yield {"type": "result", "success": False, "error": str(e)}