#!/usr/bin/env python
# coding: utf-8

"""
TVH C renderer
==============

This class renders parsed markdown to TVH C code.

## Authors and License

Copyright (C) 2016 Jaroslav Kysela

License: WTFPL 2
"""

import sys
from textwrap import wrap
from mistune import Markdown, Renderer

HUMAN=False
DEBUG=False

NOLANG_CHARS=" "

def utf8open(fn, mode):
  if sys.version_info[0] < 3:
    return open(fn, mode)
  else:
    return open(fn, mode, encoding='utf-8')

def debug(str):
  sys.stderr.write(f'DEBUG: {str}' + '\n')

class Object:

   pass

class TVH_C_Renderer(Renderer):

  def get_nolang(self, text):
    if not text:
      return ''
    return text if HUMAN else f'_{len(text)}:{text}'
    
  def get_lang(self, text):
    if not text:
      return ''

    n = ''
    while text and text[0] in NOLANG_CHARS:
      n += text[0]
      text = text[1:]
    e = ''
    while text and text[-1] in NOLANG_CHARS:
      e = text[-1] + e
      text = text[:-1]

    while text.find('  ') >= 0:
      text = text.replace('  ', ' ')

    if not HUMAN:
      text = f'x{len(text)}:{text}'
    return self.get_nolang(n) + text + self.get_nolang(e)

  def get_human(self, text):
    if HUMAN:
      return text
    xfound = 0
    xlink = []
    d = ''
    r = ''
    while text:
      type = text[0]
      p = text.find(':')
      if p <= 0:
        fatal(f'wrong text entry: {repr(text)}')
        break
      l = int(text[1:p])
      o = text[:p+1+l]
      t = text[p+1:p+1+l]
      text = text[p+l+1:]
      if not t:
        continue
      if xlink:
        xlink.append(o)
        if t.find(']') >= 0 and (t.endswith(')') or t.endswith(') ')):
          d += xfound and self.get_lang(r) or self.get_nolang(r)
          r = ''
          xfound = 0
          d += ''.join(xlink)
          xlink = []
        continue
      if type == '_' and t == ('[' or t == '!['):
        xlink.append(o)
        continue
      r += t
      if type == 'x':
        xfound = 1
      elif type != '_':
        fatal(f'wrong type: {type}' + ' {' + t + '}')
    return d + (xfound and self.get_lang(r) or self.get_nolang(r))

  def extra_cmd(self, text, tag, type):
    pos1 = text.find(f'<{tag}>')
    if pos1 < 0:
      return 0
    pos2 = text.find(f'</{tag}>')
    if pos2 < 0:
      return 0
    link = text[pos1 + len(tag) + 2:pos2]
    return 0 if len(link) <= 0 else type + str(len(link)) + ':' + link

  def get_block(self, text):
    type = text[0]
    p = text.find(':')
    if p <= 0:
      return ('', '', '')
    l = int(text[1:p])
    t = text[p+1:p+1+l]
    return (text[p+1+l:], type, t)

  def newline(self):
    if DEBUG: debug('newline')
    return '\n'

  def text(self, text):
    if not text:
      return ''
    if DEBUG:
      debug(f'text: {repr(text)}')
    text = text.replace('\n', ' ')
    text = text.replace('\t', '        ')
    return self.get_lang(text)

  def doescape(self, text):
    if DEBUG:
      debug(f'escape: {repr(text)}')
    return self.get_nolang(text)

  def linebreak(self):
    if DEBUG: debug('linebreak')
    return '\n'

  def hrule(self):
    if DEBUG: debug('hrule')
    return '\n' + self.get_nolang('---') + '\n'

  def header(self, text, level, raw=None):
    if DEBUG: debug('header[%d]: ' % level + repr(text))
    return '\n' + self.get_nolang('#'*(level+1) + ' ') + text + '\n'

  def paragraph(self, text):
    if DEBUG:
      debug(f'paragraph: {repr(text)}')
    return '\n' + self.get_human(text) + '\n'

  def list(self, text, ordered=True):
    r = '\n'
    idx = 1
    while text:
      text, type, t = self.get_block(text)
      if DEBUG:
        debug(f'list[{type}]: {repr(t)}')
      if type == 'l':
        r += self.get_nolang(ordered and f'{str(idx)}. ' or '* ') + t
        if ordered: idx += 1
    return r

  def list_item(self, text):
    while text[0] == '\n':
      text = text[1:]
    if DEBUG:
      debug(f'list item: {repr(text)}')
    a = text.split('\n')
    text = self.get_human(a[0]) + '\n'
    for t in a[1:]:
      if t:
        text += self.get_nolang('  ') + t + '\n'
    return f'l{len(text)}:{text}'

  def block_code(self, code, lang=None):
    if DEBUG:
      debug(f'block code: {repr(code)}')
    r = self.get_nolang('```no-highlight') + '\n'
    for line in code.splitlines():
      r += self.get_nolang(line) + '\n'
    return r + self.get_nolang('```') + '\n'

  def block_quote(self, text):
    return ''.join(
        self.get_nolang((line and '> ' or '')) + line + '\n'
        for line in text.splitlines())

  def block_html(self, text):
    if DEBUG:
      debug(f'block html: {repr(text)}')
    if a := self.extra_cmd(text, 'tvh_class_doc', 'd'):
      return a
    if a := self.extra_cmd(text, 'tvh_class_items', 'i'):
      return a
    if a := self.extra_cmd(text, 'tvh_include', 'I'):
      return a
    fatal(f'Block HTML not allowed: {repr(text)}')

  def inline_html(self, text):
    fatal(f'Inline HTML not allowed: {repr(text)}')

  def _emphasis(self, text, pref):
    if DEBUG:
      debug(f'emphasis[{pref}]: {repr(text)}')
    return self.get_nolang(pref) + text + self.get_nolang(f'{pref} ')

  def emphasis(self, text):
    return self._emphasis(text, '_')

  def double_emphasis(self, text):
    return self._emphasis(text, '__')

  def strikethrough(self, text):
    return self._emphasis(text, '~~')

  def codespan(self, text):
    return self.get_nolang(f'`{text}`')

  def autolink(self, link, is_email=False):
    return self.get_nolang('<') + link + self.get_nolang('>')

  def link(self, link, title, text, image=False):
    r = (self.get_nolang((image and '!' or '') + '[') + text +
         self.get_nolang(f']({link})'))
    if title:
      r += self.get_nolang('"') + title + self.get_nolang('"')
    return r

  def image(self, src, title, text):
    self.link(src, title, text, image=True)

  def table(self, header, body):
    if DEBUG:
      debug(f'table: {repr(header)} {repr(body)}')
    hrows = []
    while header:
      header, type, t = self.get_block(header)
      if type == 'r':
        flags = {}
        cols = []
        while t:
          t, type2, t2 = self.get_block(t)
          if type2 == 'f':
            fl, v = t2.split('=')
            flags[fl] = v
          elif type2 == 'c':
            c = Object()
            c.flags = flags
            c.text = t2
            cols.append(c)
        hrows.append(cols)
    brows = []
    while body:
      body, type, t = self.get_block(body)
      if type == 'r':
        flags = {}
        cols = []
        while t:
          t, type2, t2 = self.get_block(t)
          if type2 == 'f':
            fl, v = t2.split('=')
            flags[fl] = v
          elif type2 == 'c':
            c = Object()
            c.flags = flags
            c.text = t2
            cols.append(c)
        brows.append(cols)
    colscount = 0
    colmax = [0] * 100
    align = [''] * 100
    for row in hrows + brows:
      colscount = max(len(row), colscount)
      for i, col in enumerate(row):
        colmax[i] = max(len(col.text), colmax[i])
        if 'align' in col.flags:
          align[i] = col.flags['align'][0]
    r = '\n'
    for row in hrows:
      for i, col in enumerate(row):
        if i > 0:
          r += self.get_nolang(' | ')
        r += col.text
      r += '\n'
    for i in range(colscount):
      if i > 0:
        r += self.get_nolang(' | ')
      if align[i] == 'c':
        r += self.get_nolang(':---:')
      elif align[i] == 'l':
        r += self.get_nolang(':----')
      elif align[i] == 'r':
        r += self.get_nolang('----:')
      else:
        r += self.get_nolang('-----')
    r += '\n'
    for row in brows:
      for i, col in enumerate(row):
        if i > 0:
          r += self.get_nolang(' | ')
        r += col.text
      r += '\n'
    return r

  def table_row(self, content):
    if DEBUG:
      debug(f'table_row: {repr(content)}')
    return f'r{len(content)}:{content}'

  def table_cell(self, content, **flags):
    if DEBUG:
      debug(f'table_cell: {repr(content)} {repr(flags)}')
    # dirty fix for inline images
    if content.startswith('x1:!_1:['):
      content = f'_2:![{content[8:]}'
    content = content.replace('\n', ' ')
    r = ''
    for fl, v in flags.items():
      if type(v) == type(True):
        v = 1 if v else 0
      v = str(v) and str(v) or ''
      r += f'f{str(len(fl) + 1 + len(v))}:{fl}={v}'
    return f'{r}c{len(content)}:{content}'

  def footnote_ref(self, key, index):
    return self.get_nolang(f'[^{str(index)}]')

  def footnote_item(self, key, text):
    r = self.get_nolang(f'[^{str(index)}]:' + '\n')
    for l in text.split('\n'):
      r += self.get_nolang('  ') + self.get_lang(l.lstrip().rstrip()) + '\n'
    return r

  def footnotes(self, text):
    text = text.replace('\n', ' ')
    return self.get_lang(text.lstrip().rstrip()) + '\n'

