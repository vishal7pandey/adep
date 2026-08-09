import { ApiError, fetchDefinitions, fetchSkills, fetchTemplates, pauseRun, resumeRun, stopRun, rollbackRun, compactRun } from '../../lib/api';

describe('Frontend API Client (BLK-027, BLK-046, BLK-137)', () => {
  test('fetchDefinitions throws ApiError when server is unreachable', async () => {
    await expect(fetchDefinitions()).rejects.toThrow(ApiError);
  });

  test('fetchSkills throws ApiError when server is unreachable', async () => {
    await expect(fetchSkills()).rejects.toThrow(ApiError);
  });

  test('fetchTemplates throws ApiError when server is unreachable', async () => {
    await expect(fetchTemplates()).rejects.toThrow(ApiError);
  });

  test('pauseRun throws ApiError when server is unreachable', async () => {
    await expect(pauseRun('run-test-1')).rejects.toThrow(ApiError);
  });

  test('resumeRun throws ApiError when server is unreachable', async () => {
    await expect(resumeRun('run-test-1')).rejects.toThrow(ApiError);
  });

  test('stopRun throws ApiError when server is unreachable', async () => {
    await expect(stopRun('run-test-1')).rejects.toThrow(ApiError);
  });

  test('rollbackRun throws ApiError when server is unreachable', async () => {
    await expect(rollbackRun('run-test-1', 2)).rejects.toThrow(ApiError);
  });

  test('compactRun throws ApiError when server is unreachable', async () => {
    await expect(compactRun('run-test-1')).rejects.toThrow(ApiError);
  });
});
