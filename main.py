from preprocessing.tokenizer.tokenize import tokenize, TokenizeException, PPToken
from span import Span, SourceCtx, Source, MarkColor

if __name__ == "__main__":
    code = r"""
#include <stdio>
// hello
/* hello */
// hello \
world
int main(){ ??/
int i = 10;
i++++;
printf("%d\n",i);
}
"""[1:-1]


    ctx = SourceCtx(Source("x.py", code), 0)

    try:
        parsed = tokenize(ctx)

        for thing in parsed:
            if isinstance(thing, PPToken) or True:
                print(repr(thing))
                ctx.source.print_spans([(thing.span, MarkColor.INFO_BLUE)])
                # input()

        print("end:")
        ctx.source.print_spans([(ctx.point_span(), MarkColor.INFO_BLUE)])

        ctx.source.print_spans([(thing.span, MarkColor.INFO_BLUE) for thing in parsed])

    except TokenizeException as e:
        print("Error:", e.msg)
        ctx.source.print_spans([(e.span, MarkColor.ERROR_RED)])
