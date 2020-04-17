__license__ = "Apache License 2.0"
__author__ = "jan grant <argparse-helper@ioctl.org>"

import argparse
from argparse import *
from collections import defaultdict
import inspect


class ArgumentParser(argparse.ArgumentParser):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.register('action', 'parsers', _SubParsersActionAug)
        self._tree = {}
        self._branch = None
        self._parent = None
        self.set_defaults(func=lambda *args, **kwargs: self.print_usage())

    def add_command(self, line, func=None, **kwargs):
        """Build and traverse a subparser tree and decorate with flags and functions.

        Example:
            p.add_command("--global-flag foo bar --local-flag --global-flag",
                          func=cmd_foo_bar,
                          global_flag=dict(default="global-default"),
                          local_flag=dict(default=False, action="store_true"),
                          )
        """
        words = line.split()
        parser = self
        # Deep copy, since we're going to mutate these
        arg_opts = {k: dict(kwargs[k]) for k in kwargs}

        for word in words:
            if word.startswith("--"):
                key = word[2:].replace("-", "_")
                opts = arg_opts[key] = arg_opts.get(key, dict())
                parser.add_argument(word, **opts)
                # Let a flag be repeated, overriding the more global value
                opts['action'] = OptionalOverride
            elif word in parser._tree:
                parser = parser._tree[word]
            else:
                if parser._branch is None:
                    parser.add_subparsers()
                parser = parser._tree[word] = parser._branch.add_parser(word)

        if func is not None:
            parser.set_defaults(func=func)
        return parser

    def add_subparsers(self, *args, **kwargs):
        self._branch = super().add_subparsers(*args, **kwargs)
        return self._branch

    def parse_args(self, *args, namespace=None):
        return super().parse_args(*args, namespace=namespace)


class _SubParsersActionAug(argparse._SubParsersAction):
    def __init__(self, *args, **kwargs):
        frame = inspect.currentframe()
        try:
            self._parent = frame.f_back.f_locals['self']
            self._parent._branch = self
        finally:
            del frame
        super().__init__(*args, **kwargs)

    def add_parser(self, name, *args, **kwargs):
        parser = super().add_parser(name, *args, **kwargs)
        self._parent._tree[name] = parser
        parser._parent = self._parent
        return parser

    def __call__(self, parser, namespace, values, option_string=None):
        # This is entire copied to change one aspect of its behaviour :-(
        parser_name = values[0]
        arg_strings = values[1:]

        # set the parser name if requested
        if self.dest is not SUPPRESS:
            setattr(namespace, self.dest, parser_name)

        # select the parser
        try:
            parser = self._name_parser_map[parser_name]
        except KeyError:
            args = {'parser_name': parser_name,
                    'choices': ', '.join(self._name_parser_map)}
            msg = _('unknown parser %(parser_name)r (choices: %(choices)s)') % args
            raise ArgumentError(self, msg)

        # parse all the remaining options into the namespace
        # store any unrecognized options on the object, so that the top
        # level parser can decide what to do with them

        # In case this subparser defines new func defaults, we parse them
        # in a new namespace object and then update the original
        # namespace for the relevant parts.

        # However, we preserve any 'special' namespace markers in order that
        # nesting-aware Actions can operate on them.
        temp_namespace = Namespace()
        for key, value in vars(namespace).items():
            if key.startswith("__"):
                setattr(temp_namespace, key, value)
        subnamespace, arg_strings = parser.parse_known_args(arg_strings, temp_namespace)
        for key, value in vars(subnamespace).items():
            setattr(namespace, key, value)

        if arg_strings:
            vars(namespace).setdefault(argparse._UNRECOGNIZED_ARGS_ATTR, [])
            getattr(namespace, argparse._UNRECOGNIZED_ARGS_ATTR).extend(arg_strings)


class OptionalOverride(argparse.Action):
    """This can be used to repeat an argument in a subcommand

    It will update the same value as the parent; but adding it as an argument
    won't cause any default values to be reset in the namespace."""
    def __init__(self, option_strings, dest, **kwargs):
        self.__orig_dest = dest
        super().__init__(option_strings, "__override_{}".format(dest), **kwargs)

    def __call__(self, parser, namespace, values, option_string=None):
        # Go hunting for the original
        action = None
        parent = parser._parent
        while parent is not None:
            for action in parent._actions:
                if option_string in action.option_strings:
                    parent = None
                    break
            else:
                parent = parent._parent

        if action is None:
            raise ArgumentError(self, "could not find antecedent action for {}".format(option_string))

        # Ideally we would do this on the antecedent namespace
        return action(parser, namespace, values, option_string=option_string)


class MajorAppend(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        d = getattr(namespace, self.dest)
        if d is None:
            d = defaultdict(list)
            setattr(namespace, self.dest, d)

        d[values] = []
        setattr(namespace, "__last_{}".format(self.dest), d[values])


def MinorAppend(major=None):
    class _MinorAppend(argparse.Action):
        def __call__(self, parser, namespace, values, option_string=None):
            try:
                d = getattr(namespace,  "__last_{}".format(self.dest))
            except AttributeError:
                raise UsageError("{} options require a preceding --{}".format(self.option_strings[0], major))

            d.append(values)
    return _MinorAppend


class AtMostOnce(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        d = getattr(namespace, "__set_{}".format(self.dest), False)
        if d:
            raise UsageError("{} may be specified at most once".format(self.option_strings[0]))

        setattr(namespace, self.dest, values)
        setattr(namespace, "__set_{}".format(self.dest), True)


def AppendN(type=str):
    class _AppendN(argparse._AppendAction):

        def __call__(self, parser, namespace, values, option_string=None):
            super().__call__(parser, namespace, type(*values), option_string)

    return _AppendN


class UsageError(Exception):
    pass
