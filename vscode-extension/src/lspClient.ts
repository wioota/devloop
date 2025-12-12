/**
 * DevLoop LSP Client
 *
 * Manages the Language Server Protocol client connection to the DevLoop LSP server.
 */

import * as path from 'path';
import * as vscode from 'vscode';
import {
    LanguageClient,
    LanguageClientOptions,
    ServerOptions,
    TransportKind,
} from 'vscode-languageclient/node';

export class DevLoopLSPClient {
    private client: LanguageClient | undefined;
    private context: vscode.ExtensionContext;

    constructor(context: vscode.ExtensionContext) {
        this.context = context;
    }

    async start(): Promise<void> {
        // Get configuration
        const config = vscode.workspace.getConfiguration('devloop');
        const pythonPath = config.get('lsp.pythonPath', 'python');
        const debug = config.get('lsp.debug', false);

        // Server options: run the LSP server
        const serverOptions: ServerOptions = {
            command: pythonPath as string,
            args: ['-m', 'devloop.lsp.server'],
            transport: TransportKind.stdio,
            options: {
                env: {
                    ...process.env,
                    PYTHONUNBUFFERED: '1',
                },
            },
        };

        // Client options: configure language client
        const clientOptions: LanguageClientOptions = {
            documentSelector: [
                { scheme: 'file', language: 'python' },
                { scheme: 'file', language: 'javascript' },
                { scheme: 'file', language: 'typescript' },
                { scheme: 'file', language: 'javascriptreact' },
                { scheme: 'file', language: 'typescriptreact' },
            ],
            synchronize: {
                fileEvents: vscode.workspace.createFileSystemWatcher('**/*'),
            },
            outputChannelName: 'DevLoop LSP',
            revealOutputChannelOn: debug ? 1 : 4, // Never reveal unless debug
        };

        // Create and start client
        this.client = new LanguageClient(
            'devloop-lsp',
            'DevLoop Language Server',
            serverOptions,
            clientOptions
        );

        // Register custom notification handlers
        this.client.onReady().then(() => {
            console.log('DevLoop LSP client ready');

            // Handle custom notifications from server
            this.client?.onNotification('devloop/findingsUpdated', (params: any) => {
                console.log('Findings updated:', params);
            });

            this.client?.onNotification('devloop/agentStatus', (params: any) => {
                console.log('Agent status:', params);
                // Update status bar
                vscode.window.setStatusBarMessage(`DevLoop: ${params.agents?.length || 0} agents`);
            });
        });

        await this.client.start();
        console.log('DevLoop LSP client started');
    }

    async stop(): Promise<void> {
        if (this.client) {
            await this.client.stop();
            this.client = undefined;
            console.log('DevLoop LSP client stopped');
        }
    }

    async applyAllFixes(): Promise<void> {
        if (!this.client) {
            throw new Error('LSP client not started');
        }

        // Send custom request to apply all fixes
        await this.client.sendRequest('devloop/applyAllFixes', {});
    }

    async refreshDiagnostics(): Promise<void> {
        if (!this.client) {
            throw new Error('LSP client not started');
        }

        // Send custom request to refresh diagnostics
        await this.client.sendRequest('devloop/refreshDiagnostics', {});
    }

    getClient(): LanguageClient | undefined {
        return this.client;
    }
}
