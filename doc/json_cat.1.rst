==========
 json_cat
==========

Synopsis
========

::

   json_cat [FILE]...

Description
===========

Concatenate FILE(s), or standard input together and write them to
standard output as a JSON array.

Input streams are parsed as JSON if possible, otherwise they are added
to the array as strings.

Examples
========

::

   $ echo '{"foo": true, "bar": false,
   >        "baz": null}' > foofile
   $ json_cat foofile - << 'EOF'
   > This text cannot be parsed as JSON.
   > EOF
   [{"foo": true, "bar": false, "baz": null}, "This text cannot be parsed as JSON."]
   $ echo 'You can use json_cat to create 1-element JSON arrays of text,
   > if that'\''s something you like to do...' | json_cat
   ["You can use json_cat to create 1-element JSON arrays of text, if that's something you like to do..."]


