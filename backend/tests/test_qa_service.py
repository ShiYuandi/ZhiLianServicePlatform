import logging

import pytest

from app.core.errors import AppError
from app.core.normalization import normalize_question
from app.schemas.qa import QaItemCreate, QaTableCreate
from app.services import qa_service


@pytest.mark.asyncio
async def test_qa_crud_and_normalized_duplicate(db):
    table = await qa_service.create_table(db, QaTableCreate(name="示例展馆"))
    table_id = table.id
    item = await qa_service.create_item(
        db, table_id, QaItemCreate(question="Hello", answer="第一条")
    )
    assert item.question == "Hello"
    with pytest.raises(AppError) as exc:
        await qa_service.create_item(
            db, table_id, QaItemCreate(question=" hello ", answer="重复")
        )
    assert exc.value.code == "DUPLICATE_QUESTION"
    items, total = await qa_service.list_items(db, table_id, 1, 20, None)
    assert total == 1
    assert items[0].answer == "第一条"


@pytest.mark.asyncio
async def test_replace_items_is_complete(db):
    table = await qa_service.create_table(db, QaTableCreate(name="示例文化馆"))
    await qa_service.create_item(
        db, table.id, QaItemCreate(question="旧问题", answer="旧答案")
    )
    count = await qa_service.replace_items(
        db,
        table.id,
        [
            QaItemCreate(question="新问题一", answer="新答案一"),
            QaItemCreate(question="新问题二", answer="新答案二"),
        ],
    )
    assert count == 2
    items = await qa_service.all_items(db, table.id)
    assert [item.question for item in items] == ["新问题一", "新问题二"]


@pytest.mark.asyncio
async def test_find_fixed_answer_supports_fuzzy_matching(db):
    table = await qa_service.create_table(db, QaTableCreate(name="模糊匹配馆"))
    table_id = table.id
    await qa_service.create_item(
        db, table_id, QaItemCreate(question="今天天气怎么样", answer="今天晴")
    )
    await qa_service.create_item(
        db, table_id, QaItemCreate(question="附近有什么好吃的", answer="附近餐厅很多")
    )
    await qa_service.create_item(
        db, table_id, QaItemCreate(question="你们几点开门", answer="九点开门")
    )
    await qa_service.create_item(
        db, table_id, QaItemCreate(question="馆里有讲解服务吗", answer="有免费讲解")
    )

    # 精确匹配仍然优先命中
    assert await qa_service.find_fixed_answer(db, table_id, " 今天天气怎么样 ") == "今天晴"
    # 多字、少字、语气词等容错在阈值内命中
    assert await qa_service.find_fixed_answer(db, table_id, "今天天气怎样") == "今天晴"
    assert await qa_service.find_fixed_answer(db, table_id, "附近有什么好吃的呀") == "附近餐厅很多"
    assert await qa_service.find_fixed_answer(db, table_id, "你们几点开门？") == "九点开门"
    # 反义词一字之差不命中（0.8 阈值时曾错配到"开门"）
    assert await qa_service.find_fixed_answer(db, table_id, "你们几点关门") is None
    # 差异字符包含否定字时不命中（避免"有/没有"语义反转）
    assert await qa_service.find_fixed_answer(db, table_id, "馆里没有讲解服务吗") is None
    # 相似度不足时不命中
    assert await qa_service.find_fixed_answer(db, table_id, "明天会下雨吗") is None
    # 空问题不命中
    assert await qa_service.find_fixed_answer(db, table_id, "   ") is None


@pytest.mark.asyncio
async def test_fuzzy_match_returns_highest_score(db):
    table = await qa_service.create_table(db, QaTableCreate(name="最佳匹配馆"))
    table_id = table.id
    await qa_service.create_item(
        db, table_id, QaItemCreate(question="营业时间是几点", answer="九点开门")
    )
    await qa_service.create_item(
        db, table_id, QaItemCreate(question="营业时间是几点到几点", answer="九点到十八点")
    )

    # 两条均达到阈值时返回相似度更高的一条
    assert (
        await qa_service.find_fixed_answer(db, table_id, "营业时间是几点到几点呢")
        == "九点到十八点"
    )


def test_normalize_question_folds_width_and_drops_punctuation():
    # 语音识别的常见变体：全角数字、中英文标点、空白，归一化后应完全一致
    assert normalize_question("需要担保金额为１１５万元") == normalize_question(
        "需要担保金额为115万元"
    )
    assert normalize_question("你们几点开门？") == normalize_question("你们几点开门。")
    assert normalize_question(" 你 好 ") == normalize_question("你好")


@pytest.mark.asyncio
async def test_find_fixed_answer_tolerates_asr_variants(db):
    table = await qa_service.create_table(db, QaTableCreate(name="语音容错馆"))
    table_id = table.id
    await qa_service.create_item(
        db, table_id, QaItemCreate(question="你好", answer="测试通过")
    )
    await qa_service.create_item(
        db, table_id, QaItemCreate(question="需要担保金额为115万元", answer="补贴前1.15万元")
    )

    # 尾随标点与全角数字均不影响命中
    assert await qa_service.find_fixed_answer(db, table_id, "你好。") == "测试通过"
    assert (
        await qa_service.find_fixed_answer(db, table_id, "需要担保金额为１１５万元？")
        == "补贴前1.15万元"
    )


@pytest.mark.asyncio
async def test_qa_match_writes_diagnostic_logs(db, caplog):
    table = await qa_service.create_table(db, QaTableCreate(name="匹配日志馆"))
    await qa_service.create_item(
        db,
        table.id,
        QaItemCreate(question="今天天气怎么样", answer="今天晴"),
    )

    caplog.set_level(logging.INFO, logger="app.services.qa_service")
    answer = await qa_service.find_fixed_answer(
        db,
        table.id,
        "今天天气怎样",
        request_id="req-log-test",
    )

    assert answer == "今天晴"
    logs = "\n".join(record.getMessage() for record in caplog.records)
    assert "event=qa_lookup_start" in logs
    assert "request_id=req-log-test" in logs
    assert "normalized='今天天气怎样'" in logs
    assert "event=qa_candidate" in logs
    assert "score=0.9231" in logs
    assert "event=qa_match_success" in logs
    assert "match_type=fuzzy" in logs


def test_strip_wake_prefix():
    assert qa_service.strip_wake_prefix(["小智"], "小智，你们几点开门") == "你们几点开门"
    assert qa_service.strip_wake_prefix(["小智", "你好小智"], "你好小智今天天气怎样") == "今天天气怎样"
    # 问题本身就是唤醒词、无唤醒词前缀、未配置唤醒词时均不剥离
    assert qa_service.strip_wake_prefix(["小智"], "小智") is None
    assert qa_service.strip_wake_prefix(["小智"], "你们几点开门") is None
    assert qa_service.strip_wake_prefix([], "小智，你们几点开门") is None
