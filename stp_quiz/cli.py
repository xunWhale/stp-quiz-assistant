"""Command Line Interface (CLI) for stp-quiz-assistant."""

from __future__ import annotations

import argparse
import sys
from typing import Optional

from stp_quiz.models import Category, QuestionType
from stp_quiz.question_bank import QuestionBank
from stp_quiz.service import QuizService
from stp_quiz.storage import Storage


def create_parser() -> argparse.ArgumentParser:
    common_parser = argparse.ArgumentParser(add_help=False)
    common_parser.add_argument(
        "--db",
        type=str,
        default=argparse.SUPPRESS,
        help="指定 SQLite 数据库路径 (默认: ~/.stp_quiz/stp_quiz.db)",
    )

    parser = argparse.ArgumentParser(
        prog="stp-quiz",
        description="ikun 群 STP/RSTP/MSTP 抽查小助手 - 网络工程知识考核、判分与错题本管理",
        parents=[common_parser],
    )

    subparsers = parser.add_subparsers(dest="command", help="可用子命令")

    # 1. 抽题自测 / 抽查展示 (quiz)
    quiz_parser = subparsers.add_parser("quiz", parents=[common_parser], help="随机抽题或指定题号出题")
    quiz_parser.add_argument("--user", type=str, default=None, help="目标群友昵称/ID")
    quiz_parser.add_argument(
        "--category",
        choices=["stp_election", "port_roles_states", "rstp_convergence_pa", "mstp_instance", "comprehensive"],
        default=None,
        help="按知识分类抽题",
    )
    quiz_parser.add_argument(
        "--type",
        choices=["choice", "multi_choice", "essay"],
        default=None,
        help="按题型抽题",
    )
    quiz_parser.add_argument("--qid", type=str, default=None, help="指定题目ID直接出题")

    # 2. 提交答案并打分 (submit)
    submit_parser = subparsers.add_parser("submit", parents=[common_parser], help="提交回答进行智能判分并记录成绩/错题")
    submit_parser.add_argument("--user", type=str, required=True, help="群友昵称/ID")
    submit_parser.add_argument("--qid", type=str, required=True, help="题目ID")
    submit_parser.add_argument("--answer", type=str, required=True, help="群友作答内容")
    submit_parser.add_argument("--retest", action="store_true", help="是否标记为错题补考")
    submit_parser.add_argument("--wrong-id", type=int, default=None, help="补考关联的错题记录ID")

    # 3. 抽查某人 (inspect - 抽题并交互输入答案打分)
    inspect_parser = subparsers.add_parser("inspect", parents=[common_parser], help="突击抽查指定群友并进入交互答题打分")
    inspect_parser.add_argument("user", type=str, help="被抽查群友昵称/ID")
    inspect_parser.add_argument(
        "--category",
        choices=["stp_election", "port_roles_states", "rstp_convergence_pa", "mstp_instance", "comprehensive"],
        default=None,
        help="指定抽查考点分类",
    )
    inspect_parser.add_argument("--type", choices=["choice", "multi_choice", "essay"], default=None, help="指定题型")

    # 4. 补考 (retest - 针对某人的错题本逐一补考)
    retest_parser = subparsers.add_parser("retest", parents=[common_parser], help="发起指定群友的错题补考")
    retest_parser.add_argument("user", type=str, help="需补考群友昵称/ID")

    # 5. 查看错题本 (wrong-list)
    wrong_parser = subparsers.add_parser("wrong-list", parents=[common_parser], help="查看未消错题与待补考清单")
    wrong_parser.add_argument("user", nargs="?", default=None, help="可选：查看指定群友的错题")

    # 6. 排行榜 (leaderboard)
    board_parser = subparsers.add_parser("leaderboard", parents=[common_parser], help="查看 ikun 群友积分与战力排行榜")
    board_parser.add_argument("--limit", type=int, default=10, help="显示前 N 名 (默认 10)")

    # 7. 查看题库清单 (list-questions)
    list_q_parser = subparsers.add_parser("list-questions", parents=[common_parser], help="列出题库所有题目概要与考点")
    list_q_parser.add_argument(
        "--category",
        choices=["stp_election", "port_roles_states", "rstp_convergence_pa", "mstp_instance", "comprehensive"],
        default=None,
        help="按知识分类过滤",
    )

    # 8. 数据导入导出 (export-data / import-data)
    export_parser = subparsers.add_parser("export-data", parents=[common_parser], help="导出用户积分与错题本到 JSON")
    export_parser.add_argument("file", type=str, help="导出目标文件路径")

    import_parser = subparsers.add_parser("import-data", parents=[common_parser], help="从 JSON 导入用户积分与错题本")
    import_parser.add_argument("file", type=str, help="源 JSON 文件路径")

    # 9. 沉浸式交互控制台 (interactive)
    subparsers.add_parser("interactive", parents=[common_parser], help="进入全交互式 STP 抽查小助手控制台")

    return parser


