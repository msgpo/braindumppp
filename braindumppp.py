"""
braindumppp (Braindump Pre Processor)

This is called on one file and preprocesses includes and links in this file based on a pre-constructed bidirectional link graph.

a file must begiven as parameter,the output is written to standard out

Author: ulno

"""
USAGE = """
braindumpp input-dir output-dir

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


TODO: think about to allow also a precise (non fuzzy) include, maybe just give comparison threshold in %

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
  TODO: check this behavior and make sure a warning is printed to stderr



"""

import sys
import os
import shutil
import re
import yaml # for loading and saving the index
import difflib  # to allow fuzzy string matching
#import fuzzywuzzy # alternative (faster?) fuzzy string matching

# constants
INDEX_FILENAME = ".braindumppp.yaml"

# regular expressions to match the different commands
MATCH_COMMAND = re.compile(r'\!\!(i|\ |r|l)([^\!]*)\!')

COMMENT = "!!#"

EXTENSIONS = ["md", "txt", "rst", "lyx", "tex", "html", "xml"]
LABEL_FORMATS = {  # Labels/Anchors in specific markups
    "md": '<a name="%s"/>',
    "rst": '<a name="%s"/>',
    "html": '<a name="%s"/>',
    "xml": '<a name="%s"/>'
}
LINK_FORMATS = {  # Links in specific markups
    "md": ("[%(link)s]","[%(label)s](%(link)s)"),
    "rst": ("`%(link)s <%(link)s>`_","`%(label)s <%(link)s>`_"),
    "html": ('<a href="%(link)s">%(link)s</a>','<a href="%((link)s">%(label)s</a>'),
}
# global initialization
# This matches files-paths minus their extension to a list of pairs
# TODO: rethink how to really handle the extensions
# The first element of the pair is the file-path of the file included or referenced
# The second element of the pair a sorted list with all the line-numbers from where  file
index_list = {}
reverse_index_list = {}
root_input_path = "."
index_file_path = None
# indentation = 0  # usually not indented

# some helper functions
def eprint(*args):
    print(*args,file=sys.stderr)
def write(*args):
    print(*args,end="")


def find_file_in_tree(filename_approximation, threshold=0.8):
    global index_list
    find = None
    new_threshold = 0
    for p in index_list:
        s = difflib.SequenceMatcher(None, p, filename_approximation)
        match = ''.join(p[i:i+n] for i, j, n in s.get_matching_blocks() if n)
        new_threshold = len(match) / float(len(filename_approximation))
        if new_threshold >= threshold:
            threshold = new_threshold
            find = p
    return find


def add_to_reverse_index(current_path, from_path, from_label, to_label):
    global reverse_index_list
    # add to reverse index
    if from_path in reverse_index_list:
        reference_list = reverse_index_list[from_path]
    else:
        reference_list = []
        reverse_index_list[from_path] = reference_list
    reference_list.append((from_label,to_label,current_path))


def add_to_index(current_path, from_path, from_label, to_label):
    global index_list
    # add to index
    reference_list = index_list[current_path]
    reference_list.append((from_path, from_label, to_label))
    # add to reverse index
    add_to_reverse_index(current_path,from_path,from_label,to_label)


def add_backlink(output_file, file_type, current_path, from_path, from_label, to_label):
    # TODO: add threshold
    if from_path != None and from_path != "":
        label_name="__blt_" + from_path # BackLinkTarget
        if from_label != None and from_label != "":
            label_name += "_" + from_label
        if output_file is not None:
            output_file.write(LABEL_FORMATS[file_type] % {"label",label_name})
        hit = find_file_in_tree(from_path)
        if hit != "":
            add_to_index(current_path, hit,from_label,to_label)
        else:
            add_to_index(current_path, from_path, from_label, to_label)


def command_input(output_file, file_type, current_path, arg, indentation=""):
    # TODO: check number of arguments and show warning if too many
    # parse args
    args = arg.split()
    to_label = None
    from_label = None
    from_path = None
    if len(args) >= 2:  # to-label given
        to_label = args[1]
    if len(args) >= 1:
        # Now we might have a dot showing the label
        from_split = args[0].split(".")
        if len(from_split) >= 2:
            from_label = from_split[1]
        from_path = from_split[0]

    # TODO: determine exect from_path with search in tree already here
    add_backlink(output_file, file_type, current_path, from_path, from_label, to_label)

    parse_file(from_path, file_type, from_label, to_label, threshold=0.8, indentation=indentation, output_file=output_file)


