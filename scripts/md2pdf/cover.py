"""封面页 HTML 生成"""

from .utils import _escape_html


def build_cover_html(meta):
    """根据 front-matter 元数据生成封面页 HTML"""
    parts = ['<section data-page="cover" class="md2pdf-cover">']

    title = meta.get("title", "")
    if title:
        parts.append(f'<h1>{_escape_html(title)}</h1>')

    subtitle = meta.get("subtitle", "")
    if subtitle:
        parts.append(f'<p class="subtitle">{_escape_html(subtitle)}</p>')

    parts.append('<hr>')

    author = meta.get("author", "")
    if author:
        parts.append(f'<p class="meta">{_escape_html(author)}</p>')

    date = meta.get("date", "")
    if date:
        parts.append(f'<p class="meta">{_escape_html(date)}</p>')

    version = meta.get("version", "")
    if version:
        parts.append(f'<p class="version">v{_escape_html(version)}</p>')

    parts.append('</section>')
    return "\n".join(parts)
