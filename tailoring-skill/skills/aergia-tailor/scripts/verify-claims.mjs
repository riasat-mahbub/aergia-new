function assert(condition, message) {
  if (!condition) throw new Error(message);
}

function narrativePieces(value) {
  if (typeof value === "string") return value.trim() ? [value.trim()] : [];
  if (!Array.isArray(value)) return [];
  const pieces = [];
  for (const block of value) {
    if (typeof block === "string") {
      if (block.trim()) pieces.push(block.trim());
      continue;
    }
    if (!block || typeof block !== "object") continue;
    if (Array.isArray(block.items)) {
      for (const item of block.items) {
        const text = (typeof item?.text === "string" ? item.text
          : (item?.runs ?? []).map((run) => run?.text ?? "").join("")).trim();
        if (text) pieces.push(text);
      }
    } else {
      const text = (typeof block.text === "string" ? block.text
        : (block.runs ?? []).map((run) => run?.text ?? "").join("")).trim();
      if (text) pieces.push(text);
    }
  }
  return pieces;
}

export function candidateNarrativeClaims(candidate) {
  const claims = [];
  for (const section of candidate.sections ?? []) {
    if (section.enabled === false) continue;
    const rows = Array.isArray(section.data) ? section.data : section.data ? [section.data] : [];
    for (const row of rows) {
      for (const key of ["summary", "description"]) {
        for (const text of narrativePieces(row?.[key])) claims.push(text);
      }
    }
  }
  return claims;
}

export function validateClaimVerification(report, candidate, context, candidateHash, inferenceNotes = []) {
  assert(report && typeof report === "object" && !Array.isArray(report), "claim-verification.json must be an object");
  assert(report.schema_version === "claim-verification-v1", "Claim verification schema_version is invalid");
  assert(report.candidate_input_hash === candidateHash, "Claim verification is for a different candidate");
  assert(Array.isArray(report.claims), "Claim verification claims must be an array");

  const expected = candidateNarrativeClaims(candidate);
  const actual = report.claims.map((claim) => claim?.text);
  assert(expected.length === actual.length && expected.every((claim, index) => actual[index] === claim),
    "Claim verification must cover every enabled summary and description item in document order");

  const sourceById = new Map((context.retrieved_sources ?? []).map((source) => [source.source_id, source]));
  const evidenceIds = new Set((context.candidate_evidence?.groups ?? []).flatMap((group) => (group.claims ?? []).map((claim) => claim.id)));
  for (const [index, claim] of report.claims.entries()) {
    assert(["EXPLICIT", "DERIVED", "INFERRED"].includes(claim.classification), `Claim ${index + 1} is unsupported and must be revised or removed`);
    assert(Array.isArray(claim.references) && claim.references.length > 0, `Claim ${index + 1} needs source references`);
    for (const reference of claim.references) {
      if (typeof reference.evidence_claim_id === "string") {
        assert(evidenceIds.has(reference.evidence_claim_id), `Claim ${index + 1} cites unknown CandidateEvidence`);
      } else {
        const source = sourceById.get(reference.source_id);
        assert(source && typeof reference.excerpt === "string" && reference.excerpt.length > 0
          && source.narrative.includes(reference.excerpt), `Claim ${index + 1} cites an invalid Library excerpt`);
      }
    }
    if (claim.classification === "INFERRED") {
      assert(inferenceNotes.some((note) => note.claim === claim.text), `Claim ${index + 1} needs an inference note for user review`);
    }
  }
  return { verified_claims: report.claims.length };
}
