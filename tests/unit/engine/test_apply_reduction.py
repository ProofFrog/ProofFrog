from proof_frog import frog_ast, frog_parser, proof_engine


def _make_engine() -> proof_engine.ProofEngine:
    return proof_engine.ProofEngine(verbose=False)


def _get_initialize(game: frog_ast.Game) -> frog_ast.Method:
    return game.get_method("Initialize")


class TestCaseA:
    """Challenger returns Void, reduction has Initialize."""

    def test_void_challenger_void_reduction(self) -> None:
        challenger = frog_parser.parse_game("""
        Game G() {
            Int x;
            Void Initialize() {
                x = 1;
                return None;
            }
            Int Run() {
                return x;
            }
        }
        """)
        reduction = frog_parser.parse_reduction("""
        Reduction R() compose G() against H().Adversary {
            Int y;
            Void Initialize() {
                y = 2;
                return None;
            }
            Int Run() {
                return y;
            }
        }
        """)
        result = _make_engine().apply_reduction(challenger, reduction)
        init = _get_initialize(result)
        assert isinstance(init.signature.return_type, frog_ast.Void)
        assert init.signature.parameters == []


class TestCaseB:
    """Challenger returns non-Void, reduction has parameter to receive it."""

    def test_parameter_receives_return_value(self) -> None:
        challenger = frog_parser.parse_game("""
        Game G() {
            Int pk;
            Int Initialize() {
                pk = 42;
                return pk;
            }
            Int Test() {
                return pk;
            }
        }
        """)
        reduction = frog_parser.parse_reduction("""
        Reduction R() compose G() against H().Adversary {
            Int stored_pk;
            Int Initialize(Int the_pk) {
                stored_pk = the_pk;
                return stored_pk;
            }
            Int Run() {
                return stored_pk;
            }
        }
        """)
        result = _make_engine().apply_reduction(challenger, reduction)
        init = _get_initialize(result)
        # Return type should be overwritten to challenger's
        assert not isinstance(init.signature.return_type, frog_ast.Void)
        # Parameter should have been consumed
        assert init.signature.parameters == []

    def test_only_first_parameter_consumed(self) -> None:
        challenger = frog_parser.parse_game("""
        Game G() {
            Int pk;
            Int Initialize() {
                pk = 42;
                return pk;
            }
            Int Test() {
                return pk;
            }
        }
        """)
        reduction = frog_parser.parse_reduction("""
        Reduction R() compose G() against H().Adversary {
            Int stored_pk;
            Int extra;
            Int Initialize(Int the_pk, Int bonus) {
                stored_pk = the_pk;
                extra = bonus;
                return stored_pk;
            }
            Int Run() {
                return stored_pk;
            }
        }
        """)
        result = _make_engine().apply_reduction(challenger, reduction)
        init = _get_initialize(result)
        # Only the first parameter should have been consumed
        assert len(init.signature.parameters) == 1
        assert init.signature.parameters[0].name == "bonus"


class TestCaseC:
    """Challenger returns non-Void, reduction has no parameters (new case)."""

    def test_no_crash_when_no_parameters(self) -> None:
        """This case used to crash with IndexError before the fix."""
        challenger = frog_parser.parse_game("""
        Game G() {
            Int pk;
            Int sk;
            [Int, Int] Initialize() {
                pk = 1;
                sk = 2;
                return [pk, sk];
            }
            Int Test() {
                return pk;
            }
        }
        """)
        reduction = frog_parser.parse_reduction("""
        Reduction R() compose G() against H().Adversary {
            Void Initialize() {
                return None;
            }
            Int Run() {
                return 0;
            }
        }
        """)
        result = _make_engine().apply_reduction(challenger, reduction)
        init = _get_initialize(result)
        # Reduction's return type should be preserved as Void
        assert isinstance(init.signature.return_type, frog_ast.Void)
        assert init.signature.parameters == []

    def test_challenger_init_body_inlined(self) -> None:
        """Challenger's Initialize body should be inlined into the result."""
        challenger = frog_parser.parse_game("""
        Game G() {
            Int pk;
            Int Initialize() {
                pk = 42;
                return pk;
            }
            Int Test() {
                return pk;
            }
        }
        """)
        reduction = frog_parser.parse_reduction("""
        Reduction R() compose G() against H().Adversary {
            Void Initialize() {
                return None;
            }
            Int Run() {
                return 0;
            }
        }
        """)
        result = _make_engine().apply_reduction(challenger, reduction)
        init = _get_initialize(result)
        # The result should have more statements than just "return None"
        # because the challenger's Initialize body is inlined
        assert len(init.block.statements) > 1


