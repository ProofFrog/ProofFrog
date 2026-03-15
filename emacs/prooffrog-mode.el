;;; prooffrog-mode.el --- Major mode for ProofFrog files -*- lexical-binding: t; -*-

;; Copyright (C) 2026 ProofFrog Contributors

;; Author: ProofFrog Contributors
;; Maintainer: ProofFrog Contributors
;; Version: 0.1.0
;; Keywords: languages tools
;; URL: https://github.com/ProofFrog/ProofFrog
;; Package-Requires: ((emacs "26.1"))
;; SPDX-License-Identifier: MIT

;; This file is not part of GNU Emacs.

;; Permission is hereby granted, free of charge, to any person obtaining a copy
;; of this software and associated documentation files (the "Software"), to deal
;; in the Software without restriction, including without limitation the rights
;; to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
;; copies of the Software, and to permit persons to whom the Software is
;; furnished to do so, subject to the following conditions:
;;
;; The above copyright notice and this permission notice shall be included in
;; all copies or substantial portions of the Software.
;;
;; THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
;; IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
;; FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.

;;; Commentary:

;; Major mode for editing ProofFrog cryptographic proof language files.
;; ProofFrog is a tool for checking the validity of cryptographic
;; game-hopping proofs written in FrogLang.
;;
;; Supports .primitive, .scheme, .game, and .proof file extensions.
;;
;; Features:
;; - Syntax highlighting for all ProofFrog file types
;; - Automatic indentation
;; - Comment support (// single-line comments)
;; - Imenu integration for navigating definitions
;; - LSP integration via eglot (Emacs 29+) or lsp-mode
;;
;; Installation:
;;
;;   (add-to-list 'load-path "/path/to/ProofFrog/emacs")
;;   (require 'prooffrog-mode)
;;
;; Or with use-package:
;;
;;   (use-package prooffrog-mode
;;     :load-path "/path/to/ProofFrog/emacs")

;;; Code:

;; Optional dependency declarations (eglot / lsp-mode)
(defvar eglot-server-programs)
(defvar lsp-language-id-configuration)
(declare-function eglot-ensure "eglot")
(declare-function lsp "lsp-mode")
(declare-function lsp-register-client "lsp-mode")
(declare-function make-lsp-client "lsp-mode")
(declare-function lsp-stdio-connection "lsp-mode")
(declare-function lsp-activate-on "lsp-mode")

;;; Customization

(defgroup prooffrog nil
  "Major mode for editing ProofFrog files."
  :group 'languages
  :prefix "prooffrog-")

(defcustom prooffrog-indent-offset 4
  "Number of spaces for each indentation level in ProofFrog mode."
  :type 'integer
  :group 'prooffrog)

;;; Syntax table

(defvar prooffrog-mode-syntax-table
  (let ((table (make-syntax-table)))
    ;; C++-style // comments
    (modify-syntax-entry ?/ ". 12" table)
    (modify-syntax-entry ?\n ">" table)
    ;; String-like file paths in single quotes
    (modify-syntax-entry ?' "\"" table)
    ;; Punctuation
    (modify-syntax-entry ?\{ "(}" table)
    (modify-syntax-entry ?\} "){" table)
    (modify-syntax-entry ?\( "()" table)
    (modify-syntax-entry ?\) ")(" table)
    (modify-syntax-entry ?\[ "(]" table)
    (modify-syntax-entry ?\] ")[" table)
    (modify-syntax-entry ?< "." table)
    (modify-syntax-entry ?> "." table)
    ;; Operators
    (modify-syntax-entry ?+ "." table)
    (modify-syntax-entry ?- "." table)
    (modify-syntax-entry ?* "." table)
    (modify-syntax-entry ?= "." table)
    (modify-syntax-entry ?! "." table)
    (modify-syntax-entry ?& "." table)
    (modify-syntax-entry ?| "." table)
    (modify-syntax-entry ?\\ "." table)
    (modify-syntax-entry ?. "." table)
    ;; Underscore and $ are word constituents (part of identifiers)
    (modify-syntax-entry ?_ "w" table)
    (modify-syntax-entry ?$ "w" table)
    table)
  "Syntax table for `prooffrog-mode'.")

;;; Font-lock (syntax highlighting)

(defvar prooffrog-font-lock-keywords
  (let* (;; Top-level declaration keywords
         (declaration-keywords '("Primitive" "Scheme" "Game" "Reduction" "Phase"))
         ;; Proof structure keywords
         (proof-keywords '("proof" "let" "assume" "theorem" "games"
                           "induction" "from"))
         ;; Control flow keywords
         (control-keywords '("if" "else" "for" "return" "to" "in"))
         ;; Other keywords
         (other-keywords '("import" "as" "export" "extends" "requires"
                           "compose" "against" "Adversary" "oracles" "calls"))
         ;; Built-in types
         (type-keywords '("Bool" "Void" "Int" "BitString" "Set" "Map"
                          "Array"))
         ;; Constants
         (constant-keywords '("true" "false" "None"))

         ;; Build regexps
         (declaration-regexp (regexp-opt declaration-keywords 'words))
         (proof-regexp (regexp-opt proof-keywords 'words))
         (control-regexp (regexp-opt control-keywords 'words))
         (other-regexp (regexp-opt other-keywords 'words))
         (type-regexp (regexp-opt type-keywords 'words))
         (constant-regexp (regexp-opt constant-keywords 'words)))

    `(
      ;; Comments are handled by the syntax table, but ensure // comments
      ;; get highlighted properly
      ("//.*$" . font-lock-comment-face)

      ;; Import file paths (single-quoted strings)
      ("'[^']*'" . font-lock-string-face)

      ;; Binary number literals: 0b0101
      ("\\<0b[01]+\\>" . font-lock-constant-face)

      ;; Integer literals
      ("\\<[0-9]+\\>" . font-lock-constant-face)

      ;; Proof section labels (proof:, let:, assume:, theorem:, games:)
      (,(concat "\\<" (regexp-opt '("proof" "let" "assume" "theorem" "games") t) ":")
       . font-lock-preprocessor-face)

      ;; Top-level declaration keywords
      (,declaration-regexp . font-lock-keyword-face)

      ;; Proof structure keywords
      (,proof-regexp . font-lock-keyword-face)

      ;; Control flow keywords
      (,control-regexp . font-lock-keyword-face)

      ;; Other language keywords
      (,other-regexp . font-lock-keyword-face)

      ;; Set operation keywords
      (,(regexp-opt '("union" "subsets") 'words) . font-lock-keyword-face)

      ;; Built-in types
      (,type-regexp . font-lock-type-face)

      ;; Sampling operator <-
      ("<-" . font-lock-keyword-face)

      ;; Definition names: Primitive/Scheme/Game/Reduction NAME
      (,(concat "\\<\\(Primitive\\|Scheme\\|Game\\|Reduction\\)"
                "\\s-+\\([a-zA-Z_$][a-zA-Z_0-9$]*\\)")
       (2 font-lock-function-name-face))

      ;; Method definitions: Type name(
      ;; Match the method name before a paren when preceded by a type
      (,(concat "\\<\\([a-zA-Z_$][a-zA-Z_0-9$]*\\)\\s-*(")
       (1 font-lock-function-name-face))

      ;; Constants
      (,constant-regexp . font-lock-constant-face)
      ))
  "Font-lock keywords for `prooffrog-mode'.")

;;; Indentation

(defun prooffrog--previous-non-blank-line ()
  "Move to the previous non-blank line and return its indentation.
Returns nil if no such line exists."
  (forward-line -1)
  (while (and (not (bobp))
              (looking-at-p "^\\s-*$"))
    (forward-line -1))
  (unless (bobp)
    (current-indentation)))

(defun prooffrog-indent-line ()
  "Indent the current line according to ProofFrog syntax."
  (interactive)
  (let ((pos (- (point-max) (point)))
        cur-indent)
    (save-excursion
      (beginning-of-line)
      (let ((line (buffer-substring-no-properties
                   (line-beginning-position) (line-end-position))))
        ;; Determine indentation
        (cond
         ;; Top of buffer
         ((bobp)
          (setq cur-indent 0))

         ;; Closing brace: match the opening brace's indentation
         ((string-match-p "^\\s-*}" line)
          (save-excursion
            (prooffrog--previous-non-blank-line)
            (setq cur-indent (max 0 (- (current-indentation) prooffrog-indent-offset)))
            ;; If previous line also opened a block, stay aligned
            (when (string-match-p "{\\s-*$"
                                  (buffer-substring-no-properties
                                   (line-beginning-position) (line-end-position)))
              (setq cur-indent (current-indentation)))))

         ;; Proof section labels (proof:, let:, assume:, theorem:, games:)
         ((string-match-p "^\\s-*\\(proof\\|let\\|assume\\|theorem\\|games\\):" line)
          (setq cur-indent 0))

         ;; export as ... line
         ((string-match-p "^\\s-*export\\b" line)
          (setq cur-indent 0))

         ;; Lines starting with oracles:
         ((string-match-p "^\\s-*oracles:" line)
          (save-excursion
            (prooffrog--previous-non-blank-line)
            ;; oracles should be at the same level as methods inside Phase
            (setq cur-indent (max 0 (- (current-indentation) prooffrog-indent-offset)))
            ;; But if we're inside a Phase block, indent to Phase's child level
            (let ((phase-indent nil))
              (save-excursion
                (while (and (not (bobp)) (not phase-indent))
                  (forward-line -1)
                  (when (string-match-p "^\\s-*Phase\\s-*{" (buffer-substring-no-properties
                                                              (line-beginning-position)
                                                              (line-end-position)))
                    (setq phase-indent (+ (current-indentation) prooffrog-indent-offset)))))
              (when phase-indent
                (setq cur-indent phase-indent)))))

         ;; Default: look at previous line
         (t
          (save-excursion
            (let ((prev-indent (prooffrog--previous-non-blank-line)))
              (if (null prev-indent)
                  (setq cur-indent 0)
                (let ((prev-line (buffer-substring-no-properties
                                  (line-beginning-position) (line-end-position))))
                  (setq cur-indent prev-indent)

                  ;; Increase indent after opening brace
                  (when (string-match-p "{\\s-*$" prev-line)
                    (setq cur-indent (+ cur-indent prooffrog-indent-offset)))

                  ;; Increase indent after proof section labels
                  (when (string-match-p "^\\s-*\\(let\\|assume\\|theorem\\|games\\):" prev-line)
                    (setq cur-indent (+ cur-indent prooffrog-indent-offset)))))))))))

    ;; Apply the indentation
    (when cur-indent
      (indent-line-to cur-indent))

    ;; If point was within the indentation, move to the end of indentation.
    ;; Otherwise, preserve position relative to text.
    (when (> (- (point-max) pos) (point))
      (goto-char (- (point-max) pos)))))

;;; Imenu support

(defvar prooffrog-imenu-generic-expression
  `(("Primitive" ,(concat "^\\s-*Primitive\\s-+"
                          "\\([a-zA-Z_$][a-zA-Z_0-9$]*\\)") 1)
    ("Scheme" ,(concat "^\\s-*Scheme\\s-+"
                       "\\([a-zA-Z_$][a-zA-Z_0-9$]*\\)") 1)
    ("Game" ,(concat "^\\s-*Game\\s-+"
                     "\\([a-zA-Z_$][a-zA-Z_0-9$]*\\)") 1)
    ("Reduction" ,(concat "^\\s-*Reduction\\s-+"
                          "\\([a-zA-Z_$][a-zA-Z_0-9$]*\\)") 1))
  "Imenu patterns for `prooffrog-mode'.")

;;; Mode definition

;;;###autoload
(define-derived-mode prooffrog-mode prog-mode "ProofFrog"
  "Major mode for editing ProofFrog cryptographic proof language files.

ProofFrog supports four file types:
  .primitive  - Abstract cryptographic primitive definitions
  .scheme     - Concrete scheme implementations extending primitives
  .game       - Security game definitions
  .proof      - Formal proof structures

\\{prooffrog-mode-map}"
  :syntax-table prooffrog-mode-syntax-table
  :group 'prooffrog

  ;; Font lock
  (setq font-lock-defaults '(prooffrog-font-lock-keywords))

  ;; Comments
  (setq-local comment-start "// ")
  (setq-local comment-end "")
  (setq-local comment-start-skip "//+\\s-*")

  ;; Indentation
  (setq-local indent-line-function #'prooffrog-indent-line)
  (setq-local indent-tabs-mode nil)
  (setq-local tab-width prooffrog-indent-offset)

  ;; Electric pair for braces, brackets, parens, angle brackets
  (setq-local electric-pair-pairs
              (append '((?\{ . ?\})
                        (?\[ . ?\])
                        (?< . ?>))
                      (if (boundp 'electric-pair-pairs)
                          electric-pair-pairs
                        nil)))

  ;; Imenu
  (setq-local imenu-generic-expression prooffrog-imenu-generic-expression)

  ;; Paragraph handling
  (setq-local paragraph-start (concat "$\\|" page-delimiter))
  (setq-local paragraph-separate paragraph-start))

;;; LSP support

(defcustom prooffrog-python-path "python3"
  "Path to the Python interpreter used to run the ProofFrog LSP server."
  :type 'string
  :group 'prooffrog)

(defcustom prooffrog-lsp-enabled t
  "When non-nil, automatically start the LSP client when entering `prooffrog-mode'.
Requires either `eglot' (Emacs 29+) or `lsp-mode' to be installed."
  :type 'boolean
  :group 'prooffrog)

(defun prooffrog--lsp-server-command ()
  "Return the command to start the ProofFrog LSP server."
  (list prooffrog-python-path "-m" "proof_frog" "lsp"))

;; Eglot support (built-in since Emacs 29)
(with-eval-after-load 'eglot
  (add-to-list 'eglot-server-programs
               `(prooffrog-mode . ,(prooffrog--lsp-server-command))))

;; lsp-mode support
(with-eval-after-load 'lsp-mode
  (add-to-list 'lsp-language-id-configuration '(prooffrog-mode . "prooffrog"))
  (lsp-register-client
   (make-lsp-client
    :new-connection (lsp-stdio-connection #'prooffrog--lsp-server-command)
    :activation-fn (lsp-activate-on "prooffrog")
    :server-id 'prooffrog-lsp)))

(defun prooffrog-start-lsp ()
  "Start the LSP client for the current ProofFrog buffer.
Uses `eglot' if available, otherwise falls back to `lsp-mode'."
  (interactive)
  (cond
   ((fboundp 'eglot-ensure)
    (eglot-ensure))
   ((fboundp 'lsp)
    (lsp))
   (t
    (message "ProofFrog: Install `eglot' (Emacs 29+) or `lsp-mode' for LSP support"))))

(defun prooffrog--maybe-start-lsp ()
  "Start LSP if `prooffrog-lsp-enabled' is non-nil."
  (when prooffrog-lsp-enabled
    (prooffrog-start-lsp)))

(add-hook 'prooffrog-mode-hook #'prooffrog--maybe-start-lsp)

;;; File association

;;;###autoload
(add-to-list 'auto-mode-alist '("\\.primitive\\'" . prooffrog-mode))
;;;###autoload
(add-to-list 'auto-mode-alist '("\\.scheme\\'" . prooffrog-mode))
;;;###autoload
(add-to-list 'auto-mode-alist '("\\.game\\'" . prooffrog-mode))
;;;###autoload
(add-to-list 'auto-mode-alist '("\\.proof\\'" . prooffrog-mode))

(provide 'prooffrog-mode)

;;; prooffrog-mode.el ends here
