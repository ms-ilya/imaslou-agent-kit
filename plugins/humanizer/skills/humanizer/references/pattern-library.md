# Pattern Library

## How this library works

Each pattern below is an **English manifestation** of a universal AI behavior. The structure for each:

1. **Universal principle** - What AI behavior this catches, applicable to any language
2. **English details** - Specific words, examples, before/after pairs

This is not a closed list. These are the most common and well-documented patterns as of current research. For non-English text, apply the universal principle line and reason about how that behavior manifests in the target language - don't force English word lists onto other languages.

**Inline vs. referenced split:** Patterns with short, stable word lists (3, 5, 10, 12-15, 18, 20-23) keep lists inline. Patterns with large or era-specific word lists (1, 2, 4, 6, 7, 8, 9, 11, 16, 17, 19) point to reference files in `<skill-dir>/references/`. When adding a new pattern, choose inline if the word list is under ~10 items and stable; choose reference file if it will grow or needs era tagging.

## TIER 1: Always fix

These are the most reliable AI tells. Fix every instance.

### 1. Specificity over vagueness

**Universal principle:** AI makes grandiose importance claims instead of citing specific evidence. In any language, look for inflated adjectives, vague authority appeals, and promotional language that carries no information.

This principle consolidates four related AI habits. Check for all of them:

- **a) Significance inflation** - claiming something is pivotal, transformative, a testament, etc. without evidence. Replace with specific facts or cut.
- **b) Notability name-dropping** - listing media outlets or famous names without context ("featured in NYT, BBC, Wired"). Replace with one specific citation that adds information.
- **c) Vague attributions** - "Experts believe," "Industry reports suggest," "Some critics argue." Replace with who said it and when, or cut.
- **d) Promotional puffery** - "nestled," "vibrant," "breathtaking," "groundbreaking." Replace with concrete description.

**Words to watch:** See Pattern 1 in `<skill-dir>/references/ai-tells-lexicon.md` for the full list (significance inflation, promotional puffery, vague attributions).

**Rule:** Replace vague importance-claims with specific facts. Replace "Experts believe X" with who said it and when. Replace "nestled in a breathtaking region" with the actual geography.

**Before:**
> Her views have been cited in The New York Times, BBC, Financial Times, and The Hindu. Nestled in a vibrant tech ecosystem, the company serves as a testament to innovation, marking a pivotal moment in the industry's evolution. Experts believe it plays a crucial role.

**After:**
> In a 2024 New York Times interview, she argued that AI regulation should focus on outcomes rather than methods. The company is based in Austin and makes developer tools. It has about 200 employees.

### 2. AI vocabulary by era

**Universal principle:** AI models overuse certain "safe," statistically common words at abnormal rates. The specific words differ by language and model era, but the pattern is the same - a small set of words appears far more often than in human writing of the same register.

These words appear at statistically abnormal rates in AI text. They shift over time as models update.

**Vocabulary lists and replacements:** Read `<skill-dir>/references/vocabulary-by-era.md` for the full era-tagged word lists with plain alternatives.

**Rule:** Replace with plain alternatives. "Additionally" becomes "also" or nothing. "Delve" becomes "look at" or "examine." "Leverage" becomes "use." "Facilitate" becomes "help" or "enable." Most of these words can simply be cut.

### 3. Copula avoidance

**Universal principle:** AI avoids simple "to be" constructions in favor of elaborate substitutes. Every language has a basic copula or equivalent linking construction - AI consistently avoids it in favor of fancier alternatives.

**Words to watch:** serves as, stands as, marks, represents [a], boasts, features, offers [a]

**Rule:** Use "is," "are," "has." Simple copulas are human.

**Before:** "Gallery 825 serves as LAAA's exhibition space."
**After:** "Gallery 825 is LAAA's exhibition space."

### 4. Participial phrase overuse

**Universal principle:** AI packs extra information into sentence endings using dependent clauses. In English this manifests as "-ing" participial tails. Other languages have equivalent patterns - subordinate clause cramming, excessive nominalizations, or serial verb constructions that string multiple actions into one sentence.

AI uses "X, doing Y" constructions at 2-5x the human rate.

**Words to watch:** Sentence-ending participial tails - see Pattern 4 in `<skill-dir>/references/ai-tells-lexicon.md`.