class TestExistingChallengerCall:
    """Reduction already calls challenger.Initialize() explicitly."""

    def test_no_duplicate_when_reduction_calls_challenger_init(self) -> None:
        """If reduction already calls challenger.Initialize(), don't prepend another."""
        challenger = frog_parser.parse_game("""
        Game G() {
            Int x;
            Void Initialize() {
                x = 1;
                return None;
            }
            Int Run() {
                return x;
            }
        }
        """)
        reduction = frog_parser.parse_reduction("""
        Reduction R() compose G() against H().Adversary {
            Int y;
            Void Initialize() {
                challenger.Initialize();
                y = 2;
                return None;
            }
            Int Run() {
                return y;
            }
        }
        """)
        result = _make_engine().apply_reduction(challenger, reduction)
        init = _get_initialize(result)
        # The challenger's Initialize body ("x = 1; return None;") should be
        # inlined exactly once into the reduction.  Count assignments to x
        # (field renaming to challenger@x happens in _get_game_ast, not here).
        assign_count = sum(
            1
            for s in init.block.statements
            if isinstance(s, frog_ast.Assignment)
            and isinstance(s.var, frog_ast.Variable)
            and s.var.name == "x"
        )
        assert assign_count == 1

    def test_nonvoid_challenger_with_existing_call(self) -> None:
        """Reduction calls challenger.Initialize() and uses its return value."""
        challenger = frog_parser.parse_game("""
        Game G() {
            Int pk;
            Int Initialize() {
                pk = 42;
                return pk;
            }
            Int Test() {
                return pk;
            }
        }
        """)
        reduction = frog_parser.parse_reduction("""
        Reduction R() compose G() against H().Adversary {
            Int stored;
            Int Initialize() {
                Int v = challenger.Initialize();
                stored = v;
                return stored;
            }
            Int Run() {
                return stored;
            }
        }
        """)
        result = _make_engine().apply_reduction(challenger, reduction)
        init = _get_initialize(result)
        # Should not crash and should have a reasonable number of statements
        assert len(init.block.statements) >= 1


class TestNoInitialize:
    """Challenger has Initialize but reduction does not."""

    def test_challenger_initialize_copied(self) -> None:
        challenger = frog_parser.parse_game("""
        Game G() {
            Int x;
            Void Initialize() {
                x = 1;
                return None;
            }
            Int Run() {
                return x;
            }
        }
        """)
        reduction = frog_parser.parse_reduction("""
        Reduction R() compose G() against H().Adversary {
            Int Run() {
                return 0;
            }
        }
        """)
        result = _make_engine().apply_reduction(challenger, reduction)
        assert result.has_method("Initialize")

    def test_nonvoid_challenger_initialize_copied_verbatim(self) -> None:
        """When reduction has no Initialize, challenger's is used directly."""
        challenger = frog_parser.parse_game("""
        Game G() {
            Int pk;
            Int Initialize() {
                pk = 42;
                return pk;
            }
            Int Test() {
                return pk;
            }
        }
        """)
        reduction = frog_parser.parse_reduction("""
        Reduction R() compose G() against H().Adversary {
            Int Run() {
                return 0;
            }
        }
        """)
        result = _make_engine().apply_reduction(challenger, reduction)
        init = _get_initialize(result)
        # Should preserve challenger's return type
        assert not isinstance(init.signature.return_type, frog_ast.Void)
