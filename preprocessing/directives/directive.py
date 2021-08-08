from __future__ import annotations
from typing import List, Dict, Union, Optional
from abc import ABC, abstractmethod
import time

from ..tokenizer.tokenize import LexicalElement, SpaceSequence
from span import Span, Source, PseudoFilename
from ..tokenized_ctx import TokenizedCtx

from ..tokenizer.punctuator import Punctuator, PunctuatorType
from ..tokenizer.identifier import Identifier
from ..tokenizer.string import StringLiteral, StringPrefix

PREDEFINED_MACROS_SOURCE = Source(PseudoFilename.PREDEFINED_MACROS, "")

class Macro(ABC):
    @abstractmethod
    def __repr__(self) -> str:
        pass

class FunctionMacro(Macro):
    def __init__(self, parameters: List[str], has_varargs: bool, body: List[LexicalElement]) -> None:
        self.parameters = parameters
        self.has_varargs = has_varargs
        self.body = body

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.parameters}{', ...' * self.has_varargs}, {self.body})"

class ObjectMacro(Macro):
    def __init__(self, body: List[LexicalElement]) -> None:
        self.body = body

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.body})"

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
                    raise DirectiveException("# followed by a non-identifier", directive_name_ident.span)
                name = directive_name_ident.identifier

                if name == "define":
                    preprocess_define(directive_name_ident, tokens, ctx)
                elif name == "undef":
                    preprocess_undef(directive_name_ident, tokens, ctx)
                elif name == "error":
                    preprocess_error(directive_name_ident, tokens, ctx)
                elif name == "include":
                    preprocess_include(directive_name_ident, tokens, ctx)
                elif name in ["if", "ifdef", "ifndef"]:
                    preprocess_if_group(directive_name_ident, tokens, ctx)
                elif name == "line":
                    preprocess_line(directive_name_ident, tokens, ctx)
                elif name == "pragma":
                    preprocess_pragma(directive_name_ident, tokens, ctx)
                else:
                    # TODO: Should you actually emit an error here?
                    # clang and gcc do, but the standard seems to say they should be ignored
                    raise DirectiveException(f"Unknown directive {name}", directive_name_ident.span)
                continue

        # TODO: Handle identifier for macro expansion
        pass

# Makes a separate subtokenizedctx for the "arguments" of the directive
def get_directive_tokens(tokens: TokenizedCtx) -> TokenizedCtx:
    start = tokens.idx

    while True:
        el = tokens.peek_element()
        if isinstance(el, SpaceSequence) and el.has_nl or el is None:
            break

        tokens.pop_element()

    return TokenizedCtx(tokens.entries, start, tokens.idx)

def preprocess_define(directive_name: Identifier, tokens: TokenizedCtx, ctx: DirectiveExecutionContext) -> None:
    args = get_directive_tokens(tokens)

    name_token = args.pop_token()
    if name_token is None:
        raise DirectiveException("No macro name specified", directive_name.span)

    if not isinstance(name_token, Identifier):
        raise DirectiveException("Macro name has to be an identifier", name_token.span)

    paren_or_space = args.peek_element()
    if isinstance(paren_or_space, Punctuator) and paren_or_space.ty == PunctuatorType.OPEN_PAREN:
        define_function_macro(name_token, args, ctx)
    else:
        define_object_macro(name_token, args, ctx)

def define_object_macro(macro_name: Identifier, contents: TokenizedCtx, ctx: DirectiveExecutionContext) -> None:
    name = macro_name.identifier

    if name in ctx.macros:
        # TODO: We need to check if this macro is identical to the old one
        raise DirectiveException("Object macro already defined", macro_name.span)

    body: List[LexicalElement] = []
    while contents.peek_element() is not None:
        body.append(contents.pop_element()) # type: ignore # we know pop_element won't be None because we just checked in the loop condition

    macro = ObjectMacro(body)
    ctx.macros[name] = macro

