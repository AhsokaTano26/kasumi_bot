import random

from nonebot import get_plugin_config, on_command
from nonebot.adapters.qq import Message, MessageEvent
from nonebot.params import CommandArg
from nonebot.plugin import PluginMetadata
from nonebot.typing import T_State

from .config import Config

__plugin_meta__ = PluginMetadata(
    name="bangdream",
    description="BanG Dream 角色知识问答",
    usage="发送 /bangdream 或 /邦邦 开始答题",
    config=Config,
)

config = get_plugin_config(Config)

# 题库：覆盖 9 个乐队，共 24 题
QUESTIONS: list[dict[str, str]] = [
    # Poppin'Party
    {
        "question": "户山香澄的声优是谁？",
        "options": "A. 愛美\nB. 相羽あいな\nC. 伊藤美来\nD. 佐倉綾音",
        "answer": "A",
    },
    {
        "question": "Poppin'Party 的鼓手是谁？",
        "options": "A. 山吹沙綾\nB. 牛込りみ\nC. 市ヶ谷有咲\nD. 花園たえ",
        "answer": "A",
    },
    {
        "question": "牛込りみ在 Poppin'Party 中演奏什么乐器？",
        "options": "A. 吉他\nB. 贝斯\nC. 键盘\nD. 鼓",
        "answer": "B",
    },
    {
        "question": "花園たえ的声优是谁？",
        "options": "A. 大塚紗英\nB. 三澤紗千香\nC. 西本りみ\nD. 小原莉子",
        "answer": "A",
    },
    # Afterglow
    {
        "question": "美竹兰在 Afterglow 中担任什么？",
        "options": "A. 吉他手兼主唱\nB. 鼓手\nC. 贝斯手\nD. 键盘手",
        "answer": "A",
    },
    {
        "question": "Afterglow 的贝斯手是谁？",
        "options": "A. 青葉モカ\nB. 上原ひまり\nC. 宇田川あこ\nD. 羽沢つぐみ",
        "answer": "C",
    },
    {
        "question": "Afterglow 的鼓手是谁？",
        "options": "A. 青葉モカ\nB. 上原ひまり\nC. 宇田川あこ\nD. 羽沢つぐみ",
        "answer": "B",
    },
    # Pastel*Palettes
    {
        "question": "Pastel*Palettes 的主唱是谁？",
        "options": "A. 丸山彩\nB. 氷川日菜\nC. 白鷺千聖\nD. 大和麻弥",
        "answer": "A",
    },
    {
        "question": "白鷺千聖在 Pastel*Palettes 中演奏什么乐器？",
        "options": "A. 吉他\nB. 贝斯\nC. 键盘\nD. 鼓",
        "answer": "B",
    },
    {
        "question": "丸山彩的声优是谁？",
        "options": "A. 前島亜美\nB. 三澤紗千香\nC. 東山奈央\nD. 大坪由佳",
        "answer": "A",
    },
    # Roselia
    {
        "question": "Roselia 的键盘手是谁？",
        "options": "A. 凑友希那\nB. 氷川紗夜\nC. 今井リサ\nD. 宇田川巴",
        "answer": "C",
    },
    {
        "question": "凑友希那在 Roselia 中担任什么？",
        "options": "A. 主唱\nB. 吉他手\nC. 贝斯手\nD. 鼓手",
        "answer": "A",
    },
    {
        "question": "Roselia 的鼓手是谁？",
        "options": "A. 凑友希那\nB. 氷川紗夜\nC. 白金燐子\nD. 今井リサ",
        "answer": "C",
    },
    # Hello, Happy World!
    {
        "question": "Hello, Happy World! 的主唱是谁？",
        "options": "A. 弦巻こころ\nB. 濑田薰\nC. 北�的育美\nD. 松原花耶",
        "answer": "A",
    },
    {
        "question": "弦巻こころ的声优是谁？",
        "options": "A. 伊藤美来\nB. 丰田萌绘\nC. 吉田有里\nD. 黒沢ともよ",
        "answer": "A",
    },
    {
        "question": "Hello, Happy World! 的 DJ 是谁？",
        "options": "A. 弦巻こころ\nB. 濑田薰\nC. 北的育美\nD. 松原花耶",
        "answer": "D",
    },
    # Morfonica
    {
        "question": "Morfonica 的小提琴手是谁？",
        "options": "A. 仓田ましろ\nB. 桐谷透子\nC. 広町七深\nD. 二葉つくし",
        "answer": "A",
    },
    {
        "question": "Morfonica 的主唱是谁？",
        "options": "A. 仓田ましろ\nB. 八潮瑠唯\nC. 桐谷透子\nD. 二葉つくし",
        "answer": "A",
    },
    {
        "question": "八潮瑠唯在 Morfonica 中演奏什么乐器？",
        "options": "A. 小提琴\nB. 吉他\nC. 贝斯\nD. 鼓",
        "answer": "B",
    },
    # RAISE A SUILEN
    {
        "question": "RAISE A SUILEN 的 DJ 是谁？",
        "options": "A. LAYER\nB. LOCK\nC. MASKING\nD. PAREO",
        "answer": "D",
    },
    {
        "question": "和奏レイ在 RAISE A SUILEN 中演奏什么？",
        "options": "A. 吉他\nB. 贝斯\nC. 键盘\nD. 鼓",
        "answer": "A",
    },
    {
        "question": "RAISE A SUILEN 的贝斯手是谁？",
        "options": "A. 朝日六花\nB. 佐藤ますき\nC. パレオ\nD. レイヤー",
        "answer": "D",
    },
    # MyGO!!!!!
    {
        "question": "MyGO!!!!! 的主唱是谁？",
        "options": "A. 高松燈\nB. 千早愛音\nC. 豊川祥子\nD. 長崎そよ",
        "answer": "A",
    },
    {
        "question": "千早愛音在 MyGO!!!!! 中演奏什么乐器？",
        "options": "A. 吉他\nB. 贝斯\nC. 键盘\nD. 鼓",
        "answer": "A",
    },
    # Ave Mujica
    {
        "question": "Ave Mujica 的键盘手是谁？",
        "options": (
            "A. 豊川祥子 Doloris\nB. 八潮瑠唯 Mortis\n"
            "C. 若葉睦 Amoris\nD. 三角初華 Timoris"
        ),
        "answer": "A",
    },
    {
        "question": "Ave Mujica 的吉他手是谁？",
        "options": "A. 豊川祥子\nB. 若葉睦\nC. 三角初華\nD. 八潮瑠唯",
        "answer": "B",
    },
]

