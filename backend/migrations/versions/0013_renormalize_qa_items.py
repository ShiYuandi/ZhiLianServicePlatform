"""renormalize QA item questions (NFKC, drop punctuation/whitespace)"""

import hashlib

from alembic import op
import sqlalchemy as sa

from app.core.normalization import normalize_question, question_fingerprint


revision = "0013"
down_revision = "0012"
branch_labels = None
depends_on = None


def _items_table() -> sa.Table:
    return sa.table(
        "extended_qa_items",
        sa.column("id", sa.Integer),
        sa.column("table_id", sa.Integer),
        sa.column("question", sa.Text),
        sa.column("normalized_question", sa.Text),
        sa.column("question_fingerprint", sa.String(64)),
    )


def _rewrite(compute) -> None:
    bind = op.get_bind()
    items = _items_table()
    rows = (
        bind.execute(
            sa.select(items.c.id, items.c.table_id, items.c.question).order_by(
                items.c.id
            )
        )
        .mappings()
        .all()
    )
    seen: dict[tuple[int, str], str] = {}
    collisions: list[str] = []
    for row in rows:
        normalized, fingerprint = compute(row["question"])
        key = (row["table_id"], fingerprint)
        if key in seen:
            collisions.append(f"表 {row['table_id']}：「{seen[key]}」与「{row['question']}」")
            continue
        seen[key] = row["question"]
        bind.execute(
            sa.update(items)
            .where(items.c.id == row["id"])
            .values(normalized_question=normalized, question_fingerprint=fingerprint)
        )
    if collisions:
        raise RuntimeError(
            "归一化后出现等价问题，请先在后台删除重复问答项后重新执行迁移："
            + "；".join(collisions)
        )


def upgrade() -> None:
    _rewrite(lambda question: (normalize_question(question), question_fingerprint(question)))


def downgrade() -> None:
    def legacy(question: str) -> tuple[str, str]:
        normalized = question.strip().casefold()
        return normalized, hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    _rewrite(legacy)
