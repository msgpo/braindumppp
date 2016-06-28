# braindumppp
braindumppp is a bi-directional include and link enabler pre-processor for static website generators.

Parameters:

1. Input directory - read all files from this directory (the generated index, will also be stored here)

2. Output directory - copy and transform files into this directory


This is a command-line tool allowing to embed/include referenced files
into other files. While doing this, it creates an index to also allow
the inclusion of the reference into the referenced file.
This leads to the built of a bi-directional graph which can be
traversed starting at any document.
The tool works on a directory and all its sub-directories.
It handles the following extensions (unknown extensions will
be copied just raw):
- md markdown
- txt raw text or markdown
- rst restructured text
- tex latex
- lyx LaTeX frontend
- html
- xml


The idea/vision is to create a pre-processor for static website
generators like jekkyl, hugo, pelican, or nikola to turn them into a
thought-mapping tool. It also allows to parse text editing programming
languages like latex or lyx.

It should lead to an advanced note taking and mind mapping system, which
I call initially just braindump (maybe TSAR - Text Storage and Retrieval
would be nice too, credit Andreas Karabaczek).

Extra requirements:
- The referencing system shall be tolerant and try to also match
similarly named references allowing some kind of fuzzy matching of
potential candidates.
- It should also be possible to just include a part of a file using
either [line numbers, skiiping htese for now] labels, markdown headlines or paragraph names (and
lists of them), as well as pre-processor labels

The format of these includes is the following:
!!i filename_approximation [from[.label] [[tolabel]]!
from and to can either be:
- labels as defined with a pre-processor label
- line numbers <- maybe disable this as it can't be kept consistent,
  the problem is that all the following needs to understand the markup
- paragraph names (or a comma-seperated list - no spaces), a list can
  also be enclosed by curly brackets, then spaces are allowed
- when including, keep the insertion level of the include-directive
  and add also the characters leading to the label as the indentation
  Empty lines are kept empty and not pre-indented with characters or spaces
  (TODO: make this configurable?)

Just a reference (which by default will be rendered in markdown), would look like this:
!! filename_approximation [from[.label] [[tolabel]] [render-language]!


Before markup is understood from the pre-processor, we add include labels in the following format
!!l label_name!
The text after this label is either ended by the next label, the end of the file or an empty label: !!l!

The format of a space holder for showing incoming references:
!!r [type]!
type specifies the markup language in which the references are to be rendered. If empty it will
be markdown.

!!# starts a comment (the rest of the line is ignored)

If the exclamation marks should be rendered, start a line with three exclamation marks.
Then the line is not parsed - only the three exclamation marks are removed.
Example:
!!!This (!!l) will be not parsed by this script. !!# Even not this comment, so it will stay.

Remarks:
- {-commands can not span more than one line.
- Labels and commands must not include curly brackets
- recursive includes are not allowed (if a recursion
  in the include hierarchy is detected, the respective file will not
  be included and nothing will be inserted),