def define_function_macro(macro_name: Identifier, contents: TokenizedCtx, ctx: DirectiveExecutionContext) -> None:
    name = macro_name.identifier

    if name in ctx.macros:
        # TODO: We need to check if this macro is identical to the old one
        raise DirectiveException("Function macro already defined", macro_name.span)

    open_paren = contents.pop_element()
    # Following condition is checked before call in preprocess_define
    assert(isinstance(open_paren, Punctuator) and open_paren.ty == PunctuatorType.OPEN_PAREN)

    parameters: List[str] = []
    has_varargs = False
    while True:
        tok = contents.pop_token()
        if tok is None:
            raise DirectiveException("Argument list unexpectedly ended", open_paren.span)

        if isinstance(tok, Identifier):
            param_name = tok
            assert(isinstance(param_name, Identifier))

            parameters.append(param_name.identifier)

            next = contents.pop_token()
            if isinstance(next, Punctuator) and next.ty == PunctuatorType.COMMA:
                continue
            elif isinstance(next, Punctuator) and next.ty == PunctuatorType.CLOSE_PAREN:
                break
            elif next is None:
                raise DirectiveException("Argument list unexpectedly ended", open_paren.span)
            else:
                raise DirectiveException("Expected comma or closing parenthesis", next.span)

        elif isinstance(tok, Punctuator) and tok.ty == PunctuatorType.TRIPLE_DOT:
            has_varargs = True

            next = contents.pop_token()
            if isinstance(next, Punctuator) and next.ty == PunctuatorType.CLOSE_PAREN:
                break
            elif next is None:
                raise DirectiveException("Argument list unexpectedly ended", open_paren.span)
            else:
                raise DirectiveException("Expected comma or closing parenthesis", next.span)
        else:
            raise DirectiveException("Expected parameter name or ...", tok.span)

    body: List[LexicalElement] = []
    while contents.peek_element() is not None:
        body.append(contents.pop_element()) # type: ignore # we know pop_element won't be None because we just checked in the loop condition

    macro = FunctionMacro(parameters, has_varargs, body)
    ctx.macros[name] = macro

def preprocess_undef(directive_name: Identifier, tokens: TokenizedCtx, ctx: DirectiveExecutionContext) -> None:
    args = get_directive_tokens(tokens)

    name_token = args.pop_token()
    if name_token is None:
        raise DirectiveException("Expected macro name", directive_name.span)
    if not isinstance(name_token, Identifier):
        raise DirectiveException("Macro name has to be an identifier", name_token.span)

    after = args.peek_token()
    if after is not None:
        raise DirectiveException("Expected newline", after.span)

    macro_name = name_token.identifier

    if macro_name in ctx.macros:
        del ctx.macros[macro_name]

def preprocess_error(directive_name: Identifier, tokens: TokenizedCtx, ctx: DirectiveExecutionContext) -> None:
    args = get_directive_tokens(tokens)

    error_token = args.pop_token()
    if error_token is None:
        raise DirectiveException("Expected error message", directive_name.span)
    if not isinstance(error_token, StringLiteral):
        raise DirectiveException("Expected string literal", error_token.span)

    after = args.peek_token()
    if after is not None:
        raise DirectiveException("Expected newline", after.span)

    raise DirectiveError(error_token.contents, error_token.span)

def preprocess_include(directive_name: Identifier, tokens: TokenizedCtx, ctx: DirectiveExecutionContext) -> None:
    raise NotImplementedError("#include is not yet implemented")

def preprocess_if_group(directive_name: Identifier, tokens: TokenizedCtx, ctx: DirectiveExecutionContext) -> None:
    raise NotImplementedError("#if... is not yet implemented")

def preprocess_line(directive_name: Identifier, tokens: TokenizedCtx, ctx: DirectiveExecutionContext) -> None:
    raise NotImplementedError("#if... is not yet implemented")

def preprocess_pragma(directive_name: Identifier, tokens: TokenizedCtx, ctx: DirectiveExecutionContext) -> None:
    raise NotImplementedError("#pragma... is not yet implemented")
