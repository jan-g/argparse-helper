import argparse_helper as argparse
from argparse_helper import UsageError
import pytest


def test_arg_parser():
    p = make_arg_parser()
    with pytest.raises(SystemExit):
        p.parse_args("hello world".split())


def test_works():
    p = make_arg_parser()
    print(p._tree)
    a = p.parse_args("--aa a --bb b item1 list".split())
    assert a.func(a) == "item1_list"


def test_sublists():
    p = argparse.ArgumentParser()
    p.add_command("--maj --min",
                  maj=dict(dest="mmm", action=argparse.MajorAppend),
                  min=dict(dest="mmm", action=argparse.MinorAppend(major="maj")),
                  )

    # Major items are returned in order
    a = p.parse_args("--maj 1 --maj 2 --maj 3".split())
    assert list(a.mmm.keys()) == ["1", "2", "3"]

    # Minor items are associated with their preceding major
    a = p.parse_args("--maj 1 --min a --min b --maj 2 --maj 3 --min c".split())
    assert list(a.mmm.keys()) == ["1", "2", "3"]
    assert a.mmm == {"1": ["a", "b"], "2": [], "3": ["c"]}


def test_sublist_minor_requires_major():
    p = argparse.ArgumentParser()
    p.add_command("--maj --min",
                  maj=dict(dest="mmm", action=argparse.MajorAppend),
                  min=dict(dest="mmm", action=argparse.MinorAppend(major="maj")),
                  )

    # Minor items without a preceding major cause an error
    e = None
    try:
        a = p.parse_args("--min a --min b --maj 3 --min c".split())
    except UsageError as e2:
        e = e2
    assert str(e) == "--min options require a preceding --maj"


def test_at_most_once():
    p = argparse.ArgumentParser()
    p.add_command("--foo", foo=dict(action=argparse.AtMostOnce))

    a = p.parse_args("".split())
    assert a.foo is None

    a = p.parse_args("--foo f1".split())
    assert a.foo == "f1"

    with pytest.raises(UsageError) as e:
        a = p.parse_args("--foo f1 --foo f2".split())
    assert e.value.args[0] == "--foo may be specified at most once"


def test_optional_override():
    p = argparse.ArgumentParser()
    p.add_command("--foo", foo=dict(action=argparse.OptionalOverride))
    with pytest.raises(SystemExit):
        a = p.parse_args("--foo f1".split())


def sanitise(val):
    if isinstance(val, str):
        return val.replace(" ", "_")
    else:
        return ""


@pytest.mark.parametrize("command,func,expected", [
    ("", None, "foo"),            # Without any flag, the global default is used
    ("g", "g", "foo"),           # Without any flag, the global default is used
    ("--f bar g", "g", "bar"),   # Global position sets the flag
    ("g --f baz", "g", "baz"),   # Local position sets the flag
    ("--f f1 --f f2", UsageError("--f may be specified at most once"), None),      # AtMostOnce holds
    ("--f bar --f baz g", UsageError("--f may be specified at most once"), None),  # AtMostOnce globally
    ("--f bar g --f baz", UsageError("--f may be specified at most once"), None),  # AtMostOnce straddles subcommand
    ("g --f bar --f baz", UsageError("--f may be specified at most once"), None),  # AtMostOnce inherited
], ids=sanitise)
def test_optional_overrides(command, func, expected):
    p = argparse.ArgumentParser()
    p.add_command("--f g --f",
                  func=cmd("g"),
                  f=dict(default="foo", action=argparse.AtMostOnce))

    try_parser(p, command, func, {"f": expected})


def cmd(name):
    def _(*args, **kwargs):
        return name
    _.__name__ = name
    return _


class A:
    def __init__(self, *values):
        self.values = values

    def __eq__(self, other):
        return type(self) == type(other) and vars(self) == vars(other)

    def __str__(self):
        return "{}({})".format(type(self).__name__, vars(self))


