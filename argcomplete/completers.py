# Copyright 2012-2013, Andrey Kislyuk and argcomplete contributors.
# Licensed under the Apache License. See https://github.com/kislyuk/argcomplete for more info.

from __future__ import absolute_import, division, print_function, unicode_literals

import os, sys, subprocess
from .compat import USING_PYTHON2, str, sys_encoding

def _wrapcall(*args, **kwargs):
    try:
        return subprocess.check_output(*args, **kwargs).decode().splitlines()
    except AttributeError:
        return _wrapcall_2_6(*args, **kwargs)
    except subprocess.CalledProcessError:
        return []

def _wrapcall_2_6(*args, **kwargs):
    try:
        # no check_output in 2.6
        if "stdout" in kwargs:
            raise ValueError("stdout argument not allowed, it will be overridden.")
        process = subprocess.Popen(stdout=subprocess.PIPE, *args, **kwargs)
        output, unused_err = process.communicate()
        retcode = process.poll()
        if retcode:
            cmd = kwargs.get("args")
            if cmd is None:
                cmd = args[0]
            raise subprocess.CalledProcessError(retcode, cmd)
        return output.decode().splitlines()
    except subprocess.CalledProcessError:
        return []

class ChoicesCompleter(object):
    def __init__(self, choices):
        self.choices = []
        for choice in choices:
            if isinstance(choice, bytes):
                choice = choice.decode(sys_encoding)
            if not isinstance(choice, str):
                choice = str(choice)
            self.choices.append(choice)

    def __call__(self, prefix, **kwargs):
        return (c for c in self.choices if c.startswith(prefix))

def EnvironCompleter(prefix, **kwargs):
    return (v for v in os.environ if v.startswith(prefix))

class FilesCompleter(object):
    """
    File completer class, optionally takes a list of allowed extensions
    """
    def __init__(self,allowednames=(),directories=True):
        # Fix if someone passes in a string instead of a list
        if isinstance(allowednames, (str, bytes)):
            allowednames = [allowednames]

        self.allowednames = [x.lstrip("*").lstrip(".") for x in allowednames]
        self.directories = directories

    def __call__(self, prefix, **kwargs):
        completion = []
        if self.allowednames:
            if self.directories:
                files = _wrapcall(["bash", "-c", "compgen -A directory -- '{p}'".format(p=prefix)])
                completion += [ f + "/" for f in files]
            for x in self.allowednames:
                completion += _wrapcall(["bash", "-c", "compgen -A file -X '!*.{0}' -- '{p}'".format(x,p=prefix)])
        else:
            completion += _wrapcall(["bash", "-c", "compgen -A file -- '{p}'".format(p=prefix)])
            anticomp = _wrapcall(["bash", "-c", "compgen -A directory -- '{p}'".format(p=prefix)])
            completion = list( set(completion) - set(anticomp))

            if self.directories:
                completion += [f + "/" for f in anticomp]
        return completion

class _FilteredFilesCompleter(object):
    def __init__(self, predicate):
        """
        Create the completer

        A predicate accepts as its only argument a candidate path and either
        accepts it or rejects it.
        """
        assert predicate, "Expected a callable predicate"
        self.predicate = predicate

    def __call__(self, prefix, **kwargs):
        """
        Provide completions on prefix
        """
        target_dir = os.path.dirname(prefix)
        try:
            names = os.listdir(target_dir or ".")
        except:
            return # empty iterator
        incomplete_part = os.path.basename(prefix)
        # Iterate on target_dir entries and filter on given predicate
        for name in names:
            if not name.startswith(incomplete_part):
                continue
            candidate = os.path.join(target_dir, name)
            if not self.predicate(candidate):
                continue
            yield candidate + "/" if os.path.isdir(candidate) else candidate

class DirectoriesCompleter(_FilteredFilesCompleter):
    def __init__(self):
        _FilteredFilesCompleter.__init__(self, predicate=os.path.isdir)
