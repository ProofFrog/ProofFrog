import * as vscode from "vscode";
import {
  LanguageClient,
  LanguageClientOptions,
  ServerOptions,
} from "vscode-languageclient/node";
import { ProofStepsProvider, ProofStepItem } from "./proof_tree";

let client: LanguageClient | undefined;
let proofStepsProvider: ProofStepsProvider;

const outputChannel = vscode.window.createOutputChannel("ProofFrog");

export async function activate(
  context: vscode.ExtensionContext
): Promise<void> {
  outputChannel.appendLine("ProofFrog extension activating...");

  const config = vscode.workspace.getConfiguration("prooffrog");
  const pythonPath = config.get<string>("pythonPath", "python3");

  outputChannel.appendLine(`Using Python: ${pythonPath}`);
  outputChannel.appendLine(
    `Working directory: ${vscode.workspace.workspaceFolders?.[0]?.uri.fsPath ?? "(none)"}`
  );

  // Set up the proof steps tree view (before LSP so it's always available)
  proofStepsProvider = new ProofStepsProvider();
  const treeView = vscode.window.createTreeView("prooffrogProofSteps", {
    treeDataProvider: proofStepsProvider,
  });
  context.subscriptions.push(treeView);

  // Register commands
  context.subscriptions.push(
    vscode.commands.registerCommand(
      "prooffrog.showHopDetail",
      (detail: {
        step_num: number;
        valid: boolean | null;
        kind: string;
        current_desc: string;
        next_desc: string;
      }) => {
        const status =
          detail.valid === null
            ? "Assumption"
            : detail.valid
              ? "Valid"
              : "FAILED";
        const message = [
          `Step ${detail.step_num}: ${status}`,
          `Kind: ${detail.kind}`,
          `${detail.current_desc} -> ${detail.next_desc}`,
        ].join("\n");

        if (detail.valid === false) {
          vscode.window.showErrorMessage(message);
        } else {
          vscode.window.showInformationMessage(message);
        }
      }
    )
  );

  context.subscriptions.push(
    vscode.commands.registerCommand(
      "prooffrog.goToProofStep",
      (item: ProofStepItem) => {
        const editor = vscode.window.activeTextEditor;
        if (editor && item.line > 0) {
          const position = new vscode.Position(item.line - 1, 0);
          editor.revealRange(
            new vscode.Range(position, position),
            vscode.TextEditorRevealType.InCenter
          );
          editor.selection = new vscode.Selection(position, position);
        }
      }
    )
  );

  // Start the LSP client
  const serverOptions: ServerOptions = {
    command: pythonPath,
    args: ["-m", "proof_frog", "lsp"],
    options: {
      cwd: vscode.workspace.workspaceFolders?.[0]?.uri.fsPath,
    },
  };

  const clientOptions: LanguageClientOptions = {
    documentSelector: [{ language: "prooffrog" }],
    outputChannel,
  };

  client = new LanguageClient(
    "prooffrog",
    "ProofFrog Language Server",
    serverOptions,
    clientOptions
  );

  // Refresh proof steps when a .proof file is saved
  context.subscriptions.push(
    vscode.workspace.onDidSaveTextDocument((doc) => {
      if (doc.uri.fsPath.endsWith(".proof") && client) {
        setTimeout(() => {
          refreshProofSteps(doc.uri);
        }, 1000);
      }
    })
  );

  // Refresh when active editor changes to a .proof file
  context.subscriptions.push(
    vscode.window.onDidChangeActiveTextEditor((editor) => {
      if (editor?.document.uri.fsPath.endsWith(".proof") && client) {
        refreshProofSteps(editor.document.uri);
      }
    })
  );

  try {
    await client.start();
    outputChannel.appendLine("ProofFrog LSP server started successfully.");
  } catch (e) {
    outputChannel.appendLine(`Failed to start LSP server: ${e}`);
    vscode.window.showErrorMessage(
      `ProofFrog: Failed to start language server. Check Output > ProofFrog for details.`
    );
  }
}

async function refreshProofSteps(uri: vscode.Uri): Promise<void> {
  if (!client) {
    return;
  }
  try {
    const result = await client.sendRequest("workspace/executeCommand", {
      command: "prooffrog/proofSteps",
      arguments: [uri.toString()],
    });
    proofStepsProvider.update(
      result as Array<{
        step_num: number;
        valid: boolean | null;
        kind: string;
        current_desc: string;
        next_desc: string;
        line: number;
      }>
    );
  } catch {
    // Proof steps not yet available
  }
}

export async function deactivate(): Promise<void> {
  if (client) {
    await client.stop();
  }
}
