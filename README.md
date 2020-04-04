# A wrapper around argparse

Writing complex subcommand parsers using `argparse` is certainly possible, but it involves a lot
of laborious repetition.

This library provides a small wrapper around `argparse` that adds a convenience method. That
lets you specify a sequence of words that form a command, together with flags - and the
definitions of those flags are passed at the same time.

    parser = ArgumentParser()
    parser.add_command("foo bar baz --json",
                       func=lambda *args: print("foo-bar-baz"),
                       json=dict(default=False, action="store_true"),
                       )
    parser.add_command("foo bar quux",
                       func=lambda *args: print("foo-bar-quux"),
                       )

The `func` parameter will be set on the resulting namespace. Note, there is no particular requirement
for the arguments that must be passed to `func` - this is down to the library user to define.

Additionally, a new `argparse.Action` subclass is provided, `OptionalOverride`. This supports
having the *same* flag appear in a global position and be repeated by a subcommand. It works
well - in as much as defaults set by the global position won't be re-set in the subordinate
position.

    parser.add_command("--flag", flag=dict(default="foo"))
    parser.add_command("xyzzy --flag", flag=dict(action=OptionalOverride))

Where a flag is repeated in an `add_command` call, the second and subsequent values receive an
`OptionalOveride` setting automatically.

    parser.add_command("--glob xyzzy --glob", glob=dict(action=OptionalOverride))

Finally, `AtMostOnce` is supplied as an action type; this causes an explicit error (rather than
just overriding the previous value) if a flag is specified more than once.
