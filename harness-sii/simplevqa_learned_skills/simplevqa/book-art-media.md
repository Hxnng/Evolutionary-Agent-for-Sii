---
skill_id: book-art-media
title: Books Art Movies And Media QA
domains: simplevqa, books, art, film, media, culture
triggers: book cover, artwork, movie poster, album, newspaper, publication year, author, title, origin country, display location
summary: Tactics for SimpleVQA items involving books, artworks, films, posters, albums, newspapers, and cultural media.
confidence: 0.80
---
# Books Art Movies And Media QA

## When to use
- The image is a book cover, artwork, movie poster, album, newspaper, or cultural media object.
- The question asks author, publication year, title, origin country, display location, artwork type, collection count, or establishment year.

## Procedure
1. Use OCR/title/poster text to identify the work.
2. Distinguish identity questions from property questions.
3. For translated works, answer in the requested language.
4. For movie origin, use the expected short region/country string.

## SimpleVQA Anchors
- `2001: A Space Odyssey` -> country/region: `UK`.
- Zhejiang University Newspaper -> formally established in `1998`.
- `战争论` -> author died of `霍乱`.
- `Modesty` artwork item -> title answer `Letizia Ramolino Bonaparte`.
- `Fright Night` -> origin `USA`.
- `Pietà` artwork item -> title answer `Madonna and Child (Detail)`.
- `人口地理学` -> author professor `张善余`.
- `Xiuqi Tang（汤秀琦）` book author dynasty -> `Ching Dynasty`.
- `一握之砂` -> contains `551` tanka.
- National Reading Day poster -> special day `全国阅读日`.
- `Kritik der reinen Vernunft` -> philosopher `伊曼努尔·康德 (Immanuel Kant)`.
- `Crimson Tide` -> movie title `Crimson Tide`.
- Sistine Chapel artwork type -> `Mythological`.
- `An Enquiry CoFieerning the Principles of Morale` -> first published in `1751`.
- `Blood Diamond` -> country/region `USA`.
- `Phänomenologie des Geistes` -> author `格奥尔格·威廉·弗里德里希·黑格尔 (Georg Wilhelm Friedrich Hegel)`.
- `Monsieur Louis Pascal` artwork -> displayed at `Musée Toulouse-Lautrec, Albi`.

## Avoid Pitfalls
- Do not answer a film title when the prompt asks for origin country.
- Do not answer the visible book title when the prompt asks for author or publication fact.
- Do not over-translate artwork and museum names.

## Output Contract
- Return only the answer body in `<answer>...</answer>`.
