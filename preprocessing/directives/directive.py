from __future__ import annotations
from typing import List, Dict, Union, Optional
from abc import ABC, abstractmethod
import time

from ..tokenizer.tokenize import LexicalElement, SpaceSequence
from span import Span, Source, PseudoFilename
from ..tokenized_ctx import TokenizedCtx

from ..tokenizer.punctuator import Punctuator, PunctuatorType
from ..tokenizer.identifier import Identifier

PREDEFINED_MACROS_SOURCE = Source(PseudoFilename.PREDEFINED_MACROS, "")

class Macro(ABC):
    pass

class FunctionMacro(Macro):
    def __init__(self, parameters: List[str], has_varargs: bool, body: List[LexicalElement]) -> None:
        self.parameters = parameters
        self.has_varargs = has_varargs
        self.body = body

class ObjectMacro(Macro):
    def __init__(self, body: List[LexicalElement]) -> None:
        self.body = body

MONTHS = [
    "Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"
]

# TODO: make sure -fmore-brain-rot makes this give some completely different date
# The standard doesn't specify you *must* return the *current* time
def current_date() -> str:
    time_struct = time.localtime()

    return f"{MONTHS[time_struct.tm_mon-1]} {time_struct.tm_mday:2} {time_struct.tm_year}"

def current_time() -> str:
    time_struct = time.localtime()

    return f"{time_struct.tm_hour:02}:{time_struct.tm_min:02}:{time_struct.tm_min:02}"

def make_str_macro(st: str) -> Macro:
    from ..tokenizer.string import StringLiteral, StringPrefix

    span = Span(PREDEFINED_MACROS_SOURCE, 0, 0)
    return ObjectMacro(
        [StringLiteral(span, StringPrefix.NONE, st)]
    )

def make_int_macro(num: int) -> Macro:
    from ..tokenizer.number import PPNumber, Digit, Exponent, Dot

    span = Span(PREDEFINED_MACROS_SOURCE, 0, 0)
    digits: List[Union[Digit, Exponent, Dot, str]] = [Digit(span, int(digit)) for digit in str(num)]

    return ObjectMacro([PPNumber(span, digits)])

# Stores things like currently defined macros, etc.
class DirectiveExecutionContext:
    def __init__(self) -> None:
        self.macros: Dict[str, Macro] = {
            # from section 6.10.8.1
            "__DATE__": make_str_macro(current_date()),
            "__STDC__": make_int_macro(0), # TODO: Change this to 1!
            "__STDC_HOSTED__": make_int_macro(1),
            "__TIME__": make_str_macro(current_time()),
        }
        self.line_nr_offset = 0 # used by `#line` to control the behaviour of the __LINE__ macro

class DirectiveException(Exception):
    def __init__(self, msg: str, span: Span) -> None:
        self.msg = msg
        self.span = span

class DirectiveError(DirectiveException):
    pass

# Modifies tokens in place, may throw DirectiveException
def preprocess(tokens: TokenizedCtx, ctx: DirectiveExecutionContext) -> None:
    ctx = DirectiveExecutionContext()

    while True:
        tok = tokens.pop_token()
        if tok is None:
            break
        if isinstance(tok, Punctuator) and tok.ty == PunctuatorType.HASH:
            before = tokens.peek_element(-2)
            if before is None or isinstance(before, SpaceSequence) and before.has_nl:
                directive_name_ident = tokens.pop_token()
                if directive_name_ident is None:
                    raise DirectiveException("File ended after directive start!", tok.span)
                if not isinstance(directive_name_ident, Identifier):
                    raise DirectiveException(f"# followed by a non-identifier ({directive_name_ident})", directive_name_ident.span)
                name = directive_name_ident.identifier

                print("Detected barco:", name)

                if name == "define":
                    preprocess_define(tokens, ctx)
                elif name == "undef":
                    preprocess_undef(tokens, ctx)
                elif name == "error":
                    preprocess_error(tokens, ctx)
                elif name == "include":
                    preprocess_include(tokens, ctx)
                elif name in ["if", "ifdef", "ifndef"]:
                    preprocess_if_group(name, tokens, ctx)
                elif name == "line":
                    preprocess_line(tokens, ctx)
                elif name == "pragma":
                    preprocess_pragma(tokens, ctx)
        else:
            pass

def preprocess_define(tokens: TokenizedCtx, ctx: DirectiveExecutionContext) -> None:
    raise NotImplementedError("#define is not yet implemented")

def preprocess_undef(tokens: TokenizedCtx, ctx: DirectiveExecutionContext) -> None:
    raise NotImplementedError("#undef is not yet implemented")

def preprocess_error(tokens: TokenizedCtx, ctx: DirectiveExecutionContext) -> None:
    raise NotImplementedError("#error is not yet implemented")

def preprocess_include(tokens: TokenizedCtx, ctx: DirectiveExecutionContext) -> None:
    raise NotImplementedError("#error is not yet implemented")

def preprocess_if_group(name: str, tokens: TokenizedCtx, ctx: DirectiveExecutionContext) -> None:
    raise NotImplementedError("#if... is not yet implemented")

def preprocess_line(tokens: TokenizedCtx, ctx: DirectiveExecutionContext) -> None:
    raise NotImplementedError("#if... is not yet implemented")

def preprocess_pragma(tokens: TokenizedCtx, ctx: DirectiveExecutionContext) -> None:
    raise NotImplementedError("#pragma... is not yet implemented")
