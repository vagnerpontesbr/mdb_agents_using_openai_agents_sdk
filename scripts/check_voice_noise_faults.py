"""Bounded synthetic noise and denied-provider probes; never records audio."""
import argparse
import asyncio
from datetime import datetime, timezone
import json
import logging
import os
from pathlib import Path
import uuid

if __package__:
    from . import check_voice_engine as voice
else:
    import check_voice_engine as voice


async def live():
    import numpy as np
    from openai import AsyncOpenAI, AuthenticationError
    session = 'phase0-noisy-voice-' + uuid.uuid4().hex[:12]
    report = {'session_id': session, 'calls': [], 'checks': {},
              'scope': 'One generated English fixture at 10 dB additive white noise; one real provider credential denial',
              'limitations': ['Not an acoustic benchmark, hosted service outage or remote cancellation proof.']}
    try:
        async with AsyncOpenAI(timeout=30, max_retries=0) as client:
            clean = await voice.fixture_audio(client)
            samples = np.frombuffer(clean, dtype='<i2').astype(np.float64)
            signal_rms = float(np.sqrt(np.mean(samples ** 2)))
            if signal_rms <= 0:
                raise ValueError('Empty generated fixture')
            rng = np.random.default_rng(20261029)
            noise = rng.normal(size=samples.shape)
            noise *= signal_rms / (10 ** (10 / 20)) / np.sqrt(np.mean(noise ** 2))
            mixed = samples + noise
            # Common gain avoids clipping and preserves the specified SNR.
            mixed *= min(1.0, 32760 / np.max(np.abs(mixed)))
            pcm = np.rint(mixed).astype('<i2').tobytes()
            report.update(snr_db=10, seed=20261029, input_pcm_bytes=len(pcm))
            try:
                output, lifecycle = await voice.voice_turn(pcm, session, report['calls'], client)
            except voice.UnexpectedTranscript as error:
                report.update(noise_outcome='rejected_before_engine', rejection_reason=error.reason)
                report['checks']['noise_rejected_without_engine_dispatch'] = not report['calls']
            else:
                report.update(noise_outcome='completed', output_pcm_bytes=len(output), lifecycle=lifecycle)
                report['checks']['noisy_fixture_engine_review_speech'] = True
        denied_calls = []
        async with AsyncOpenAI(api_key='synthetic-invalid-phase0-key', timeout=30, max_retries=0) as denied:
            try:
                await voice.voice_turn(pcm, session + '-denied', denied_calls, denied)
            except AuthenticationError as error:
                if error.status_code != 401:
                    raise
                report['checks']['provider_401_stops_before_engine'] = not denied_calls
                report['denied_provider_status'] = error.status_code
            else:
                raise ValueError('Expected invalid provider credential denial')
        report['status'] = 'passed' if all(report['checks'].values()) else 'failed'
    except Exception as error:
        report.update(status='failed_or_incomplete', error_class=type(error).__name__)
    report['recorded_at'] = datetime.now(timezone.utc).isoformat()
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--allow-live', action='store_true')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if not args.allow_live or not os.environ.get('OPENAI_API_KEY'):
        parser.error('Requires --allow-live and privately injected OPENAI_API_KEY')
    logging.disable(logging.CRITICAL)
    report = asyncio.run(live())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))
    return 0 if report['status'] == 'passed' else 1


if __name__ == '__main__':
    raise SystemExit(main())
