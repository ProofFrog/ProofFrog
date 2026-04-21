EMACS ?= emacs

PACKAGE_NAME = prooffrog-mode
PACKAGE_FILE = prooffrog-mode.el

.PHONY: all compile lint checkdoc clean package

all: compile lint checkdoc

compile:
	$(EMACS) -Q --batch -L . -f batch-byte-compile $(PACKAGE_FILE)

lint:
	$(EMACS) -Q --batch \
	  --eval "(progn \
	    (require 'package) \
	    (push '(\"melpa\" . \"https://melpa.org/packages/\") package-archives) \
	    (package-initialize) \
	    (unless (package-installed-p 'package-lint) \
	      (package-refresh-contents) \
	      (package-install 'package-lint)) \
	    (require 'package-lint) \
	    (setq package-lint-main-file \"$(PACKAGE_FILE)\") \
	    (package-lint-batch-and-exit))" \
	  $(PACKAGE_FILE)

checkdoc:
	$(EMACS) -Q --batch \
	  --eval "(progn \
	    (require 'checkdoc) \
	    (let ((files '(\"$(PACKAGE_FILE)\")) \
	          (errors nil)) \
	      (dolist (file files) \
	        (with-current-buffer (find-file-noselect file) \
	          (let ((errs (checkdoc-file file))) \
	            (when errs (push errs errors))))) \
	      (when errors \
	        (message \"checkdoc errors found\") \
	        (kill-emacs 1))))"

package:
	$(EMACS) -Q --batch \
	  --eval "(progn \
	    (require 'package) \
	    (with-current-buffer (find-file-noselect \"$(PACKAGE_FILE)\") \
	      (let* ((pkg-desc (package-buffer-info)) \
	             (name (package-desc-name pkg-desc)) \
	             (version (package-desc-version pkg-desc)) \
	             (version-str (mapconcat #'number-to-string version \".\")) \
	             (tar-name (format \"%s-%s.tar\" name version-str)) \
	             (pkg-dir (format \"%s-%s\" name version-str))) \
	        (make-directory pkg-dir t) \
	        (copy-file \"$(PACKAGE_FILE)\" (expand-file-name \"$(PACKAGE_FILE)\" pkg-dir) t) \
	        (shell-command (format \"tar cf %s %s\" tar-name pkg-dir)) \
	        (delete-directory pkg-dir t) \
	        (message \"Created %s\" tar-name))))"

clean:
	rm -f *.elc
	rm -rf prooffrog-mode-*/
	rm -f prooffrog-mode-*.tar
