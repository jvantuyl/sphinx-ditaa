#ditaa sphinx-doc extension

This adds a basic ditaa builder for sphinx.
Supports html,latex and latexpdf output.

**Python 3 compatible.**

##Usage:

    .. ditaa::
      +--------+   +-------+    +-------+
      |        | --+ ditaa +--> |       |
      |  Text  |   +-------+    |diagram|
      |Document|   |!magic!|    |       |
      |     {d}|   |       |    |       |
      +---+----+   +-------+    +-------+
          :                         ^
          |       Lots of work      |
          +-------------------------+

or alternatively

    .. ditaa:: some/file/name.ditaa

##Installation

it has got a setup.py script so just usual `python setup.py build` and
`install` will suffice.
