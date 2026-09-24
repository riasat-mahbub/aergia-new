import test from "node:test";
import assert from "node:assert/strict";

import { candidateInputHash } from "../skills/aergia-tailor/scripts/validate-candidate.mjs";
import { candidateNarrativeClaims, validateClaimVerification } from "../skills/aergia-tailor/scripts/verify-claims.mjs";

const candidate = {
  sections: [{ id: "experience", type: "experience", enabled: true, data: [{
    description: [{ items: [{ runs: [{ text: "Worked on client-facing software projects." }] }] }],
  }] }],
};
const context = {
  retrieved_sources: [{ source_id: "source-1", narrative: "Worked directly with clients on software projects." }],
  candidate_evidence: { groups: [{ claims: [{ id: "claim-1" }] }] },
};
const verified = {
  schema_version: "claim-verification-v1",
  candidate_input_hash: candidateInputHash(candidate),
  claims: [{
    text: "Worked on client-facing software projects.",
    classification: "DERIVED",
    references: [{ source_id: "source-1", excerpt: "Worked directly with clients on software projects." }],
  }],
};

test("derived wording may cite a verified Library excerpt", () => {
  assert.deepEqual(candidateNarrativeClaims(candidate), ["Worked on client-facing software projects."]);
  assert.deepEqual(candidateNarrativeClaims({ sections: [{ type: "experience", enabled: true, data: [
    { description: [{ items: [{ text: "Built software with Git." }] }] },
  ] }] }), ["Built software with Git."]);
  assert.deepEqual(validateClaimVerification(verified, candidate, context, candidateInputHash(candidate)), { verified_claims: 1 });
});

test("unsupported, uncited, and stale claims cannot render", () => {
  assert.throws(() => validateClaimVerification({ ...verified, claims: [{ ...verified.claims[0], classification: "UNSUPPORTED" }] }, candidate, context, candidateInputHash(candidate)), /unsupported/);
  assert.throws(() => validateClaimVerification({ ...verified, claims: [{ ...verified.claims[0], references: [{ source_id: "source-1", excerpt: "Invented Azure work" }] }] }, candidate, context, candidateInputHash(candidate)), /invalid Library excerpt/);
  assert.throws(() => validateClaimVerification({ ...verified, candidate_input_hash: "0".repeat(64) }, candidate, context, candidateInputHash(candidate)), /different candidate/);
  assert.throws(() => validateClaimVerification({ ...verified, claims: [] }, candidate, context, candidateInputHash(candidate)), /cover every enabled/);
});

test("inferred wording requires an exact review note", () => {
  const inferred = { ...verified, claims: [{ ...verified.claims[0], classification: "INFERRED" }] };
  assert.throws(() => validateClaimVerification(inferred, candidate, context, candidateInputHash(candidate)), /inference note/);
  assert.deepEqual(validateClaimVerification(inferred, candidate, context, candidateInputHash(candidate), [
    { claim: "Worked on client-facing software projects." },
  ]), { verified_claims: 1 });
});
