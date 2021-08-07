from preprocessing.tokenizer.tokenize import TokenizeException, ProperPPToken
from preprocessing.tokenized_ctx import TokenizedCtx

from span import Span, SourceCtx, Source, MarkColor

if __name__ == "__main__":
    code = r"""
hello $ world

"""[1:-1]


    ctx = SourceCtx(Source("x.py", code), 0)

    try:
        tokenized = TokenizedCtx.tokenize(ctx)

        while True:
            thing = tokenized.pop_token()
            if thing is None:
                break

            print(repr(thing))
            ctx.source.print_spans([(thing.span, MarkColor.INFO_BLUE)])
            # input()

        print("end:")
        ctx.source.print_spans([(ctx.point_span(), MarkColor.INFO_BLUE)])

        # ctx.source.print_spans([(thing.span, MarkColor.INFO_BLUE) for thing in parsed])

    except TokenizeException as e:
        print("Error:", e.msg)
        ctx.source.print_spans([(e.span, MarkColor.ERROR_RED)])
