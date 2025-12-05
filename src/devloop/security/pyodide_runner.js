#!/usr/bin/env node
/**
 * Pyodide Runner for DevLoop Sandbox
 *
 * Executes Python code in isolated Pyodide WASM environment.
 * Receives execution parameters via stdin (JSON), returns results via stdout (JSON).
 *
 * Usage:
 *   echo '{"command": ["python3", "script.py"], "cwd": "/path"}' | node pyodide_runner.js
 *
 * Requirements:
 *   - Node.js 18+
 *   - pyodide npm package
 */

const fs = require('fs').promises;
const path = require('path');

// Constants
const DEFAULT_TIMEOUT_MS = 30000;
const DEFAULT_MAX_MEMORY_MB = 500;

/**
 * Main execution function
 */
async function main() {
    const startTime = Date.now();

    try {
        // Read execution parameters from stdin
        const params = await readStdinJSON();

        // Validate parameters
        validateParams(params);

        // Execute Python code in Pyodide
        const result = await executePyodide(params, startTime);

        // Output result as JSON
        console.log(JSON.stringify(result));
        process.exit(0);

    } catch (error) {
        // Output error as JSON result
        const errorResult = {
            stdout: "",
            stderr: `Pyodide runner error: ${error.message}\n${error.stack}`,
            exitCode: 1,
            durationMs: Date.now() - startTime,
            memoryPeakMb: process.memoryUsage().heapUsed / 1024 / 1024
        };

        console.log(JSON.stringify(errorResult));
        process.exit(1);
    }
}

/**
 * Read and parse JSON from stdin
 */
async function readStdinJSON() {
    return new Promise((resolve, reject) => {
        let data = '';

        process.stdin.on('data', chunk => {
            data += chunk;
        });

        process.stdin.on('end', () => {
            try {
                const params = JSON.parse(data);
                resolve(params);
            } catch (error) {
                reject(new Error(`Invalid JSON input: ${error.message}`));
            }
        });

        process.stdin.on('error', reject);

        // Timeout for reading stdin
        setTimeout(() => {
            reject(new Error('Timeout reading stdin'));
        }, 5000);
    });
}

/**
 * Validate execution parameters
 */
function validateParams(params) {
    if (!params.command || !Array.isArray(params.command)) {
        throw new Error('Missing or invalid "command" parameter');
    }

    if (!params.cwd || typeof params.cwd !== 'string') {
        throw new Error('Missing or invalid "cwd" parameter');
    }

    const executable = params.command[0];
    if (executable !== 'python3' && executable !== 'python') {
        throw new Error(`Invalid executable: ${executable}. Only python3/python allowed.`);
    }
}

/**
 * Execute Python code in Pyodide WASM environment
 */
async function executePyodide(params, startTime) {
    // NOTE: This is a POC implementation
    // Full implementation requires:
    // 1. Install pyodide: npm install pyodide
    // 2. Load Pyodide runtime
    // 3. Setup virtual filesystem
    // 4. Execute Python code

    // For POC, we'll simulate execution without actually loading Pyodide
    // This allows testing the integration without the 30MB Pyodide dependency

    const command = params.command;
    const cwd = params.cwd;
    const timeout = params.timeout || DEFAULT_TIMEOUT_MS / 1000;
    const maxMemoryMb = params.maxMemoryMb || DEFAULT_MAX_MEMORY_MB;

    // Check if this is a real Pyodide execution or POC mode
    const pocMode = process.env.PYODIDE_POC_MODE === '1' || !isPyodideInstalled();

    if (pocMode) {
        return await executePOC(command, cwd, startTime);
    } else {
        return await executeRealPyodide(command, cwd, timeout, maxMemoryMb, startTime);
    }
}

/**
 * Check if Pyodide is installed
 */
function isPyodideInstalled() {
    try {
        require.resolve('pyodide');
        return true;
    } catch (e) {
        return false;
    }
}

/**
 * POC execution (without Pyodide)
 *
 * This allows testing the PyodideSandbox integration without installing
 * the full 30MB Pyodide package.
 */
