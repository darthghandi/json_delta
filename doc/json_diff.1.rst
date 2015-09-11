===========
 json_diff
===========

Synopsis
========

::

  json_diff [--output FILE] [--verbose] [--unified] [left] [right]
  json_diff [--version]
  json_diff [--help]

Description
===========

`json_diff` produces deltas between JSON-serialized data structures.
If no arguments are specified, stdin will be expected to be a JSON
array ``[left, right]``, and the output will be written to stdout.

The default output is itself a JSON data structure, specifically an
array of arrays of the form ``[<keypath>]`` or ``[<keypath>,
<replacement>]``. The companion program :manpage:`json_patch(1)` can
be used to apply such a diff.

A keypath is an array of string or integer tokens specifying a
path to a terminal node in the data structure.  For example, in the
structure ``[{}, {"foo": "bar"}]``, the string ``"bar"`` appears at
the node addressed by the key sequence ``[1, 'foo']``, and the empty
object ``{}`` appears at key sequence ``[0]``.

If a diff stanza is an array of length 1, consisting only of a key
sequence, :manpage:`json_patch(1)` interprets it as an instruction to
delete the node the key sequence points to.  If a stanza is of length
2, the node is replaced by the last element of the stanza.

An alternative output format for `json_diff` is accessed using the
:option:`--unified` / :option:`-u` option.  This is designed to be
more legible to the human eye, inspired by unified diffs as output by
:manpage:`diff(1)`. :manpage:`json_patch(1)` can read
either format, and, since there is enough information in the format,
can apply :option:`--unified` patches in reverse.


Options
=======

--output FILE, -o FILE   Write output to FILE instead of stdout.
--unified, -u            Write diffs in a more legible format, 
                         inspired by the output of ``diff -u``
--verbose                Print compression statistics on stderr.

--version                Show the program's version number and exit.

--help, -h               Show a brief help message and exit.

Examples
========

::

  $ json_diff << 'EOF'
  > [{"foo": "bar"},
  >  {"foo": "bar",
  >   "baz": ["quux"]}]
  > EOF
  [[["baz"],["quux"]]]

  $ cat > foofile << 'EOF'
  > {"foods": ["spam", "spam", "spam", "spam"],
  >  "weaponry": "Mainly battleaxes.",
  >  "spanish inquisition expected": false,
  >  "drinks": "Delicious mead!",
  >  "other supplies": null}
  > EOF
  $ cat > barfile << 'EOF'
  > {"foods": ["spam", "spam", "spam", "pickled eggs", "spam"],
  >  "weaponry": "Mainly battleaxes.",
  >  "spanish inquisition expected": false,
  >  "drinks": "Soda water."}
  > EOF
  $ json_diff -u foofile barfile
  --- foofile	2014-04-14 21:32:00 BST
  +++ barfile	2014-04-14 21:32:17 BST
   {
    "foods":
    ...
    "weaponry": "Mainly battleaxes.",
     ["spam",
      ...(2),
  +   "pickled eggs",
      "spam"]

    "drinks":
  -  "Delicious mead!",
  +  "Soda water.",

  - "other supplies": null
   }
