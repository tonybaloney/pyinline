from ast import arg
import sys
import libcst as cst
from pyinline import InlineTransformer
from rich.console import Console
import difflib
import argparse

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--diff", action="store_true", help="Print as diff")
    parser.add_argument("file", action="store", help="file to transform")
    args = parser.parse_args()
    transformer = InlineTransformer()
    with open(args.file, "rb") as source:
        source_tree = cst.parse_module(source.read())

    modified_tree = source_tree.visit(transformer)
    console = Console()
    if args.diff:
        console.print(
            "\n".join(
                difflib.unified_diff(
                    source_tree.code.splitlines(), modified_tree.code.splitlines()
                )
            )
        )
    else:
        console.print(modified_tree.code)
