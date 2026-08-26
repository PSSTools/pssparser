"""Type stubs for :mod:`pssparser.tokens`.

Hand-written, because ``Token`` and ``TokenStream`` are defined in the Cython
``core`` extension and a type checker cannot see into it.
"""

from typing import Any, Iterator, List, Sequence, Union

CHANNEL_DEFAULT: int
CHANNEL_WS: int
CHANNEL_SL_COMMENT: int
CHANNEL_ML_COMMENT: int
CHANNEL_ERROR: int
CHANNEL_BOM: int

TYPE_ERROR_CHAR: int
TYPE_BOM: int

class Token:
    #: Position in the stream, 0-based and contiguous, trivia included.
    index: int
    #: Lexer token type.
    type: int
    #: Symbolic name of :attr:`type` -- ``"ID"``, ``"SL_COMMENT"``, ...
    type_name: str
    #: One of the ``CHANNEL_*`` constants.
    channel: int
    #: First code point of the token, 0-based, inclusive.
    start: int
    #: Last code point of the token, 0-based, inclusive.
    stop: int
    #: Line of :attr:`start`, 1-based.
    line: int
    #: Column of :attr:`start`, 0-based.
    col: int
    #: The token's source text, exactly as written.
    text: str

    @property
    def is_trivia(self) -> bool: ...
    @property
    def is_comment(self) -> bool: ...
    @property
    def is_error(self) -> bool: ...

class TokenStream(Sequence[Token]):
    tokens: tuple
    num_errors: int
    valid_utf8: bool

    def __len__(self) -> int: ...
    def __iter__(self) -> Iterator[Token]: ...
    def __getitem__(self, idx: Any) -> Any: ...
    @property
    def text(self) -> str: ...
    def code(self) -> List[Token]: ...

def tokenize(src: Union[str, bytes, bytearray, Any]) -> TokenStream: ...
