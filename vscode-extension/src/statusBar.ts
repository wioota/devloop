/**
 * Status Bar Manager
 *
 * Manages the DevLoop status bar item showing agent activity.
 */

import * as vscode from 'vscode';
import { DevLoopLSPClient } from './lspClient';

export class StatusBarManager {
    private statusBarItem: vscode.StatusBarItem;
    private lspClient: DevLoopLSPClient;

    constructor(lspClient: DevLoopLSPClient) {
        this.lspClient = lspClient;

        // Create status bar item
        this.statusBarItem = vscode.window.createStatusBarItem(
            vscode.StatusBarAlignment.Left,
            100
        );

        this.statusBarItem.text = '$(sync~spin) DevLoop';
        this.statusBarItem.tooltip = 'DevLoop agent system';
        this.statusBarItem.command = 'devloop.openDashboard';
        this.statusBarItem.show();

        // Update status periodically
        this.updateStatus();
        setInterval(() => this.updateStatus(), 5000);
    }

    private async updateStatus() {
        // TODO: Get actual agent status from LSP server
        this.statusBarItem.text = '$(check) DevLoop';
        this.statusBarItem.tooltip = 'DevLoop agents ready';
    }

    dispose() {
        this.statusBarItem.dispose();
    }
}
