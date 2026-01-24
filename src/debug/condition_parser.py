"""Safe Condition Parser - AST-based expression evaluator.

This module implements a safe condition parser for breakpoint conditions.
CRITICAL: Uses AST-based parsing ONLY. NO eval(), NO exec().

Supported Operations:
- Comparison: ==, !=, <, >, <=, >=
- Membership: in, not in
- Logical: and, or, not
- Attribute access: inputs.topic, outputs.confidence
- Length: len(inputs.sources)

Security:
- Whitelist of allowed AST node types
- No function calls except len()
- No imports allowed
- Max expression length: 500 chars
- Max nesting depth: 10

Author: Migration Implementation Agent
Created: 2025-12-18
Taskcard: VIS-002
"""

import ast
import logging
from typing import Any

logger = logging.getLogger(__name__)


class ConditionEvaluationError(Exception):
    """Raised when condition evaluation fails."""

    pass


class ConditionParser:
    """Safe expression parser using AST.

    The ConditionParser provides secure evaluation of breakpoint conditions
    without using eval() or exec(). Only whitelisted operations are allowed.

    Example:
        >>> parser = ConditionParser()
        >>> context = {"inputs": {"topic": "Python"}, "outputs": {"confidence": 0.8}}
        >>> result = parser.evaluate("inputs.topic == 'Python'", context)
        >>> assert result is True

    Security:
        - NO eval() or exec() calls
        - Whitelist of allowed AST nodes
        - Max expression length enforced
        - Max nesting depth enforced
    """

    # Maximum expression length
    MAX_EXPRESSION_LENGTH = 500

    # Maximum nesting depth
    MAX_DEPTH = 10

    # Whitelist of allowed AST node types
    ALLOWED_NODES = {
        ast.Expression,  # Top-level expression
        ast.Compare,  # Comparison operators
        ast.BoolOp,  # and, or
        ast.UnaryOp,  # not
        ast.Attribute,  # inputs.topic
        ast.Name,  # Variable names
        ast.Constant,  # Literal values (str, int, float, bool, None)
        ast.List,  # List literals
        ast.Tuple,  # Tuple literals
        ast.Call,  # Function calls (only len allowed)
        # Comparison operators
        ast.Eq,  # ==
        ast.NotEq,  # !=
        ast.Lt,  # <
        ast.Gt,  # >
        ast.LtE,  # <=
        ast.GtE,  # >=
        ast.In,  # in
        ast.NotIn,  # not in
        # Boolean operators
        ast.And,  # and
        ast.Or,  # or
        ast.Not,  # not
        # Context nodes (safe metadata about how variables are used)
        ast.Load,  # Variable read context
        ast.Store,  # Variable write context (shouldn't appear in expressions, but safe)
    }

    # Allowed function calls
    ALLOWED_FUNCTIONS = {"len"}

    def __init__(self):
        """Initialize condition parser."""
        logger.debug("ConditionParser initialized")

    def parse(self, expression: str) -> ast.Expression:
        """Parse expression into AST.

        Args:
            expression: Python expression string

        Returns:
            Parsed AST Expression node

        Raises:
            ConditionEvaluationError: If expression is invalid or unsafe

        Example:
            >>> parser = ConditionParser()
            >>> tree = parser.parse("inputs.topic == 'Python'")
            >>> assert isinstance(tree, ast.Expression)
        """
        if not expression:
            raise ConditionEvaluationError("Expression cannot be empty")

        if len(expression) > self.MAX_EXPRESSION_LENGTH:
            raise ConditionEvaluationError(
                f"Expression too long ({len(expression)} > {self.MAX_EXPRESSION_LENGTH})"
            )

        # Parse expression
        try:
            tree = ast.parse(expression, mode="eval")
        except SyntaxError as e:
            # Syntax errors in eval mode often indicate forbidden operations
            raise ConditionEvaluationError(
                f"Syntax error (operation not allowed): {e}"
            )

        # Validate AST security
        self._validate_ast(tree)

        return tree

    def evaluate(self, expression: str, context: dict[str, Any]) -> bool:
        """Evaluate expression in given context.

        Args:
            expression: Python expression string
            context: Variables available to expression (e.g., inputs, outputs, context)

        Returns:
            Boolean result of expression evaluation

        Raises:
            ConditionEvaluationError: If expression is invalid or evaluation fails

        Example:
            >>> parser = ConditionParser()
            >>> context = {"inputs": {"topic": "Python"}}
            >>> result = parser.evaluate("inputs.topic == 'Python'", context)
            >>> assert result is True
        """
        # Parse and validate
        tree = self.parse(expression)

        # Evaluate
        try:
            result = self._eval_node(tree.body, context)
            return bool(result)
        except ConditionEvaluationError:
            # Re-raise our own exceptions without wrapping
            raise
        except Exception as e:
            # Wrap unexpected exceptions
            raise ConditionEvaluationError(f"Evaluation error: {e}")

    def _validate_ast(self, tree: ast.Expression, depth: int = 0) -> None:
        """Validate AST tree security.

        Args:
            tree: AST node to validate
            depth: Current nesting depth

        Raises:
            ConditionEvaluationError: If tree contains unsafe operations
        """
        if depth > self.MAX_DEPTH:
            raise ConditionEvaluationError(
                f"Expression too deeply nested (max depth: {self.MAX_DEPTH})"
            )

        # Check node type is allowed
        if type(tree) not in self.ALLOWED_NODES:
            raise ConditionEvaluationError(
                f"Operation not allowed: {type(tree).__name__}"
            )

        # Special validation for function calls
        if isinstance(tree, ast.Call):
            if not isinstance(tree.func, ast.Name):
                raise ConditionEvaluationError(
                    "Complex function calls not allowed (only simple function names)"
                )

            if tree.func.id not in self.ALLOWED_FUNCTIONS:
                raise ConditionEvaluationError(
                    f"Function '{tree.func.id}' not allowed. "
                    f"Allowed functions: {', '.join(self.ALLOWED_FUNCTIONS)}"
                )

        # Recursively validate children
        for child in ast.iter_child_nodes(tree):
            self._validate_ast(child, depth + 1)

    def _eval_node(self, node: ast.AST, context: dict[str, Any]) -> Any:
        """Recursively evaluate AST node.

        Args:
            node: AST node to evaluate
            context: Variable context

        Returns:
            Evaluation result

        Raises:
            ConditionEvaluationError: If evaluation fails
        """
        # Constant value
        if isinstance(node, ast.Constant):
            return node.value

        # Variable name
        if isinstance(node, ast.Name):
            if node.id not in context:
                raise ConditionEvaluationError(f"Variable '{node.id}' not found")
            return context[node.id]

        # Attribute access (e.g., inputs.topic)
        if isinstance(node, ast.Attribute):
            value = self._eval_node(node.value, context)
            if not hasattr(value, node.attr):
                # Try dictionary access
                if isinstance(value, dict):
                    if node.attr not in value:
                        raise ConditionEvaluationError(
                            f"Attribute '{node.attr}' not found"
                        )
                    return value[node.attr]
                raise ConditionEvaluationError(
                    f"Attribute '{node.attr}' not found"
                )
            return getattr(value, node.attr)

        # Comparison (e.g., x == y, x > y)
        if isinstance(node, ast.Compare):
            left = self._eval_node(node.left, context)
            for op, comparator in zip(node.ops, node.comparators):
                right = self._eval_node(comparator, context)

                if isinstance(op, ast.Eq):
                    result = left == right
                elif isinstance(op, ast.NotEq):
                    result = left != right
                elif isinstance(op, ast.Lt):
                    result = left < right
                elif isinstance(op, ast.Gt):
                    result = left > right
                elif isinstance(op, ast.LtE):
                    result = left <= right
                elif isinstance(op, ast.GtE):
                    result = left >= right
                elif isinstance(op, ast.In):
                    result = left in right
                elif isinstance(op, ast.NotIn):
                    result = left not in right
                else:
                    raise ConditionEvaluationError(f"Unsupported operator: {type(op)}")

                if not result:
                    return False

                left = right

            return True

        # Boolean operation (and, or)
        if isinstance(node, ast.BoolOp):
            if isinstance(node.op, ast.And):
                return all(self._eval_node(v, context) for v in node.values)
            elif isinstance(node, ast.Or):
                return any(self._eval_node(v, context) for v in node.values)
            else:
                raise ConditionEvaluationError(f"Unsupported bool op: {type(node.op)}")

        # Unary operation (not)
        if isinstance(node, ast.UnaryOp):
            if isinstance(node.op, ast.Not):
                return not self._eval_node(node.operand, context)
            else:
                raise ConditionEvaluationError(
                    f"Unsupported unary op: {type(node.op)}"
                )

        # Function call
        if isinstance(node, ast.Call):
            func_name = node.func.id
            args = [self._eval_node(arg, context) for arg in node.args]

            if func_name == "len":
                if len(args) != 1:
                    raise ConditionEvaluationError("len() takes exactly 1 argument")
                return len(args[0])

            raise ConditionEvaluationError(f"Function '{func_name}' not allowed")

        # List literal
        if isinstance(node, ast.List):
            return [self._eval_node(elt, context) for elt in node.elts]

        # Tuple literal
        if isinstance(node, ast.Tuple):
            return tuple(self._eval_node(elt, context) for elt in node.elts)

        raise ConditionEvaluationError(f"Unsupported node type: {type(node).__name__}")


__all__ = ["ConditionParser", "ConditionEvaluationError"]
