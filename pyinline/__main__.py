import sys
import libcst as cst
from pyinline import InlineTransformer
from rich.console import Console

if __name__ == "__main__":
    transformer = InlineTransformer()
    with open(sys.argv[1], "rb") as source:
        source_tree = cst.parse_module(source.read())

    modified_tree = source_tree.visit(transformer)
    console = Console()
    console.print(source_tree.code)
    console.print("------------------- After ---------------------")
    console.print(modified_tree.code)