#
#
#

def optimize(text):

  r = ''
  x = ''
  n = ''

  def repl(t):
    return t.replace('"', '\\"')

  def nolang(t):
    return '"' + repl(t) + '",\n'

  def lang(t):
    return 'LANGPREF N_("' + repl(t) + '"),\n'

  text = text.lstrip().rstrip()
  while text.find('\n\n\n') >= 0:
    text = text.replace('\n\n\n', '\n\n')
  if HUMAN:
    return text

  for text in text.splitlines():
    while text:
      type = text[0]
      p = text.find(':')
      if p <= 0:
        fatal(f'wrong text entry: {repr(text)}')
        break
      l = int(text[1:p])
      t = text[p+1:p+1+l]
      if type == 'x':
        if n: r += nolang(n)
        n = ''
        x += t
      elif type == '_':
        if x: r += lang(x)
        x = ''
        n += t
      elif type in ['d', 'i', 'I']:
        if n: r += nolang(n)
        if x: r += lang(x)
        n = ''
        x = ''
        if type == 'd':
          r += 'DOCINCPREF "' + t + '",\n'
        elif type == 'i':
          r += 'ITEMSINCPREF "' + t + '",\n'
        else:
          r += 'MDINCLUDE "' + t + '",\n'
      text = text[p+l+1:]
    if x: r += lang(x)
    x = ''
    n += '\\n'
  if n: r += nolang(n)
  if x: r += lang(x)
  return r