**Rule:** If a sentence ends with a participial phrase, either make it a separate sentence or cut it. Most participial tails are filler.

**Before:**
> The team redesigned the dashboard, streamlining the workflow and enabling users to access reports faster, ultimately contributing to higher satisfaction scores.

**After:**
> The team redesigned the dashboard. Reports load in two clicks instead of five.

### 5. Rule of three

**Universal principle:** AI forces ideas into groups of three for rhetorical balance. This is cross-linguistic - AI in any language gravitates toward tripled lists, tripled adjectives, and tripled examples. Humans use two, four, or one.

**Before:** "innovation, inspiration, and industry insights"
**After:** "talks and panels" or just "talks"

### 6. Formulaic transitions

**Universal principle:** AI uses stock bridge phrases between ideas instead of letting the logical connection speak for itself. Every language has its own set of AI-overused transition phrases - in English they're "That said," "Moving on," etc.; in other languages, look for the equivalent mechanical connectors.

**Words to watch:** See Pattern 6 in `<skill-dir>/references/ai-tells-lexicon.md`.

**Rule:** Cut the transition. Start the next thought directly. The connection is usually obvious without a bridge phrase.

### 7. Conclusion bloat and "Overall" opener

**Universal principle:** AI summarizes what it already said in a concluding paragraph. Human writers end when the content ends - the last paragraph carries new information or a specific forward-looking statement, not a recap.

**Words to watch:** See Pattern 7 in `<skill-dir>/references/ai-tells-lexicon.md`. Also: any final paragraph that restates everything already said.

**Rule:** End when the content ends. Don't summarize. Don't write an "in conclusion" paragraph. The last paragraph should contain new information or a specific forward-looking statement, not a recap.

**Before:**
> Overall, the new API is faster, more reliable, and easier to use. In conclusion, it represents a significant step forward for developers.

**After:**
> The migration guide is at docs.example.com/v3. We're deprecating v2 in March.

### 8. Didactic disclaimers

**Universal principle:** AI prefaces statements with importance markers - throat-clearing that signals "the following point is worth your attention," which paradoxically undermines the point. This pattern exists in every language. Cut and state directly.

**Words to watch:** See Pattern 8 in `<skill-dir>/references/ai-tells-lexicon.md`.

**Rule:** Cut the disclaimer. State the thing directly.

**Before:** "It's important to note that the data shows a declining trend."
**After:** "The data shows a declining trend."

## TIER 2: Fix when present

These matter but are more situational.

### 9. Negative parallelisms

**Universal principle:** AI constructs rhetorical "not X, but Y" contrasts to sound profound. The contrast is almost always filler - state the actual point directly.

**Words to watch:** See Pattern 9 in `<skill-dir>/references/ai-tells-lexicon.md`.

**Rule:** State the point directly. The rhetorical contrast is almost always filler.

**Before:** "It's not just about writing code; it's about crafting experiences that resonate with users."
**After:** "The focus has shifted from code quality to user experience."

### 10. Synonym cycling

**Universal principle:** AI rotates synonyms to avoid word repetition. Humans repeat the same word - it's natural and clear. When the same concept gets 3+ different names in a few paragraphs, AI was trying to sound varied.

**Words to watch:** When the same concept is referred to by 3+ different names within a few paragraphs.

**Before:** "The protagonist faces a crisis. The main character must then decide. The central figure ultimately chooses..."
**After:** "The protagonist faces a crisis. She must decide. She ultimately chooses..."

### 11. False ranges

**Universal principle:** AI creates "from X to Y" spans that suggest breadth but don't represent meaningful scales. The range is rhetorical filler, not information.

**Words to watch:** See Pattern 11 in `<skill-dir>/references/ai-tells-lexicon.md`.

**Before:** "The platform helps everyone from solo developers to enterprise teams, from startups to Fortune 500 companies."
**After:** "Mostly used by mid-size dev teams, though some large companies have adopted it."

### 12. Em dash overuse

**Universal principle:** AI latches onto one punctuation mark as a universal connector and overuses it. In English, this is the em dash (—). In other languages, look for whichever punctuation mark appears with suspicious frequency as a catch-all separator. The em dash character (—) is always an AI marker - human writers use a regular hyphen with spaces ( - ) instead.

