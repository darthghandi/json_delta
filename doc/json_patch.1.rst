============
 json_patch
============

Synopsis
========

::

  json_diff [--output FILE] [--unified | --normal] 
            [--strip NUM] [--reverse] [originalfile] [patchfile]
  json_diff [--version]
  json_diff [--help]

Description
===========

json_patch applies diffs in the format produced by
:manpage:`json_diff(1)` to JSON-serialized data structures.

The program attempts to mimic the interface of the :manpage:`patch(1)`
utility as far as possible, while also remaining compatible with the
script functionality of the `json_delta.py` library on which it
relies.  There are, therefore, at least four different ways its input
can be specified.

#. The simplest, of course, is if the filenames are both specified as
   positional arguments.

#. Closely following in terms of simplicity, the inputs can be fed as
   a JSON array ``[<structure>, <patch>]`` to standard input.

#. If only one positional argument is specified, it is read as the
   filename of the original data structure, and the patch is expected
   to appear on stdin.

#. Finally, if there are no positional arguments, and stdin cannot be
   parsed as JSON, it can alternatively be a udiff, as output by
   ``json_diff -u``.  In this case, json_patch will read the name of
   the file containing the structure to modify out of the first header
   line of the udiff (the one beginning with ``---``).

The most salient departure from the behavior of :manpage:`patch(1)` is
that, by default, json_patch will **not** modify files in place.
Instead, the patched structure is written as JSON to stdout.  Frankly,
this is to save having to implement backup filename options, getting
it wrong, and having angry hackers blame me for their lost data.

However, the input structure is read into memory before the output
file handle is opened, so an in-place modification can be accomplished
by setting the option ``--output`` to point to ``<originalfile>``.

Also, note that json_diff and json_patch can only manipulate a single
file at a time: even the output of ``json_diff -u`` is not a "unified"
diff *sensu stricto*.

Options
=======

--output FILE, -o FILE   Write output to FILE instead of stdout.
--unified, -u            Force the patch to be interpreted as a udiff.
--normal, -n             Force the patch to be interpreted as a normal
                         (i.e. JSON-format) patch
--reverse                Assume the patch was created with old and new 
                         files swapped.
--string NUM             Strip NUM leading components from file names 
                         read out of udiff headers.

--version                Show the program's version number and exit.

--help, -h               Show a brief help message and exit.

Udiff Format
============

The program has strict requirements of the format of "unified" diffs.
It works by discarding header lines, then creating two strings: one by
discarding every line beginning with ``-``, then discarding the first
character of every remaining line, and one following the same
procedure, but with lines beginnig with ``+`` discarded.  For
json_patch to function, these strings must be interpretable according
to a superset of the JSON spec, which I will now describe:

* Within objects, the string ``...`` may appear in any context where a
  ``"property": <object>`` construction would be valid JSON.  This
  indicates that one or more properties have been omitted from the
  representation of the object.

* Within arrays, the string ``...`` may appear as an array element.
  It may optionally be followed by an integer in parentheses,
  e.g. ``(1)``, ``(15)``.  This indicates that that number of elements
  have been omitted from the array, or that one element has, if no
  parenthesized number is present.

By interpreting the strings extracted from the udiff according to this
format, json_patch arrives at a subset of each of the structures that
it expresses the delta between.  To construct its output, it then
replaces the ``...`` constructions with object properties and/or array
elements from the structure to be patched (if they are not present in
the other subset, which would indicate that the diff expects that that
node in the structure is to be deleted).
