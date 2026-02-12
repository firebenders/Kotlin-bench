#!/usr/bin/env node
/**
 * Codex SDK Runner
 * 
 * Wrapper script for @openai/codex-sdk that runs a prompt and outputs
 * structured JSON with the result and trace information.
 * 
 * Usage:
 *   node codex_runner.js --prompt-file prompt.txt [--model gpt-5.2-codex]
 *   echo "Fix the bug" | node codex_runner.js [--model gpt-5.2-codex]
 * 
 * Output (JSON to stdout):
 *   {
 *     "success": true,
 *     "result": "...",
 *     "thread_id": "...",
 *     "model": "...",
 *     "duration_ms": 12345,
 *     "error": null
 *   }
 * 
 * Requires: npm install @openai/codex-sdk
 * Auth: Set OPENAI_API_KEY environment variable
 * 
 * Docs: https://developers.openai.com/codex/sdk/
 */

const { Codex } = require("@openai/codex-sdk");
const fs = require("fs");
const path = require("path");

async function main() {
  const startTime = Date.now();
  const args = parseArgs(process.argv.slice(2));

  // Read prompt
  let prompt;
  if (args["prompt-file"]) {
    prompt = fs.readFileSync(args["prompt-file"], "utf-8").trim();
  } else {
    // Read from stdin
    prompt = await readStdin();
  }

  if (!prompt) {
    outputError("No prompt provided. Use --prompt-file or pipe via stdin.");
    process.exit(1);
  }

  // Log to stderr (stdout is reserved for JSON output)
  console.error(`[codex_runner] Starting Codex SDK...`);
  console.error(`[codex_runner] Model: ${args.model || "default"}`);
  console.error(`[codex_runner] Prompt length: ${prompt.length} chars`);

  try {
    // Initialize Codex SDK
    const codexOptions = {};
    if (args.model) {
      codexOptions.model = args.model;
    }
    
    const codex = new Codex(codexOptions);
    const thread = codex.startThread();

    console.error(`[codex_runner] Running prompt...`);

    // Run the prompt
    const result = await thread.run(prompt);

    const durationMs = Date.now() - startTime;
    console.error(`[codex_runner] Completed in ${durationMs}ms`);

    // Output structured JSON
    const output = {
      success: true,
      result: typeof result === "string" ? result : JSON.stringify(result),
      thread_id: thread.id || null,
      model: args.model || "default",
      duration_ms: durationMs,
      error: null,
    };

    process.stdout.write(JSON.stringify(output, null, 2));
    process.exit(0);

  } catch (err) {
    const durationMs = Date.now() - startTime;
    console.error(`[codex_runner] Error: ${err.message}`);

    const output = {
      success: false,
      result: null,
      thread_id: null,
      model: args.model || "default",
      duration_ms: durationMs,
      error: err.message,
    };

    process.stdout.write(JSON.stringify(output, null, 2));
    process.exit(1);
  }
}

function parseArgs(argv) {
  const args = {};
  for (let i = 0; i < argv.length; i++) {
    if (argv[i].startsWith("--")) {
      const key = argv[i].slice(2);
      const next = argv[i + 1];
      if (next && !next.startsWith("--")) {
        args[key] = next;
        i++;
      } else {
        args[key] = true;
      }
    }
  }
  return args;
}

function readStdin() {
  return new Promise((resolve) => {
    if (process.stdin.isTTY) {
      resolve("");
      return;
    }
    let data = "";
    process.stdin.setEncoding("utf-8");
    process.stdin.on("data", (chunk) => (data += chunk));
    process.stdin.on("end", () => resolve(data.trim()));
    // Timeout after 5 seconds if no stdin
    setTimeout(() => resolve(data.trim()), 5000);
  });
}

function outputError(message) {
  const output = {
    success: false,
    result: null,
    thread_id: null,
    model: null,
    duration_ms: 0,
    error: message,
  };
  process.stdout.write(JSON.stringify(output, null, 2));
}

main();