AI uses em dashes as a universal connector. Always replace the em dash character (—) with a regular hyphen with spaces ( - ), comma, period, or parentheses. No exceptions - the typographic em dash is an AI fingerprint regardless of language, formality, or content type.

**Non-English languages (Russian, German, etc.):** Some languages use em dashes as standard grammar (e.g., Russian "тире" replaces copulas: "Москва — столица России"). This does NOT create an exception. AI overuses dashes in these languages at rates far above human norms, turning them into a catch-all connector just like in English. Replace with regular hyphens ( - ) in every language. Do not rationalize a "language exception" to skip this rule.

**Before:** "The tool — which launched last year — handles deployment — including rollbacks — and monitoring — both real-time and historical."
**After:** "The tool launched last year. It handles deployment (including rollbacks) and monitoring, both real-time and historical."

### 13. Boldface, emoji overuse, and list addiction

**Universal principle:** AI uses visual formatting (bold, emoji, bullet-point labels) and list structures as a structural crutch instead of letting prose carry meaning. This is cross-linguistic and cross-format. AI also converts naturally narrative content into bullet lists or numbered lists when flowing prose would be more natural and readable.

Remove mechanical bolding on every key term. Remove decorative emojis. Remove inline-header vertical lists (the **Bold Label:** followed by description pattern). Convert bullet lists back to prose when the items are naturally narrative or closely related.

**How to spot list addiction:**
- Content that reads as a paragraph broken into bullets - each item is a full sentence, items flow logically into each other, and the list format adds no clarity
- Numbered lists where the order doesn't matter (if you can shuffle the items without losing meaning, numbers are fake structure)
- Lists of 2-3 items that would read better as a single sentence with commas or "and"
- Exhaustive lists covering every possible case when 2-3 representative examples would suffice

**Before (bold labels):**
> - **Speed:** Code generation is significantly faster.
> - **Quality:** Output quality has improved.
> - **Adoption:** Usage continues to grow. 🚀

**After:**
> Code generation is faster. Output quality has improved somewhat, and adoption is growing - though the numbers are self-reported.

**Before (list addiction):**
> Key benefits of the migration:
> 1. Reduced latency by 40%
> 2. Simplified the deployment pipeline
> 3. Eliminated the need for manual configuration
> 4. Improved error messages
> 5. Better logging

**After:**
> The migration cut latency by 40% and simplified deployments - no more manual configuration. Error messages and logging got better too.

### 14. Title case in headings

**Universal principle:** AI applies mechanical capitalization rules uniformly. Match the capitalization conventions natural to the target language and format - don't apply English Title Case universally.

Use sentence case for headings. Title Case Every Word is an AI tell in most contexts outside newspaper headlines.

**Before:** "Strategic Negotiations And Global Partnerships"
**After:** "Strategic negotiations and global partnerships"

### 15. Curly quotation marks

**Universal principle:** AI applies typographic conventions inconsistently or in the wrong context. Match the target format's conventions - plaintext gets straight quotes, typeset prose gets proper typography.

