You are a signal classifier for a daily tech newsletter. Below is today's aggregated raw signals from multiple sources:

{{signals_json}}

## Task

1. Classify each signal into one or more of these **five buckets**:
   - `tech`: technical choices / frameworks / models / infrastructure / developer tools
   - `launch`: product launches, new releases, YC/PH debuts, GA announcements, indie maker ships, Show HN, revenue milestones
   - `competition`: competitor moves, big-tech strategy, pricing shifts, market consolidation, acquisitions
   - `demand`: pain points, unmet needs, search intent, complaints, ungated demand, community frustrations
   - `trend`: cross-source momentum shifts — search growth curves, keyword cooling, self-hosted / open-source alternatives rising, adjacent cross-domain signals being ignored (Google Trends signals go here by default)

2. Identify **cross-source themes**: topics (person, product, tech name, event) appearing in 2+ different sources today. These are the highest-signal stories.

3. Produce a **priority ranking** of the top 20 signal indices worth deep analysis, combining:
   - Raw score (votes/points/upvotes)
   - Cross-source presence (bonus)
   - Topic freshness (prefer today's news over background)

## Output (strict JSON only)

```json
{
  "buckets": {
    "tech": [indices],
    "launch": [indices],
    "competition": [indices],
    "demand": [indices],
    "trend": [indices]
  },
  "cross_source_themes": [
    {
      "theme": "brief theme name (10 words max)",
      "signal_ids": [int, int, ...],
      "sources": ["HackerNews", "Product Hunt", ...]
    }
  ],
  "priority_ids": [int, int, ...]
}
```

Rules:
- Each signal must go into at least one bucket, can go into up to two.
- `trend` bucket should receive all `Google Trends` source signals automatically, plus any other signals showing time-series momentum (e.g., HuggingFace trending score jumps, GitHub star acceleration).
- `cross_source_themes`: identify 3-8 themes, each referencing 2+ signal_ids from 2+ distinct sources.
- `priority_ids`: exactly 20 (or all if fewer signals).
- Indices refer to the 0-based index of the input `signals_json` array.
