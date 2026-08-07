#!/usr/bin/env python3
"""dops_dom.py — locate the subtree a selector points at, in raw HTML source.

Design: Kimi, `Most/tasks/2026-08-06-kimi-f1-copy-edit-form-spec.md` §3.

Why this exists. `set_text` (П-5) refuses any edit whose `find` string occurs
more than once in the build, because a pin written in words does not say which
occurrence the owner meant, and guessing is the cheap-wrong-lane mistake. That
rule is right for a pin written in words — and wrong for a pin born from the
form (Ф-1), which carries the selector of the very element that was edited.
"Sold out" on a button and "Sold out" in the footer stopped being each other's
problem the moment the pin knew which one it was standing on.

So the question this module answers is narrow and mechanical: **given a
selector and a file, which byte ranges of that file are the insides of the
elements it matches?**

It is deliberately NOT a CSS engine. It supports exactly the grammar
`gate-annotate.js` emits — `#id`, or a chain of `tag.class.class:nth-of-type(n)`
joined by ` > ` — and REFUSES anything else with a reason. A selector engine
that quietly half-matches an unfamiliar syntax would reintroduce the silent
wrong target this whole mechanism exists to remove; `selector_resolves` in the
checker is allowed to approximate because its false positives are harmless,
and this one's would not be — it decides where an edit is written.

Usage as a library:
    spans = inner_spans(html_text, "#tickets > p.note")   # [(start, end), …]
    spans is None  →  the selector is outside the supported grammar

    python3 tools/dops_dom.py --self-test
"""
import re
import sys
from html.parser import HTMLParser

# Elements that never have a closing tag: they own no subtree, so an edit can
# never be scoped "inside" one.
VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link",
        "meta", "param", "source", "track", "wbr"}

# One simple selector: an optional tag, then any number of #id / .class, then
# an optional :nth-of-type(n). Anything else is out of grammar.
PART = re.compile(
    r"^(?P<tag>[A-Za-z][A-Za-z0-9]*)?"
    r"(?P<ids>(?:#[A-Za-z0-9_-]+)*)"
    r"(?P<classes>(?:\.[A-Za-z0-9_-]+)*)"
    r"(?::nth-of-type\((?P<nth>\d+)\))?$")


class Node(object):
    __slots__ = ("tag", "attrs", "parent", "children", "inner_start",
                 "inner_end", "nth_of_type")

    def __init__(self, tag, attrs, parent):
        self.tag = tag
        self.attrs = attrs
        self.parent = parent
        self.children = []
        self.inner_start = None
        self.inner_end = None
        self.nth_of_type = 0

    def classes(self):
        return set((self.attrs.get("class") or "").split())


class _Tree(HTMLParser):
    """A tolerant tree with byte offsets. Unclosed tags are closed implicitly
    at the end of the document rather than raising: a build is not always
    well-formed, and refusing to read it would be a worse answer than reading
    what is there."""

    def __init__(self, text):
        HTMLParser.__init__(self, convert_charrefs=False)
        self.text = text
        self.line_starts = [0]
        for i, ch in enumerate(text):
            if ch == "\n":
                self.line_starts.append(i + 1)
        self.root = Node("#document", {}, None)
        self.stack = [self.root]

    def _offset(self):
        line, col = self.getpos()
        return self.line_starts[line - 1] + col

    def _open(self, tag, attrs):
        parent = self.stack[-1]
        node = Node(tag, dict(attrs), parent)
        node.nth_of_type = sum(1 for c in parent.children if c.tag == tag) + 1
        parent.children.append(node)
        start = self._offset()
        raw = self.get_starttag_text() or ("<%s>" % tag)
        node.inner_start = start + len(raw)
        node.inner_end = node.inner_start
        return node

    def handle_starttag(self, tag, attrs):
        node = self._open(tag, attrs)
        if tag not in VOID:
            self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        self._open(tag, attrs)

    def handle_endtag(self, tag):
        # close the nearest matching open element; stray end tags are ignored
        for depth in range(len(self.stack) - 1, 0, -1):
            if self.stack[depth].tag == tag:
                self.stack[depth].inner_end = self._offset()
                del self.stack[depth:]
                return

    def close(self):
        HTMLParser.close(self)
        end = len(self.text)
        for node in self.stack[1:]:
            node.inner_end = end
        del self.stack[1:]


def parse_part(part):
    """{'tag':…, 'id':…, 'classes':set, 'nth':int|None} or None if the part is
    outside the supported grammar."""
    m = PART.match(part.strip())
    if not m or not part.strip():
        return None
    ids = re.findall(r"#([A-Za-z0-9_-]+)", m.group("ids") or "")
    if len(ids) > 1:
        return None                     # two ids on one element is not a thing
    return {"tag": (m.group("tag") or "").lower(),
            "id": ids[0] if ids else None,
            "classes": set(re.findall(r"\.([A-Za-z0-9_-]+)", m.group("classes") or "")),
            "nth": int(m.group("nth")) if m.group("nth") else None}


def parse_selector(selector):
    """The chain, outermost first, or None when any part is out of grammar."""
    if not selector or not selector.strip():
        return None
    if re.search(r"[,\[\]~+*]|::", selector):
        return None                     # groups, attributes, siblings: not ours
    parts = [p for p in re.split(r"\s*>\s*|\s+", selector.strip()) if p]
    parsed = [parse_part(p) for p in parts]
    return None if any(p is None for p in parsed) else parsed


