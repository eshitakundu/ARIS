#!/usr/bin/env python3
"""
ARIS GÇö Adoption Decision Brief generator  (v2 GÇö professional redesign)

White-body, dark-header layout: reads as a document, not a webpage screenshot.
ARIS brand: dark header bar, gold accents, color-coded verdict and score bands.

Modes
-----
CLI:
    python generate_report.py verdict.json
    python generate_report.py verdict.json -o report.pdf
    cat verdict.json | python generate_report.py -

Heym pythonExec (invoked with no CLI args):
    Reads JSON from stdin, writes JSON to stdout:
    {"pdf_b64": "...", "filename": "ARIS-brief-{tool}.pdf",
     "verdict": "ADOPT", "score": 87}

Dependencies: reportlab>=4.0  (pip install reportlab)
"""
import json, sys, io, base64, re, textwrap
from datetime import date
from pathlib import Path

try:
    from reportlab.pdfgen import canvas as rl_canvas
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.colors import HexColor, white
    from reportlab.lib.units import mm
except ImportError:
    sys.exit("reportlab not installed GÇö run: pip install reportlab")

# GöÇGöÇ Page constants GöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇ
W, H   = A4          # 595.27 +ù 841.89 pts
LM     = 15 * mm     # left margin
RM     = W - 15*mm   # right margin
BODY_W = RM - LM     # usable width (~165mm)

# GöÇGöÇ Palette GöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇ
#  White body GÇö professional and printable.
#  Dark header GÇö ARIS brand identity.
#  Gold accents GÇö section titles, bars, wordmark.
#  Verdict / band colors GÇö semantic, color-blind distinguishable.
HDR_BG   = HexColor('#0A0A0F')
GOLD     = HexColor('#E3A92C')
GOLD_DIM = HexColor('#C4921A')
TEXT     = HexColor('#18181B')   # near-black body text
BODY     = HexColor('#3F3F46')   # secondary body text
MUTED    = HexColor('#71717A')   # captions, footnotes
RULE     = HexColor('#E4E4E7')   # separator lines
BAR_BG   = HexColor('#F4F4F5')   # bar track background
PANEL_BG = HexColor('#FAFAFA')   # score panel tint

ADOPT_C  = HexColor('#16A34A')
TRIAL_C  = HexColor('#2563EB')
HOLD_C   = HexColor('#D97706')
AVOID_C  = HexColor('#DC2626')

VERDICT_COLOR = {
    'ADOPT': ADOPT_C,
    'TRIAL': TRIAL_C,
    'HOLD':  HOLD_C,
    'AVOID': AVOID_C,
}
VERDICT_DESC = {
    'ADOPT': 'Strong evidence across dimensions GÇö adopt with confidence.',
    'TRIAL': 'Promising GÇö trial in a bounded context before wider rollout.',
    'HOLD':  'Significant risks or gaps GÇö hold until concerns are addressed.',
    'AVOID': 'Risk clearly outweighs benefit in the evaluated context.',
}

DIMS = [
    ('maintenance_health',  'Maintenance Health',  '20%'),
    ('security_risk',       'Security Risk',       '20%'),
    ('stack_compatibility', 'Stack Compatibility', '20%'),
    ('ecosystem_maturity',  'Ecosystem Maturity',  '15%'),
    ('production_adoption', 'Production Adoption', '15%'),
    ('learning_curve',      'Learning Curve',      '10%'),
]


# GöÇGöÇ Utilities GöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇ

def _band_color(v):
    if v is None: return MUTED
    if v >= 75:   return ADOPT_C
    if v >= 60:   return TRIAL_C
    if v >= 40:   return HOLD_C
    return AVOID_C


def _wrap(text, width=92):
    return textwrap.wrap(str(text), width=width) if text else []


def _find_verdict(obj):
    """Walk nested JSON to find the verdict dict (has recommendation + weighted_score)."""
    if isinstance(obj, dict):
        if 'recommendation' in obj and 'weighted_score' in obj:
            return obj
        for v in obj.values():
            r = _find_verdict(v)
            if r: return r
    elif isinstance(obj, list):
        for v in obj:
            r = _find_verdict(v)
            if r: return r
    return None


