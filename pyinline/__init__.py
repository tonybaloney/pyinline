import libcst as cst
from typing import Optional, List, Union
from functools import wraps
from libcst.helpers import get_full_name_for_node
import logging
from dataclasses import dataclass
from typing import Optional, Sequence, Union
from libcst._nodes.internal import (
    CodegenState,
    visit_sequence,
)
from libcst._add_slots import add_slots

log = logging.getLogger(__name__)


@wraps
def inline():
    pass


MODULE_NAME = "pyinline"
DECORATOR_NAME = "inline"


@add_slots
@dataclass(frozen=True)
class InlineBlock(cst.BaseSuite):
    body: Sequence[cst.BaseStatement]

    #: Any optional trailing comment and the final ``NEWLINE`` at the end of the line.
    header: cst.TrailingWhitespace = cst.TrailingWhitespace.field()

    def _visit_and_replace_children(self, visitor: cst.CSTVisitorT) -> "InlineBlock":
        return InlineBlock(
            body=visit_sequence(self, "body", self.body, visitor), header=self.header
        )

    def _codegen_impl(self, state: CodegenState) -> None:
        self.header._codegen(state)

        if self.body:
            with state.record_syntactic_position(
                self, start_node=self.body[0], end_node=self.body[-1]
            ):
                for stmt in self.body:
                    stmt._codegen(state)


class AssignedNamesVisitor(cst.CSTVisitor):
    def __init__(self) -> None:
        self._to_mangle = []

    def leave_Assign(self, original_node: cst.Assign):
        self._to_mangle.extend(target.target.value for target in original_node.targets)

    @property
    def names_to_mangle(self):
        return self._to_mangle


class NameManglerTransformer(cst.CSTTransformer):
    def __init__(self, prefix: str, to_mangle=List[str]) -> None:
        self.prefix = prefix
        self.to_mangle = to_mangle

    def visit_Name(self, node: cst.Name) -> Optional[bool]:
        if node.value == self.prefix:
            raise ValueError("Inline functions cannot be recursive")

        return super().visit_Name(node)

    def leave_Name(
        self, original_node: cst.Name, updated_node: cst.Name
    ) -> cst.BaseExpression:
        if original_node.value in self.to_mangle:
            return original_node.with_changes(
                value=f"_{self.prefix}__{original_node.value}"
            )
        else:
            return original_node


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
        return original_node

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

        # IF the function has no nesting, use a simple Statement suite
        if all(isinstance(line, cst.SimpleStatementLine) for line in match.body.body):
            suite = cst.SimpleStatementSuite(
                body=[
                    fragment
                    for statement in match.body.body
                    for fragment in statement.body
                ],
                leading_whitespace=cst.SimpleWhitespace(""),  # TODO: Work out indent
            )
        else:
            suite = InlineBlock(body=match.body.body)  # TODO: Work out indent

        # Mangle names
        mangledNamesVisitor = AssignedNamesVisitor()
        suite.visit(mangledNamesVisitor)
        transformer = NameManglerTransformer(
            get_full_name_for_node(original_node), mangledNamesVisitor.names_to_mangle
        )
        suite = suite.visit(transformer)

        # resolve arguments
        if original_node.args:
            for i, arg in enumerate(original_node.args):
                # Is this a constant?
                if isinstance(
                    original_node.args[i].value,
                    (
                        cst.SimpleString,
                        cst.Integer,
                        cst.Float,
                    ),  # TODO: Other useful constants
                ):
                    # Replace names with constant value in functions
                    transformer = NameToConstantTransformer(
                        match.params.params[i].name, arg.value
                    )
                    suite = suite.visit(transformer)
                else:
                    # Replace names with constant value in functions
                    transformer = NameToNameTransformer(
                        match.params.params[i].name, arg.value
                    )
                    suite = suite.visit(transformer)

        return suite
