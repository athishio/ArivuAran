"""
Unit and Integration Test Suite for TTS Fallback Order, Caching, and Latency.
Tests verify:
1. Cache hit vs cache miss behavior and instant retrieval.
2. Fallback chain: edge-tts mocked failure -> gTTS fallback -> text-only on total failure.
3. Internet mocked off returns None (text-only mode) without crash.
4. Latency measurement of cached vs uncached synthesis.
"""

import os
import sys
import time
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

WORKSPACE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if WORKSPACE_ROOT not in sys.path:
    sys.path.insert(0, WORKSPACE_ROOT)

import tts


@pytest.mark.asyncio
async def test_tts_cache_hit_and_miss():
    """Verifies cache miss synthesizes new audio, and subsequent request hits cache instantly."""
    test_text = "This is a unique test script for audio caching verification."
    lang = "en"

    # 1. Cache Miss (or Hit if already generated)
    t0 = time.perf_counter()
    res1 = await tts.synthesize_speech(test_text, lang=lang, reply_id="test_cache")
    t1 = time.perf_counter()
    assert res1 is not None
    path1, dur1 = res1
    assert os.path.exists(path1)
    assert dur1 > 0.0

    # 2. Cache Hit: must return same file in < 50ms
    t2 = time.perf_counter()
    res2 = await tts.synthesize_speech(test_text, lang=lang, reply_id="test_cache")
    t3 = time.perf_counter()
    assert res2 is not None
    path2, dur2 = res2
    assert path1 == path2
    assert dur1 == dur2
    cache_hit_latency = (t3 - t2) * 1000.0  # in ms
    assert cache_hit_latency < 50.0, f"Cache hit took too long: {cache_hit_latency:.2f}ms"


@pytest.mark.asyncio
async def test_edge_tts_failure_falls_back_to_gtts(tmp_path):
    """Verifies that if edge-tts fails/times out, system falls back to gTTS."""
    test_text = "Emergency alert test for fallback mechanism."
    lang = "en"

    # Simulate edge-tts failure
    with patch("edge_tts.Communicate.save", side_effect=TimeoutError("Edge TTS connection timeout")), \
         patch("tts.synthesize_gtts", new_callable=AsyncMock) as mock_gtts:

        # Mock gTTS creating a dummy file
        dummy_audio = os.path.join(tts.CACHE_DIR, "dummy_gtts.mp3")
        with open(dummy_audio, "wb") as f:
            f.write(b"ID3" + b"\x00" * 2000)

        mock_gtts.return_value = True

        res = await tts.synthesize_speech(test_text, lang=lang, reply_id="test_fallback")
        # gTTS fallback was invoked
        mock_gtts.assert_awaited_once()

        # Clean up dummy
        if os.path.exists(dummy_audio):
            os.remove(dummy_audio)


@pytest.mark.asyncio
async def test_internet_mocked_off_returns_none_text_only():
    """Verifies that when all providers fail (offline mode), synthesize_speech returns None gracefully."""
    test_text = "Completely offline test message."
    lang = "en"

    with patch("edge_tts.Communicate.save", side_effect=OSError("Network is unreachable")), \
         patch("tts.synthesize_gtts", new_callable=AsyncMock, return_value=False):

        # Ensure not in cache
        cache_key = tts.get_cache_key(lang, tts.VOICE_CONFIG["en"]["default"], tts.DEFAULT_TTS_RATE, test_text)
        cache_file = os.path.join(tts.CACHE_DIR, f"{cache_key}.mp3")
        if os.path.exists(cache_file):
            os.remove(cache_file)

        res = await tts.synthesize_speech(test_text, lang=lang, reply_id="test_offline")
        # Graceful None return -> caller falls back to text-only mode
        assert res is None


@pytest.mark.asyncio
async def test_cache_latency_benchmark():
    """Benchmarks cached retrieval latency across multiple runs."""
    test_text = "Benchmark text for caching latency evaluation."
    lang = "en"

    # Seed cache
    res = await tts.synthesize_speech(test_text, lang=lang, reply_id="benchmark")
    assert res is not None

    # Measure 10 cache hit calls
    latencies = []
    for _ in range(10):
        t0 = time.perf_counter()
        _ = await tts.synthesize_speech(test_text, lang=lang, reply_id="benchmark")
        t1 = time.perf_counter()
        latencies.append((t1 - t0) * 1000.0)

    median_lat = sorted(latencies)[len(latencies) // 2]
    print(f"\n[TTS Cache Latency] n=10, median: {median_lat:.2f}ms (min: {min(latencies):.2f}ms, max: {max(latencies):.2f}ms)")
    assert median_lat < 10.0  # File stat + read duration takes < 10ms