def command_link( output_file, file_type, current_path, arg, threshold=0.8 ):
    # create an internal link (to another document in the same space)
    # TODO: check number of arguments and show warning if too many
    # parse args
    args = arg.split()
    from_label = None
    from_path = None
    link_text = None
    if len(args) >= 2:  # text given
        link_text = " ".join(args[1:])
    if len(args) >= 1:
        # Now we might have a dot showing the label
        from_split = args[0].split(".")
        if len(from_split) >= 2:
            from_label = from_split[1]
        from_path = from_split[0]

    # TODO: resolve the path better and include current_path
    p = find_file_in_tree( from_path, threshold=threshold )

    add_backlink(output_file, file_type, current_path, from_path, from_label, None)

    # TODO:support also non-markdown
    if output_file is not None:
        if link_text is not None:
            output_file.write(LINK_FORMATS[file_type][1] % {"label": link_text, "link":p})
        else:
            output_file.write(LINK_FORMATS[file_type][0] % {"link",p})


def command_label( arg ):
    # TODO: check number of arguments and show warning if too many
    s = arg.split()
    if len(s) == 0:
        return ""
    return s[0]


def command_references( output_file, file_type, current_path, current_label, arg ):
    # TODO: check number of arguments and show warning if too many
    # TODO: add threshold
    s = arg.split()
    if len(s) >= 0:
        # TODO: check markup type in s[0]
        output = ""
        # TODO: use fuzzy find
        hit = find_file_in_tree(current_path,threshold=0.8)
        if hit != "":
            for r in reverse_index_list[hit]:
                # TODO: check current_label and show only respective in-links based on option?
                (from_label, to_label, source_path) = r
                output += "Source: " + source_path + " "
                if from_label is not None:
                    output += "from-label: %s " % from_label
                if to_label is not None:
                    output += "to-label: %s " % to_label
            if output != "":
                if output_file is not None:
                    output_file.write("references: %s"%output)
        else:  # no backlinks found
            eprint("No incoming backlinks for %s" % current_path)

# command_lookup = {
#     'i': command_input,
#     ' ': command_link,
#     'l': command_label,
#     'r': command_references
# }


def parse_file(filename_approximation, file_type, from_label=None,
               to_label=None, threshold=0.8, indentation="",
               output_file = None):
    # first, we need to find the file
    # then match all the lines

    # TODO: implement from and to labels
    # TODO: implement reverse links

    # global indentation
    global root_input_path

    count = 0
    printing = from_label is None
    p = find_file_in_tree(filename_approximation, threshold=threshold)
    if p is not None:
        count += 1
        first = True
        for l in open(os.path.join(root_input_path, p)):
            if l.startswith("!!!"):
                if output_file is not None:
                    output_file.write(l[3:])  # do not parse this line but remove the exclamation marks
                continue
            # scan for comment and eventually cut it off
            comment_find = l.find(COMMENT)
            if comment_find != -1:
                line_ending = ""
                if l[-1] == "\n":
                    line_ending = "\n"
                    if len(l)>1 and l[-2] == "\r":
                        line_ending = "\r\n"
                l = l[0:comment_find] + line_ending
            # first do current indentation
            if first:
                first = False
            else:
                if printing and output_file is not None:
                    # write(" " * indentation) # if not first line indent (else already indented)
                    line_copy = l.strip()
                    if len(line_copy) > 0: # ignore lines with only whitespace
                        output_file.write(indentation) # if not first line indent (else already indented)
            current_start = 0
            for m in MATCH_COMMAND.finditer(l):
                extra_indent = m.start()
                old_indentation = indentation
                indentation += l[current_start:extra_indent]
                if printing and output_file is not None:
                    output_file.write(l[current_start:extra_indent]) # already print prefix
                current_start = m.end()
                # indentation += extra_indent # the future may be indented
                t = tuple(m.groups()[1:])
                label = None
                # label = command_lookup[m.groups()[0]](*t)
                c = m.groups()[0]
                if c == 'l': # allow label detection even when not printing
                    label = command_label(*t)
                elif printing:
                    if c == ' ':
                        command_link(output_file, file_type, p, *t)
                    elif c == 'i':
                        command_input(output_file, file_type, p, *t, indentation=indentation)
                    elif c == 'r':
                        command_references(output_file, file_type, p, label, *t)
                if from_label is not None and label is not None:  # There was actually a label found
                    if label == from_label:  # TODO: compare fuzzy
                        printing = True
                    else:
                        # if no to-label is given, all other labels disable printing again
                        if to_label is None:
                            printing = False
                        else:  # else disable when to_label found TODO: fuzzy?
                            if label == to_label:
                                printing = False
                #indentation -= extra_indent # back to previous indentation
                indentation = old_indentation # remove indentation
            # print unprocessed rest
            if output_file is not None and printing:
                output_file.write(l[current_start:])
                output_file.flush()  # TODO: remove
    else:
        eprint("Input file not found.")


