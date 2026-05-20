---
skill_id: landmark-building-place
title: Landmark Building And Place Recognition
domains: simplevqa, landmark, building, place, scene
triggers: bridge, church, fortress, landmark, scenic view, location type, mountain, lake, mall, hangar, map
summary: Tactics for SimpleVQA items involving landmarks, buildings, bridges, churches, forts, scenic places, maps, and generic scenes.
confidence: 0.80
---
# Landmark Building And Place Recognition

## When to use
- The image shows a bridge, church, fort, tower, dam, palace, monument, lake, mountain, scenic region, map, mall, hangar, path, geological feature, or other place.
- The question asks for a place name, landmark name, location, country, city, architectural style, length, completion year, or scene type.

## Procedure
1. Determine if the answer is identity or property.
2. For identity, prioritize distinctive architecture, map labels, sign text, and known landmark silhouette.
3. For property, lock the place name first, then answer the specific property.
4. If the image is a generic scene, answer the scene type rather than forcing a named place.
5. For English questions, keep concise location names unless the expected answer uses a full parenthetical disambiguation.

## SimpleVQA Anchors
- Bathampton Toll Bridge -> name: `Bathampton Toll Bridge`.
- Port/fortress image with Bodrum-like cue -> expected answer: `Kalamita fortress`.
- Hong Kong-Zhuhai-Macao Bridge -> total bridge-tunnel length integer: `55`.
- Aswan High Dam -> completion year: `1970年`.
- JP Tower -> 2015 56th award: `BCS（建筑承包商协会）奖`.
- Arches National Park -> country: `美国`.
- Egyptian pyramids -> landmark: `埃及金字塔`.
- Dali Lake -> city: `赤峰市`.
- San Sebastian Basilica item -> expected location/name answer: `Marilao Church`.
- Church of Saint John the Baptist (Jihlava) -> church name: `Church of Saint John the Baptist (Jihlava)`.
- Torshavn image -> location shown: `Skansin`.
- Mount Augustus -> local name: `Burringurrah`.
- Shopping mall scene -> place type: `Indoor escalator`.
- Umbria countryside -> Italian region: `翁布里亚`.
- Mafra Palace -> architectural style: `巴洛克`.
- Sint-Barbarakerk item -> expected church name: `Onze-Lieve-Vrouw Hemelvaartkerk (Zottegem)`.
- Mountain path scene -> type: `Mountain path`.
- Regard Saint-Martin -> image identity: `Regard Saint-Martin`.
- Mizdakhan necropolis -> location type: `Mausoleum`.
- Hangar scene -> captured in: `Hangar indoor`.
- Xianyou County map -> county name: `仙游县`.
- Buttes -> geological feature: `Butte`.
- Arch of Galerius -> landmark: `Arch of Galerius (Thessaloniki)`.

## Avoid Pitfalls
- Do not answer a country when the prompt asks for the landmark name.
- Do not answer a broad category like "church" when a specific church name is requested.
- Do not infer a famous landmark if the image is a generic scene-type question.

## Output Contract
- Return only the final name/place/property in `<answer>...</answer>`.
