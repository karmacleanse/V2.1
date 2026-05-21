"""
Open Graph image generator for Karma Cleanse certificates.
Produces a 1200x630 PNG with brutalist-style cert preview for social sharing.

Design priorities:
- Readable at thumbnail size (Twitter Card displays ~600x315 in feed)
- High contrast, BIG fonts, minimal clutter
- Brand recognition at a glance: KARMA CLEANSE + severity badge + registry ID
"""
import io
import logging
from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger(__name__)

FONT_PATH_BOLD = '/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf'
FONT_PATH_REGULAR = '/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf'
FONT_PATH_MONO = '/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf'
FONT_PATH_MONO_BOLD = '/usr/share/fonts/truetype/liberation/LiberationMono-Bold.ttf'

OG_WIDTH = 1200
OG_HEIGHT = 630

# Brutalist palette
BG = (244, 244, 240)
INK = (10, 10, 10)
MUTED = (115, 115, 115)
ACCENT_LOW = (21, 128, 61)
ACCENT_MODERATE = (82, 82, 82)
ACCENT_HIGH = (180, 83, 9)
ACCENT_CRITICAL = (217, 45, 32)
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
    return text[:max_chars - 1].rstrip() + '\u2026'


def generate_og_image(cert: dict) -> bytes:
    """Generate a 1200x630 PNG. Optimized for thumbnail readability."""
    img = Image.new('RGB', (OG_WIDTH, OG_HEIGHT), BG)
    draw = ImageDraw.Draw(img)
    
    severity = cert.get('severity_class', 'Low')
    sev_color = _color_for(severity)
    is_compliance = cert.get('receipt_type') == 'tc_acknowledgment'
    
    # Card with thick black border
    margin = 28
    card = (margin, margin, OG_WIDTH - margin, OG_HEIGHT - margin)
    draw.rectangle(card, fill=(255, 255, 255), outline=INK, width=6)
    
    # Severity-colored top band (visual cue at thumbnail size)
    band_height = 84
    draw.rectangle(
        (card[0], card[1], card[2], card[1] + band_height),
        fill=sev_color,
    )
    
    # KARMA CLEANSE — large, white on color band
    font_brand = _load(FONT_PATH_BOLD, 56)
    draw.text(
        (card[0] + 30, card[1] + 14),
        'KARMA CLEANSE',
        font=font_brand,
        fill=(255, 255, 255),
    )
    
    # Severity word on right of band
    font_band_right = _load(FONT_PATH_BOLD, 36)
    if is_compliance:
        right_text = 'COMPLIANCE'
    else:
        right_text = f'CLASS {severity.upper()}'
    bbox = draw.textbbox((0, 0), right_text, font=font_band_right)
    rw = bbox[2] - bbox[0]
    draw.text(
        (card[2] - 30 - rw, card[1] + 24),
        right_text,
        font=font_band_right,
        fill=(255, 255, 255),
    )
    
    # Content area
    inner_left = card[0] + 50
    inner_right = card[2] - 50
    y = card[1] + band_height + 50
    
    # REGISTRY ID label
    font_label = _load(FONT_PATH_MONO_BOLD, 20)
    draw.text((inner_left, y), 'REGISTRY ID', font=font_label, fill=MUTED)
    y += 32
    
    # Registry ID — huge
    font_reg = _load(FONT_PATH_BOLD, 92)
    reg_id = cert.get('registry_id', 'KR-XXXX-XXX')
    draw.text((inner_left, y), reg_id, font=font_reg, fill=INK)
    y += 110
    
    # SUBJECT
    draw.text((inner_left, y), 'SUBJECT', font=font_label, fill=MUTED)
    y += 28
    font_field_big = _load(FONT_PATH_MONO_BOLD, 38)
    name = cert.get('name') or 'Anonymous Entity'
    draw.text((inner_left, y), _truncate(name, 32), font=font_field_big, fill=INK)
    y += 52
    
    # Risk / Jurisdiction — big, single line, no clutter
    if is_compliance:
        sub_text = f"Jurisdiction: {cert.get('jurisdiction', 'Unspecified')}"
    else:
        risk = cert.get('risk_score', 0)
        sub_text = f'Risk Score: {risk}/100'
    font_sub = _load(FONT_PATH_MONO_BOLD, 34)
    draw.text((inner_left, y), _truncate(sub_text, 40), font=font_sub, fill=INK)
    y += 60
    
    # Bottom CTA — big, hard to miss
    cta_y = card[3] - 80
    draw.line([(inner_left, cta_y - 24), (inner_right, cta_y - 24)],
              fill=INK, width=4)
    
    font_cta_left = _load(FONT_PATH_BOLD, 44)
    draw.text(
        (inner_left, cta_y),
        'karmacleanse.online',
        font=font_cta_left,
        fill=INK,
    )
    
    font_cta_right = _load(FONT_PATH_BOLD, 32)
    right = 'CLEANSE YOUR KARMA \u2192'
    rbb = draw.textbbox((0, 0), right, font=font_cta_right)
    draw.text(
        (inner_right - (rbb[2] - rbb[0]), cta_y + 8),
        right,
        font=font_cta_right,
        fill=sev_color,
    )
    
    buf = io.BytesIO()
    img.save(buf, format='PNG', optimize=True)
    return buf.getvalue()


def build_share_html(cert: dict, image_url: str, app_url: str) -> str:
    """Build HTML page with Open Graph meta tags + JS redirect to React app."""
    registry_id = cert.get('registry_id', '')
    is_compliance = cert.get('receipt_type') == 'tc_acknowledgment'
    
    if is_compliance:
        title = f'Karma Cleanse \u2014 Compliance Receipt {registry_id}'
        description = (
            f"{cert.get('name', 'Anonymous')} procedurally acknowledged the "
            f"Karma Cleanse Operational Terms. Filed in triplicate."
        )
    else:
        severity = cert.get('severity_class', 'Low')
        title = f'Karma Cleanse \u2014 Class {severity} \u00b7 {registry_id}'
        description = (
            f"{cert.get('name', 'Anonymous')} has been issued a karma cleanse "
            f"certificate. Class: {severity}. Risk Score: {cert.get('risk_score', 0)}/100. "
            f"Cleanse your own karma at karmacleanse.online."
        )
    
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
<p>Loading certificate {esc(registry_id)}\u2026</p>
<p><a href="{app_e}">Continue to the certificate</a></p>
<script>window.location.replace("{app_e}");</script>
</body>
</html>"""
