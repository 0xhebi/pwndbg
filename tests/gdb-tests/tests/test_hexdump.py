from __future__ import annotations

import gdb
from pwnlib.util.cyclic import cyclic

import pwndbg
import pwndbg.aglib.memory
import pwndbg.aglib.regs
import pwndbg.aglib.vmmap
import tests

BINARY = tests.binaries.get("reference-binary.out")


def run_tests(stack, use_big_endian, expected):
    pwndbg.config.hexdump_group_use_big_endian = use_big_endian

    # Put some data onto the stack
    pwndbg.aglib.memory.write(stack, cyclic(0x100))

    # Test empty hexdump
    result = gdb.execute("hexdump 0", to_string=True)
    assert result == "+0000 0x000000  \n"

    results = []
    # TODO: Repetition is not working in tests
    results.append(gdb.execute(f"hexdump {stack} 64", to_string=True))
    results.append(gdb.execute(f"hexdump {stack} 3", to_string=True))

    assert len(results) == len(expected)
    for i, result in enumerate(results):
        expected_result = expected[i]
        assert result == expected_result


def test_hexdump(start_binary):
    start_binary(BINARY)
    pwndbg.config.hexdump_group_width = -1

    # TODO: Setting theme options with Python isn't working
    gdb.execute("set hexdump-byte-separator")
    stack_addr = pwndbg.aglib.regs.rsp - 0x100

    expected = [
        f"""+0000 0x{stack_addr:x}  6161616261616161 6161616461616163 │aaaabaaa│caaadaaa│
+0010 0x{stack_addr+0x10:x}  6161616661616165 6161616861616167 │eaaafaaa│gaaahaaa│
+0020 0x{stack_addr+0x20:x}  6161616a61616169 6161616c6161616b │iaaajaaa│kaaalaaa│
+0030 0x{stack_addr+0x30:x}  6161616e6161616d 616161706161616f │maaanaaa│oaaapaaa│\n""",
        f"""+0000 0x{stack_addr:x}            616161                  │aaa     │        │\n""",
    ]
    run_tests(stack_addr, True, expected)

    expected = [
        f"""+0000 0x{stack_addr:x}  6161616162616161 6361616164616161 │aaaabaaa│caaadaaa│
+0010 0x{stack_addr+0x10:x}  6561616166616161 6761616168616161 │eaaafaaa│gaaahaaa│
+0020 0x{stack_addr+0x20:x}  696161616a616161 6b6161616c616161 │iaaajaaa│kaaalaaa│
+0030 0x{stack_addr+0x30:x}  6d6161616e616161 6f61616170616161 │maaanaaa│oaaapaaa│\n""",
        f"""+0000 0x{stack_addr:x}  616161                            │aaa     │        │\n""",
    ]
    run_tests(stack_addr, False, expected)


def test_hexdump_collapse_lines(start_binary):
    start_binary(BINARY)
    sp = pwndbg.aglib.regs.rsp

    pwndbg.aglib.memory.write(sp, b"abcdefgh\x01\x02\x03\x04\x05\x06\x07\x08" * 16)

    def hexdump_lines(lines):
        offset = (lines - 1) * 0x10  # last line offset
        skipped_lines = lines - 2

        out = gdb.execute(f"hexdump $rsp {offset+16}", to_string=True)

        expected = (
            f"+0000 0x{sp:x}  61 62 63 64 65 66 67 68  01 02 03 04 05 06 07 08  │abcdefgh│........│\n"
            f"... ↓            skipped {skipped_lines} identical lines ({skipped_lines*16} bytes)\n"
            f"+{offset:04x} 0x{sp+offset:x}  61 62 63 64 65 66 67 68  01 02 03 04 05 06 07 08  │abcdefgh│........│\n"
        )
        assert out == expected

    hexdump_lines(3)
    hexdump_lines(4)
    hexdump_lines(10)


def test_hexdump_saved_address_and_offset(start_binary):
    # TODO There is no way to verify repetition: the last_address and offset are reset
    # before each command
    start_binary(BINARY)
    sp = pwndbg.aglib.regs.rsp

    SIZE = 21

    pwndbg.aglib.memory.write(sp, b"abcdefgh\x01\x02\x03\x04\x05\x06\x07\x08" * 16)

    out1 = gdb.execute(f"hexdump $rsp {SIZE}", to_string=True)
    out2 = (
        f"+0000 0x{sp:x}  61 62 63 64 65 66 67 68  01 02 03 04 05 06 07 08  │abcdefgh│........│\n"
        f"+0010 0x{sp+0x10:x}  61 62 63 64 65                                    │abcde   │        │\n"
    )

    assert out1 == out2
    assert pwndbg.commands.hexdump.hexdump.last_address == sp + SIZE
    assert pwndbg.commands.hexdump.hexdump.offset == SIZE
