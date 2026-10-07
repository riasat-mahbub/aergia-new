// Export the actual helper's allowlisted package with an opaque binding.
// Usage: node docs/fixtures/tailoring-v10-semantic/prepare-review.mjs <case> <arm> [candidate-final]
import { mkdir, readFile, writeFile } from 'node:fs/promises';
import { randomUUID } from 'node:crypto';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { prepareReviewPackage } from '../../../tailoring-skill/skills/aergia-tailor/scripts/fit-review.mjs';

const root = dirname(fileURLToPath(import.meta.url));
const [caseName, arm, stem = 'candidate'] = process.argv.slice(2);
if (!['software', 'analysis', 'collaboration'].includes(caseName)
  || !['baseline', 'revised'].includes(arm)
  || !['candidate', 'candidate-final'].includes(stem)) throw new Error('Synthetic case/arm required');
const run = join(root, caseName, arm);
const metadata = JSON.parse(await readFile(join(run, `${stem}-render.json`), 'utf8'));
const job = JSON.parse(await readFile(join(root, caseName, 'job.json'), 'utf8'));
const reviewRoot = join(root, 'review-packages');
await mkdir(reviewRoot, { recursive: true, mode: 0o700 });
const result = await prepareReviewPackage({
  reviewRoot,
  attempt: {
    evaluationId: randomUUID(), candidateHash: metadata.candidate_hash,
    preview: { pdf_sha256: metadata.pdf_sha256 },
    pdfBytes: await readFile(join(run, `${stem}.pdf`)),
  },
  job,
});
await writeFile(join(run, `${stem}-review-package.json`), `${JSON.stringify(result, null, 2)}\n`);
console.log(result.directory);