@pytest.mark.parametrize("command,func,values", [
    ("", None, dict(api_endpoint="https://some.service.or.other/v1", aa="foo", bb="bar")),
    ("--help", SystemExit(0), {}),
    ("config", None, {}),
    ("config list", "config_list", dict(json=False)),
    ("config list --json", "config_list", dict(json=True)),
    ("config sub list --json", "config_sub_list", dict(json=True)),
    ("item1 list", "item1_list", dict()),
    ("item1 --json list", SystemExit(2), dict()),
    ("item1 frob --item1 i1 --file f1 --item2 i2 --type1", "item1_frob", dict(item1="i1", type1=True, type2=False)),
    ("item1 frob --item1 i1 --type2", "item1_frob", dict(item1="i1", type1=False, type2=True, file=None)),
    ("item1 frob --item2 i2 --type2", SystemExit(2), dict()),   # missing required argument
    ("item1 download", SystemExit(2), dict()),
    ("item1 download --item1 i1", "item1_download", dict(item1="i1", file="file.dat", type1=False, type2=False)),
    ("item1 upload", SystemExit(2), dict()),
    ("item1 upload --item1 i1 --file bar.dat --type1 --type2", "item1_upload", dict(item1="i1", file="bar.dat", type1=True, type2=True)),
    ("item2 list --json --max 6 --show-widgets --name blargh --item2 i2 --show-grommets", "item2_list",
        dict(json=True, max=6, show_widgets=True, name="blargh", item2="i2", show_grommets=True)),
    ("item2 create --json --config c1 --type1 --type2 --item3 i3 --item1 i1", "item2_create",
        dict(json=True, config="c1", item3s={"i3": ["i1"]})),
    ("bb show", "bb_show", dict(json=False, aa="foo", bb="bar")),
    ("bb show --json --aa a2 --bb b2", "bb_show", dict(aa="a2", bb="b2")),
    ("bb list --json --aa a2", "bb_list", dict(aa="a2", json=True)),
    ("bb create --json --aa a2 --bb b2 --loc1 l1 --path ..", "bb_create",
        dict(json=True, aa="a2", bb="b2", loc1="l1", loc2=None, path="..")),
    ("--aa a0 bb create --json --aa a2", UsageError("--aa may be specified at most once"), dict()),
    ("--aa a0 --aa a1 bb create --json", UsageError("--aa may be specified at most once"), dict()),
    ("bb create --json --aa a2 --aa a3", UsageError("--aa may be specified at most once"), dict()),
    ("bb create --json --foo bar baz --foo x y", "bb_create", dict(foo=[A("bar", "baz"), A("x", "y")])),
], ids=sanitise)
def test_complex_commands(command, func, values):
    p = make_arg_parser()
    try_parser(p, command, func, values)


def try_parser(parser, command, func, values):
    # Sometimes we want to catch an exception
    if isinstance(func, BaseException):
        with pytest.raises(type(func)) as e:
            print(parser.parse_args(command.split()))
        assert e.value.args == func.args
        return

    a = parser.parse_args(command.split())
    assert a.func() == func
    for k in values:
        assert getattr(a, k) == values[k]


def make_arg_parser():
    # A more complex example
    cfg = {"aa": "foo", "bb": "bar"}

    parser = argparse.ArgumentParser()

    # Some options show up repeatedly. Specify them like this
    json = dict(json=dict(default=False, action="store_true"))
    item_type = dict(type1=dict(default=False, action="store_true"),
                     type2=dict(default=False, action="store_true"),
                     )

    parser.add_command("--api-endpoint --aa --bb",
                       api_endpoint=dict(
                           default="https://some.service.or.other/v1"),
                       aa=dict(default=cfg.get("aa"), action=argparse.AtMostOnce),
                       bb=dict(default=cfg.get("bb"), action=argparse.AtMostOnce),
                       )

    parser.add_command("config list --json",
                       func=cmd("config_list"),
                       **json,
                       )

    parser.add_command("config sub list --json",
                       func=cmd("config_sub_list"),
                       **json,
                       )

    parser.add_command("item1 list --json",
                       func=cmd("item1_list"),
                       **json,
                       )

    parser.add_command("item1 frob --item1 --file --item2 --type1 --type2",
                       func=cmd("item1_frob"),
                       item1=dict(required=True),
                       file=dict(default=None),
                       item2=dict(default=None),
                       **item_type,
                       )

    parser.add_command("item1 download --item1 --file --type1 --type2",
                       func=cmd("item1_download"),
                       item1=dict(required=True),
                       file=dict(default="file.dat"),
                       **item_type,
                       )

    parser.add_command("item1 upload --item1 --file --type1 --type2",
                       func=cmd("item1_upload"),
                       item1=dict(required=True),
                       file=dict(default="file.dat"),
                       **item_type,
                       )

    parser.add_command("item2 list --json --max --show-widgets --name --item2 --show-grommets",
                       func=cmd("item2_list"),
                       **json,
                       max=dict(type=int),
                       show_widgets=dict(default=False, action="store_true"),
                       show_grommets=dict(default=False, action="store_true"),
                       )

    parser.add_command("item2 create --json --config --type1 --type2 --item3 --item1",
                       func=cmd("item2_create"),
                       **json,
                       config=dict(default=None),
                       **item_type,
                       item3=dict(dest="item3s", action=argparse.MajorAppend),
                       item1=dict(dest="item3s", action=argparse.MinorAppend("item3")),
                       )

    # Here we need to explicitly specify that these are overrides, or defaults will be reset
    parser.add_command("bb show --json --aa --bb",
                       func=cmd("bb_show"),
                       **json,
                       aa=dict(action=argparse.OptionalOverride),
                       bb=dict(action=argparse.OptionalOverride),
                       )

    parser.add_command("bb list --json --aa",
                       func=cmd("bb_list"),
                       **json,
                       aa=dict(action=argparse.OptionalOverride),
                       )

    parser.add_command("bb create --json --aa --bb --loc1 --loc2 --path --foo",
                       func=cmd("bb_create"),
                       **json,
                       aa=dict(action=argparse.OptionalOverride),
                       bb=dict(action=argparse.OptionalOverride),
                       path=dict(default="."),
                       foo=dict(action=argparse.AppendN(A), nargs=2)
                       )

    return parser
