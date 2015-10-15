# -*- coding: utf-8 -*-
"""
    sphinx.ext.ditaa
    ~~~~~~~~~~~~~~~~~~~~~~~~~

    Allow ditaa-formatted graphs to by included in Sphinx-generated
    documents inline.

    :copyright: Copyright 2011 by Arthur Gautier
    :copyright: Copyright 2011 by Zenexity
    :license: BSD, see LICENSE for details.
"""

import codecs
import os
import re
import tempfile
from subprocess import Popen, PIPE
try:
    from hashlib import sha1 as sha
except ImportError:
    from sha import sha

from docutils import nodes
from docutils.parsers.rst import directives

from sphinx.errors import SphinxError
from sphinx.util.osutil import ensuredir, EINVAL, ENOENT, EPIPE
from sphinx.util.compat import Directive
from sphinx.util.pycompat import sys_encoding


mapname_re = re.compile(r'<map id="(.*?)"')
svg_dim_re = re.compile(r'<svg\swidth="(\d+)pt"\sheight="(\d+)pt"', re.M)


class DitaaError(SphinxError):
    category = 'Ditaa error'


class ditaa(nodes.General, nodes.Element):
    pass


class Ditaa(Directive):
    """
    Directive to insert ditaa markup.
    """
    has_content = True
    required_arguments = 0
    optional_arguments = 1
    final_argument_whitespace = False
    option_spec = {
        'alt': directives.unchanged,
        'inline': directives.flag,
        'caption': directives.unchanged,
    }

    def run(self):
        if self.arguments:
            document = self.state.document
            if self.content:
                return [document.reporter.warning(
                    'Ditaa directive cannot have both content and '
                    'a filename argument', line=self.lineno)]
            env = self.state.document.settings.env
            rel_filename, filename = env.relfn2path(self.arguments[0])
            env.note_dependency(rel_filename)
            try:
                fp = codecs.open(filename, 'r', 'utf-8')
                try:
                    dotcode = fp.read()
                finally:
                    fp.close()
            except (IOError, OSError):
                return [document.reporter.warning(
                    'External Ditaa file %r not found or reading '
                    'it failed' % filename, line=self.lineno)]
        else:
            dotcode = '\n'.join(self.content)
            if not dotcode.strip():
                return [self.state_machine.reporter.warning(
                    'Ignoring "ditaa" directive without content.',
                    line=self.lineno)]
        node = ditaa()
        node['code'] = dotcode
        node['options'] = []
        if 'alt' in self.options:
            node['alt'] = self.options['alt']
        if 'caption' in self.options:
            node['caption'] = self.options['caption']
        node['inline'] = 'inline' in self.options
        return [node]


def render_ditaa(self, code, options, prefix='ditaa'):
    """Render ditaa code into a PNG output file."""
    hashkey = code.encode('utf-8') + str(options).encode('utf-8') + \
              str(self.builder.config.ditaa).encode('utf-8') + \
              str(self.builder.config.ditaa_args).encode('utf-8')
    outfname = '%s-%s.png' % (prefix, sha(hashkey).hexdigest())
    outrelfn = os.path.join(self.builder.imgpath, outfname)
    outfullfn = os.path.join(self.builder.outdir, '_images', outfname)

    if os.path.isfile(outfullfn):
        return outrelfn, outfullfn

    if hasattr(self.builder, '_ditaa_warned'):
        return None, None

    ensuredir(os.path.dirname(outfullfn))

    # ditaa expects UTF-8 by default
    if isinstance(code, str):
        code = code.encode('utf-8')

    ditaa_code = tempfile.NamedTemporaryFile(suffix='.ditaa', delete=False)
    ditaa_cmd = [self.builder.config.ditaa]
    ditaa_cmd.extend(self.builder.config.ditaa_args)
    ditaa_cmd.extend(options)
    ditaa_cmd.append(ditaa_code.name)
    ditaa_cmd.append(outfullfn)

    ditaa_code.write(code)
    ditaa_code.close()

    try:
        try:
            p = Popen(ditaa_cmd, stdout=PIPE, stdin=PIPE, stderr=PIPE)
        except OSError as err:
            if err.errno != ENOENT:   # No such file or directory
                raise
            self.builder.warn('ditaa command %r cannot be run: check'
                              ' the "ditaa" and "ditaa_args" settings' %
                              ' '.join(ditaa_cmd))
            self.builder._ditaa_warned = True
            return None, None

        wentWrong = False
        try:
            # Ditaa may close standard input when an error occurs,
            # resulting in a broken pipe on communicate()
            stdout, stderr = p.communicate(code)
        except OSError as err:
            if err.errno != EPIPE:
                raise
            wentWrong = True
        except IOError as err:
            if err.errno != EINVAL:
                raise
            wentWrong = True

        if wentWrong:
            # in this case, read the standard output and standard error streams
            # directly, to get the error message(s)
            stdout, stderr = p.stdout.read(), p.stderr.read()
            p.wait()

        if p.returncode != 0:
            self.builder._ditaa_warned = True
            raise DitaaError('ditaa exited with error:\n[stderr]\n%s\n'
                             '[stdout]\n%s' % (stderr.decode(sys_encoding),
                                               stdout.decode(sys_encoding)))
    finally:
        os.unlink(ditaa_code.name)

    return outrelfn, outfullfn


def render_ditaa_html(self, node, code, options, prefix='ditaa',
                    imgcls=None, alt=None):
    try:
        fname, outfn = render_ditaa(self, code, options, prefix)
    except DitaaError as exc:
        info = str(exc)
        sm = nodes.system_message(info, type='WARNING', level=2,
                                  backrefs=[], source=node['code'])
        sm.walkabout(self)
        self.builder.warn(info)
        raise nodes.SkipNode

    inline = node.get('inline', False)
    if inline:
        wrapper = 'span'
    else:
        wrapper = 'p'

    self.body.append(self.starttag(node, wrapper, CLASS='ditaa'))
    if fname is None:
        self.body.append(self.encode(code))
    else:
        # nothing in image map (the lines are <map> and </map>)
        self.body.append('<img src="%s"/>\n' %
                         fname)

    self.body.append('</%s>\n' % wrapper)
    raise nodes.SkipNode


def html_visit_ditaa(self, node):
    render_ditaa_html(self, node, node['code'], node['options'])


def render_ditaa_latex(self, node, code, options, prefix='ditaa'):
    try:
        fname, outfn = render_ditaa(self, code, options, prefix)
    except DitaaError as exc:
        info = str(exc)
        sm = nodes.system_message(info, type='WARNING', level=2,
                                  backrefs=[], source=node['code'])
        sm.walkabout(self)
        self.builder.warn(info)
        raise nodes.SkipNode

    if fname is not None:
        self.body.append('\\par\\includegraphics{%s}\\par' % outfn)
    raise nodes.SkipNode


def latex_visit_ditaa(self, node):
    render_ditaa_latex(self, node, node['code'], node['options'])


def setup(app):
    app.add_node(ditaa,
                 html=(html_visit_ditaa, None),
                 latex=(latex_visit_ditaa, None))
    app.add_directive('ditaa', Ditaa)
    app.add_config_value('ditaa', 'ditaa', 'html')
    app.add_config_value('ditaa_args', [], 'html')
