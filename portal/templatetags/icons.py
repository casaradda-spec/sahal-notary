"""Inline SVG icon system — Heroicons-style outline glyphs with zero JS/runtime
dependency. Usage in templates: {% icon "users" %} or {% icon "trash" size=16 class="icon-danger" %}
"""
from django import template
from django.utils.html import format_html
from django.utils.safestring import mark_safe

register = template.Library()

# Each value is the inner <path>/<circle>/... markup for a 24x24 viewBox outline icon.
# Style (stroke, fill, line caps) is applied once on the wrapping <svg> so every icon
# stays visually consistent without repeating attributes.
_ICONS = {
    'home': '<path d="M4 11.5 12 4l8 7.5"/><path d="M6 10v9a1 1 0 0 0 1 1h3v-6h4v6h3a1 1 0 0 0 1-1v-9"/>',
    'users': '<circle cx="9" cy="8" r="3"/><path d="M3.5 20c0-3 2.5-5 5.5-5s5.5 2 5.5 5"/><path d="M16 9.5a2.5 2.5 0 1 0 0-5"/><path d="M15 15c2.5 0 4.5 2 4.7 4.6"/>',
    'shield-check': '<path d="M12 3.5 5 6v6c0 4.2 3 7 7 8.5 4-1.5 7-4.3 7-8.5V6z"/><path d="M9 12l2.2 2.2L15.5 9.6"/>',
    'document-text': '<path d="M7 3.5h7l3 3V20a.8.8 0 0 1-.8.8H7.8A.8.8 0 0 1 7 20V4.3a.8.8 0 0 1 .8-.8z"/><path d="M14 3.5V7h3"/><path d="M9.3 12h5.4M9.3 15h5.4M9.3 9h2.5"/>',
    'document-plus': '<path d="M7 3.5h7l3 3V20a.8.8 0 0 1-.8.8H7.8A.8.8 0 0 1 7 20V4.3a.8.8 0 0 1 .8-.8z"/><path d="M14 3.5V7h3"/><path d="M12 11v6M9 14h6"/>',
    'rectangle-stack': '<path d="M5 8.5 12 5l7 3.5-7 3.5z"/><path d="M5 13l7 3.5L19 13"/><path d="M5 17l7 3.5L19 17"/>',
    'chart-bar': '<path d="M4.5 20V12M10 20V6.5M15.5 20v-9M21 20H3"/>',
    'trending-up': '<path d="M3.5 17.5 9 12l3.5 3.5L20.5 7"/><path d="M15 7h5.5V12.5"/>',
    'user-circle': '<circle cx="12" cy="12" r="8.5"/><circle cx="12" cy="9.8" r="2.6"/><path d="M6.3 18.2c1-2.2 3-3.4 5.7-3.4s4.7 1.2 5.7 3.4"/>',
    'arrow-right-on-rectangle': '<path d="M10 19H6.2a1 1 0 0 1-1-1V6a1 1 0 0 1 1-1H10"/><path d="M14.5 16l4-4-4-4"/><path d="M18 12H9"/>',
    'arrow-left-on-rectangle': '<path d="M14 19h3.8a1 1 0 0 0 1-1V6a1 1 0 0 0-1-1H14"/><path d="M9.5 8l-4 4 4 4"/><path d="M6 12h9"/>',
    'check-circle': '<circle cx="12" cy="12" r="8.5"/><path d="M8.3 12.3l2.5 2.5 5-5.2"/>',
    'x-circle': '<circle cx="12" cy="12" r="8.5"/><path d="M9.3 9.3l5.4 5.4M14.7 9.3l-5.4 5.4"/>',
    'exclamation-triangle': '<path d="M12 4.5 21 19.5H3z"/><path d="M12 10v4"/><circle cx="12" cy="16.6" r="0.15" fill="currentColor" stroke="none"/>',
    'clock': '<circle cx="12" cy="12" r="8.5"/><path d="M12 7.2V12l3.3 2"/>',
    'pencil-square': '<path d="M14.3 5.3 18.7 9.7 8.6 19.8l-4.9.5.5-4.9z"/><path d="M12.8 6.8l4.4 4.4"/>',
    'trash': '<path d="M5 7h14"/><path d="M9.5 7V5.3A1.3 1.3 0 0 1 10.8 4h2.4a1.3 1.3 0 0 1 1.3 1.3V7"/><path d="M7.3 7l.9 12a1.3 1.3 0 0 0 1.3 1.2h5a1.3 1.3 0 0 0 1.3-1.2l.9-12"/><path d="M10.3 11v6M13.7 11v6"/>',
    'eye': '<path d="M3 12c1.8-3.8 5-6 9-6s7.2 2.2 9 6c-1.8 3.8-5 6-9 6s-7.2-2.2-9-6z"/><circle cx="12" cy="12" r="2.6"/>',
    'arrow-down-tray': '<path d="M12 4v11.5"/><path d="M8 12l4 4 4-4"/><path d="M5 18.5h14"/>',
    'magnifying-glass': '<circle cx="11" cy="11" r="6.5"/><path d="M19.5 19.5l-4-4"/>',
    'pencil': '<path d="M4 20l1.2-4.7L15.6 4.9a1.6 1.6 0 0 1 2.3 0l1.2 1.2a1.6 1.6 0 0 1 0 2.3L8.7 18.8z"/><path d="M14 6.9l3.1 3.1"/>',
    'signature': '<path d="M3.5 17c1.6 0 1.6-2.4 3.2-2.4S8.3 17 9.9 17s1.6-3.6 3.2-3.6 1.6 3.6 3.2 3.6 1.6-2.4 3.2-2.4"/><path d="M4 20.2h16"/>',
    'camera': '<path d="M4 8.3A1.3 1.3 0 0 1 5.3 7h2L8.6 4.8h6.8L16.7 7h2A1.3 1.3 0 0 1 20 8.3v9.4A1.3 1.3 0 0 1 18.7 19H5.3A1.3 1.3 0 0 1 4 17.7z"/><circle cx="12" cy="12.7" r="3.4"/>',
    'plus': '<path d="M12 5v14M5 12h14"/>',
    'plus-circle': '<circle cx="12" cy="12" r="8.5"/><path d="M12 8v8M8 12h8"/>',
    'chevron-left': '<path d="M14.5 5.5 8 12l6.5 6.5"/>',
    'chevron-right': '<path d="M9.5 5.5 16 12l-6.5 6.5"/>',
    'check': '<path d="M5 12.5l4.5 4.5L19 7"/>',
    'qr-code': '<rect x="4" y="4" width="6" height="6" rx="0.8"/><rect x="14" y="4" width="6" height="6" rx="0.8"/><rect x="4" y="14" width="6" height="6" rx="0.8"/><path d="M14 14h2.5v2.5M14 19.5h2.5M19.5 14V19.5h-1"/>',
    'lock-closed': '<rect x="5.5" y="10.5" width="13" height="9" rx="1.3"/><path d="M8.3 10.5V7.8a3.7 3.7 0 0 1 7.4 0v2.7"/>',
    'globe-alt': '<circle cx="12" cy="12" r="8.5"/><path d="M3.5 12h17M12 3.5c2.3 2.2 3.5 5.2 3.5 8.5s-1.2 6.3-3.5 8.5c-2.3-2.2-3.5-5.2-3.5-8.5S9.7 5.7 12 3.5z"/>',
    'phone': '<path d="M6 4.5h3l1.3 4-2 1.6a11 11 0 0 0 5.6 5.6l1.6-2 4 1.3v3a1.3 1.3 0 0 1-1.4 1.3A15.5 15.5 0 0 1 4.7 5.9 1.3 1.3 0 0 1 6 4.5z"/>',
    'envelope': '<rect x="3.5" y="5.5" width="17" height="13" rx="1.3"/><path d="M4 6.5l8 6.5 8-6.5"/>',
    'map-pin': '<path d="M12 21s6.5-6 6.5-11A6.5 6.5 0 0 0 5.5 10c0 5 6.5 11 6.5 11z"/><circle cx="12" cy="10" r="2.2"/>',
    'identification': '<rect x="3.5" y="5.5" width="17" height="13" rx="1.5"/><circle cx="8.3" cy="11" r="1.8"/><path d="M5.8 16c.4-1.6 1.4-2.4 2.5-2.4s2.1.8 2.5 2.4M13.5 9.5h5M13.5 12.5h5M13.5 15.5h3.3"/>',
    'building-office': '<rect x="4.5" y="3.5" width="9" height="17"/><rect x="13.5" y="9.5" width="6" height="11"/><path d="M7.5 7h3M7.5 10.5h3M7.5 14h3M7.5 17.5h3M16 13h1.5M16 16.5h1.5"/>',
    'arrow-path': '<path d="M4.5 12a7.5 7.5 0 0 1 12.6-5.5M19.5 12a7.5 7.5 0 0 1-12.6 5.5"/><path d="M17.5 4.5v3.5H14M6.5 19.5V16H10"/>',
    'sparkles': '<path d="M12 4l1.4 4.2L17.5 9.7l-4.1 1.5L12 15.5l-1.4-4.3-4.1-1.5 4.1-1.5z"/><path d="M5 17l.7 2 2 .7-2 .7-.7 2-.7-2-2-.7 2-.7z"/>',
}


@register.simple_tag
def icon(name, size=20, css_class='', stroke_width=1.8):
    """Render an inline outline-style SVG icon. Unknown names render nothing (fails
    quiet rather than breaking a page over a typo'd icon name)."""
    inner = _ICONS.get(name)
    if inner is None:
        return ''
    classes = f'icon {css_class}'.strip()
    return format_html(
        '<svg class="{}" width="{}" height="{}" viewBox="0 0 24 24" fill="none" '
        'stroke="currentColor" stroke-width="{}" stroke-linecap="round" '
        'stroke-linejoin="round" aria-hidden="true">{}</svg>',
        classes, size, size, stroke_width, mark_safe(inner),
    )
