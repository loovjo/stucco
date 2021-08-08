from __future__ import annotations
from typing import List, Dict, Optional
from enum import Enum


class BrainRotAmount(Enum):
    REDUCED = -1
    STANDARD = 0
    EXTRA = 1


class CompilationCtxArgsParseException(Exception):
    def __init__(self, msg: str, argidx: Optional[int] = None) -> None:
        super().__init__()
        self.msg = msg
        self.argidx = argidx

    def __str__(self) -> str:
        return f"{self.__class__.__name__}(msg={self.msg})"

class CompilationCtx:
    def __init__(
        self,
        input_file: str,

        output_file: Optional[str] = None,
        include_paths: Optional[List[str]] = None,
        predefined_macros: Optional[Dict[str, str]] = None,
        brain_rot_amount: Optional[BrainRotAmount] = None,

        compiler_path: Optional[str] = None,
    ) -> None:
        self.input_file = input_file
        self.output_file = output_file or "a.out"
        self.include_paths = include_paths or []
        self.predefined_macros = predefined_macros or {}
        self.brain_rot_amount = brain_rot_amount or BrainRotAmount.STANDARD

        self.compiler_path = compiler_path

    def __str__(self) -> str:
        return f"{self.__class__.__name__}(" \
                f"input_file={self.input_file!r}, " \
                f"output_file={self.output_file!r}, " \
                f"include_paths={self.include_paths!r}, " \
                f"predefined_macros={self.predefined_macros!r}, " \
                f"brain_rot_amount={self.brain_rot_amount!r})" \

# Option format:
    #   <file>. Compile <file>. Can only appear once
    #   -o<file> or -o <file>: Output to <file>. Default a.out. Can only appear once
    #   -I<path> or -I <path>: Include <path>. Can appear multiple times
    #   -D<name>=<code> or -D <name>=<code>: Define macro <name> to be <code>
    #   -D<name> or -D <name>: Define macro <name> to be 1
    #
    #   -fno-brain-rot, -fextra-brain-rot: Set brain rot amount
    #
    #   TODO following arguments
    #   -: Read from stdin
    #   -U<name>: Undefine name (?)

    # args include file name
    @staticmethod
    def from_args(args: List[str]) -> CompilationCtx:
        input_file = None

        output_file = None
        include_paths = []
        predefined_macros = {}
        brain_rot_amount = None

        compiler_path = None

        argidx = 0
        while argidx < len(args) - 1:
            argidx += 1 # intentionally skip arg 0

            arg = args[argidx]
            if arg == "":
                continue

            if arg[0] == "-":
                if len(arg) == 1:
                    # TODO: Support - as option
                    raise CompilationCtxArgsParseException("Stdin input through - is not yet supported", argidx)
                elif arg[1] == "o":
                    name = None
                    if len(arg) == 2:
                        argidx += 1
                        if argidx >= len(args):
                            raise CompilationCtxArgsParseException("Expected path after -o", argidx - 1)
                        name = args[argidx]
                    else:
                        name = arg[2:]

                    if output_file is not None:
                        raise CompilationCtxArgsParseException("Multiple values for -o", argidx - 1)

                    output_file = name
                    continue
                elif arg[1] == "I":
                    name = None
                    if len(arg) == 2:
                        argidx += 1
                        if argidx >= len(args):
                            raise CompilationCtxArgsParseException("Expected path after -I", argidx - 1)
                        name = args[argidx]
                    else:
                        name = arg[2:]

                    include_paths.append(name)
                    continue
                elif arg[1] == "D":
                    macro = None

                    if len(arg) == 2:
                        argidx += 1
                        if argidx >= len(args):
                            raise CompilationCtxArgsParseException("Expected macro after -D", argidx - 1)
                        macro = args[argidx]
                    else:
                        macro = arg[2:]

                    name = macro
                    code = "1"
                    if "=" in macro:
                        name, code = macro.split("=", 1)

                    predefined_macros[name] = code
                    continue
                elif arg[1] == "f":
                    if arg == "-fno-brain-rot":
                        brain_rot_amount = BrainRotAmount.REDUCED
                        continue
                    elif arg == "-fextra-brain-rot":
                        brain_rot_amount = BrainRotAmount.EXTRA
                        continue

                raise CompilationCtxArgsParseException(f"Unknown option {arg}", argidx)
            else:
                if input_file is None:
                    input_file = arg
                else:
                    raise CompilationCtxArgsParseException("Only one input file can be specified", argidx)


        if input_file is None:
            raise CompilationCtxArgsParseException("Missing input file!")


        return CompilationCtx(
            input_file=input_file,

            output_file=output_file,
            include_paths=include_paths,
            predefined_macros=predefined_macros,
            brain_rot_amount=brain_rot_amount,

            compiler_path=compiler_path,
        )
