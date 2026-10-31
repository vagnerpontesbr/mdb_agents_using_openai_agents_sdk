"""Exercise a price adaptation in an isolated source copy, with no provider or live writes."""
import importlib.util
import json
import sys
import tempfile
from pathlib import Path


def main():
    root = Path(__file__).resolve().parents[1]
    source = root / 'compatibility/openai_engine_adapter/src/openai_engine_adapter/journey_domain.py'
    old = source.read_text()
    assert old.count('"fiber-500": (500, 8990)') == 1
    adapted = old.replace('"fiber-500": (500, 8990)', '"fiber-500": (500, 9490)')
    with tempfile.TemporaryDirectory(prefix='telecom-adaptation-') as directory:
        target = Path(directory) / 'adapted_domain.py'
        target.write_text(adapted)
        spec = importlib.util.spec_from_file_location('telecom_adaptation_trial', target)
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        try:
            spec.loader.exec_module(module)
            quote = module.offer_plan('synthetic-adaptation', 'fiber-500', True)
            assert quote.monthly_minor == 9490 and 'USD 94.90 per month' in quote.text
            try:
                module.simulate_change('synthetic-adaptation', 'fiber-500', 8990, quote.reference)
            except ValueError:
                pass
            else:
                raise AssertionError('Stale quoted price was accepted')
            result = module.simulate_change('synthetic-adaptation', 'fiber-500', 9490, quote.reference)
            assert result.text == ('Simulation approved for fiber-500 at USD 94.90 per month. '
                                   'No live plan or charge was changed.')
        finally:
            sys.modules.pop(spec.name, None)
    assert source.read_text() == old
    print(json.dumps({'adapted_quote':True, 'stale_price_rejected':True,
                      'exact_simulation_template':True, 'repository_source_unchanged':True,
                      'provider_calls':0, 'live_business_writes':0}))


if __name__ == '__main__':
    main()