#
#
#

def dopages(pages):
  print("\n\nconst struct tvh_doc_page tvh_doc_markdown_pages[] = {")
  for page in pages.split(' '):
    if not page: continue
    print("  { \"%s\", tvh_doc_root_%s }," % (page, page.replace('/', '_')))
  print("  { NULL, NULL },")
  print("};")

#
#
#

def fatal(msg):
  sys.stderr.write(f'FATAL: {msg}' + '\n')
  sys.exit(1)

def argv_get(what):
  what = f'--{what}'
  for a in sys.argv:
    if a.startswith(what):
      a = a[len(what):]
      return a[1:] if a and a[0] == '=' else True
  return None

#
#
#

def run(input, name, human):
  fp = utf8open(input, 'r')
  text = fp.read(1024*1024*2)
  fp.close()

  renderer = TVH_C_Renderer(parse_html=1)
  md = Markdown(renderer)
  text = md(text)
  text = optimize(text)
  if human:
    return text
  return f'const char *{name}' + '[] = {\n' + text + '\nNULL\n};\n'

HUMAN=argv_get('human')
DEBUG=argv_get('debug')
if pages := argv_get('pages'):
  dopages(pages)
  sys.exit(0)
if BATCH := argv_get('batch'):
  inpath = argv_get('inpath')
  out = argv_get('out')
  name = argv_get('name')
  list = argv_get('list')
  fp = utf8open(out, "a+")
  for l in list.split(' '):
    input = inpath % l
    print(f"Markdown: {input}")
    n = (name % l).replace('/', '_')
    text = run(input, n, HUMAN)
    fp.write(text)
  fp.close()
else:
  input = argv_get('in')
  if not input:
    fatal('Specify input file.')
  name = argv_get('name')
  if not name:
    fatal('Specify class name.')
  name = name.replace('/', '_')
  text = run(input, name, HUMAN)
  print(text)
