"""
braindumppp (Braindump Pre Processor)

This is called on one file and preprocesses includes and links in this file based on a pre-constructed bidirectional link graph.

a file must begiven as parameter,the output is written to standard out

Author: ulno

"""
USAGE = """
Bi-directional pre-processor (braindumppp)

This is a command-line tool allowing to embed/include referenced files
into another file. While doing this it creates an index to also allow
the inclusion of the reference into the referenced file.
This leads to the built of a bi-directional graph which can be
traversed starting at any document.

The idea/vision is to create a pre-processor for static website
generators like jekkyl, hugo, pelican, or nikola to turn them into a
thought-mapping tool.

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
import re
import yaml # for loading and saving the index
import difflib  # to allow fuzzy string matching
#import fuzzywuzzy # alternative (faster?) fuzzy string matching

# constants
INDEX_FILENAME = ".braindumppp.yaml"

# regular expressions to match the different commands
MATCH_COMMAND = re.compile(r'\!\!(i|\ |r|l)([^\!]*)\!')

COMMENT = "!!#"

# global initialization
# This matches files-paths minus their extension to a list of pairs
# TODO: rethink how to really handle the extensions
# The first element of the pair is the file-path of the file included or referenced
# The second element of the pair a sorted list with all the line-numbers from where  file
index_list = {}
reverse_index_list = {}
root_path = "."
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


def add_backlink(current_path, from_path, from_label, to_label):
    # TODO: add threshold
    if from_path != None and from_path != "":
        label_name="__blt_" + from_path # BackLinkTarget
        if from_label != None and from_label != "":
            label_name += "_" + from_label
        write('<a name="%s"/>'%label_name)
        hit = find_file_in_tree(from_path)
        if hit != "":
            add_to_index(current_path, hit,from_label,to_label)
        else:
            add_to_index(current_path, from_path, from_label, to_label)


def command_input(current_path, arg, indentation=""):
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
    add_backlink(current_path, from_path, from_label, to_label)

    parse_file(from_path,from_label,to_label,threshold=0.8,indentation=indentation)


def command_link( current_path, arg, threshold=0.8 ):
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

    add_backlink(current_path, from_path, from_label, None)

    # TODO:support also non-markdown
    if link_text is not None:
        write("[%s](%s)" % (link_text, p))
    else:
        write("[%s]" % p)


def command_label( arg ):
    # TODO: check number of arguments and show warning if too many
    s = arg.split()
    if len(s) == 0:
        return ""
    return s[0]


def command_references( current_path, current_label, arg ):
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
                write("references: %s"%output)
        else:  # no backlinks found
            eprint("No incoming backlinks for %s" % current_path)

# command_lookup = {
#     'i': command_input,
#     ' ': command_link,
#     'l': command_label,
#     'r': command_references
# }


def parse_file(filename_approximation, from_label=None, to_label=None, threshold=0.8, indentation=""):
    # first, we need to find the file
    # then match all the lines

    # TODO: implement from and to labels
    # TODO: implement reverse links

    # global indentation

    count = 0
    printing = from_label is None
    p = find_file_in_tree(filename_approximation, threshold=threshold)
    if p is not None:
        count += 1
        first = True
        for l in open(os.path.join(root_path,p)):
            if l.startswith("!!!"):
                write(l[3:])  # do not parse this line but remove the exclamation marks
                continue
            # scan for comment and eventually cut it off
            comment_find = l.find(COMMENT)
            if comment_find != -1:
                line_ending = ""
                if(l[-1] == "\n"):
                    line_ending = "\n"
                    if(len(l)>1 and l[-2] == "\r"):
                        line_ending = "\r\n"
                l = l[0:comment_find] + line_ending
            # first do current indentation
            if first:
                first = False
            else:
                if printing:
                    # write(" " * indentation) # if not first line indent (else already indented)
                    line_copy = l.strip()
                    if len(line_copy) > 0: # ignore lines with only whitespace
                        write(indentation) # if not first line indent (else already indented)
            current_start = 0
            for m in MATCH_COMMAND.finditer(l):
                extra_indent = m.start()
                old_indentation = indentation
                indentation = indentation + l[current_start:extra_indent]
                if printing:
                    write(l[current_start:extra_indent]) # already print prefix
                current_start = m.end()
                # indentation += extra_indent # the future may be indented
                t = tuple(m.groups()[1:])
                label = None
                # label = command_lookup[m.groups()[0]](*t)
                c = m.groups()[0]
                if c == ' ':
                    command_link(p, *t)
                elif c == 'i':
                    command_input(p, *t, indentation=indentation)
                elif c == 'l':
                    label = command_label(*t)
                elif c == 'r':
                    command_references(p, label, *t)
                if from_label != None and label != None:  # There was actually a lable found
                    if label == from_label: # TODO: compare fuzzy
                        printing = True
                    else:
                        # if no to-label is given, all other labels disable printing again
                        if to_label == None:
                            printing = False
                        else: # else disable when to_label found TODO: fuzzy?
                            if label == to_label:
                                printing = False
                #indentation -= extra_indent # back to previous indentation
                indentation = old_indentation # remove indentation
            # print unprocessed rest
            if printing:
                write(l[current_start:])
    else:
        eprint("Input file not found.")


def init_index(file_to_parse):
    """
    Try to read existing graph index from disk.
    """
    global index_list
    global root_path
    global index_file_path

    # find index file in a parent directory
    file_to_parse_real = os.path.realpath(file_to_parse)
    current_path = os.path.dirname(file_to_parse_real)  # start in current
    initial_path = current_path  # save for later
    while True:  # we escape later
        # get new path one directory up
        parent_path = os.path.realpath(os.path.join(current_path,".."))
        if parent_path == current_path:  # we are at the top and didn't find anything
            current_path = initial_path
            break
        current_path = parent_path  # let's move one dir up
        # check if here exists a graph file
        # of course somebody could in between now delete the graph-file, however, this would just
        # trigger the regeneration of the file at this position.
        # Therefore, using exists should be considered safe
        if os.path.exists(os.path.join(current_path, INDEX_FILENAME)):
            break
    # we should now know the path where the graph file is or should be saved
    # try to read it
    index_file_path = os.path.join(current_path, INDEX_FILENAME)

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

    root_path = current_path

    # walk from start_path and init the file-tree
    for dirpath, dirnames, filenames in os.walk(root_path, topdown=True, followlinks=True):
        for f in filenames:
            path_name = os.path.join(dirpath,f)[len(root_path)+1:]  # cut off root-path
            if not path_name in index_list:
                index_list[path_name] = []

    # strip root from current path
    return file_to_parse_real[len(root_path)+1:]


def main():
    global indentation
    if len(sys.argv) != 2: # exactly one filename needs to be given
        print(USAGE)
        return 1
    file_to_parse = sys.argv[1]
    file_to_parse_relative = init_index(file_to_parse)  # try to load graph index or init it
    indentation = 0  # indentation initially to 0
    parse_file(file_to_parse_relative, threshold=1.0)

    # write back index file
    yaml.dump(index_list, open(index_file_path,"w"))  # TODO:consider backups

    return 0 # success


if __name__ == '__main__':
    sys.exit(main())