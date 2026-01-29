## Project Concept
A FastAPI-based backend server with functionality to extract requirement lists related to given keywords from knowledge bases stored in Vector DB. It operates using a Multi Model Generation & Validation approach that queries multiple LLM models, aggregates their responses, and repeatedly queries for validation purposes.

The process goes through the following 3 Layers:
- Layer 1. Generation Layer: Layer that sends prompts to LLM models to generate responses
- Layer 2. Ensemble Layer: Layer that aggregates model responses into one
- Layer 3. Validation Layer: Layer that validates whether the aggregated response violates given Specs


## Provided Features
- External LLM query functionality
- Current knowledge base list provision
- Multi-model workflow execution functionality

## Feature Details
### 1. External LLM Query Functionality
- Must provide the types of LLM models available through multiple LLM Provider APIs via REST API
- Must be able to query prompts to specified LLM models

### 2. Current Knowledge Base List Provision
- Must be able to check the list of knowledge bases built in the server's knowledge base path and provide them via REST API

### 3. Multi-Model Workflow Execution Functionality
- Must receive workflow configuration and provide validated results after going through multiple models (nodes)
- Must be able to pass output from each node to the next node
- generation-node must be able to query LLM prompts including knowledge base content
- Based on given Generation Node configurations, must query one or more requirements, then aggregate results and pass to Ensemble Layer Node
- ensemble-node must be able to integrate multiple given inputs
- validation-node must be able to validate input based on knowledge base content
