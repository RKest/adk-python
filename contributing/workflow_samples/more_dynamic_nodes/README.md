# ADK Workflow Dynamic Node Execution Sample: Calorie Estimator

## Overview

This sample demonstrates how to use `ctx.run_node` to execute nodes dynamically and in parallel during workflow execution in **ADK Workflows**.

In standard workflow execution, the execution path is defined statically by the `edges`. However, there are scenarios where the exact nodes, or the number of times a node runs, cannot be determined until runtime—such as when you need to process a list of items where each item requires a separate agent call.

In this sample, we handle the **parallel execution** scenario:
1.  A `dish_decomposer` agent breaks down a dish into its top ingredients.
2.  A custom Python node `estimate_calories` receives the list of ingredients.
3.  The `estimate_calories` node uses `asyncio.gather` and `ctx.run_node` to call a `calorie_estimator` agent for *each* ingredient concurrently.
4.  Finally, a `summarizer` agent provides a breakdown of the results to the user.

This approach leverages native Python concurrency (`asyncio`) combined with asynchronous `ctx.run_node` calls to scale workflow tasks dynamically based on input data.

## Sample Inputs

- `Lasagna`
- `Chicken Caesar Salad`
- `Pad Thai`

## Graph

```text
          [ START ]
              |
              v
      [dish_decomposer]
              |
              v
     [estimate_calories]
      (PYTHON FUNCTION)
       |      |      |
       v      v      v
      [calorie_estimator] (Parallel execution via ctx.run_node)
       |      |      |
       \______+______/
              |
              v
        [summarizer]
```

## How To

1. **Enable Resumability**: For a Python node to use `ctx.run_node`, it must be declared with `@node(rerun_on_resume=True)`. This ensures the engine can handle interruptions (like waiting for tool calls or human-in-the-loop) and correctly resume the orchestrating node.

   ```python
   from google.adk.workflow import node

   @node(rerun_on_resume=True)
   async def estimate_calories(ctx: Context, node_input: Dish):
       # ...
   ```

2. **Run Multiple Nodes Concurrently**: You can combine `ctx.run_node` with standard Python `asyncio` utilities. In this sample, we create a list of tasks and gather them to process all ingredients in parallel.

   ```python
   @node(rerun_on_resume=True)
   async def estimate_calories(ctx: Context, node_input: Dish):
       # Create tasks for each ingredient
       tasks = [
           asyncio.create_task(ctx.run_node(calorie_estimator, node_input=ing.name))
           for ing in node_input.ingredients
       ]

       # Wait for all estimator calls to complete
       results = await asyncio.gather(*tasks)
       
       # Process results and yield the final data for the next node
       yield processed_results
   ```
