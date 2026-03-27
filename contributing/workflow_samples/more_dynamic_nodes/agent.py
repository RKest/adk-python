# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import asyncio

from google.adk import Agent
from google.adk import Context
from google.adk import Workflow
from google.adk.workflow import node
from pydantic import BaseModel
from pydantic import Field

from opentelemetry import trace

tracer = trace.get_tracer(instrumenting_module_name='gcp.vertex.agent')

class Ingrediant(BaseModel):
  amount: int = Field(
    description="Estimate how much grams in 100 grams of the dish."
  )
  name: str = Field(
    description="Name the Ingrediant."
  )


class Dish(BaseModel):
  name: str = Field(
    description="Name of the dish verbatim."
  )
  ingredients: list[Ingrediant] = Field(
    description="List of ingrediants per 100g of the dish."
  )


class CalorieEstimate(BaseModel):
  name: str = Field(
    description="Name of the ingredient."
  )
  calories_per_100_grams: int = Field(
    description="Number of calories in 100 grams of the ingredient."
  )

dish_decomposer = Agent(
    name="dish_decomposer",
    instruction="""Decompose the dish user inputs into ingrediants. Limit to three top ingrediants.""",
    output_key="dish",
    output_schema=Dish,
    mode="single_turn",
)

calorie_estimator = Agent(
    name="calorie_estimator",
    instruction="""Return the calories of an ingrediant per 100 grams of product.""",
    output_key="calories",
    output_schema=CalorieEstimate,
    mode="single_turn",
)

summarizer = Agent(
  name="summarizer",
  instruction="""
  Summarize calorie breakdown of the following dish: {dish}.
  You will recieve all ingredients of the dish, with the exact number of calories per ingrediant.
  Outline these findings to the user.
  """,
  mode="single_turn",
)

@node(rerun_on_resume=True)
async def estimate_calories(ctx: Context, node_input: Dish):
  with tracer.start_as_current_span("execute_node estimate_calories") as span:
    calorie_estimation_tasks = [
      asyncio.create_task(ctx.run_node(calorie_estimator, node_input=ingrediant.name))
      for ingrediant in node_input.ingredients
    ]

    yield [
      (ingrediant.name, (ingrediant.amount / 100) * CalorieEstimate.model_validate(calorie_estimate).calories_per_100_grams)
      for ingrediant, calorie_estimate in zip(node_input.ingredients, await asyncio.gather(*calorie_estimation_tasks))
    ]
  

root_agent = Workflow(
    name="root_agent",
    edges=[("START", dish_decomposer, estimate_calories, summarizer)],
)
