---
skill_id: image
title: Image Product Identification & Search Strategy
domains: image, search, evidence
triggers: product image query, visual identification required, apple product release date, tech hardware recognition
summary: 处理包含产品图片的查询：先进行视觉/OCR特征提取以锁定型号，再构造精确查询词，最后验证日期信息。
confidence: 0.85
---
# Image Product Identification & Search Strategy

## When to use
- Question type: 涉及产品图片的发布、规格、价格等属性查询。
- Trigger: 输入包含Base64或URL的产品图片，且问题询问该产品的特定属性（如发售日期、型号、功能）。

## Diagnostic Cues / Credit Assignment
- **Failure Mode**: 直接忽略图像内容，使用通用关键词（如"Apple product"）搜索，导致结果混杂，无法定位具体型号。
- **Root Cause**: 缺乏从视觉到实体的映射步骤，未将图像特征转化为可检索的实体名称。
- **Success Pattern**: 成功识别图像中的关键视觉特征（如品牌Logo、独特设计、屏幕形态、文字标签），将其作为搜索的核心实体。

## Context & Evidence Selection Process
1. **Visual Extraction Phase**:
   - Analyze the image for brand identifiers (e.g., Apple logo, specific font).
   - Identify form factors and unique features (e.g., "headset", "glasses", "foldable screen", "transparent display").
   - Extract any visible text via OCR (model numbers, slogans).
   - *Constraint*: If visual analysis is ambiguous, generate a list of candidate models based on visual similarity.

2. **Query Construction Phase**:
   - Formulate search queries using the identified model name + specific attribute + target region.
   - Example: Instead of "Apple product China release", use "Apple Vision Pro release date China".
   - If multiple candidates exist, construct queries to distinguish them (e.g., "iPhone 15 vs iPhone 16 release date China").

3. **Evidence Verification Phase**:
   - Prioritize official sources (Apple Newsroom, official store pages) or authoritative tech news outlets.
   - Cross-check the extracted date against at least two independent snippets if possible.
   - Ensure the context matches the specific market (e.g., "China mainland" vs "Global").

## Tool Plan
- **Primary**: `search_text` with highly specific queries derived from visual analysis.
- **Secondary**: `browser_navigate` only if search snippets are insufficient or point to a specific press release page that needs full text extraction.
- **Fallback**: If visual identification fails completely, state the limitation and ask for clarification or provide a range of possibilities based on general knowledge.

## Stop / Retreat Conditions
- **Stop**: When a reliable source explicitly states the release date for the identified model in the target region.
- **Retreat**: If search results consistently return unrelated products or no clear match for the visual description, re-evaluate the visual features or acknowledge uncertainty.
- **Safety**: Do not hallucinate a model name if the image is too blurry or generic; output "Unable to identify specific model from image".

## Output Format Risks
- Avoid returning generic dates (e.g., "2024") without specifying the exact day/month if the question asks for precision.
- Ensure the final answer strictly follows the `<answer>...</answer>` format with only the date string.
- Do not include the reasoning process or image analysis steps in the final answer tag.
