/**
 * DevLoop VSCode Extension
 *
 * Provides real-time agent feedback, inline diagnostics, and quick fixes.
 */

import * as vscode from 'vscode';
import { DevLoopLSPClient } from './lspClient';
import { StatusBarManager } from './statusBar';

let lspClient: DevLoopLSPClient | undefined;
let statusBar: StatusBarManager | undefined;

export async function activate(context: vscode.ExtensionContext) {
    console.log('DevLoop extension activating...');

    // Check if DevLoop is enabled
    const config = vscode.workspace.getConfiguration('devloop');
    if (!config.get('enabled', true)) {
        console.log('DevLoop is disabled');
        return;
    }

    try {
        // Initialize LSP client
        lspClient = new DevLoopLSPClient(context);
        await lspClient.start();

        // Initialize status bar
        if (config.get('statusBar.enabled', true)) {
            statusBar = new StatusBarManager(lspClient);
        }

        // Register commands
        registerCommands(context);

        console.log('DevLoop extension activated');
    } catch (error) {
        console.error('Failed to activate DevLoop extension:', error);
        vscode.window.showErrorMessage(`DevLoop: ${error}`);
    }
}

export async function deactivate(): Promise<void> {
    console.log('DevLoop extension deactivating...');

    // Stop status bar
    if (statusBar) {
        statusBar.dispose();
        statusBar = undefined;
    }

    // Stop LSP client
    if (lspClient) {
        await lspClient.stop();
        lspClient = undefined;
    }

    console.log('DevLoop extension deactivated');
}

function registerCommands(context: vscode.ExtensionContext) {
    // Open Dashboard
    context.subscriptions.push(
        vscode.commands.registerCommand('devloop.openDashboard', async () => {
            vscode.window.showInformationMessage('Agent Dashboard (coming soon)');
        })
    );

    // Apply All Fixes
    context.subscriptions.push(
        vscode.commands.registerCommand('devloop.applyAllFixes', async () => {
            if (!lspClient) {
                return;
            }

            try {
                await lspClient.applyAllFixes();
                vscode.window.showInformationMessage('Applied all safe fixes');
            } catch (error) {
                vscode.window.showErrorMessage(`Failed to apply fixes: ${error}`);
            }
        })
    );

    // Refresh Diagnostics
    context.subscriptions.push(
        vscode.commands.registerCommand('devloop.refreshDiagnostics', async () => {
            if (!lspClient) {
                return;
            }

            try {
                await lspClient.refreshDiagnostics();
                vscode.window.showInformationMessage('Diagnostics refreshed');
            } catch (error) {
                vscode.window.showErrorMessage(`Failed to refresh: ${error}`);
            }
        })
    );

    // Show Agent Config
    context.subscriptions.push(
        vscode.commands.registerCommand('devloop.showAgentConfig', async () => {
            const workspaceFolders = vscode.workspace.workspaceFolders;
            if (!workspaceFolders) {
                vscode.window.showErrorMessage('No workspace folder open');
                return;
            }

            const configPath = vscode.Uri.joinPath(
                workspaceFolders[0].uri,
                '.devloop',
                'agents.json'
            );

            try {
                const doc = await vscode.workspace.openTextDocument(configPath);
                await vscode.window.showTextDocument(doc);
            } catch (error) {
                vscode.window.showErrorMessage(`Config file not found: ${configPath.fsPath}`);
            }
        })
    );
}
