import random

HIGH_KEYWORDS = ['ghosted', 'cheated', 'lied', 'betrayed', 'stole', 'manipulated', 'abandoned', 'hurt', 'ruined']
MODERATE_KEYWORDS = ['overreacted', 'ignored', 'forgot', 'risky', 'problem', 'awkward', 'mistake', 'regret']
LOW_KEYWORDS = ['late', 'clumsy', 'petty', 'minor', 'small', 'trivial']

PROTOCOLS = [
    'Protocol 1.1a — Minor Social Friction',
    'Protocol 2.3c — Moderate Emotional Disruption',
    'Protocol 4.2b — Significant Interpersonal Event',
    'Protocol 7.0 — Critical Karmic Incident',
]

STABILITY = ['Fully Recoverable', 'Recoverable', 'Conditionally Stable', 'Unstable']

DIAGNOSTICS_POOL = [
    'Emotional residue scan complete.',
    'Passive aggression residue detected.',
    'Unread emotional debt identified.',
    'Interpersonal friction coefficient elevated.',
    'Social contract violation logged.',
    'Guilt accumulation within normal parameters.',
    'Minor accountability deficit observed.',
    'Karmic balance sheet updated.',
]

CRITICAL_DIAGNOSTICS = [
    'Multiple interpersonal anomalies detected.',
    'Critical emotional infrastructure failure.',
    'Immediate administrative intervention recommended.',
]

def analyze_severity(confession: str) -> dict:
    """Analyze confession text and return severity classification"""
    text = confession.lower()
    score = 30 + random.randint(0, 20)  # base 30-50

    # Keyword scoring
    for keyword in HIGH_KEYWORDS:
        if keyword in text:
            score += 20
    
    for keyword in MODERATE_KEYWORDS:
        if keyword in text:
            score += 10
    
    for keyword in LOW_KEYWORDS:
        if keyword in text:
            score += 5

    # Length factor
    if len(text) > 200:
        score += 10
    if len(text) > 400:
        score += 5

    # Random noise ±10
    score += random.randint(-10, 10)
    score = max(10, min(99, score))

    # Determine classification
    if score < 30:
        severity_class = 'Low'
        protocol_idx = 0
        stability_idx = 0
    elif score < 55:
        severity_class = 'Moderate'
        protocol_idx = 1
        stability_idx = 1
    elif score < 80:
        severity_class = 'High'
        protocol_idx = 2
        stability_idx = 2
    else:
        severity_class = 'Critical'
        protocol_idx = 3
        stability_idx = 3

    # Generate diagnostics
    diagnostics = [random.choice(DIAGNOSTICS_POOL)]
    if severity_class in ['High', 'Critical']:
        diagnostics.append('Significant emotional debt identified.')
    if severity_class == 'Critical':
        diagnostics.extend(random.sample(CRITICAL_DIAGNOSTICS, 2))

    return {
        'severity_class': severity_class,
        'stability': STABILITY[stability_idx],
        'risk_score': score,
        'protocol': PROTOCOLS[protocol_idx],
        'diagnostics': diagnostics,
    }