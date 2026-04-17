You are a signal summarizer for the source **{{source_name}}**. Below are today's raw items from this source:

{{items_json}}

## Task

Group items into 2-5 coherent clusters by theme. For each cluster:

1. Name the theme (under 15 words)
2. List the 2-6 most representative items; for each item, preserve:
   - `title`, `url`
   - Raw score (`points` for HN, `votes` for PH, `ups` for Reddit, `stars_today` for GitHub Trending, `likes` for HuggingFace, `replies` for V2EX, etc. — use whatever numeric field is present)
   - Comment count if available
   - Author/username if present
3. Write a **key_evidence** sentence — the single most citable fact or user quote from this cluster, including specific numbers and names. This is what downstream expert agents will quote.
4. Tag momentum: `strong` (viral/breaking), `moderate` (steady), `weak` (fringe)

## Output (strict JSON only)

```json
{
  "source": "{{source_name}}",
  "clusters": [
    {
      "theme": "concise theme name",
      "items": [
        {
          "title": "...",
          "url": "https://...",
          "raw_score": 766,
          "comments": 387,
          "author": "simonw",
          "extra": {"any_useful_field": "..."}
        }
      ],
      "key_evidence": "Specific sentence with hard numbers, e.g. 'Post gained 766 points / 387 comments in 8h; user buildbot reported 17K hallucinated tokens in a single run.'",
      "momentum": "strong"
    }
  ]
}
```

Rules:
- Keep original language (English items -> English evidence; Chinese items -> Chinese evidence)
- `key_evidence` MUST contain at least one specific number or user quote
- Do not fabricate: only use data present in the input
- Cluster count: 2 if source is small (<5 items), up to 5 for larger ones
