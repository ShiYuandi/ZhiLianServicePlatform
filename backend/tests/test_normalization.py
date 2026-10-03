from app.core.normalization import (
    normalize_question,
    question_fingerprint,
    validate_table_name,
)


def test_question_normalization_folds_width_and_drops_separators():
    assert normalize_question("  Hello  World  ") == "helloworld"
    assert normalize_question("  瑞安是什么？ ") == "瑞安是什么"
    assert normalize_question("１１５万元") == normalize_question("115万元")
    assert question_fingerprint("Hello") == question_fingerprint(" hello ")


def test_table_name_blocks_path_traversal():
    for value in ("../secret", "a/b", "a\\b"):
        try:
            validate_table_name(value)
        except ValueError:
            pass
        else:
            raise AssertionError(f"unsafe table name accepted: {value}")
