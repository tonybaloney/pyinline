import libcst as cst
from typing import Optional, List, Tuple, Union
from functools import wraps
from libcst.helpers import get_full_name_for_node
import logging

log = logging.getLogger(__name__)


@wraps
def inline():
    pass


MODULE_NAME = "pyinline"
DECORATOR_NAME = "inline"


class NameToConstantTransformer(cst.CSTTransformer):
    def __init__(self, name: cst.Name, constant: cst.CSTNode) -> None:
        self.name = name
        self.constant = constant

    def leave_Name(
        self, original_node: cst.Name, updated_node: cst.Name
    ) -> cst.BaseExpression:
        if original_node.deep_equals(self.name):
            return self.constant
        return original_node


class NameToNameTransformer(cst.CSTTransformer):
    def __init__(self, name: cst.Name, replacement_name: cst.Name) -> None:
        self.name = name
        self.replacement_name = replacement_name

    def leave_Name(
        self, original_node: cst.Name, updated_node: cst.Name
    ) -> cst.BaseExpression:
        if original_node.deep_equals(self.name):
            return self.replacement_name
        return original_node


class InlineTransformer(cst.CSTTransformer):
    def __init__(self) -> None:
        self.inline_functions: List[cst.FunctionDef] = []
        self.stack: List[Tuple[str, ...]] = []
        super().__init__()

    def visit_FunctionDef(self, node: cst.FunctionDef) -> Optional[bool]:
        if node.decorators:
            is_inline = any(
                get_full_name_for_node(decorator.decorator) == DECORATOR_NAME
                for decorator in node.decorators
            )
            if is_inline:
                self.inline_functions.append(node)
        return super().visit_FunctionDef(node)

    def leave_FunctionDef(
        self, original_node: cst.FunctionDef, updated_node: cst.FunctionDef
    ) -> Union[
        cst.BaseStatement, cst.FlattenSentinel[cst.BaseStatement], cst.RemovalSentinel
    ]:
        if original_node in self.inline_functions:
            return cst.RemovalSentinel.REMOVE
        return super().leave_FunctionDef(original_node, updated_node)

    def leave_ImportFrom(
        self, original_node: cst.ImportFrom, updated_node: cst.ImportFrom
    ) -> Union[
        cst.BaseSmallStatement,
        cst.FlattenSentinel[cst.BaseSmallStatement],
        cst.RemovalSentinel,
    ]:
        if (
            original_node.module.value == MODULE_NAME
            and original_node.names[0].name.value == DECORATOR_NAME
        ):
            return cst.RemovalSentinel.REMOVE
        return super().leave_ImportFrom(original_node, updated_node)

    def visit_Call(self, node: cst.Call) -> Optional[bool]:
        match = [
            f
            for f in self.inline_functions
            if get_full_name_for_node(f) == get_full_name_for_node(node)
        ]
        if match:
            self.stack.append(get_full_name_for_node(match[0]))
            return False
        return super().visit_Call(node)

    def leave_Call(
        self, original_node: cst.Call, updated_node: cst.BaseExpression
    ) -> Union[cst.Call, cst.BaseSuite]:
        match = [
            f
            for f in self.inline_functions
            if get_full_name_for_node(f) == get_full_name_for_node(original_node)
        ]
        if not match:
            return updated_node

        match = match[0]
        log.debug(f"Replacing function call to {get_full_name_for_node(original_node)}")
        # IF the inline function has no arguments and is just a single-line, return as a SimpleStatement.
        if (
            isinstance(match.body, cst.IndentedBlock)
            and len(match.body.body) == 1
            and not original_node.args
        ):
            return match.body.body[0]

        # Otherwise build a suite
        suite = cst.SimpleStatementSuite(
            body=[
                fragment for statement in match.body.body for fragment in statement.body
            ],
            leading_whitespace=cst.SimpleWhitespace(""),
        )

        # resolve arguments
        if original_node.args:

            for i, arg in enumerate(original_node.args):
                # Is this a constant?
                if isinstance(
                    original_node.args[i].value,
                    (cst.SimpleString, cst.Integer, cst.Float),
                ):
                    # Replace names with constant value in functions
                    transformer = NameToConstantTransformer(
                        match.params.params[i].name, arg.value
                    )
                    suite = suite.visit(transformer)
                    continue
                else:
                    # Replace names with constant value in functions
                    transformer = NameToNameTransformer(
                        match.params.params[i].name, arg.value
                    )
                    suite = suite.visit(transformer)
                    continue

        return suite
