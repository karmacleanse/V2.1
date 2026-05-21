"""
Open Graph image generator for Karma Cleanse certificates.
Produces a 1200x630 PNG with brutalist-style cert preview for social sharing.
"""
import io
import logging
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger(__name__)

# Fonts (Liberation is pre-installed; falls back to default if missing)
FONT_PATH_BOLD = '/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf'
FONT_PATH_REGULAR = '/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf'
FONT_PATH_MONO = '/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf'
FONT_PATH_MONO_BOLD = '/usr/share/fonts/truetype/liberation/LiberationMono-Bold.ttf'

OG_WIDTH = 1200
OG_HEIGHT = 630

# Brutalist palette
BG = (244, 244, 240)     # F4F4F0
INK = (10, 10, 10)        # 0A0A0A
MUTED = (115, 115, 115)   # 737373
ACCENT_LOW = (21, 128, 61)        # green
ACCENT_MODERATE = (82, 82, 82)    # neutral grey
ACCENT_HIGH = (180, 83, 9)        # amber
ACCENT_CRITICAL = (217, 45, 32)   # red
ACCENT_COMPLIANCE = (21, 128, 61)


def _color_for(severity: str) -> tuple:
    return {
        'Low': ACCENT_LOW,
        'Moderate': ACCENT_MODERATE,
        'High': ACCENT_HIGH,
        'Critical': ACCENT_CRITICAL,
        'Compliance': ACCENT_COMPLIANCE,
    }.get(severity, INK)


def _load(path: str, size: int):
    try:
        return ImageFont.truetype(path, size)
    except Exception:
        return ImageFont.load_default()