def _extract_signals(d):
    """Derive key signal bullets from verdict fields."""
    out = []
    if d.get('already_dependency') or d.get('stack_already_dependency'):
        ver = d.get('already_version') or d.get('stack_already_version') or ''
        out.append(f'Already a declared dependency in the target repo{(" (" + ver + ")" if ver else "")}.')
    sec = (d.get('dimension_scores') or {}).get('security_risk')
    if sec is not None and float(sec) < 30:
        out.append(f'Security veto triggered GÇö security score {sec:.0f} < 30.')
    cve = d.get('unpatched_cve_count') or d.get('open_cves')
    if cve is not None:
        out.append(f'{cve} unpatched CVE{"s" if cve != 1 else ""} in current release surface.')
    stars = d.get('github_stars') or d.get('stars')
    if stars:
        out.append(f'{int(stars):,} GitHub stars.')
    dl = d.get('weekly_downloads') or d.get('downloads_weekly')
    if dl:
        traj = d.get('trajectory') or ''
        out.append(f'{int(dl):,} weekly downloads{(" GÇö " + traj + " trajectory" if traj else "")}.')
    conf = d.get('confidence') or 0
    if 0 < conf < 0.60:
        out.append(f'Low confidence ({conf*100:.0f}%) GÇö key data sources unavailable; treat as indicative.')
    return out


# GöÇGöÇ Shared chrome GöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇ

def _header(c, h_mm, subtitle='', tool='', date_str=''):
    H_pts = h_mm * mm
    # Dark background
    c.setFillColor(HDR_BG)
    c.rect(0, H - H_pts, W, H_pts, fill=1, stroke=0)
    # Gold top accent line
    c.setFillColor(GOLD)
    c.rect(0, H - 2.5, W, 2.5, fill=1, stroke=0)

    mid_y = H - H_pts / 2

    # ARIS wordmark
    c.setFillColor(GOLD)
    c.setFont('Courier-Bold', 15)
    c.drawString(LM, mid_y + 2*mm, 'ARIS')

    # Subtitle (brief type)
    c.setFillColor(HexColor('#A1A1AA'))
    c.setFont('Helvetica', 7.5)
    c.drawString(LM + 38, mid_y + 2*mm + 1, subtitle)

    # Tool name (top-right, bold white)
    if tool:
        c.setFillColor(white)
        c.setFont('Courier-Bold', 10)
        c.drawRightString(RM, mid_y + 2*mm + 1, tool.upper())

    # Date (below tool name)
    if date_str:
        c.setFillColor(MUTED)
        c.setFont('Courier', 6.5)
        c.drawRightString(RM, mid_y - 2*mm, date_str)


def _footer(c, page, total, date_str):
    c.setStrokeColor(RULE)
    c.setLineWidth(0.5)
    c.line(LM, 18*mm, RM, 18*mm)
    c.setFillColor(MUTED)
    c.setFont('Courier', 6)
    c.drawString(LM, 14*mm, 'ARIS -+ Technology Adoption Intelligence -+ heuristic decision support, not investment advice')
    c.drawRightString(RM, 14*mm, f'{date_str}  -+  {page} of {total}')


def _section_title(c, y, title):
    """Gold left-border section header. Returns y below the rule."""
    c.setFillColor(GOLD)
    c.rect(LM, y - 1, 2.5, 10, fill=1, stroke=0)
    c.setFillColor(TEXT)
    c.setFont('Helvetica-Bold', 7.5)
    c.drawString(LM + 5, y, title)
    c.setStrokeColor(RULE)
    c.setLineWidth(0.4)
    c.line(LM, y - 3.5, RM, y - 3.5)
    return y - 11


# GöÇGöÇ Page 1: Executive Brief GöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇ

