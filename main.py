from preprocessing.tokenizer.tokenize import TokenizeException, ProperPPToken
from preprocessing.tokenized_stream import TokenizedStream, render_stream
from preprocessing.tokenizer.identifier import Identifier
from preprocessing.directives import (
    preprocess,
    DirectiveExecutionContext,
    DirectiveException,
)
from compilation_ctx import CompilationCtx
import traceback

from span import Span, SourceStream, Source, MarkColor

if __name__ == "__main__":
    args = ["main.py", "-Dbeans", "-fno-brain-rot", "test_src/main.c", "-I", "test_src", "-L", "/Library/Developer/CommandLineTools/SDKs/MacOSX11.3.sdk/usr/include"]

    ctx = CompilationCtx.from_args(args)

    data = SourceStream(ctx.input_source(), 0)

    try:
        tokenized = TokenizedStream.tokenize(data)

        dectx = DirectiveExecutionContext(ctx)
        preprocess(tokenized, dectx)
        tokenized.idx = tokenized.entries[tokenized.end].next

        for le in tokenized.collect():
            if isinstance(le, Identifier):
                print(repr(le))
                le.span.source.print_spans([(le.span, MarkColor.INFO_BLUE)])

    except TokenizeException as e:
        traceback.print_exc()
        print("Tokenization error:", e.msg)
        data.source.print_spans([(e.span, MarkColor.ERROR_RED)])
    except DirectiveException as e:
        # traceback.print_exc()
        print("Directive expansion error:", e.msg)
        data.source.print_spans([(e.span, MarkColor.ERROR_RED)])
