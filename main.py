from preprocessing.tokenizer.tokenize import TokenizeException, ProperPPToken
from preprocessing.tokenized_stream import TokenizedStream
from preprocessing.directives import (
    preprocess,
    DirectiveExecutionContext,
    DirectiveException,
)
from compilation_ctx import CompilationCtx
import traceback

from span import Span, SourceStream, Source, MarkColor

if __name__ == "__main__":
    args = ["main.py", "-Dbeans", "-fno-brain-rot", "x.c", "-I", "sample_code"]
    ctx = CompilationCtx.from_args(args)
    print(ctx)

    code = r"""
// #if 1 == 1
#include <the.h>
#include "helloboi.h"
#define S_(x) #x
#define S(x) S_(x)
#define dprintf(...) printf(__FILE__ ":" S(__LINE__) ": " __VA_ARGS__)
#define E 2.71

dprintf(E);

#undef E
// #endif
// #error "helo world"

"""[
        1:-1
    ]

    data = SourceStream(Source("x.c", code), 0)

    try:
        tokenized = TokenizedStream.tokenize(data)

        dectx = DirectiveExecutionContext()
        preprocess(tokenized, dectx)
        print(dectx.macros.keys())

        while True:
            thing = tokenized.pop_token()
            if thing is None:
                break

            print(repr(thing))
            data.source.print_spans([(thing.span, MarkColor.INFO_BLUE)])
            # input()

        print("end:")
        data.source.print_spans([(data.point_span(), MarkColor.INFO_BLUE)])

        # ctx.source.print_spans([(thing.span, MarkColor.INFO_BLUE) for thing in parsed])

    except TokenizeException as e:
        traceback.print_exc()
        print("Tokenization error:", e.msg)
        data.source.print_spans([(e.span, MarkColor.ERROR_RED)])
    except DirectiveException as e:
        # traceback.print_exc()
        print("Directive expansion error:", e.msg)
        data.source.print_spans([(e.span, MarkColor.ERROR_RED)])