async function executePOC(command, cwd, startTime) {
    // Determine what to execute
    const args = command.slice(1);

    if (args.length === 0) {
        // No script provided, run interactive mode (not supported)
        return {
            stdout: "",
            stderr: "POC Mode: Interactive Python not supported\n",
            exitCode: 1,
            durationMs: Date.now() - startTime,
            memoryPeakMb: process.memoryUsage().heapUsed / 1024 / 1024
        };
    }

    // Check for -c flag (inline code)
    if (args[0] === '-c' && args.length > 1) {
        const code = args[1];
        return {
            stdout: `POC Mode: Would execute inline code: ${code}\n`,
            stderr: "",
            exitCode: 0,
            durationMs: Date.now() - startTime,
            memoryPeakMb: process.memoryUsage().heapUsed / 1024 / 1024
        };
    }

    // Execute script file
    const scriptPath = path.resolve(cwd, args[0]);

    try {
        const scriptContent = await fs.readFile(scriptPath, 'utf-8');

        return {
            stdout: `POC Mode: Successfully loaded script (${scriptContent.length} bytes)\n` +
                   `Would execute: ${scriptPath}\n`,
            stderr: "",
            exitCode: 0,
            durationMs: Date.now() - startTime,
            memoryPeakMb: process.memoryUsage().heapUsed / 1024 / 1024
        };

    } catch (error) {
        return {
            stdout: "",
            stderr: `POC Mode: Failed to read script: ${error.message}\n`,
            exitCode: 1,
            durationMs: Date.now() - startTime,
            memoryPeakMb: process.memoryUsage().heapUsed / 1024 / 1024
        };
    }
}

/**
 * Real Pyodide execution (requires pyodide npm package)
 */
async function executeRealPyodide(command, cwd, timeout, maxMemoryMb, startTime) {
    // Load Pyodide (lazy loaded only when needed)
    const { loadPyodide } = require('pyodide');

    // Initialize Pyodide runtime
    const pyodide = await loadPyodide({
        indexURL: "https://cdn.jsdelivr.net/pyodide/v0.25.0/full/",
    });

    const args = command.slice(1);
    let code = '';

    // Determine Python code to execute
    if (args.length === 0) {
        throw new Error('Interactive Python not supported in Pyodide sandbox');
    }

    if (args[0] === '-c' && args.length > 1) {
        // Inline code execution
        code = args[1];
    } else {
        // Script file execution
        const scriptPath = path.resolve(cwd, args[0]);
        code = await fs.readFile(scriptPath, 'utf-8');
    }

    // Setup timeout
    const timeoutMs = timeout * 1000;
    const executionPromise = executeWithTimeout(pyodide, code, timeoutMs);

    try {
        const output = await executionPromise;

        return {
            stdout: output,
            stderr: "",
            exitCode: 0,
            durationMs: Date.now() - startTime,
            memoryPeakMb: process.memoryUsage().heapUsed / 1024 / 1024
        };

    } catch (error) {
        if (error.message === 'TIMEOUT') {
            throw new Error(`Execution exceeded ${timeout}s timeout`);
        }

        return {
            stdout: "",
            stderr: `Python execution error: ${error.message}\n`,
            exitCode: 1,
            durationMs: Date.now() - startTime,
            memoryPeakMb: process.memoryUsage().heapUsed / 1024 / 1024
        };
    }
}

/**
 * Execute Python code with timeout
 */
async function executeWithTimeout(pyodide, code, timeoutMs) {
    return new Promise((resolve, reject) => {
        const timer = setTimeout(() => {
            reject(new Error('TIMEOUT'));
        }, timeoutMs);

        pyodide.runPythonAsync(code)
            .then(result => {
                clearTimeout(timer);
                resolve(String(result));
            })
            .catch(error => {
                clearTimeout(timer);
                reject(error);
            });
    });
}

// Run main function
if (require.main === module) {
    main();
}

module.exports = { executePyodide, isPyodideInstalled };