In plaintext, markdown, and code-adjacent contexts, replace curly quotes (" " ' ') with straight quotes (" '). **Exception:** In typeset prose intended for print or web publishing, curly quotes are correct typography - keep them.

**Before (markdown):** "Here's what I think"
**After (markdown):** "Here's what I think"

### 16. Chatbot artifacts, sycophancy, and knowledge-cutoff disclaimers

**Universal principle:** AI leaves conversational scaffolding from its chat interface in the output - greetings, sign-offs, offers to continue, excessive agreement. These are direct evidence of machine origin in any language.

**Words to watch:** See Pattern 16 in `<skill-dir>/references/ai-tells-lexicon.md`.

**Rule:** Remove all of these. They are direct evidence of chatbot origin.

**Before:** "Great question! Here's a comprehensive overview. Let me know if you'd like me to expand on any section!"
**After:** (just the overview, no wrapper)

### 17. Filler phrases

**Universal principle:** AI pads sentences with phrases that add no information. Every language has its own set of filler constructions that AI overuses - in English, "in order to" instead of "to"; in other languages, equivalent verbose circumlocutions.

Cut these on sight. See Pattern 17 in `<skill-dir>/references/ai-tells-lexicon.md` for the full replacement table.

**Before:** "In order to fully realize the potential of these tools, it is worth noting that teams should align with best practices."
**After:** "Teams should follow the migration guide."

### 18. Excessive hedging

**Universal principle:** AI stacks hedge words and qualifiers to avoid commitment. One hedge is human caution; three hedges in one sentence is AI avoidance. This applies in any language.

AI stacks hedge words. Use one or zero.

**Before:** "It could potentially be argued that this might possibly have some positive effect on outcomes."
**After:** "It probably helps."

### 19. Generic positive conclusions

**Universal principle:** AI ends with optimistic, forward-looking platitudes instead of specific next steps. "The future looks bright" is meaningless in any language.

**Words to watch:** See Pattern 19 in `<skill-dir>/references/ai-tells-lexicon.md`.

**Before:** "In conclusion, the future of AI-assisted development looks bright. Exciting times lie ahead as we continue this journey."
**After:** "v3 ships in March. The migration guide covers breaking changes." (Or just end the piece - no conclusion needed.)

### 20. Hyphenated compound modifiers

**Universal principle:** AI applies formatting and grammar rules with mechanical, perfect consistency. Humans are inconsistent in gray areas - that inconsistency is natural. Look for suspiciously uniform application of any optional grammar rule.

AI hyphenates compound modifiers with perfect, mechanical consistency. The real issue isn't hyphens themselves - compound adjectives before nouns ("data-driven approach", "high-quality code") correctly need hyphens. The AI tell is *uniform* application even where style varies.

**Rule:** Keep hyphens where grammar requires them (compound adjective before noun). Vary in gray areas where style guides disagree. Don't hyphenate after a linking verb ("the approach is data driven") or well-established compounds that read fine open ("real time monitoring" vs "real-time monitoring" - either is acceptable in informal text).

**Before (AI-uniform):** "The cross-functional, data-driven, high-quality, well-established, open-source tool..."
**After (human-variable):** "The cross-functional, data-driven tool is high quality and well established. It's open source."

### 21. Pronoun avoidance

**Universal principle:** AI restates the full noun phrase instead of using pronouns. Every language has pronoun or reference-tracking mechanisms - AI underuses them because restating is "safer" for the model.

**Before:** "The machine learning model processes input data. The machine learning model then generates predictions. The machine learning model can also be fine-tuned."
**After:** "The machine learning model processes input data. It then generates predictions and can also be fine-tuned."

### 22. Structural monotony

**Universal principle:** AI writes paragraphs of uniform length with predictable structure - intro, body, body, body, conclusion. Humans write unevenly: one-sentence paragraphs, paragraphs without topic sentences, sections of wildly different length.

**Paragraph-level tells to watch for:**
- Every paragraph has exactly 3-4 sentences (AI's "comfort zone")
- Every paragraph opens with a topic sentence and closes with a mini-conclusion
- Sections are suspiciously balanced - each has the same number of paragraphs
- The "comprehensive overview" structure: AI organizes everything into neat, exhaustive categories with uniform coverage. Humans are selective and leave gaps.
- No paragraph is notably shorter or longer than its neighbors

**Rule:** Break this with one-sentence paragraphs, paragraphs without a topic sentence, uneven section lengths. Not every paragraph needs to be the same number of sentences. Let some sections be notably longer or shorter than others.

**Before:**
> The API handles authentication through OAuth 2.0. It supports both client credentials and authorization code flows. Tokens expire after one hour and can be refreshed automatically.
>
> The rate limiter enforces per-endpoint quotas. It uses a sliding window algorithm for accurate counting. Exceeded limits return a 429 status code with retry headers.

**After:**
> The API uses OAuth 2.0 - both client credentials and auth code flows. Tokens last an hour and refresh automatically.
>
> Rate limiting is per-endpoint, sliding window. You'll get a 429 with retry headers if you exceed it. Most apps never hit the limits.

### 23. Colon-itis

**Universal principle:** AI overuses a single syntactic pattern for introducing information. In English, it's the colon. In other languages, look for whatever introductory construction appears with suspicious regularity.

AI overuses colons to introduce clauses, lists, and explanations. Fold the setup into the statement.

**Before:** "The reason is simple: the API was never designed for real-time use. Consider the following: each request takes 200ms."
**After:** "The API was never designed for real-time use. Each request takes 200ms."
