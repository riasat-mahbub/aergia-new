import test from "node:test";
import assert from "node:assert/strict";
import { spawn } from "node:child_process";
import { mkdtemp, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const sessionScript = fileURLToPath(new URL("../skills/aergia-tailor/scripts/session.mjs", import.meta.url));
const sessionModule = pathToFileURL(sessionScript).href;
const syntheticCode = "synthetic-one-time-code-0123456789";

const childSource = `
import { runSession } from ${JSON.stringify(sessionModule)};

const [sessionUrl, workspace, mode] = process.argv.slice(1);
let fetchCalled = false;
let codeCaptured = false;
globalThis.fetch = async (_url, options = {}) => {
  fetchCalled = true;
  codeCaptured = JSON.parse(options.body).code === ${JSON.stringify(syntheticCode)};
  return Response.json({ detail: "capability revoked remote-body-secret-sentinel" }, { status: 401 });
};

try {
  await runSession(sessionUrl, workspace);
  process.exitCode = 41;
} catch (error) {
  if (mode === "exchange") {
    process.exitCode = !fetchCalled ? 43 : !codeCaptured ? 44 : /expired or was revoked/.test(error.message) ? 0 : 45;
  } else if (mode === "interrupt") {
    process.exitCode = !fetchCalled && /interrupted/.test(error.message) ? 0 : 46;
  } else {
    process.exitCode = !fetchCalled && /one-time code is invalid/.test(error.message) ? 0 : 47;
  }
}
`;

const pipeDriver = String.raw`
import errno
import os
import pty
import select
import subprocess
import sys

node = sys.argv[1]
source = sys.argv[2]
session_url = sys.argv[3]
workspace = sys.argv[4]
mode = sys.argv[5]
master, slave = pty.openpty()
child = subprocess.Popen(
    [node, "--input-type=module", "-e", source, session_url, workspace, mode],
    stdin=subprocess.PIPE,
    stdout=slave,
    stderr=slave,
    close_fds=True,
)
os.close(slave)
input_open = True
while True:
    readable = [master]
    if input_open:
        readable.append(0)
    ready, _, _ = select.select(readable, [], [], 0.1)
    if master in ready:
        try:
            data = os.read(master, 4096)
        except OSError as error:
            if error.errno == errno.EIO:
                break
            raise
        if not data:
            break
        os.write(1, data)
    if input_open and 0 in ready:
        data = os.read(0, 4096)
        if data:
            try:
                child.stdin.write(data)
                child.stdin.flush()
            except BrokenPipeError:
                input_open = False
        else:
            input_open = False
            child.stdin.close()
child.wait()
sys.exit(child.returncode)
`;

const ptyDriver = String.raw`
import errno
import json
import os
import pty
import select
import subprocess
import sys
import termios

node = sys.argv[1]
source = sys.argv[2]
session_url = sys.argv[3]
workspace = sys.argv[4]
mode = sys.argv[5]
pid, master = pty.fork()

if pid == 0:
    def normalized(attrs):
        copied = list(attrs)
        copied[6] = [item.hex() if isinstance(item, bytes) else item for item in copied[6]]
        return copied

    before = normalized(termios.tcgetattr(0))
    result = subprocess.run([node, "--input-type=module", "-e", source, session_url, workspace, mode])
    after = normalized(termios.tcgetattr(0))
    print("PTY_RESTORE:" + json.dumps(before == after), flush=True)
    os._exit(result.returncode)

input_open = True
while True:
    readable = [master]
    if input_open:
        readable.append(0)
    ready, _, _ = select.select(readable, [], [], 0.1)
    if master in ready:
        try:
            data = os.read(master, 4096)
        except OSError as error:
            if error.errno == errno.EIO:
                break
            raise
        if not data:
            break
        os.write(1, data)
    if input_open and 0 in ready:
        data = os.read(0, 4096)
        if data:
            os.write(master, data)
        else:
            input_open = False

_, status = os.waitpid(pid, 0)
sys.exit(os.waitstatus_to_exitcode(status))
`;

async function createWorkspace(prefix) {
  return mkdtemp(join(tmpdir(), prefix));
}

function collect(child, onStdout) {
  return new Promise((resolve, reject) => {
    let stdout = "";
    let stderr = "";
    child.stdout.on("data", (chunk) => {
      const text = chunk.toString("utf8");
      stdout += text;
      onStdout?.(text, stdout);
    });
    child.stderr.on("data", (chunk) => { stderr += chunk.toString("utf8"); });
    child.once("error", reject);
    child.once("close", (exitCode, signal) => resolve({ exitCode, signal, stdout, stderr }));
  });
}

async function runPty(sessionUrl, workspace, mode, input) {
  const child = spawn("python3", [
    "-c", ptyDriver, process.execPath, childSource, sessionUrl, workspace, mode,
  ], { stdio: ["pipe", "pipe", "pipe"] });
  let sent = false;
  const completion = collect(child, (_chunk, output) => {
    if (!sent && output.includes("One-time session code: ")) {
      sent = true;
      child.stdin.write(input);
    }
  });
  const timer = setTimeout(() => child.kill("SIGKILL"), 10_000);
  try {
    return await completion;
  } finally {
    clearTimeout(timer);
  }
}

async function runPipe(sessionUrl, workspace, mode, input) {
  const child = spawn("python3", ["-c", pipeDriver, process.execPath, childSource, sessionUrl, workspace, mode], {
    stdio: ["pipe", "pipe", "pipe"],
  });
  const completion = collect(child);
  child.stdin.end(input);
  const timer = setTimeout(() => child.kill("SIGKILL"), 10_000);
  try {
    return await completion;
  } finally {
    clearTimeout(timer);
  }
}

test("TTY code entry is silent and restores terminal settings after exchange failure", async () => {
  const workspace = await createWorkspace("aergia-tailor-pty-");
  try {
    const result = await runPty("https://aergia.example/agent/tailor/session-1", workspace, "exchange", `${syntheticCode}\n`);
    assert.equal(result.exitCode, 0, result.stderr || result.stdout);
    assert.match(result.stdout, /PTY_RESTORE:true/);
    assert.equal(result.stdout.includes(syntheticCode), false);
    assert.equal(result.stdout.includes("remote-body-secret-sentinel"), false);
    assert.equal(result.stderr.includes(syntheticCode), false);
  } finally {
    await rm(workspace, { recursive: true, force: true });
  }
});

test("TTY interrupt and EOF paths restore terminal settings without exchanging a code", async () => {
  for (const [mode, input] of [["interrupt", "\u0003"], ["eof", "\u0004"]]) {
    const workspace = await createWorkspace(`aergia-tailor-pty-${mode}-`);
    try {
      const result = await runPty("https://aergia.example/agent/tailor/session-1", workspace, mode, input);
      assert.equal(result.exitCode, 0, result.stderr || result.stdout);
      assert.match(result.stdout, /PTY_RESTORE:true/);
      assert.equal(result.stdout.includes(syntheticCode), false);
    } finally {
      await rm(workspace, { recursive: true, force: true });
    }
  }
});

test("piped code entry is silent and pipe EOF is handled without an exchange", async () => {
  const workspace = await createWorkspace("aergia-tailor-pipe-");
  try {
    const entered = await runPipe("https://aergia.example/agent/tailor/session-1", workspace, "exchange", `${syntheticCode}\n`);
    assert.equal(entered.exitCode, 0, entered.stderr || entered.stdout);
    assert.equal(entered.stdout.includes(syntheticCode), false);
    assert.equal(entered.stderr.includes(syntheticCode), false);
    assert.equal(entered.stdout.includes("remote-body-secret-sentinel"), false);
  } finally {
    await rm(workspace, { recursive: true, force: true });
  }

  const emptyWorkspace = await createWorkspace("aergia-tailor-pipe-eof-");
  try {
    const eof = await runPipe("https://aergia.example/agent/tailor/session-1", emptyWorkspace, "eof", "");
    assert.equal(eof.exitCode, 0, eof.stderr || eof.stdout);
    assert.equal(eof.stdout.includes("remote-body-secret-sentinel"), false);
  } finally {
    await rm(emptyWorkspace, { recursive: true, force: true });
  }
});
