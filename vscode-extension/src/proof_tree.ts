import * as vscode from "vscode";

interface ProofStepData {
  step_num: number;
  valid: boolean | null;
  kind: string;
  current_desc: string;
  next_desc: string;
  line: number;
}

export class ProofStepItem extends vscode.TreeItem {
  public readonly line: number;

  constructor(data: ProofStepData) {
    const kindLabel =
      data.kind === "by_assumption" ? "by assumption" : "interchangeability";
    const status = data.valid === false ? " -- FAILED" : "";

    const label = `Step ${data.step_num}: ${data.current_desc} -> ${data.next_desc}`;

    super(label, vscode.TreeItemCollapsibleState.None);

    this.line = data.line;
    this.description = `${kindLabel}${status}`;
    this.tooltip = [
      `Step ${data.step_num}`,
      `Kind: ${data.kind}`,
      `${data.current_desc} -> ${data.next_desc}`,
      data.valid === null
        ? "Assumed"
        : data.valid
          ? "Valid"
          : "FAILED",
    ].join("\n");

    this.command = {
      command: "prooffrog.goToProofStep",
      title: "Go to Step",
      arguments: [this],
    };

    if (data.valid === null) {
      // Assumption hop — blue checkbox
      this.iconPath = new vscode.ThemeIcon(
        "pass",
        new vscode.ThemeColor("charts.blue")
      );
    } else if (data.valid) {
      // Valid interchangeability — green checkbox
      this.iconPath = new vscode.ThemeIcon(
        "pass",
        new vscode.ThemeColor("charts.green")
      );
    } else {
      // Failed — red X
      this.iconPath = new vscode.ThemeIcon(
        "error",
        new vscode.ThemeColor("charts.red")
      );
    }
  }
}

export class ProofStepsProvider
  implements vscode.TreeDataProvider<ProofStepItem>
{
  private steps: ProofStepData[] = [];

  private _onDidChangeTreeData = new vscode.EventEmitter<
    ProofStepItem | undefined | null | void
  >();
  readonly onDidChangeTreeData = this._onDidChangeTreeData.event;

  update(steps: ProofStepData[]): void {
    this.steps = steps;
    this._onDidChangeTreeData.fire();
  }

  getTreeItem(element: ProofStepItem): vscode.TreeItem {
    return element;
  }

  getChildren(): ProofStepItem[] {
    return this.steps.map((step) => new ProofStepItem(step));
  }
}
