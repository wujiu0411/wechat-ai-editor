import re
from app.templates.css_templates import TEMPLATES, get_template_for_content_type


def format_article(
    title: str,
    markdown_content: str,
    images: list[dict],
    cta: str = "点击阅读原文了解更多",
    template_id: str = "",
    content_type: str = "",
) -> str:
    if not template_id:
        template_id = get_template_for_content_type(content_type)

    template = TEMPLATES.get(template_id, TEMPLATES["base"])
    css_template = template["css_template"]
    styles = template["styles"]

    content_with_images = _insert_images(markdown_content, images)
    body_html = _markdown_to_inline_html(content_with_images, styles)

    html = css_template.format(title=title, body=body_html, cta=cta)
    return html


def _insert_images(markdown_content: str, images: list[dict]) -> str:
    content = markdown_content

    for img in images:
        position = img.get("position", "")
        source = img.get("source", "")
        alt_text = img.get("alt_text", "")

        if source.startswith("[缺失"):
            placeholder = f"\n> **[图片占位]** {alt_text} - 请手动补充图片\n"
            pattern = re.compile(r'\[IMG:' + re.escape(position) + r'\]', re.IGNORECASE)
            content = pattern.sub(placeholder, content)
            continue

        img_tag = f'\n![{alt_text}]({source})\n'
        pattern = re.compile(r'\[IMG:' + re.escape(position) + r'\]', re.IGNORECASE)
        if pattern.search(content):
            content = pattern.sub(img_tag, content)
        else:
            content += f"\n{img_tag}\n"

    content = re.sub(r'\[IMG:[^\]]+\]', '', content)

    return content


def _markdown_to_inline_html(markdown_text: str, styles: dict) -> str:
    lines = markdown_text.split('\n')
    html_parts = []
    in_list = False

    for line in lines:
        stripped = line.strip()

        if not stripped:
            if in_list:
                html_parts.append('</ul>')
                in_list = False
            continue

        if stripped.startswith('### '):
            if in_list:
                html_parts.append('</ul>')
                in_list = False
            text = _process_inline(stripped[4:], styles)
            html_parts.append(f'<h3 style="{styles["h3"]}">{text}</h3>')

        elif stripped.startswith('## '):
            if in_list:
                html_parts.append('</ul>')
                in_list = False
            text = _process_inline(stripped[3:], styles)
            html_parts.append(f'<h2 style="{styles["h2"]}">{text}</h2>')

        elif stripped.startswith('# '):
            if in_list:
                html_parts.append('</ul>')
                in_list = False
            text = _process_inline(stripped[2:], styles)
            html_parts.append(f'<h2 style="{styles["h2"]}">{text}</h2>')

        elif stripped.startswith('- ') or stripped.startswith('* '):
            if not in_list:
                html_parts.append(f'<ul style="{styles["ul"]}">')
                in_list = True
            text = _process_inline(stripped[2:], styles)
            html_parts.append(f'<li style="{styles["li"]}">• {text}</li>')

        elif re.match(r'^\d+\.\s', stripped):
            if in_list:
                html_parts.append('</ul>')
                in_list = False
            html_parts.append(f'<ul style="{styles["ul"]}">')
            in_list = True
            text = re.sub(r'^\d+\.\s', '', stripped)
            text = _process_inline(text, styles)
            num_match = re.match(r'^(\d+)\.', stripped)
            num = num_match.group(1) if num_match else "1"
            html_parts.append(f'<li style="{styles["li"]}">{num}. {text}</li>')

        elif stripped.startswith('>') or stripped.startswith('> '):
            if in_list:
                html_parts.append('</ul>')
                in_list = False
            text = stripped.lstrip('> ').strip()
            text = _process_inline(text, styles)
            html_parts.append(f'<blockquote style="{styles["blockquote"]}">{text}</blockquote>')

        elif stripped.startswith('---') or stripped.startswith('***'):
            if in_list:
                html_parts.append('</ul>')
                in_list = False
            html_parts.append(f'<hr style="{styles["hr"]}" />')

        elif stripped.startswith('!['):
            if in_list:
                html_parts.append('</ul>')
                in_list = False
            alt_match = re.match(r'!\[([^\]]*)\]\(([^)]+)\)', stripped)
            if alt_match:
                alt = alt_match.group(1)
                src = alt_match.group(2)
                html_parts.append(f'<img src="{src}" alt="{alt}" style="{styles["img"]}" />')

        else:
            if in_list:
                html_parts.append('</ul>')
                in_list = False
            text = _process_inline(stripped, styles)
            html_parts.append(f'<p style="{styles["p"]}">{text}</p>')

    if in_list:
        html_parts.append('</ul>')

    return '\n'.join(html_parts)


def _process_inline(text: str, styles: dict) -> str:
    text = re.sub(r'\*\*(.+?)\*\*', rf'<strong style="{styles["strong"]}">\1</strong>', text)
    text = re.sub(r'\*(.+?)\*', r'<em>\1</em>', text)
    text = re.sub(r'`(.+?)`', r'<code style="background:#f5f5f5;padding:2px 4px;border-radius:3px;font-size:13px;">\1</code>', text)
    text = re.sub(r'\[(.+?)\]\((.+?)\)', r'<a href="\2" style="color:#0066CC;text-decoration:none;">\1</a>', text)
    return text
