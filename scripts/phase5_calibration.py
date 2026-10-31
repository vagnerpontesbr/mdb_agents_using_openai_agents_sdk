"""Offline threshold selection; only development observations may choose a value."""


def evaluate(rows, threshold):
    paraphrases = [r for r in rows if r['case_id'].startswith('paraphrase')]
    hits = [r for r in rows if r['similarity'] >= threshold]
    harmful = [r for r in hits if (
        r['counterfactual_warm']['candidate_recall'] < r['fresh']['candidate_recall']
        or r['counterfactual_warm']['top1']['precision'] < r['fresh']['top1']['precision'])]
    correct = sum((r['counterfactual_warm'] if r['similarity'] >= threshold else r['fresh'])[
        'top1']['precision'] == 1 for r in rows)
    return {'threshold':threshold, 'cases':len(rows), 'hits':len(hits),
            'harmful_hits':len(harmful), 'effective_top1_correct':correct,
            'paraphrase_hits':sum(r['similarity'] >= threshold for r in paraphrases),
            'paraphrases':len(paraphrases),
            'paraphrase_hit_rate':sum(r['similarity'] >= threshold for r in paraphrases)/len(paraphrases)
                                    if paraphrases else None}


def select(rows, thresholds, minimum, *, per_group=False):
    if not rows or any(not r['partition'].startswith('development') for r in rows):
        raise ValueError('Threshold selection requires development rows only')
    scores = [evaluate(rows, value) for value in sorted(thresholds, reverse=True)]
    if per_group:
        for score in scores:
            score['group_paraphrase_rates'] = {group:evaluate(
                [r for r in rows if r['partition']==group],score['threshold'])['paraphrase_hit_rate']
                for group in sorted({r['partition'] for r in rows})}
    eligible = [s for s in scores if s['harmful_hits'] == 0
                and s['paraphrase_hit_rate'] is not None and s['paraphrase_hit_rate'] >= minimum
                and s['effective_top1_correct'] == s['cases']
                and (not per_group or all(rate is not None and rate >= minimum
                     for rate in s['group_paraphrase_rates'].values()))]
    return {'selected':eligible[0]['threshold'] if eligible else None,'candidates':scores}
