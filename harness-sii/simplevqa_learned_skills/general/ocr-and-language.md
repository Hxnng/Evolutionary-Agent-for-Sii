---
skill_id: ocr-and-language
title: OCR And Text-Grounded Image QA
domains: image, OCR, text, language, simplevqa
triggers: visible text, title, poster, book cover, map label, formula, font, diagram, newspaper
summary: OCR-first strategy for SimpleVQA items where visible text, symbols, formulas, maps, posters, or covers identify the entity.
confidence: 0.78
---
# OCR And Text-Grounded Image QA

## When to use
- The image contains readable text: book title, newspaper masthead, poster title, map label, formula, algorithm diagram, font sample, brand logo, or treaty name.
- The visual object is generic, but the text disambiguates the entity.
- The question asks a factual property of the text-identified entity.

## Diagnostic Cues
- Book/media questions: author, publication year, philosophical work, album, newspaper establishment.
- Science/tech questions: formula name, algorithm inventor, font designer, index developer.
- Place questions: map county, church/landmark name visible on signs or metadata.

## Procedure
1. Extract every visible title, label, logo, or formula symbol before making a guess.
2. Normalize OCR errors:
   - `CoFieerning` may mean `Concerning`.
   - Transliterated Chinese names may need canonical English or Chinese forms.
   - Formula or diagram text may identify the concept rather than the final answer.
3. Use OCR text to lock the entity, then answer the relation.
4. If OCR conflicts with visual category, prefer OCR for named works and diagrams; prefer image for object position/scene category.
5. Keep the answer language consistent with the question or dataset style.

## Stop / Fallback
- Stop if the visible title/entity and requested relation match a known fact.
- If OCR is partial, combine it with entity class and source category before searching.
- If multiple works share a title, use image/source context and question relation to disambiguate.

## Output Contract
- Return a single concise answer in `<answer>...</answer>`.
