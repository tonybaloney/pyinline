import libcst as cst
from typing import List, Tuple, Dict, Optional
import sys
from functools import wraps


@wraps
def inline():
    pass


class InlineTransformer(cst.CSTVisitor):
    def __init__(self) -> None:
        self.inline_functions = []
        super().__init__()

    def visit_FunctionDef(self, node: cst.FunctionDef) -> Optional[bool]:
        if node.decorators:
            is_inline = any(
                decorator.decorator.value == "inline" for decorator in node.decorators
            )
            if is_inline:
                self.inline_functions.append(node)
        return super().visit_FunctionDef(node)


if __name__ == "__main__":

    transformer = InlineTransformer()
    with open(sys.argv[1], "rb") as source:
        source_tree = cst.parse_module(source.read())

    modified_tree = source_tree.visit(transformer)

    # print(modified_tree.code)
