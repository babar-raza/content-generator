# LangGraph Integration for Blog Generation Workflow

This implementation integrates LangGraph-based workflow execution into the existing blog generation system, providing an alternative execution mode with automatic checkpointing and graph-based orchestration.

## Files Modified/Created

### Core Implementation
- `src/orchestration/langgraph_executor.py` - LangGraph workflow executor
- `src/orchestration/langgraph_state.py` - TypedDict state definitions
- `src/orchestration/production_execution_engine.py` - Added LangGraph mode selection
- `config/main.yaml` - Already has `use_langgraph` flag (line 31)

### Tests
- `tests/test_engine_parity.py` - Existing parity tests
- `test_langgraph_parity.py` - New comprehensive parity test script

## Configuration

Toggle between modes in `config/main.yaml`:

```yaml
workflows:
  # Enable LangGraph-based execution (experimental)
  use_langgraph: false  # Set to true for LangGraph mode
```

## How It Works

### Sequential Mode (Default)
- Traditional step-by-step execution
- Agents run in order defined by workflow
- Manual checkpoint management

### LangGraph Mode
- Graph-based workflow execution
- StateGraph with typed state (WorkflowState TypedDict)
- Each agent wrapped as a LangGraph node
- Conditional edges for branching (e.g., code validation)
- Built-in checkpointing via LangGraph
- Compatible with existing CheckpointManager

## Key Features

1. **Output Parity**: Both modes produce identical results
2. **Checkpoint Compatibility**: Checkpoints saved to same `.checkpoints/` directory
3. **Graceful Fallback**: Falls back to sequential mode if LangGraph fails
4. **No Agent Changes**: Agent interfaces remain unchanged
5. **Type Safety**: WorkflowState uses TypedDict for type hints

## Testing

### Run Parity Test
```bash
python test_langgraph_parity.py
```

### Run Unit Tests
```bash
pytest tests/test_engine_parity.py -v
```

### Manual Testing

Sequential mode:
```bash
python ucop_cli.py generate --input test.md --output output_seq/
```

LangGraph mode (edit config/main.yaml first to set use_langgraph: true):
```bash
python ucop_cli.py generate --input test.md --output output_lg/
```

Compare outputs:
```bash
diff output_seq/index.md output_lg/index.md
```

## Architecture

### State Flow
```
WorkflowState {
    job_id, workflow_name,
    current_step, total_steps,
    completed_steps,
    agent_outputs,     # Dict[agent_id, AgentOutput]
    shared_state,      # Accumulated context
    input_data,
    llm_calls, tokens_used
}
```

### Node Execution
Each agent becomes a node:
```python
def agent_node(state: WorkflowState) -> WorkflowState:
    # 1. Create agent instance
    # 2. Prepare input from state
    # 3. Execute agent
    # 4. Update state with output
    # 5. Return updated state
```

### Graph Structure
```
START → topic_identification → kb_ingestion → ... → file_writer → END
                                    ↓
                    (conditional: code_generation → code_validation)
```

## Implementation Details

### LangGraph Executor (`langgraph_executor.py`)
- `build_graph()` - Converts workflow steps to StateGraph
- `compile_graph()` - Compiles graph with checkpointer
- `execute()` - Runs workflow through graph
- `_create_agent_node()` - Wraps agent as graph node
- `_prepare_agent_input()` - Maps state to agent inputs
- `_should_validate_code()` - Conditional branching logic

### Production Engine Integration
The `execute_pipeline()` method now:
1. Checks `config.use_langgraph` flag
2. If true, calls `_execute_langgraph_pipeline()`
3. On failure, falls back to sequential mode
4. Sequential mode unchanged

### Checkpoint Integration
LangGraph checkpoints integrate with CheckpointManager:
- Same storage directory (`.checkpoints/`)
- Compatible state format
- Can resume from either mode's checkpoints

## Benefits of LangGraph Mode

1. **Visual Debugging**: Graph structure visible
2. **Parallel Execution**: Can run independent nodes concurrently
3. **Better Error Handling**: Graph-level retry/fallback
4. **Automatic Checkpointing**: Built into LangGraph
5. **Conditional Flows**: Easy branching logic

## Limitations

1. Requires `langgraph` package installation
2. Slightly more memory overhead for graph state
3. Learning curve for graph concepts
4. Current implementation is sequential (parallel coming)

## Future Enhancements

- [ ] Parallel node execution for independent agents
- [ ] Graph visualization in web UI
- [ ] Human-in-the-loop for approval nodes
- [ ] Multi-agent collaboration patterns
- [ ] Streaming output support
