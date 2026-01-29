## Project Concept
A React-based Web Application for extracting requirement lists related to given keywords. It provides functionality for users to configure workflows utilizing multiple LLM Models. React Flow is used for this purpose, and it must be implemented using a modern UI framework.

## Provided Features
The App GUI must provide the following features:
- Workflow configuration
- Workflow execution after selecting knowledge base and entering keyword
- Visualization of workflow execution results
- Export workflow execution results to various file formats

## Feature Details
### 1. Workflow Configuration
- Nodes have LLM model type and prompt content as properties
   - Double-clicking a node opens an edit popup where you can select the model type (dropdown) and modify prompt content. The prompt content is pre-filled with specific default content
- Add/delete nodes per Layer
   - One node exists by default per Layer
   - The first node per Layer cannot be deleted, delete functionality is provided for the last node per Layer
   - Generation Layer can have up to 5 nodes, Ensemble Layer 1 node, Validation Layer up to 3 nodes
   - PlaceholderNode should be shown at positions where new nodes can be added
- Local save/restore workflow functionality
   - Node positions within React Flow and Canvas Zoom and View Point must be saved/restored together
- Export current workflow to JSON file, import from JSON functionality
- All nodes have fixed positions and are arranged on the left side of the Canvas by default
- Directional Arrows must connect nodes according to the Data Flow direction
   - All nodes in Generation Layer arrows connect to the single Ensemble Layer node
   - The single Ensemble Layer node arrow connects to the first Validation Layer node
   - Validation Layer arrows connect to the next node in the same Layer
   - Example)
     Generation  []  []
                 ↓ ↙
     Ensemble    []
                 ↓
     Validation  [] → [] → []

### 2. Workflow Execution
- On App load, call Rest API to load the list of knowledge bases built on the remote server
- Pass prompt content including knowledge base and keyword, along with node information to the Rest API for workflow execution and receive results

### 3. Workflow Results Visualization
- The requirement list resulting from the last Validation Layer node must be visualized in table format and provided in the execution results area