def _truncate(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    return text[:max_chars - 1].rstrip() + '…'


def generate_og_image(cert: dict) -> bytes:
    """Generate a 1200x630 PNG preview of the certificate. Returns bytes."""
    img = Image.new('RGB', (OG_WIDTH, OG_HEIGHT), BG)
    draw = ImageDraw.Draw(img)
    
    # White card with thick black border
    card_margin = 32
    card = (card_margin, card_margin, OG_WIDTH - card_margin, OG_HEIGHT - card_margin)
    draw.rectangle(card, fill=(255, 255, 255), outline=INK, width=4)
    
    pad = 50
    inner_left = card[0] + pad
    inner_right = card[2] - pad
    y = card[1] + pad
    
    # Header: KARMA CLEANSE
    font_header = _load(FONT_PATH_BOLD, 36)
    draw.text((inner_left, y), 'KARMA CLEANSE', font=font_header, fill=INK)
    
    # Subtitle small mono right-aligned
    font_micro = _load(FONT_PATH_MONO, 14)
    subtitle = 'OFFICIAL CERTIFICATE V2.1'
    bbox = draw.textbbox((0, 0), subtitle, font=font_micro)
    draw.text((inner_right - (bbox[2] - bbox[0]), y + 8), subtitle, font=font_micro, fill=MUTED)
    
    y += 60
    # Thin divider
    draw.line([(inner_left, y), (inner_right, y)], fill=INK, width=2)
    y += 30
    
    # Severity stamp (top-left of body area)
    severity = cert.get('severity_class', 'Low')
    sev_color = _color_for(severity)
    is_compliance = cert.get('receipt_type') == 'tc_acknowledgment'
    stamp_text = f'CLASS {severity.upper()}'
    font_stamp = _load(FONT_PATH_BOLD, 22)
    stamp_bbox = draw.textbbox((0, 0), stamp_text, font=font_stamp)
    stamp_w = stamp_bbox[2] - stamp_bbox[0]
    stamp_h = stamp_bbox[3] - stamp_bbox[1]
    sx, sy = inner_left, y
    draw.rectangle(
        (sx - 14, sy - 8, sx + stamp_w + 14, sy + stamp_h + 12),
        outline=sev_color, width=4,
    )
    draw.text((sx, sy), stamp_text, font=font_stamp, fill=sev_color)
    
    # ACKNOWLEDGED / VERIFIED label (right side)
    label = 'ACKNOWLEDGED' if is_compliance else 'VERIFIED'
    label_color = ACCENT_LOW
    font_label = _load(FONT_PATH_BOLD, 22)
    lbbox = draw.textbbox((0, 0), label, font=font_label)
    lw = lbbox[2] - lbbox[0]
    lh = lbbox[3] - lbbox[1]
    lx = inner_right - lw - 14
    draw.rectangle(
        (lx - 14, sy - 8, lx + lw + 14, sy + lh + 12),
        outline=label_color, width=4,
    )
    draw.text((lx, sy), label, font=font_label, fill=label_color)
    
    y += 70
    
    # Registry ID — big
    font_reg_label = _load(FONT_PATH_MONO_BOLD, 14)
    draw.text((inner_left, y), 'REGISTRY ID', font=font_reg_label, fill=MUTED)
    y += 22
    font_reg = _load(FONT_PATH_BOLD, 56)
    reg_id = cert.get('registry_id', 'KR-2026-XXXXXX')
    draw.text((inner_left, y), reg_id, font=font_reg, fill=INK)
    y += 78
    
    # Two-column: Subject | Classification (if not compliance)
    col_w = (inner_right - inner_left) // 2 - 20
    
    # Subject (left)
    draw.text((inner_left, y), 'SUBJECT', font=font_reg_label, fill=MUTED)
    name = cert.get('name') or 'Anonymous Entity'
    font_field = _load(FONT_PATH_MONO_BOLD, 24)
    draw.text((inner_left, y + 22), _truncate(name, 28), font=font_field, fill=INK)
    
    # Right column varies by cert type
    rx = inner_left + col_w + 40
    if is_compliance:
        draw.text((rx, y), 'JURISDICTION', font=font_reg_label, fill=MUTED)
        jur = cert.get('jurisdiction') or 'Unspecified'
        draw.text((rx, y + 22), _truncate(jur, 28), font=font_field, fill=INK)
    else:
        draw.text((rx, y), 'RISK SCORE', font=font_reg_label, fill=MUTED)
        risk = cert.get('risk_score', 0)
        draw.text((rx, y + 22), f'{risk}/100', font=font_field, fill=INK)
    
    y += 80
    
    # Protocol
    draw.text((inner_left, y), 'PROTOCOL APPLIED', font=font_reg_label, fill=MUTED)
    y += 22
    protocol = cert.get('protocol', 'Standard Absolution Protocol')
    font_proto = _load(FONT_PATH_MONO, 18)
    draw.text((inner_left, y), _truncate(protocol, 72), font=font_proto, fill=INK)
    
    y += 60
    # Bottom divider
    draw.line([(inner_left, y), (inner_right, y)], fill=INK, width=2)
    y += 20
    
    # Footer line — verification + tagline
    font_footer = _load(FONT_PATH_MONO, 14)
    tier = (cert.get('tier') or 'free').upper()
    status = (cert.get('status') or 'Issued').upper()
    footer_left = f'{tier} TIER · {status}'
    footer_right = 'karmacleanse.online'
    draw.text((inner_left, y), footer_left, font=font_footer, fill=MUTED)
    bb = draw.textbbox((0, 0), footer_right, font=font_footer)
    draw.text(
        (inner_right - (bb[2] - bb[0]), y),
        footer_right,
        font=font_footer,
        fill=MUTED,
    )
    
    buf = io.BytesIO()
    img.save(buf, format='PNG', optimize=True)
    return buf.getvalue()


def build_share_html(cert: dict, image_url: str, app_url: str) -> str:
    """Build HTML page with Open Graph meta tags + JS redirect to React app."""
    registry_id = cert.get('registry_id', '')
    is_compliance = cert.get('receipt_type') == 'tc_acknowledgment'
    
    if is_compliance:
        title = f'Karma Cleanse — Compliance Receipt {registry_id}'
        description = (
            f"{cert.get('name', 'Anonymous')} has procedurally acknowledged "
            f"Karma Cleanse Operational Terms. Filed in triplicate. "
            f"Jurisdiction: {cert.get('jurisdiction', 'Unspecified')}."
        )
    else:
        severity = cert.get('severity_class', 'Low')
        title = f'Karma Cleanse — {severity} Class · {registry_id}'
        description = (
            f"{cert.get('name', 'Anonymous')} has been issued an official "
            f"Karma Cleanse certificate. Severity: {severity}. "
            f"Risk Score: {cert.get('risk_score', 0)}/100. "
            f"Emotional bureaucracy since 2026."
        )
    
    # Escape minimally for HTML attributes
    def esc(s: str) -> str:
        return (s.replace('&', '&amp;').replace('"', '&quot;')
                 .replace('<', '&lt;').replace('>', '&gt;'))
    
    title_e = esc(title)
    desc_e = esc(description)
    img_e = esc(image_url)
    app_e = esc(app_url)
    
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8" />
<title>{title_e}</title>
<meta name="description" content="{desc_e}" />

<!-- Open Graph -->
<meta property="og:type" content="website" />
<meta property="og:title" content="{title_e}" />
<meta property="og:description" content="{desc_e}" />
<meta property="og:image" content="{img_e}" />
<meta property="og:image:width" content="1200" />
<meta property="og:image:height" content="630" />
<meta property="og:url" content="{app_e}" />
<meta property="og:site_name" content="Karma Cleanse" />

<!-- Twitter -->
<meta name="twitter:card" content="summary_large_image" />
<meta name="twitter:title" content="{title_e}" />
<meta name="twitter:description" content="{desc_e}" />
<meta name="twitter:image" content="{img_e}" />

<meta http-equiv="refresh" content="0; url={app_e}" />
<style>
body{{font-family:monospace;background:#F4F4F0;color:#0A0A0A;text-align:center;padding:80px 20px}}
a{{color:#0A0A0A}}
</style>
</head>
<body>
<h1>Karma Cleanse</h1>
<p>Loading certificate {esc(registry_id)}...</p>
<p><a href="{app_e}">Continue to the certificate</a></p>
<script>window.location.replace("{app_e}");</script>
</body>
</html>"""
