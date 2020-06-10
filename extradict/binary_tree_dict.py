from collections.abc import Mapping, MutableMapping
from copy import copy
from itertools import zip_longest


"""Implements an AVLTree auto=balancing tree with a Python Mapping interface"""


_empty = object()


class EmptyNode:
    __slots__ = ()
    depth = 0
    value = None

    def __bool__(self):
        return False

    def __len__(self):
        return 0

    def __repr__(self):
        return "EmptyNode"

    def __str__(self):
        return ""

    def __iter__(self):
        return iter(())

    def get(self, key):
        raise KeyError(key)

    def delete(self, key):
        raise KeyError(key)


EmptyNode = EmptyNode()  # The KISS Singleton


class PlainNode:
    __slots__ = "key value _left _right key_func _len _depth".split()
    def __init__(self, key, value=_empty, left=EmptyNode, right=EmptyNode, key_func=None):
        self.key = key
        self.value = value if value != _empty else key
        self.left = left
        self.right = right
        self.key_func = None
        self._depth = 1
        self._len = 1

    @property
    def leaf(self):
        return not (self.left or self.right)

    def _cmp_key(self, key):
        return self.key_func(key) if self.key_func else key

    def insert(self, key, value=_empty, replace=True):
        self_key = self._cmp_key(self.key)
        new_key = self._cmp_key(key)
        if new_key == self_key and replace:
            self.value = value if value is not _empty else key
            return
        try:
            target_str = "left" if new_key < self_key else "right"
        except TypeError as error:
            raise KeyError(f"{key} type incompatible with other keys in the tree")
        target = getattr(self, target_str)
        if target:
            target.insert(key, value, replace)
        else:
            setattr(self, target_str, type(self)(key=key, value=value, key_func=self.key_func))
        self._update_depth()
        self._update_len()

    def get(self, key):
        self_key = self._cmp_key(self.key)
        new_key = self._cmp_key(key)

        if self_key == new_key:
            return self
        try:
            new_key_smaller = new_key < self_key
        except TypeError as error:
            raise KeyError(f"{key} type incompatible with other keys in the tree")

        if new_key_smaller:
            return self.left.get(key)
        return self.right.get(key)

    def get_node_path(self, key, path=None):
        """Retrieve a list of nodes down to the node with the given Key.

        If the key does not exist, the last element is set to EmptyNode
        """
        if path is None:
            path = []
        path.append(self)
        self_key = self._cmp_key(self.key)
        new_key = self._cmp_key(key)
        if self_key == new_key:
            return path
        if new_key < self_key:
            if self.left:
                return self.left.get_node_path(key, path)
        elif self.right:
            return self.right.get_node_path(key, path)
        path.append(EmptyNode)
        return path

    def get_closest(self, key, path=None):
        if path is None:
            path = []
        path.append(self)
        self_key = self._cmp_key(self.key)
        new_key = self._cmp_key(key)
        if self_key == new_key:
            return self, self
        elif new_key > self_key:
            if self.right:
                return self.right.get_closest(key, path)
            return self, self._get_closest_ancestor_on_other_side(path, side="right")
        if self.left:
            return self.left.get_closest(key, path)
        return self._get_closest_ancestor_on_other_side(path, side="left"), self

    def _get_closest_ancestor_on_other_side(self, path, side):
        # backtrack up to detour
        index = len(path) - 1
        while True:
            index -= 1
            if index < 0:
                return EmptyNode
            side_of_child = "same" if getattr(path[index], side) is path[index + 1] else "other"
            if side_of_child == "other":
                return path[index]

    def _update_depth(self):
        self._depth = max(self.left.depth, self.right.depth) + 1

    @property
    def depth(self):
        return self._depth

    @property
    def right(self):
        return getattr(self, "_right", EmptyNode)

    @right.setter
    def right(self, value):
        self._right = value
        self._update_depth()
        self._update_len()

    @property
    def left(self):
        return getattr(self, "_left", EmptyNode)

    @left.setter
    def left(self, value):
        self._left = value
        self._update_depth()
        self._update_len()


    def _mute_into(self, other, full=False):
        self.key = other.key
        self.value = other.value
        self.key_func = other.key_func
        if full:
            self.right = other.right
            self.left = other.left

    def delete(self, key):
        self_key = self._cmp_key(self.key)
        new_key = self._cmp_key(key)

        if self_key == new_key:
            if self.leaf:
                return EmptyNode
            target_str = "left" if self.left.depth > self.right.depth else "right"
            target = getattr(self, target_str)
            self._mute_into(target)
            key = target.key  # key to delete in target subtree.
        else:
            target_str = "left" if new_key < self_key else "right"
            target = getattr(self, target_str)

        setattr(self, target_str, target.delete(key))
        self._update_depth()
        self._update_len()
        return self

    def __iter__(self):
        yield from self.left
        yield self
        yield from self.right

    def _update_len(self):
        self._len = 1 + len(self.left) + len(self.right)

    def __len__(self):
        return self._len

    @property
    def balanced(self):
        return abs(self.left.depth - self.right.depth) <= 1

    def __repr__(self):
        return f"{self.key}, ({repr(self.left) if self.left else ''}, {repr(self.right) if self.right else ''})"



