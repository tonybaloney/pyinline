import libcst as cst
from typing import Optional, List, Tuple, Union
from functools import wraps
from libcst.helpers import get_full_name_for_node
import logging

log = logging.getLogger(__name__)


@wraps
def inline():
    pass


class InlineTransformer(cst.CSTTransformer):
    def __init__(self) -> None:
        self.inline_functions: List[cst.FunctionDef] = []
        self.stack: List[Tuple[str, ...]] = []
        super().__init__()

    def visit_FunctionDef(self, node: cst.FunctionDef) -> Optional[bool]:
        if node.decorators:
            is_inline = any(
                decorator.decorator.value == "inline" for decorator in node.decorators
            )
            if is_inline:
                self.inline_functions.append(node)
        return super().visit_FunctionDef(node)

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
        if match:
            log.debug(
                f"Replacing function call to {get_full_name_for_node(original_node)}"
            )
            if isinstance(match[0].body, cst.IndentedBlock):
                if len(match[0].body.body) == 1:
                    return match[0].body.body[0]
        return updated_node
