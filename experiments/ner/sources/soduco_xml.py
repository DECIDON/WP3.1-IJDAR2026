"""Parseur partagé des entrées SoDUCo/FTD annotées en XML-like (tags imbriqués possibles)."""
import html
import re

TAG = re.compile(r"<(/?)([A-Za-z][A-Za-z_-]*)>")


def parse_xml(x):
    """-> (text, [[start, end, label, depth], ...]). U+2029 -> \n, entités XML décodées."""
    text, spans, stack, pos = [], [], [], 0
    n = 0
    for m in TAG.finditer(x):
        chunk = html.unescape(x[pos:m.start()]).replace(" ", "\n")
        text.append(chunk)
        n += len(chunk)
        if m.group(1):
            lab, start, depth = stack.pop()
            assert lab == m.group(2), (lab, m.group(2), x)
            if n > start:
                spans.append([start, n, lab, depth])
        else:
            stack.append((m.group(2), n, len(stack)))
        pos = m.end()
    chunk = html.unescape(x[pos:]).replace(" ", "\n")
    text.append(chunk)
    assert not stack, x
    return "".join(text), spans