class AVLNode(PlainNode):
    __slots__ = ()

    def insert(self, key, value=_empty, replace=True):
        super().insert(key, value, replace)
        self.balance()

    def balance(self):
        if self.balanced:
            return

        if self.left.depth > self.right.depth:
            self._avl_rotate_right()
        else:
            self._avl_rotate_left()

    def _avl_rotate_left(self):
        new_parent = self.right
        new_self = copy(self)
        new_self.right = new_parent.left
        new_parent.left = new_self
        self._mute_into(new_parent, full=True)

    def _avl_rotate_right(self):
        new_parent = self.left
        new_self = copy(self)
        new_self.left = new_parent.right
        new_parent.right = new_self
        self._mute_into(new_parent, full=True)



class TreeDict(MutableMapping):
    """Implements an AVLTree autobalancing tree with a Python Mapping interface.


    It can be used as a normal dictionary, although it will be much less eficient
    than a native dict.  Key types must not be mixed, or one will get a KeyError.

    The constructor does not accept key/value pairs to be created
    as dictionary members - pass a plain dictionary as first argument
    should be passed if that is needed.

    The keyword arg "key" to the constructor can take a callable analog to the
    "key" argument to "sorted" and "list.sort": it will
    accept one parameter and will be passed the insert/search
    key on all insertions and retrievals. Thus the internal
    order of the underlying tree can be fully customized.

    Having an inner AVL tree and a custom key function,  extra
    features are that `__getitem__` can retrieve a range of itens,
    and `get_closest` will return a tuple of surrounding keys that exist.

    """
    node_cls = AVLNode

    def __init__(self, *args, key=None):
        self.key = key
        self.root = None
        if len(args) == 1 and isinstance(args[0], Mapping):
            args = args[0].items()
        for key, value in args:
            self[key] = value

    def __getitem__(self, key):
        if not self.root:
            raise KeyError(key)
        if isinstance(key, slice):
            return self._getslice(key)
        return self.root.get(key).value

    def __setitem__(self, key, value):
        if self.root is None:
            self.root = self.node_cls(key=key, value=value, key_func=self.key)
        else:
            self.root.insert(key=key, value=value)

    def __delitem__(self, key):
        if not self.root:
            raise KeyError(key)
        if len(self.root) == 1:
            self.root = None
        else:
            self.root.delete(key)

    def get_closest(self, key):
        if not self.root:
            return None, None
        parent1, parent2 = self.root.get_closest(key)
        ret_values = (parent1.key if parent1 else None), (parent2.key if parent2 else None)

    def _get_slice(self, slice_):
        start, _ = self.root.get_closest(slice_.start)
        _, stop = self.root.get_closest(slice_.stop)
        step = slice_.step or 1


    def __iter__(self):
        return (n.key for n in self.root) if self.root else iter(())

    def __len__(self):
        return len(self.root) if self.root else 0

    def __repr__(self):
        return f"{self.__class__.__name__}({', '.join('%r=%r' % (k, v) for k, v in self.items())}{', key_func= %r' % (self.key_func) if self.key_func else ''})"