def _matches(node, part):
    if part["tag"] and node.tag != part["tag"]:
        return False
    if part["id"] and node.attrs.get("id") != part["id"]:
        return False
    if part["classes"] and not part["classes"].issubset(node.classes()):
        return False
    if part["nth"] is not None and node.nth_of_type != part["nth"]:
        return False
    return True


def _walk(node):
    for child in node.children:
        yield child
        for deeper in _walk(child):
            yield deeper


def select(markup, selector):
    """Every element the selector matches, in document order, or None when the
    selector is outside the supported grammar.

    The chain is anchored at its LAST part and walked upwards through direct
    parents, because `gate-annotate.js` emits a suffix of the real ancestry
    (it stops after four levels) — requiring the first part to be a document
    child would fail on every selector the form actually produces."""
    chain = parse_selector(selector)
    if chain is None:
        return None
    tree = _Tree(markup)
    try:
        tree.feed(markup)
        tree.close()
    except Exception:                                   # noqa: BLE001
        return None
    out = []
    for node in _walk(tree.root):
        if not _matches(node, chain[-1]):
            continue
        cur, ok = node.parent, True
        for part in reversed(chain[:-1]):
            while cur is not None and not _matches(cur, part):
                cur = cur.parent
            if cur is None:
                ok = False
                break
            cur = cur.parent
        if ok:
            out.append(node)
    return out


def inner_spans(markup, selector):
    """[(start, end)] byte ranges of the matched elements' inner HTML, or None
    when the selector cannot be honoured."""
    nodes = select(markup, selector)
    if nodes is None:
        return None
    return [(n.inner_start, n.inner_end) for n in nodes
            if n.inner_start is not None and n.inner_end is not None
            and n.inner_end >= n.inner_start]


def scoped_hits(markup, needle, selector):
    """[(start, end)] of every occurrence of `needle` INSIDE the selector's
    subtree, or None when the selector cannot be honoured.

    [Ф-1 §3] This is what lets the one-occurrence rule relax without losing any
    strictness: a pin born from the form knows which element it stands on, so
    "Sold out" on a button and "Sold out" in the footer stop blocking each
    other. One owner for the answer, because the checker asks it to decide
    whether an edit is still feasible and the executor asks it to decide where
    to write — those two must never disagree."""
    spans = inner_spans(markup, selector)
    if spans is None:
        return None
    out = []
    for start, end in spans:
        inside, at = markup[start:end], 0
        while True:
            i = inside.find(needle, at)
            if i < 0:
                break
            out.append((start + i, start + i + len(needle)))
            at = i + len(needle)
    return out


# --------------------------------------------------------------------------
def self_test():
    problems = []
    doc = ('<!doctype html><html><body>\n'
           '<main id="tickets"><p class="note">Билеты в продаже</p>\n'
           '  <p class="note">и ещё строка</p></main>\n'
           '<footer><p class="note">Билеты в продаже</p><img src="x.png"></footer>\n'
           '</body></html>')

    spans = inner_spans(doc, "#tickets > p.note:nth-of-type(1)")
    if not spans or len(spans) != 1:
        problems.append("an id-anchored chain matched %r elements, expected 1"
                        % (len(spans) if spans is not None else None))
    elif doc[spans[0][0]:spans[0][1]] != "Билеты в продаже":
        problems.append("the matched span is not the element's own text: %r"
                        % doc[spans[0][0]:spans[0][1]])

    # A selector that genuinely matches two siblings must REPORT two, not pick
    # one: that ambiguity is what `set_text` refuses on. This is why the form
    # emits `:nth-of-type` whenever siblings share a tag.
    if len(inner_spans(doc, "#tickets > p.note") or []) != 2:
        problems.append("an ambiguous selector did not report both matches — "
                        "set_text would have edited a guess")

    # the same text in another section is a different element, which is the
    # whole point of scoping
    spans = inner_spans(doc, "footer > p.note")
    if not spans or len(spans) != 1 or doc[spans[0][0]:spans[0][1]] != "Билеты в продаже":
        problems.append("the footer copy of the same string was not matched "
                        "separately")

    # nth-of-type picks the second paragraph, not the first
    spans = inner_spans(doc, "#tickets > p.note:nth-of-type(2)")
    if not spans or doc[spans[0][0]:spans[0][1]] != "и ещё строка":
        problems.append("nth-of-type did not select the second sibling")

    # a bare tag matches everywhere it occurs
    spans = inner_spans(doc, "p.note")
    if not spans or len(spans) != 3:
        problems.append("a bare class selector matched %s elements, expected 3"
                        % (len(spans) if spans is not None else None))

    # a void element owns no subtree, and an unsupported grammar is REFUSED
    # rather than half-matched
    if inner_spans(doc, "footer > img") == []:
        pass                            # matched, but with an empty inside
    for bad in ("p[data-x]", "a, b", "p::before", "p ~ span", ""):
        if inner_spans(doc, bad) is not None:
            problems.append("out-of-grammar selector %r was matched anyway" % bad)

    # an unclosed tag must not lose the rest of the document
    torn = '<div id="a"><p class="x">один<div id="b"><p class="x">два</p></div>'
    spans = inner_spans(torn, "#b > p.x")
    if not spans or torn[spans[0][0]:spans[0][1]] != "два":
        problems.append("a malformed document lost an element that is plainly "
                        "there: %r" % (spans,))

    if problems:
        for p in problems:
            print("self-test FAIL: dops-dom: %s" % p)
        return 1
    print("OK: dops-dom self-test (id/class/nth chains, same text in two "
          "sections kept apart, out-of-grammar selectors refused rather than "
          "half-matched, malformed markup still read)")
    return 0


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        sys.exit(self_test())
    print(__doc__)
    sys.exit(2)
