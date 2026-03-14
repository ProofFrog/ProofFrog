"""Tests for InstantiationTransformer, especially the FuncCall.field case."""

from proof_frog import frog_ast, visitors


def _make_scheme_with_field_alias(
    scheme_name: str, param_name: str, field_name: str, field_alias_on: str
) -> frog_ast.Scheme:
    """Return a scheme with one Set field that aliases a field from a parameter.

    Generates the equivalent of:
        Scheme <scheme_name>(<param_name>) extends SomePrimitive {
            Set <field_name> = <param_name>.<field_alias_on>;
        }
    """
    the_field = frog_ast.Field(
        frog_ast.SetType(),
        field_name,
        frog_ast.FieldAccess(frog_ast.Variable(param_name), field_alias_on),
    )
    param = frog_ast.Parameter(frog_ast.Variable(param_name), param_name)
    return frog_ast.Scheme(
        imports=[],
        name=scheme_name,
        parameters=[param],
        primitive_name="SomePrimitive",
        fields=[the_field],
        requirements=[],
        methods=[],
    )


def _make_primitive_with_bitstring_field(
    prim_name: str, field_name: str, size: int
) -> frog_ast.Primitive:
    """Return a primitive with one Set field that is BitString<size>."""
    the_field = frog_ast.Field(
        frog_ast.SetType(),
        field_name,
        frog_ast.BitStringType(frog_ast.Integer(size)),
    )
    return frog_ast.Primitive(
        name=prim_name,
        parameters=[],
        fields=[the_field],
        methods=[],
    )


def test_funccall_field_resolves_through_scheme_parameter() -> None:
    """FuncCall(Variable('UG'), [Variable('K')]).EncapsKey should resolve.

    When the namespace contains:
      - 'UG' -> Scheme with parameter K_param and field EncapsKey = K_param.EncapsKey
      - 'K'  -> Primitive with field EncapsKey = BitString<256>

    Then InstantiationTransformer should transform
      FieldAccess(FuncCall(Variable('UG'), [Variable('K')]), 'EncapsKey')
    into BitStringType(Integer(256)).
    """
    # UG scheme: Scheme UG(K_param) { Set EncapsKey = K_param.EncapsKey; }
    ug_scheme = _make_scheme_with_field_alias(
        scheme_name="UG",
        param_name="K_param",
        field_name="EncapsKey",
        field_alias_on="EncapsKey",
    )
    # K primitive: Primitive K() { Set EncapsKey = BitString<256>; }
    k_prim = _make_primitive_with_bitstring_field("K", "EncapsKey", 256)

    namespace: frog_ast.Namespace = {"UG": ug_scheme, "K": k_prim}

    # Build FuncCall(Variable("UG"), [Variable("K")]).EncapsKey
    func_call = frog_ast.FuncCall(frog_ast.Variable("UG"), [frog_ast.Variable("K")])
    node = frog_ast.FieldAccess(func_call, "EncapsKey")

    result = visitors.InstantiationTransformer(namespace).transform(node)
    expected = frog_ast.BitStringType(frog_ast.Integer(256))
    assert result == expected


def test_funccall_field_missing_field_returns_original() -> None:
    """If the field doesn't exist on the scheme, the node is returned unchanged."""
    ug_scheme = _make_scheme_with_field_alias("UG", "K_param", "EncapsKey", "EncapsKey")
    k_prim = _make_primitive_with_bitstring_field("K", "EncapsKey", 256)
    namespace: frog_ast.Namespace = {"UG": ug_scheme, "K": k_prim}

    func_call = frog_ast.FuncCall(frog_ast.Variable("UG"), [frog_ast.Variable("K")])
    node = frog_ast.FieldAccess(func_call, "NonExistentField")

    result = visitors.InstantiationTransformer(namespace).transform(node)
    # Should return unchanged (still a FieldAccess on the FuncCall)
    assert isinstance(result, frog_ast.FieldAccess)
    assert result.name == "NonExistentField"


def test_funccall_field_unknown_scheme_returns_original() -> None:
    """If the scheme name is not in the namespace, the node is returned unchanged."""
    namespace: frog_ast.Namespace = {}  # empty

    func_call = frog_ast.FuncCall(
        frog_ast.Variable("Unknown"), [frog_ast.Variable("K")]
    )
    node = frog_ast.FieldAccess(func_call, "EncapsKey")

    result = visitors.InstantiationTransformer(namespace).transform(node)
    assert isinstance(result, frog_ast.FieldAccess)
    assert result.name == "EncapsKey"