def draw_page1(c, d):
    today = date.today().strftime('%d %b %Y').upper()
    tool  = (d.get('tool_name') or d.get('package_name') or d.get('evaluated_tool') or '').strip()
    ctx   = (d.get('evaluation_context') or '').strip()

    # White page background
    c.setFillColor(white)
    c.rect(0, 0, W, H, fill=1, stroke=0)

    HDR_H = 38
    _header(c, HDR_H, subtitle='Adoption Decision Brief', tool=tool, date_str=today)

    # Context subtitle below header
    if ctx:
        ctx_short = ctx[:80] + ('GÇª' if len(ctx) > 80 else '')
        c.setFillColor(GOLD_DIM)
        c.setFont('Helvetica', 7.5)
        c.drawString(LM, H - HDR_H*mm - 5*mm, ctx_short)

    y = H - HDR_H*mm - (12*mm if ctx else 8*mm)

    # GöÇGöÇ Verdict block GöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇ
    rec   = (d.get('recommendation') or 'HOLD').upper()
    score = float(d.get('weighted_score') or 0)
    conf  = float(d.get('confidence') or 0)
    vc    = VERDICT_COLOR.get(rec, HOLD_C)

    VERDICT_H = 26*mm
    SPLIT     = W * 0.52

    # Left: colored panel with verdict text
    c.setFillColor(vc)
    c.rect(LM, y - VERDICT_H, SPLIT - LM - 4*mm, VERDICT_H, fill=1, stroke=0)

    c.setFillColor(white)
    c.setFont('Helvetica-Bold', 28)
    c.drawString(LM + 5*mm, y - 17*mm, rec)

    vdesc = VERDICT_DESC.get(rec, '')
    c.setFont('Helvetica', 7.5)
    c.drawString(LM + 5*mm, y - 23.5*mm, vdesc[:55])

    # Right: light panel with score
    c.setFillColor(PANEL_BG)
    c.setStrokeColor(RULE)
    c.setLineWidth(0.6)
    c.rect(SPLIT, y - VERDICT_H, RM - SPLIT, VERDICT_H, fill=1, stroke=1)

    panel_cx = SPLIT + (RM - SPLIT) / 2
    c.setFillColor(vc)
    c.setFont('Courier-Bold', 40)
    c.drawCentredString(panel_cx - 8, y - 17*mm, f'{score:.0f}')

    c.setFillColor(MUTED)
    c.setFont('Courier', 8.5)
    c.drawString(panel_cx + 16, y - 13*mm, '/ 100')

    c.setFillColor(MUTED)
    c.setFont('Helvetica', 7)
    c.drawCentredString(panel_cx, y - 23*mm, f'Confidence  {conf*100:.0f}%')

    y -= VERDICT_H + 9*mm

    # GöÇGöÇ Dimension Breakdown GöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇ
    y = _section_title(c, y, 'DIMENSION BREAKDOWN')
    y -= 4*mm

    LABEL_W = 44*mm
    WGHT_W  = 10*mm
    SCOR_W  = 9*mm
    BAR_H   = 5.5*mm
    ROW_GAP = 5*mm
    BAR_W   = BODY_W - LABEL_W - WGHT_W - SCOR_W - 4*mm

    dims  = d.get('dimension_scores') or {}
    narrs = d.get('dimension_narratives') or {}

    for key, label, weight in DIMS:
        val  = dims.get(key)
        narr = (narrs.get(key) or '').strip()
        bc   = _band_color(val)

        # Dimension label
        c.setFillColor(TEXT)
        c.setFont('Helvetica', 8.5)
        c.drawString(LM, y - 3, label)

        # Weight
        c.setFillColor(MUTED)
        c.setFont('Courier', 6.5)
        c.drawString(LM + LABEL_W, y - 3, weight)

        # Bar track
        bx = LM + LABEL_W + WGHT_W
        c.setFillColor(BAR_BG)
        c.roundRect(bx, y - BAR_H + 1.5*mm, BAR_W, BAR_H - 1.5*mm, 1.5, fill=1, stroke=0)

        # Bar fill GÇö color by score band
        if val is not None:
            fw = BAR_W * max(0.0, min(100.0, float(val))) / 100.0
            c.setFillColor(bc)
            if fw > 3:
                c.roundRect(bx, y - BAR_H + 1.5*mm, fw, BAR_H - 1.5*mm, 1.5, fill=1, stroke=0)

        # Score value
        c.setFillColor(bc)
        c.setFont('Courier-Bold', 9)
        sv = f'{val:.0f}' if val is not None else 'GÇö'
        c.drawString(bx + BAR_W + 3*mm, y - 3, sv)

        y -= BAR_H

        # Per-dimension narrative (one line, muted)
        if narr:
            note = narr[:96] + ('GÇª' if len(narr) > 96 else '')
            c.setFillColor(MUTED)
            c.setFont('Helvetica', 6.5)
            c.drawString(LM + LABEL_W + WGHT_W, y, note)
            y -= 4*mm

        y -= ROW_GAP

        # Subtle row rule
        c.setStrokeColor(RULE)
        c.setLineWidth(0.25)
        c.line(LM, y + 2, RM, y + 2)

    y -= 3*mm

    # GöÇGöÇ Security veto alert GöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇ
    sec_score = dims.get('security_risk')
    if sec_score is not None and float(sec_score) < 30:
        c.setFillColor(HexColor('#FEF2F2'))
        c.setStrokeColor(AVOID_C)
        c.setLineWidth(0.8)
        c.roundRect(LM, y - 9*mm, BODY_W, 9*mm, 2, fill=1, stroke=1)
        c.setFillColor(AVOID_C)
        c.setFont('Helvetica-Bold', 7.5)
        c.drawString(LM + 4*mm, y - 5.5*mm, 'GÜá  SECURITY VETO')
        c.setFillColor(HexColor('#991B1B'))
        c.setFont('Helvetica', 7.5)
        c.drawString(LM + 36*mm, y - 5.5*mm,
                     f'Score {float(sec_score):.0f} < 30 GÇö verdict capped at HOLD regardless of weighted total.')
        y -= 13*mm

    # GöÇGöÇ Key signals GöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇ
    signals = _extract_signals(d)
    if signals and y > 52*mm:
        y = _section_title(c, y, 'KEY SIGNALS')
        y -= 3*mm
        for sig in signals[:5]:
            if y < 26*mm: break
            c.setFillColor(GOLD)
            c.setFont('Courier-Bold', 9)
            c.drawString(LM, y, '-+')
            c.setFillColor(BODY)
            c.setFont('Helvetica', 7.5)
            c.drawString(LM + 4.5*mm, y, sig[:93])
            y -= 5*mm

    _footer(c, 1, 2, today)


