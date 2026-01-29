# Workflow Configuration and Execution Definition

## Client Side

### Connection Rules

Connections are only possible between nodes that satisfy the following conditions. Workflows that do not satisfy these conditions cannot be executed.
When executing a workflow, users must be notified of unsatisfied conditions.

1. A node connected in the incoming direction to a node is called a pre-node, and a node connected in the outgoing direction from a node is called a post-node
2. All nodes must have at least one pre-node and post-node. However, input-node cannot have a pre-node and output-node cannot have a post-node
3. Only ensemble-node can be connected to multiple pre-nodes
4. Only input-node can be connected to multiple post-nodes
5. The initial workflow must have one input-node and one output-node
6. Connection information between nodes cannot be changed while the workflow is running

### Node Types and Characteristics

Node types include input-node, output-node, generation-node, ensemble-node, and validation-node

1. input-node
   - Node that holds plain-text (content) to be passed as input data to the next node
   - Cannot connect pre-nodes
   - Can connect multiple post-nodes
   - At least one must exist in the workflow, so the last one cannot be deleted
   - Uses ReactFlow's TextNode component, and content can be modified in the edit popup
   - Properties: content (string)

2. generation-node
   - Node that sends prompts to LLM models to generate initial responses
   - Only input-node can be a pre-node
   - ensemble-node, validation-node, output-node can be post-nodes
   - Uses ReactFlow's ModelNode component, and model can be selected via dropdown in the edit popup
   - Properties: model_type (string), llm_provider (string)

3. ensemble-node
   - Node that concatenates outputs from connected pre-nodes and organizes them into one
   - Can connect multiple pre-nodes
   - All nodes except output-node can be pre-nodes
   - All nodes except input-node can be post-nodes
   - Uses ReactFlow's ModelNode component, and model can be selected via dropdown in the edit popup
   - Properties: model_type (string), llm_provider (string)

4. validation-node
   - Node that performs validation on input data
   - input-node, generation-node, ensemble-node, validation-node can be pre-nodes
   - validation-node, ensemble-node, output-node can be post-nodes
   - Uses ReactFlow's ModelNode component, and model can be selected via dropdown in the edit popup
   - Properties: model_type (string), llm_provider (string)

5. output-node
   - Node that receives and outputs results from previous nodes
   - Cannot connect post-nodes
   - Only one can exist in the workflow and cannot be removed
   - Uses ReactFlow's TextNode component, and content can be modified in the edit popup
   - Properties: content (string)

### Workflow Execution

- Clicking the workflow execution button calls the server-side workflow execution API
- The configured workflow information, node type prompts, selected Knowledge Base name, and search intensity are sent together in the Request
- During workflow execution, content (description or error) responded by the server is output to the execution results panel
- Nodes that have responded are marked as execution complete on the ReactFlow canvas

## Server Side

### Workflow Execution API

The following process is performed when executing a workflow:

1. Find all input-nodes in the workflow and add them to the execution queue
2. Repeat the following until there are no more nodes to execute in the queue:
    2-1. Find nodes in the queue that have no pre-nodes or all pre-nodes have outputs (i.e., all pre-nodes have completed execution)
    2-2. Execute the found nodes in parallel
    2-3. Wait until execution is complete
    2-4. For nodes that have finished execution, register post-nodes to the queue and remove the finished node from the queue

### ResultParser Execution

1. Extract content within `<output>...</output>` tags from LLM output to use as data passed to the next node

2. On parsing failure (when output tag is missing)
   - Use the entire text as output
   - Send error content to client

3. On parsing success
   - The entire markdown text is streamed to the client (serves as description)
   - Return the `<output>` tag content as data to be passed to the next node

### Node Execution

1. input-node, output-node execution

1-1. Input for node execution is as follows:

```json
{
    "input": [pre-node's output property (string)]
}
```

1-2. If input value is not null, update the content property

1-3. Process the node's content property in markdown format

1-4. Execute ResultParser with content property as argument

1-5. Store ResultParser's return value in output property

2. Other node execution

2-1. Input for node execution is as follows:

```json
{
    "inputs": [array of pre-nodes' output properties (string array)],
    "knowledge_base": [knowledge base name to search (string)],
    "intensity": [search intensity within knowledge base],
    "prompt": [prompt to send to LLM model (string)],
    "output_format": [output format to include in prompt]
}
```

2-2. Concatenate elements of inputs to create input_data

2-3. Find '{input_data}' string in input prompt and replace with input_data content

2-4. If knowledge_base is provided:
   2-4-1. Determine top_k for search based on intensity value
   2-4-2. Find the knowledge_base in VectorDB and get search results for input_data
   2-4-3. Find '{context}' string in input prompt and replace with search results from knowledge_base

2-5. Find '{output_format}' string and replace with markdown output format guide
2-6. Call LLM API to send prompt (streaming response)
2-7. Stream LLM API output to client in real-time while extracting final output with ResultParser
2-8. Store ResultParser's return value in output property
