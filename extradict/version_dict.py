# coding: utf-8
"""
Module for a versioned version of Python's dictionaries -
one can retrieve any "past" value that had existed previously
by using the "get" method with an extra "version" parameter -
also, the "version" is an explicit read only attribute
that allows one to know wether a dictionary had  changed.

"""

try:
    from collections.abc import MutableMapping
except ImportError:
    from collections import MutableMapping

from collections import namedtuple, OrderedDict
import threading


VersionedValue = namedtuple("VersionedValue", "version value")

_Deleted = object()


class VersionDict(MutableMapping):
    _dictclass = dict
    def __init__(self, *args, **kw):
        self._version = 0
        initial = self._dictclass(*args, **kw)
        self.data = self._dictclass()
        for key, value in initial.items():
            self.data[key] = [VersionedValue(self._version, value)]
        self.local= threading.local()
        self.local._updating = False

    def copy(self):
        new = VersionDict.__new__(self.__class___)
        from copy import copy
        new._version = self._version
        new.data = copy(self.data)
        return new

    def update(self, other):
        """The update operation uses a single version number for
            all affected keys
        """
        with threading.Lock():
            self._version += 1
            try:
                self.local._updating = True
                super(VersionDict, self).update(other)
            finally:
                self.local._updating = False


    def get(self, item, default=_Deleted, version=None):
        """
            VersionedDict.get(item, default=None) -> same as dict.get
            VersionedDict.get(item, [default=Sentinel], version) ->
                returns existing value at the given dictionary version. If
                value was not set, and no default is given,
                raises KeyError (unlike regular dict)
        """
        if version is None:
            return super(VersionDict, self).get(item, default=(None if default is _Deleted else default))
        try:
            values = self.data[item]
            i = -1
            while values[i].version > version:
                i -= 1
        except (KeyError, IndexError):
            if default is not _Deleted:
                return default
            raise KeyError("'{}' was not set at dict version {}".format(item, version))
        if values[i].value is _Deleted:
            if default is not _Deleted:
                return default
            raise KeyError("'{}' was not set at dict version {}".format(item, version))
        return values[i].value

    def __getitem__(self, item):
        value = self.data[item][-1]
        if value.value is _Deleted:
            raise KeyError("'{}' is a deleted key".format(item))
        return value.value

    def __setitem__(self, item, value):
        with threading.Lock():
            if not self.local._updating:
                self._version += 1
            if item not in self.data:
                self.data[item] = []
            self.data[item].append(VersionedValue(self._version, value))

    def __delitem__(self, item):
        self._version += 1
        self.data[item].append(VersionedValue(self._version, _Deleted))

    def __iter__(self):
        for key, value in self.data.items():
            if value[-1].value is not _Deleted:
                yield key

    def __len__(self):
        return sum(1 for x in self.data.values() if x[-1].value != _Deleted)

    @property
    def version(self):
        return self._version

    def __repr__(self):
        return "<{}({}) at version {}>".format(
            self.__class__.__name__,
            ", ".join("{}={!r}".format(*item) for item in self.items()),
            self.version
        )


class OrderedVersionDict(VersionDict):
    _dictclass = OrderedDict
    def __iter__(self):
        versions_for_keys = {}
        for key, values in self.data.items():
            if values[-1].value is _Deleted:
                continue
            versions_for_keys.setdefault(values[-1].version, []).append(key)
        for version in sorted(versions_for_keys.keys()):
            # yield from versions_for_keys[key]
            for key in versions_for_keys[version]:
                yield key