# GöÇGöÇ Page 2: Intelligence Brief GöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇ

def draw_page2(c, d):
    today = date.today().strftime('%d %b %Y').upper()
    tool  = (d.get('tool_name') or d.get('package_name') or d.get('evaluated_tool') or '').strip()

    # White background
    c.setFillColor(white)
    c.rect(0, 0, W, H, fill=1, stroke=0)

    _header(c, 22, subtitle='Intelligence Brief', tool=tool, date_str=today)
    y = H - 22*mm - 10*mm

    # GöÇGöÇ Recommendation Rationale GöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇ
    rationale = (d.get('recommendation_rationale') or d.get('rationale') or '').strip()
    if rationale:
        y = _section_title(c, y, 'RECOMMENDATION RATIONALE')
        y -= 4*mm
        for line in _wrap(rationale, 93):
            if y < 25*mm: break
            c.setFillColor(BODY)
            c.setFont('Helvetica', 8)
            c.drawString(LM, y, line)
            y -= 5*mm
        y -= 7*mm

    # GöÇGöÇ Alternatives GöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇ
    alts = d.get('alternatives') or []
    alts_text = ''
    if isinstance(alts, str):
        alts_text = alts
        alts = []
    if not alts:
        alts_text = alts_text or (d.get('alternatives_summary') or '')

    if alts or alts_text:
        y = _section_title(c, y, 'ALTERNATIVES CONSIDERED')
        y -= 4*mm

        if alts:
            # 3-column table: tool | description | when to choose
            COL_W = (32*mm, 74*mm, 54*mm)
            xpos  = (LM, LM + COL_W[0], LM + COL_W[0] + COL_W[1])

            # Header row
            c.setFillColor(HexColor('#F4F4F5'))
            c.rect(LM, y - 7*mm, BODY_W, 7*mm, fill=1, stroke=0)
            c.setStrokeColor(RULE)
            c.setLineWidth(0.35)
            c.rect(LM, y - 7*mm, BODY_W, 7*mm, fill=0, stroke=1)
            for hdr, x in zip(('TOOL', 'DESCRIPTION / FIT', 'WHEN TO CHOOSE'), xpos):
                c.setFillColor(MUTED)
                c.setFont('Helvetica-Bold', 6)
                c.drawString(x + 2*mm, y - 4.5*mm, hdr)
            y -= 7*mm

            for i, alt in enumerate(alts[:4]):
                if y < 30*mm: break
                name = (alt.get('name') or alt.get('tool') or '')[:24]
                desc = (alt.get('description') or alt.get('fit') or alt.get('summary') or '')[:55]
                when = (alt.get('win_condition') or alt.get('when') or alt.get('choose_when') or '')[:40]

                row_bg = white if i % 2 == 0 else HexColor('#FAFAFA')
                c.setFillColor(row_bg)
                c.rect(LM, y - 7*mm, BODY_W, 7*mm, fill=1, stroke=0)
                c.setStrokeColor(RULE)
                c.setLineWidth(0.2)
                c.line(LM, y - 7*mm, RM, y - 7*mm)

                for txt, x in ((name, xpos[0]), (desc, xpos[1]), (when, xpos[2])):
                    c.setFillColor(TEXT)
                    c.setFont('Helvetica', 7)
                    c.drawString(x + 2*mm, y - 4.5*mm, txt)
                y -= 7*mm
            y -= 6*mm
        else:
            for line in _wrap(alts_text, 93):
                if y < 25*mm: break
                c.setFillColor(BODY)
                c.setFont('Helvetica', 8)
                c.drawString(LM, y, line)
                y -= 5*mm
            y -= 7*mm

    # GöÇGöÇ Caveats GöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇ
    caveats = d.get('caveats') or []
    if isinstance(caveats, str):
        caveats = [caveats] if caveats.strip() else []
    if caveats:
        y = _section_title(c, y, 'CAVEATS & CONFIDENCE NOTES')
        y -= 4*mm
        for cav in caveats[:6]:
            if not cav or y < 35*mm: break
            lines = _wrap(str(cav), 91)
            for i, line in enumerate(lines[:2]):
                prefix = '-+  ' if i == 0 else '    '
                c.setFillColor(MUTED)
                c.setFont('Helvetica', 7.5)
                c.drawString(LM, y, prefix + line)
                y -= 4.5*mm
            y -= 2*mm

    # GöÇGöÇ Methodology footnote GöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇ
    NOTE_Y = 28*mm
    c.setStrokeColor(RULE)
    c.setLineWidth(0.4)
    c.line(LM, NOTE_Y + 5, RM, NOTE_Y + 5)
    c.setFillColor(HexColor('#A1A1AA'))
    c.setFont('Helvetica', 6)
    c.drawString(LM, NOTE_Y,
        'Scoring methodology: all dimension scores computed by deterministic Python GÇö no LLM ever produces a number.')
    c.drawString(LM, NOTE_Y - 4.5,
        'Confidence = 0.50+ùdata-completeness + 0.30+ùdeterministic-coverage + 0.20+ùagreement, capped at 0.95.')

    _footer(c, 2, 2, today)


