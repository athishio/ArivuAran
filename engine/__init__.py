"""
ArivuAran Detection Engine Package.
Deterministic scam scoring, PII redaction, link analysis, and verdict evaluation.
"""

from .redact import extract_urls, redact, extract_features
from .links import analyse_url, Signal
from .rules import evaluate_text_rules
from .decide import decide, analyse, analyze, AnalysisResult
from .voice_norm import normalise_voice_transcript

__all__ = [
    "extract_urls",
    "redact",
    "extract_features",
    "analyse_url",
    "Signal",
    "evaluate_text_rules",
    "decide",
    "analyse",
    "analyze",
    "AnalysisResult",
    "normalise_voice_transcript",
]
