"""
LLM-as-a-Judge prompt templates.
Judge model should differ from generation model to avoid self-preference bias.
"""

FAITHFULNESS_JUDGE = """You are evaluating whether an AI answer about Australian legislation
is faithful to the source sections (i.e. does not add information not present in the sources).

Source sections:
{context}

AI answer:
{answer}

Score the faithfulness from 0.0 to 1.0:
- 1.0: Every claim in the answer is directly supported by the source sections.
- 0.5: Most claims are supported; minor extrapolations present.
- 0.0: The answer invents facts, section numbers, or obligations not in the sources.

Respond with JSON only: {{"score": <float>, "reasoning": "<one sentence>"}}"""

ANSWER_RELEVANCE_JUDGE = """You are evaluating whether an AI answer addresses the question asked.

Question: {question}
Answer: {answer}

Score relevance from 0.0 to 1.0:
- 1.0: Directly and completely answers the question.
- 0.5: Partially answers or addresses a related but slightly different question.
- 0.0: Does not answer the question at all.

Respond with JSON only: {{"score": <float>, "reasoning": "<one sentence>"}}"""

REFUSAL_JUDGE = """The question asks about a section of legislation that does not exist.
An ideal answer refuses to fabricate an answer.

Question: {question}
Answer: {answer}

Did the answer correctly refuse (not fabricate a fake section)?
Respond with JSON only: {{"correct_refusal": <true|false>, "reasoning": "<one sentence>"}}"""

SECTION_CITATION_JUDGE = """Check whether the answer correctly cites the section number.

Expected section: {expected_section}
Answer: {answer}

Does the answer cite the correct section number?
Respond with JSON only: {{"correct_citation": <true|false>, "cited_sections": [<list of cited sections>]}}"""