# GöÇGöÇ Core GöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇGöÇ

def generate(d: dict) -> bytes:
    """Generate 2-page PDF from a verdict dict. Returns raw bytes."""
    buf = io.BytesIO()
    c   = rl_canvas.Canvas(buf, pagesize=A4)
    c.setTitle(f"ARIS GÇö {d.get('tool_name') or d.get('package_name') or 'Adoption Decision Brief'}")
    c.setAuthor('ARIS GÇö Technology Adoption Intelligence')
    c.setSubject('Adoption Decision Brief')

    draw_page1(c, d)
    c.showPage()
    draw_page2(c, d)
    c.showPage()
    c.save()

    buf.seek(0)
    return buf.read()

    import argparse
    p = argparse.ArgumentParser(description='ARIS PDF Report Generator')
    p.add_argument('source', help='Verdict JSON file path, or - for stdin')
    p.add_argument('-o', '--output', help='Output PDF path (default: ARIS-brief-{tool}.pdf)')
    args = p.parse_args()

    d   = load_verdict(args.source)
    out = args.output or f'ARIS-brief-{(d.get("tool_name") or "brief").lower().replace(" ", "-")}.pdf'
    pdf = generate(d)
    Path(out).write_bytes(pdf)
    print(f'G£ô  {out}', file=sys.stderr)


if __name__ == '__main__':
    main()
