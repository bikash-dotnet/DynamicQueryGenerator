# Sprint 2: NLP Engine & Query Generation (7 Days)

## Goal
Implement NLP pipeline converting natural language to MongoDB queries

## Google ADK Integration Note
**Can use Google ADK instead of spaCy** for better accuracy:
- Better intent detection and entity extraction
- Pre-built query understanding agents
- Multi-language support (50+ languages)
- Cost: ~$0.002 per query

## High-Level Tasks

### Task 2.1: NLP Environment (3 hours)
- Install Google ADK SDK (or spaCy + transformers)
- Download language models
- Setup NLP processor class structure
- Configure model caching

### Task 2.2: Intent Detection (6 hours)
- Implement intent classifier using Google ADK
- Detect SELECT (allowed), DELETE/UPDATE/INSERT (blocked)
- Use keyword matching + ML classification
- Return confidence scores
- Log rejected intents with reasons

### Task 2.3: Field & Value Extraction (8 hours)
- Extract entities (fields, operators, values)
- Support operators: $eq, $gt, $lt, $gte, $lte, $ne, $regex
- Handle value type detection (number, string, date)
- Map natural language fields to schema fields
- Extract multiple conditions from complex sentences

### Task 2.4: Collection Detection (4 hours)
- Detect target collection from query text
- Use schema descriptions for context matching
- Build collection synonym mapping
- Return confidence score, ask if ambiguous

### Task 2.5: MongoDB Query Generator (8 hours)
- Build MongoDB query from extracted conditions
- Handle AND/OR logical operators
- Add default limit of 5 records
- Validate query against schema
- Escape user input to prevent injection

### Task 2.6: Similarity Search (5 hours)
- Implement text similarity using embeddings
- Use exact hash matching (fast path)
- Use cosine similarity for semantic matching
- Set similarity threshold at 85%
- Return top 3 similar queries with scores

### Task 2.7: Query Normalization (4 hours)
- Normalize text (lowercase, punctuation removal)
- Sanitize generated queries
- Whitelist allowed MongoDB operators
- Escape regex special characters

### Task 2.8: Testing (4 hours)
- Create test suite with 50+ sample queries
- Test all operator types
- Test injection attempts
- Achieve 85% code coverage

## Deliverables
- [ ] NLP pipeline converting text to MongoDB queries
- [ ] Intent detection with 95%+ accuracy
- [ ] Field extraction with 6+ operator types
- [ ] Query similarity for cache hits
- [ ] Test suite with 85% coverage

## Acceptance Criteria
- [ ] 95% accuracy on intent detection
- [ ] DELETE/UPDATE queries blocked with clear message
- [ ] Query generation produces valid MongoDB syntax
- [ ] Similarity search finds 85%+ similar queries
- [ ] No injection vulnerabilities

## Dependencies
- Sprint 1 (infrastructure)

## Risks
| Risk | Mitigation |
|------|------------|
| Google ADK costs too high | Implement spaCy fallback, cache results |
| NLP accuracy below target | Hybrid rule-based + ML, feedback loop |
| Latency > 2 seconds | Response caching, optimize models |