def run_inspect_interactive(service: QuizService, user: str, category: Optional[str] = None, qtype: Optional[str] = None):
    question = service.draw_question(category=category, qtype=qtype)
    if not question:
        print(f"❌ 题库中未找到符合条件的考题！")
        return

    print(service.format_quiz_card(question, target_user=user))
    print("\n⏳ 请输入回答（输入完成后按回车，简答题输入完毕后直接回车提交）:")
    try:
        user_answer = input("> ").strip()
    except (KeyboardInterrupt, EOFError):
        print("\n🚫 已取消作答。")
        return

    if not user_answer:
        print("⚠️ 未输入作答内容！")
        return

    eval_result, user_rec, wrong_rec = service.submit_answer(
        user_id=user,
        question_id=question.id,
        answer=user_answer,
    )
    print("\n" + service.format_eval_report(question, eval_result, user_rec))


def run_retest_interactive(service: QuizService, user: str):
    wrongs = service.get_user_pending_wrongs(user)
    if not wrongs:
        print(f"✨ 太棒了！群友 [{user}] 当前没有未补错题，错题本已全部清空！")
        return

    print(f"\n📋 【群友 {user} 的待补考错题清单 - 共 {len(wrongs)} 题】")
    for idx, w in enumerate(wrongs, start=1):
        print(f"  {idx}. [{w.question_id}] {w.question_title} (上次得分: {w.score}分, 时间: {w.created_at[:16]})")

    print("\n🚀 开始补考模式（答对可当场消错）！")
    for idx, w in enumerate(wrongs, start=1):
        q = service.qb.get(w.question_id)
        if not q:
            continue
        print(f"\n--- [补考第 {idx}/{len(wrongs)} 题] ---")
        print(service.format_quiz_card(q, target_user=user))
        print(f"💡 上次历史作答: {w.user_answer}")
        print("👉 请输入你的最新订正回答（输入 'skip' 跳过此题，'exit' 退出补考）:")
        try:
            ans = input("> ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n🚫 退出补考。")
            break

        if ans.lower() == "exit":
            print("🚪 已退出补考模式。")
            break
        if ans.lower() == "skip" or not ans:
            print("⏩ 已跳过本题。")
            continue

        eval_res, urec, _ = service.submit_answer(
            user_id=user,
            question_id=q.id,
            answer=ans,
            is_retest=True,
            wrong_record_id=w.id,
        )
        print("\n" + service.format_eval_report(q, eval_res, urec, is_retest=True))


def run_interactive_menu(service: QuizService):
    print("=" * 65)
    print("  🏀 欢迎来到 ikun 群 STP 抽查小助手交互控制台 🏀")
    print("  作者: xunWhale | 专注于 STP/RSTP/MSTP 机制高阶内卷与抽查")
    print("=" * 65)

    current_user = "ikun-007"

    while True:
        print(f"\n当前操作群友: [{current_user}]")
        print("1. 🎲 随机抽取题目自测")
        print("2. 🔍 突击抽查指定群友")
        print("3. 📝 进行错题补考（清空错题本）")
        print("4. 📕 查看我的待补考错题")
        print("5. 🏆 查看群友积分战力排行榜")
        print("6. 📚 浏览题库所有考点目录")
        print("7. 👤 切换当前操作群友")
        print("0. 🚪 退出系统")

        try:
            choice = input("\n请选择功能序号 [0-7]: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n👋 拜拜咯~")
            break

        if choice == "1":
            q = service.draw_question()
            if not q:
                print("题库为空！")
                continue
            print("\n" + service.format_quiz_card(q, target_user=current_user))
            try:
                ans = input("请输入作答: ").strip()
            except (KeyboardInterrupt, EOFError):
                continue
            if ans:
                res, u, _ = service.submit_answer(current_user, q.id, ans)
                print("\n" + service.format_eval_report(q, res, u))
        elif choice == "2":
            target = input("请输入被抽查群友的昵称/ID: ").strip()
            if target:
                run_inspect_interactive(service, target)
        elif choice == "3":
            run_retest_interactive(service, current_user)
        elif choice == "4":
            wrongs = service.get_user_pending_wrongs(current_user)
            if not wrongs:
                print(f"✨ 恭喜，[{current_user}] 没有未消错题！")
            else:
                print(f"\n📕 群友 [{current_user}] 待补考列表 ({len(wrongs)} 题):")
                for w in wrongs:
                    print(f"   • [{w.question_id}] {w.question_title} (历史得分: {w.score})")
        elif choice == "5":
            leaders = service.get_leaderboard()
            print("\n🏆 ===== ikun 群生成树积分风云榜 ===== 🏆")
            print(f"{'排名':<6}{'群友ID/昵称':<18}{'总积分':<10}{'刷题数':<8}{'通过率'}")
            print("-" * 55)
            for rank, u in enumerate(leaders, start=1):
                print(f"{rank:<6}{u.nickname:<18}{u.total_score:<10.1f}{u.total_quizzes:<8}{u.pass_rate}%")
            print("-" * 55)
        elif choice == "6":
            questions = service.qb.list_all()
            print(f"\n📚 题库现有 {len(questions)} 道考题:")
            for q in questions:
                print(f"   [{q.id}] ({q.category.value} | {q.qtype.value}) {q.title}")
        elif choice == "7":
            new_u = input("请输入新的群友昵称/ID: ").strip()
            if new_u:
                current_user = new_u
                service.get_or_register_user(current_user)
                print(f"✅ 已切换为: {current_user}")
        elif choice == "0":
            print("👋 拜拜咯~ ikun 网络攻城狮继续努力！")
            break
        else:
            print("⚠️ 无效选项，请重新输入！")


