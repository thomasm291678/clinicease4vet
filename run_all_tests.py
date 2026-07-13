#!/usr/bin/env python
"""
PetCare 宠物医院管理系统 — 全量自动化测试运行脚本

用法: python run_all_tests.py [--quick] [--verbose]

  --quick    仅运行单元测试（跳过集成测试）
  --verbose  显示详细输出
"""

import subprocess
import sys
import os
import time
from pathlib import Path

# 项目根目录
ROOT = Path(__file__).parent
BACKEND_DIR = ROOT / "backend"
CLIENT_DIR = ROOT / "client"
BACKEND_TESTS = BACKEND_DIR / "tests"
CLIENT_TESTS = CLIENT_DIR / "tests"

# ANSI 颜色
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"


def run_pytest(test_path, pythonpath, label, verbose=False, quick=False):
    """运行 pytest 并返回 (passed, failed, errors, total, duration)"""
    env = os.environ.copy()
    env["PYTHONPATH"] = str(pythonpath)

    args = ["python", "-m", "pytest", str(test_path), "-v"]
    if not verbose:
        args.append("--tb=short")

    if quick and "integration" in str(test_path).lower():
        # 跳过慢速集成测试
        args.append("--ignore=" + str(test_path / "test_integration.py"))

    print(f"\n{CYAN}{'='*60}{RESET}")
    print(f"{BOLD}{label}{RESET}")
    print(f"{CYAN}{'='*60}{RESET}")

    start = time.time()
    result = subprocess.run(args, cwd=str(ROOT), env=env,
                            capture_output=True, text=True)
    duration = time.time() - start

    # 解析输出
    output = result.stdout + result.stderr
    passed = 0
    failed = 0
    errors = 0
    total = 0

    for line in output.split("\n"):
        if "passed" in line and ("=" in line or "in" in line):
            # 尝试解析最后总结行
            pass
        if "PASSED" in line:
            passed += 1
        elif "FAILED" in line:
            failed += 1
        elif "ERROR" in line and "ERRORS" not in line:
            # 更精确的 errors 计数
            pass

    # 从最终总结行提取统计数据
    for line in reversed(output.split("\n")):
        if "passed" in line.lower() and ("=" in line):
            # e.g. "====================== 104 passed in 10.75s ======================="
            parts = line.strip("= ").split()
            for i, p in enumerate(parts):
                if "passed" in p:
                    try:
                        passed = int(p.replace("passed", "").strip())
                        total += passed
                    except ValueError:
                        pass
                elif "failed" in p:
                    try:
                        failed = int(p.replace("failed", "").strip())
                        total += failed
                    except ValueError:
                        pass
                elif "error" in p.lower() and "errors" not in p.lower():
                    try:
                        errors = int(p.replace("error", "").replace("errors", "").strip())
                        total += errors
                    except ValueError:
                        pass
            break

    # 如果没解析出来，使用字符串匹配方式重新计算
    if total == 0:
        passed = output.count("PASSED")
        failed = output.count("FAILED")
        errors = output.count("ERROR") - output.count("ERRORS")
        total = passed + failed + max(0, errors)

    # 打印精简输出
    for line in output.split("\n"):
        stripped = line.strip()
        if "PASSED" in stripped or "FAILED" in stripped:
            status = "✅" if "PASSED" in stripped else "❌"
            test_name = stripped.split("::")[-1].split(" ")[0] if "::" in stripped else stripped[:80]
            print(f"  {status} {test_name}")

    return passed, failed, errors, total, duration


def main():
    quick = "--quick" in sys.argv
    verbose = "--verbose" in sys.argv

    print(f"""
{BOLD}{CYAN}
╔══════════════════════════════════════════════════════╗
║     🐾 PetCare 宠物医院管理系统 v2.1                ║
║        全量自动化测试                                ║
╚══════════════════════════════════════════════════════╝
{RESET}
""")

    results = []
    overall_start = time.time()

    # ========== 后端测试 ==========
    passed, failed, errors, total, dur = run_pytest(
        BACKEND_TESTS, BACKEND_DIR,
        "📦 后端测试 (单元 + 集成)", verbose, quick
    )
    results.append(("后端测试", passed, failed, errors, total, dur))

    # ========== 客户端测试 ==========
    passed, failed, errors, total, dur = run_pytest(
        CLIENT_TESTS, CLIENT_DIR,
        "💻 客户端测试", verbose, quick
    )
    results.append(("客户端测试", passed, failed, errors, total, dur))

    overall_duration = time.time() - overall_start

    # ========== 汇总报告 ==========
    total_passed = sum(r[1] for r in results)
    total_failed = sum(r[2] for r in results)
    total_errors = sum(r[3] for r in results)
    total_all = sum(r[4] for r in results)

    status_color = GREEN if total_failed == 0 and total_errors == 0 else RED

    print(f"""
{BOLD}{'='*60}{RESET}
{BOLD}  📊 测试汇总报告{RESET}
{BOLD}{'='*60}{RESET}
""")

    for name, p, f, e, t, d in results:
        line = f"  {name}: {p} passed, {f} failed, {e} errors ({t} total) - {d:.1f}s"
        if f == 0 and e == 0:
            print(f"{GREEN}{line}{RESET}")
        else:
            print(f"{RED}{line}{RESET}")

    print(f"""
{BOLD}{'='*60}{RESET}
{status_color}{BOLD}  总计: {total_passed} passed, {total_failed} failed, {total_errors} errors ({total_all} total){RESET}
{status_color}{BOLD}  执行时间: {overall_duration:.1f}s{RESET}
{BOLD}{'='*60}{RESET}
""")

    if total_failed == 0 and total_errors == 0:
        print(f"{GREEN}{BOLD}  🎉 全部测试通过！系统运行正常。{RESET}\n")
    else:
        print(f"{RED}{BOLD}  ❌ 存在失败测试，请检查上述错误。{RESET}\n")

    return 0 if total_failed == 0 and total_errors == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
