"""Lab 2 actuators: a safe calculator and a Wikipedia lookup.

Both tools are ordinary Python functions. The model never runs them: it only
writes text asking for one of them, and react_agent.py executes it.
"""

import ast
import operator as op
from urllib.parse import quote

import requests

# Arithmetic we are willing to execute. Anything not in this table (attribute
# access, calls, imports, comprehensions) is rejected by _eval, which is why we
# do not need eval().
OPS = {
    ast.Add: op.add,
    ast.Sub: op.sub,
    ast.Mult: op.mul,
    ast.Div: op.truediv,
    ast.FloorDiv: op.floordiv,
    ast.Mod: op.mod,
    ast.Pow: op.pow,
    ast.USub: op.neg,
    ast.UAdd: op.pos,
}


def _eval(node):
    """Walk the parsed AST and compute only the operations in OPS."""
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        if isinstance(node.value, bool):
            raise ValueError("Unsupported expression")
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in OPS:
        return OPS[type(node.op)](_eval(node.left), _eval(node.right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in OPS:
        return OPS[type(node.op)](_eval(node.operand))
    raise ValueError("Unsupported expression")


def calculator(expression: str) -> str:
    """Evaluate an arithmetic expression safely and return it as text."""
    try:
        expr = str(expression).replace(",", "").replace("GHS", "").strip()
        value = _eval(ast.parse(expr, mode="eval").body)
        if isinstance(value, float) and value.is_integer():
            value = int(value)
        return str(round(value, 6))
    except Exception as e:
        return f"Error: {e}"


def wiki_lookup(title: str) -> str:
    """Return the first 800 characters of a Wikipedia summary, or a message."""
    url = (
        "https://en.wikipedia.org/api/rest_v1/page/summary/"
        + quote(title.strip().replace(" ", "_"), safe="")
    )
    try:
        r = requests.get(url, timeout=10, headers={"User-Agent": "DCIT403-lab"})
    except requests.RequestException as e:
        return f"Wikipedia lookup failed (network error: {e})."
    if r.status_code != 200:
        return f"No Wikipedia page found for '{title}'."
    extract = r.json().get("extract", "")
    if not extract:
        return f"Wikipedia page '{title}' has no summary text."
    return extract[:800]


# Registry the agent loop uses to turn an action name into a function.
TOOLS = {"calculator": calculator, "wiki_lookup": wiki_lookup}

# The tool list is part of the prompt: the model can only choose tools whose
# names, purpose and input format it can read here.
TOOL_DESCRIPTIONS = """- calculator: evaluates one arithmetic expression. Input: a plain expression
  such as 4*185 + 3*95. Use it for every arithmetic step.
- wiki_lookup: returns a short Wikipedia summary. Input: a page title such as
  Makola Market. Use it for facts about people, places and history."""

TOOL_NAMES = " | ".join(TOOLS) + " | finish"
