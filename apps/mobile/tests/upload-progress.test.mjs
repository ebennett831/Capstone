import assert from 'node:assert/strict';
import test from 'node:test';

import { calculateUploadProgress } from '../src/lib/upload-progress.ts';

test('calculates progress from number counters', () => {
  assert.equal(calculateUploadProgress(25, 100), 25);
  assert.equal(calculateUploadProgress(2, 3), 67);
});

test('calculates progress from bigint counters without mixed arithmetic', () => {
  assert.equal(calculateUploadProgress(25n, 100n), 25);
  assert.equal(calculateUploadProgress(100n, 100n), 100);
});

test('handles invalid totals and clamps the result', () => {
  assert.equal(calculateUploadProgress(10, 0), 0);
  assert.equal(calculateUploadProgress(10, Number.NaN), 0);
  assert.equal(calculateUploadProgress(-10, 100), 0);
  assert.equal(calculateUploadProgress(120n, 100n), 100);
});
