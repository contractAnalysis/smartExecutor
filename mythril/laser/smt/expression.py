"""This module contains the SMT abstraction for a basic symbol expression."""
from typing import Optional, Set, Any, TypeVar, Generic, cast
import z3
import fdg

Annotations = Set[Any]
T = TypeVar("T", bound=z3.ExprRef)


class Expression(Generic[T]):
    """This is the base symbol class and maintains functionality for
    simplification and annotations."""

    def __init__(self, raw: T, annotations: Optional[Annotations] = None):
        """

        :param raw:
        :param annotations:
        """
        self.raw = raw

        if annotations:
            assert isinstance(annotations, set)

        self._annotations = annotations or set()

    @property
    def annotations(self) -> Annotations:
        """Gets the annotations for this expression.

        :return:
        """

        return self._annotations

    def annotate(self, annotation: Any) -> None:
        """Annotates this expression with the given annotation.

        :param annotation:
        """

        self._annotations.add(annotation)

    def simplify(self) -> None:
        """Simplify this expression."""
        # self.raw = cast(T, z3.simplify(self.raw))
        if fdg.global_config.flag_preprocessing:
            pass
        else:
            self.raw = cast(T, z3.simplify(self.raw))

    def simplify_yes(self) -> None:
        """Simplify this expression."""
        self.raw = cast(T, z3.simplify(self.raw))


    def __repr__(self) -> str:
        return repr(self.raw)

    def size(self):
        return self.raw.size()

    def __hash__(self) -> int:
        return self.raw.__hash__()

    def get_annotations(self, annotation: Any):
        return list(filter(lambda x: isinstance(x, annotation), self.annotations))


G = TypeVar("G", bound=Expression)


def simplify(expression: G) -> G:
    """Simplify the expression .

    :param expression:
    :return:
    """
    expression.simplify()
    return expression

# change simplify() for the benefits of preprocessing
# simplication can cause some data missing in conditions collected in the preprocessing
# I would like to get the slots read in conditions
#@wei
def simplify_yes(expression: G) -> G:
    """Simplify the expression .

    :param expression:
    :return:
    """
    expression.simplify_yes()
    return expression