def init_index(input_dir):
    """
    Try to read existing graph index from disk.
    """
    global index_list
    global root_input_path, root_output_path
    global index_file_path

    if os.path.exists(os.path.join(root_input_path, INDEX_FILENAME)):
        # try to read it
        index_file_path = os.path.join(root_input_path, INDEX_FILENAME)

        try:
            index_list = yaml.safe_load(open(index_file_path))
        except:
            # catch errors like file not found or corrupt data
            # TODO: treat no write permissions differently (think how and if)
            # TODO: print warning to stderr
            index_list = {} # initialize with empty dict
            # TODO: more initialization necessary?

    if index_list is None:
        index_list = {}

    # update the reference graph by reading all files
    # walk from start_path and init the file-tree
    for dir_path, dir_names, file_names in os.walk(root_input_path, topdown=True, followlinks=True):
        dir_path_stripped = dir_path[len(root_input_path) + 1:]
        for f in file_names:
            base_name_ext_tuple = os.path.splitext(f)
            if len(base_name_ext_tuple) > 1 \
                and base_name_ext_tuple[1][1:] in EXTENSIONS:
                file_type = base_name_ext_tuple[1]
                parse_file(os.path.join(dir_path_stripped, f), file_type, threshold=1.0, output_file=None)
            path_name = os.path.join(dir_path, f)[len(root_input_path) + 1:]  # cut off root-path
            if not path_name in index_list:
                index_list[path_name] = []


def parse_directory(input_dir,output_dir):
    # walk from start_path and init the file-tree
    # TODO: check last accessed (and also its dependencies) value from index to eventually skip
    input_dir_real_path = os.path.realpath(input_dir)
    output_dir_real_path = os.path.realpath(output_dir)
    for dir_path, dir_names, file_names in os.walk(input_dir_real_path, topdown=True, followlinks=True):
        dir_path_stripped = dir_path[len(input_dir_real_path)+1:]
        for f in file_names:
            src = os.path.join(input_dir_real_path, dir_path_stripped, f)
            dest = os.path.join(output_dir_real_path, dir_path_stripped, f)
            base_name_ext_tuple = os.path.splitext(f)
            if len(base_name_ext_tuple) > 1 \
                and base_name_ext_tuple[1][1:] in EXTENSIONS:
                file_type = base_name_ext_tuple[1][1:]
                output_file = open(dest, "w")
                parse_file(os.path.join(dir_path_stripped,f), file_type, threshold=1.0, output_file=output_file)
                output_file.close()
            else:  # if extension not found, just copy
                shutil.copy(src, dest)
            path_name = os.path.join(dir_path, f)[len(root_input_path) + 1:]  # cut off root-path
            if not path_name in index_list:
                index_list[path_name] = []

        for d in dir_names:  # create destination dirs if necessary
            os.mkdirs(os.path.join(output_dir, d), exist_ok=True)




def main():
    global global_indentation, index_file_path
    global root_input_path, root_output_path
    if len(sys.argv) != 3: # exactly one input-dir and one output-dir need to be given
        print(USAGE)
        return 1
    global_indentation = 0  # indentation initially to 0
    input_dir = sys.argv[1]
    output_dir = sys.argv[2]
    root_input_path = os.path.realpath(input_dir)
    root_output_path = os.path.realpath(output_dir)
    init_index(input_dir)  # try to load graph index or init it
    parse_directory(input_dir,output_dir)  # parse all files recursively

    # write back index file
    yaml.dump(index_list, open(index_file_path,"w"))  # TODO:consider backups

    return 0  # success


if __name__ == '__main__':
    sys.exit(main())