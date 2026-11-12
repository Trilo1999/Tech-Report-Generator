"""
RAG Faithfulness and Hallucination Verification Engine.

Evaluates draft report assertions against accumulated evidence chunks to detect
fabricated claims, invalid citations, and unsupported empirical statements.
"""

import re
from typing import Any, Dict, List, Set


class FaithfulnessVerifier:
    """Verifies that generated reports are faithfully grounded in retrieved evidence."""

    CITATION_PATTERN = re.compile(
        r"\[([A-Z0-9_\-]+(?::\s*[^\]]+)?)\]"
    )  # e.g. [QDR-01: Architectural Guidelines] or [QDR-01]
    NUMERICAL_OR_ABSOLUTE_PATTERN = re.compile(
        r"(\b\d+(?:\.\d+)?%|\$\d+(?:,\d{3})*(?:\.\d+)?|\b\d+(?:\.\d+)?ms|\bops/sec\b|\bautomatically eliminates\b|\bzero latency\b|\bwithout latency penalty\b|\bguarantees zero\b)",
        re.IGNORECASE,
    )

    @classmethod
    def extract_source_ids(cls, text: str) -> List[str]:
        """Extract canonical source IDs from inline citation markers."""
        matches = cls.CITATION_PATTERN.findall(text)
        cleaned_ids = []
        for match in matches:
            # Strip extra descriptor like ': Architectural Guidelines'
            base_id = match.split(":")[0].strip()
            if base_id:
                cleaned_ids.append(base_id)
        return list(dict.fromkeys(cleaned_ids))

    @classmethod
    def verify_report(
        cls,
        sections: Dict[str, str],
        evidence_list: List[Dict[str, Any]],
        existing_unsupported_claims: List[str] | None = None,
    ) -> Dict[str, Any]:
        """Perform comprehensive faithfulness and hallucination verification.

        Args:
            sections: Report section title -> markdown content.
            evidence_list: Normalized list of EvidenceItem dictionaries.
            existing_unsupported_claims: Pre-existing unsupported claims flagged by generator.

        Returns:
            Dict containing:
                - faithfulness_score: float (0.0 to 1.0)
                - hallucination_detected: bool
                - unsupported_claims: List of unverified or contradicted assertions
                - invalid_citations: List of cited source IDs not found in evidence
                - total_claims: int
                - verified_claims: int
        """
        valid_source_ids: Set[str] = {
            e.get("source_id", "").strip().upper()
            for e in evidence_list
            if e.get("source_id")
        }

        # Build combined text of evidence per source
        evidence_by_source: Dict[str, str] = {}
        for e in evidence_list:
            sid = e.get("source_id", "").strip().upper()
            content = f"{e.get('title', '')} {e.get('content', '')}".lower()
            if sid in evidence_by_source:
                evidence_by_source[sid] += " " + content
            else:
                evidence_by_source[sid] = content

        unsupported_claims: List[str] = list(existing_unsupported_claims or [])
        invalid_citations: Set[str] = set()

        total_claims = 0
        verified_claims = 0

        # Split text into candidate sentences/assertions
        for sec_name, content in sections.items():
            # Skip references or citations section if present
            if "reference" in sec_name.lower() or "citation" in sec_name.lower():
                continue

            sentences = [
                s.strip()
                for s in re.split(r"(?<=[.!?])\s+", content)
                if len(s.strip()) > 20
            ]

            for sentence in sentences:
                total_claims += 1
                cited_in_sentence = cls.extract_source_ids(sentence)

                if not cited_in_sentence:
                    # Sentence has no citation - check if it makes bold empirical claims
                    if cls.NUMERICAL_OR_ABSOLUTE_PATTERN.search(sentence):
                        claim_desc = f"{sentence} (No empirical citation provided in section '{sec_name}')"
                        if not any(sentence in c for c in unsupported_claims):
                            unsupported_claims.append(claim_desc)
                    else:
                        # General prose without quantitative claim
                        verified_claims += 1
                    continue

                # Sentence has citations - verify citation validity
                sentence_verified = True
                for cid in cited_in_sentence:
                    clean_cid = cid.strip().upper()
                    if clean_cid not in valid_source_ids:
                        invalid_citations.add(cid)
                        sentence_verified = False
                        claim_desc = f"Citation [{cid}] cited in '{sec_name}' does not exist in gathered evidence."
                        if not any(cid in c for c in unsupported_claims):
                            unsupported_claims.append(claim_desc)

                if sentence_verified:
                    verified_claims += 1

        # Deduplicate unsupported claims
        deduped_unsupported = list(dict.fromkeys(unsupported_claims))

        # Calculate faithfulness score
        if total_claims == 0:
            faithfulness_score = 1.0
        else:
            # Score penalizes unsupported claims
            score = max(0.0, (total_claims - len(deduped_unsupported)) / total_claims)
            faithfulness_score = round(score, 3)

        hallucination_detected = (
            len(deduped_unsupported) > 0 or len(invalid_citations) > 0
        )

        return {
            "faithfulness_score": faithfulness_score,
            "hallucination_detected": hallucination_detected,
            "unsupported_claims": deduped_unsupported,
            "invalid_citations": sorted(list(invalid_citations)),
            "total_claims": total_claims,
            "verified_claims": verified_claims,
        }


def verify_draft_faithfulness(
    draft_sections: Dict[str, str],
    evidence_list: List[Dict[str, Any]],
    existing_unsupported: List[str] | None = None,
) -> Dict[str, Any]:
    """Convenience functional wrapper for FaithfulnessVerifier."""
    return FaithfulnessVerifier.verify_report(
        sections=draft_sections,
        evidence_list=evidence_list,
        existing_unsupported_claims=existing_unsupported,
    )