def main(argv=None):
    parser = create_parser()
    args = parser.parse_args(argv)

    db_path = getattr(args, "db", None)
    storage = Storage(db_path=db_path) if db_path else Storage()
    service = QuizService(storage=storage)

    if not args.command:
        # Default to interactive mode if no arguments provided
        run_interactive_menu(service)
        return

    if args.command == "interactive":
        run_interactive_menu(service)

    elif args.command == "quiz":
        if args.qid:
            question = service.qb.get(args.qid)
            if not question:
                print(f"❌ 未找到题号为 {args.qid} 的考题")
                sys.exit(1)
        else:
            question = service.draw_question(category=args.category, qtype=args.type)
            if not question:
                print("❌ 没有找到匹配条件的考题")
                sys.exit(1)

        print(service.format_quiz_card(question, target_user=args.user))

    elif args.command == "submit":
        try:
            eval_res, user_rec, wrong_rec = service.submit_answer(
                user_id=args.user,
                question_id=args.qid,
                answer=args.answer,
                is_retest=args.retest,
                wrong_record_id=args.wrong_id,
            )
            q = service.qb.get(args.qid)
            if q:
                print(service.format_eval_report(q, eval_res, user_rec, is_retest=args.retest))
            else:
                print(f"得分: {eval_res.score}, 通过: {eval_res.passed}")
        except Exception as e:
            print(f"❌ 判分异常: {e}", file=sys.stderr)
            sys.exit(1)

    elif args.command == "inspect":
        run_inspect_interactive(service, args.user, category=args.category, qtype=args.type)

    elif args.command == "retest":
        run_retest_interactive(service, args.user)

    elif args.command == "wrong-list":
        wrongs = service.get_user_pending_wrongs(args.user)
        if not wrongs:
            print("✨ 暂无未补错题！全员网络工程及格！")
        else:
            print(f"\n📕 待补考错题列表 (共 {len(wrongs)} 条):")
            print(f"{'记录ID':<8}{'群友':<14}{'题目ID':<16}{'得分':<8}{'题目标题'}")
            print("-" * 65)
            for w in wrongs:
                print(f"{w.id:<8}{w.user_id:<14}{w.question_id:<16}{w.score:<8.1f}{w.question_title}")
            print("-" * 65)

    elif args.command == "leaderboard":
        leaders = service.get_leaderboard(limit=args.limit)
        if not leaders:
            print("暂无群友答题数据，快去执行 'stp-quiz quiz' 开启抽查吧！")
        else:
            print("\n🏆 ===== ikun 群生成树积分风云榜 ===== 🏆")
            print(f"{'排名':<6}{'群友ID/昵称':<18}{'总积分':<10}{'刷题数':<8}{'通过率'}")
            print("-" * 55)
            for rank, u in enumerate(leaders, start=1):
                print(f"{rank:<6}{u.nickname:<18}{u.total_score:<10.1f}{u.total_quizzes:<8}{u.pass_rate}%")
            print("-" * 55)

    elif args.command == "list-questions":
        cat_enum = Category(args.category) if args.category else None
        questions = service.qb.filter(category=cat_enum)
        print(f"\n📚 题库题目列表 (共 {len(questions)} 道):")
        print(f"{'ID':<16}{'分类':<22}{'题型':<14}{'难度':<8}{'标题'}")
        print("-" * 75)
        for q in questions:
            diff_str = "★" * q.difficulty
            print(f"{q.id:<16}{q.category.value:<22}{q.qtype.value:<14}{diff_str:<8}{q.title}")
        print("-" * 75)

    elif args.command == "export-data":
        try:
            service.storage.export_json(args.file)
            print(f"✅ 成功将数据备份导出至: {args.file}")
        except Exception as e:
            print(f"❌ 导出失败: {e}", file=sys.stderr)
            sys.exit(1)

    elif args.command == "import-data":
        try:
            service.storage.import_json(args.file)
            print(f"✅ 成功从 {args.file} 恢复导入数据！")
        except Exception as e:
            print(f"❌ 导入失败: {e}", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main()
