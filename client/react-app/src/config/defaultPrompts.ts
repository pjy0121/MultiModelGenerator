// Default prompt templates for each node type
export const DEFAULT_PROMPTS = {
  'generation-node': `You are a requirements analysis expert. Generate as many detailed and specific requirements as possible for the keyword '{input_data}' from the knowledge base context.

**Knowledge Base Context:**
{context}

**Input Data:**
{input_data}

**Instructions:**
1. Generate specific and high-quality requirements based on the provided context
2. Each requirement must be clear and written in maximum detail
3. Derive requirements only from within the context content
4. Do not excessively modify the content stated in the context
5. Specify in detail the sentences that serve as the basis for each requirement in the document
6. Specify the page number or section number (e.g., 5.1.8) where the basis for the requirement can be verified in the document
7. Assign requirement IDs sequentially starting from REQ-001
8. Write requirements in English`,

  'ensemble-node': `You are an expert in integrating multiple knowledge sources. Consolidate the following multiple requirement tables into one and organize them in a consistent format.

**Input Results (requirement generation result tables from multiple models):**
{input_data}

**Integration Instructions:**
1. **Merge Tables**: Combine requirement tables generated from multiple models into a single table
2. **Ensure Consistency**: Unify the requirement ID system and organize in a consistent format
3. **Add Verification Status**: Add a verification status field and mark all requirements as "unchecked" before starting
4. **Remove Duplicates**: Identify requirements with completely identical meanings, keep the higher quality one, and remove lower quality duplicates
5. **No Modifications**: Do not modify content or arbitrarily change the order

**Integration Summary:**
- Total input requirements: [count]
- Final consolidated requirements: [count]
- Items marked as duplicates: [count]

**Rules to Follow:**
1. Use only "unchecked" for verification status
2. Reassign requirement IDs sequentially starting from REQ-001
3. Only change verification status or remove duplicates without modifying content or order`,

  'validation-node': `You are a technical document verification expert. Sequentially verify requirements with "unchecked" status in the given requirement table against the knowledge base context and update their verification status.

**Requirements to Verify:**
{input_data}

**Knowledge Base Context:**
{context}

**Verification Instructions:**
1. **Already Passed Items**: Keep requirements with "pass" or "fail" status as is
2. **Sequential Verification**: Only verify requirements with "unchecked" status
3. **Pass Condition**: Change verification status to "pass" if clear evidence for the requirement can be found in the knowledge base
4. **Fail Condition**: Change verification status to "fail" if content contradicts the knowledge base
5. **Uncertain Cases**: Keep verification status as "unchecked" for ambiguous or uncertain cases that don't meet pass or fail conditions

**Verification Criteria:**
- **Factual Accuracy**: Check if it matches knowledge base content
- **Evidence Existence**: Check if the requirement's reference can be found in the knowledge base
- **Clarity**: Check if the requirement content is sufficiently understandable

Include the following in your output:

✅ **Passed Requirements:**
| ID | Summary | Requirement | Pass Reason |
|---|---|---|---|
| REQ-XXX | [Short summary of requirement] | [Original requirement content] | [Clear evidence found in knowledge base] |

❌ **Failed Requirements:**
| ID | Summary | Requirement | Fail Reason |
|---|---|---|---|
| REQ-YYY | [Short summary of requirement] | [Original requirement content] | [Content contradicting knowledge base] |

**Verification Statistics:**
- Total requirements: [total count]
- Requirements verified this time: [current verification count]
- Total passed so far: [cumulative pass count]
- Total failed so far: [cumulative fail count]
- Unchecked: [unchecked count]
- Current verification completion rate: [completion rate]%

**Rules to Follow:**
1. Use only "unchecked", "pass", or "fail" for verification status
2. When changing verification status, always judge carefully according to the verification criteria
3. Only change verification status without modifying content, removing items, or changing order`
};

// Output format templates for each node type (markdown tag based)
export const OUTPUT_FORMAT_TEMPLATES = {
  'generation-node': `| ID | Summary | Requirement | Reference |
|---|---|---|---|
| REQ-001 | [Short summary of requirement] | [Specific requirement content] | [Original text and location] |
| REQ-002 | ... | ... | ... |`,

  'ensemble-node': `| ID | Summary | Requirement | Reference | Verification Status |
|---|---|---|---|---|
| REQ-001 | [Short summary of requirement] | [Specific requirement content] | [Original text and location] | unchecked |
| REQ-002 | ... | ... | ... | unchecked |`,

  'validation-node': `| ID | Summary | Requirement | Reference | Verification Status |
|---|---|---|---|---|
| REQ-001 | [Short summary of requirement] | [Specific requirement content] | [Original text and location] | pass/fail/unchecked |
| REQ-002 | ... | ... | ... | pass/fail/unchecked |`
};

// Variable descriptions
export const PROMPT_VARIABLES = {
  '{input_data}': 'Data passed from previous nodes will be inserted here',
  '{context}': 'Related document content retrieved from knowledge base will be inserted here'
};