# 记分板：user_id -> {"correct": int, "total": int}
SCORES: dict[str, dict[str, int]] = {}


def update_score(user_id: str, *, is_correct: bool) -> None:
    if user_id not in SCORES:
        SCORES[user_id] = {"correct": 0, "total": 0}
    SCORES[user_id]["total"] += 1
    if is_correct:
        SCORES[user_id]["correct"] += 1


def get_leaderboard() -> list[tuple[str, dict[str, int]]]:
    """返回按正确率排序的排行榜"""
    return sorted(
        SCORES.items(),
        key=lambda x: (x[1]["correct"] / max(x[1]["total"], 1), x[1]["total"]),
        reverse=True,
    )


def check_answer(user_answer: str, correct_answer: str) -> bool:
    return user_answer.strip().upper() == correct_answer.strip().upper()


# 主命令：/bangdream 或 /邦邦
bangdream_cmd = on_command("bangdream", aliases={"邦邦"}, priority=10, block=True)


@bangdream_cmd.handle()
async def handle_bangdream(
    event: MessageEvent, state: T_State, args: Message[str] = CommandArg()
) -> None:
    args_str = args.extract_plain_text().strip()

    # 子命令：查看个人分数
    if args_str in ("score", "分数"):
        user_id = event.get_user_id()
        if user_id not in SCORES:
            await bangdream_cmd.finish("你还没有答过题哦，发送 /bangdream 开始答题！")
        score = SCORES[user_id]
        await bangdream_cmd.finish(
            f"你的得分：{score['correct']}/{score['total']}\n"
            f"正确率：{score['correct'] / score['total'] * 100:.1f}%"
        )

    # 子命令：查看排行榜
    if args_str in ("rank", "排行"):
        leaderboard = get_leaderboard()
        if not leaderboard:
            await bangdream_cmd.finish("暂无排行数据")
        lines = ["邦邦知识排行榜："]
        for i, (uid, score) in enumerate(leaderboard[:10], 1):
            correct = score["correct"]
            total = score["total"]
            lines.append(
                f"{i}. {uid[:8]}... - {correct}/{total}"
                f" ({correct / total * 100:.0f}%)"
            )
        await bangdream_cmd.finish("\n".join(lines))

    # 开始新一轮问答
    question_data = random.choice(QUESTIONS)
    state["question"] = question_data

    await bangdream_cmd.send(
        f"邦邦问答时间！\n\n"
        f"{question_data['question']}\n"
        f"{question_data['options']}\n\n"
        f"请回复选项字母（A/B/C/D）"
    )


@bangdream_cmd.receive()
async def handle_answer(event: MessageEvent, state: T_State) -> None:
    question_data: dict[str, str] = state["question"]
    user_answer = event.get_message().extract_plain_text().strip()
    correct_answer = question_data["answer"]
    user_id = event.get_user_id()

    is_correct = check_answer(user_answer, correct_answer)
    update_score(user_id, is_correct=is_correct)

    if is_correct:
        await bangdream_cmd.finish("回答正确！太厉害了！")
    else:
        await bangdream_cmd.finish(f"回答错误！正确答案是：{correct_answer}")
