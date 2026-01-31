#!/usr/bin/env python3
"""
Hook script to send audit reports to Codex for analysis and fixes
"""

import json
import subprocess
import datetime
import os
import sys
from pathlib import Path

# Project directory
PROJECT_DIR = "/Users/mac/Documents/GitHub/zero-times.github.io"

def call_codex(prompt, workdir=PROJECT_DIR):
    """
    Execute Codex CLI with the given prompt
    Returns True if successful, False otherwise
    """
    try:
        print(f"\n🤖 Calling Codex for analysis and fixes...")
        print(f"📁 Working directory: {workdir}")

        # Execute Codex with the prompt
        # Using --full-auto flag to auto-approve workspace changes
        result = subprocess.run(
            ["codex", "exec", "--full-auto", prompt],
            cwd=workdir,
            capture_output=True,
            text=True,
            timeout=1800  # 30 minutes timeout
        )

        print(f"\n📋 Codex Output:")
        print("=" * 60)
        print(result.stdout)

        if result.stderr:
            print(f"\n⚠️ Codex Errors/Warnings:")
            print(result.stderr)

        if result.returncode != 0:
            print(f"\n❌ Codex failed with return code: {result.returncode}")
            return False

        print("\n✅ Codex completed successfully")
        return True

    except subprocess.TimeoutExpired:
        print("\n⏱️ Codex timed out after 10 minutes")
        return False
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Error executing Codex: {str(e)}")
        if e.stderr:
            print(f"Stderr: {e.stderr}")
        return False
    except FileNotFoundError:
        print("\n❌ Codex CLI not found. Please install Codex.")
        return False
    except Exception as e:
        print(f"\n❌ Unexpected error: {str(e)}")
        return False

def send_report_to_codex(report_path):
    """Send audit report to Codex for analysis and fixes"""

    # Read audit report
    with open(report_path, 'r', encoding='utf-8') as f:
        report_data = json.load(f)

    # Create a detailed prompt for Codex
    prompt = f"""
请分析以下网站审计报告，并提出具体的改进建议和代码修复：

网站审计报告
===============================
时间: {report_data['audit_timestamp']}
网站 URL: {report_data['website_url']}
总体评分: {report_data['overall_score']}/10.0

布局评估:
- 评分: {report_data['sections']['layout_assessment']['score']}/10.0
- 结果: {json.dumps(report_data['sections']['layout_assessment']['findings'], indent=2, ensure_ascii=False)}

链接有效性检查:
- 评分: {report_data['sections']['broken_links_check']['score']}/10.0
- 发现的断链数量: {len(report_data['sections']['broken_links_check'].get('broken_links', []))}
- 详情: {json.dumps(report_data['sections']['broken_links_check']['findings'], indent=2, ensure_ascii=False)}

SEO 评估:
- 评分: {report_data['sections']['seo_evaluation']['score']}/10.0
- 结果: {json.dumps(report_data['sections']['seo_evaluation']['findings'], indent=2, ensure_ascii=False)}

内容质量评估:
- 评分: {report_data['sections']['content_quality']['score']}/10.0
- 结果: {json.dumps(report_data['sections']['content_quality']['findings'], indent=2, ensure_ascii=False)}

建议:
{json.dumps(report_data.get('recommendations', []), indent=2, ensure_ascii=False)}

请提供具体的改进建议并实施代码修复：

1. 修复识别出的断链（更新链接或删除无效链接）
2. 改进布局和响应式设计
3. 优化 SEO 元素（标题、描述、关键词、sitemap 等）
4. 提升整体内容质量
5. 实施其他建议的改进

请直接在相应的文件中实施这些改进。
完成后，请提交所有更改到 git。

重要：使用中文进行所有改进说明和代码注释。
"""

    # Write prompt to a temporary file for Codex
    temp_prompt_file = Path(PROJECT_DIR) / "temp_codex_prompt.txt"
    with open(temp_prompt_file, 'w', encoding='utf-8') as f:
        f.write(prompt)

    print(f"📄 Prompt file created: {temp_prompt_file}")

    # Call Codex with the prompt
    try:
        success = call_codex(prompt, PROJECT_DIR)

        if success:
            # Create a completion note
            completion_note = f"""
Codex 处理完成
============================
时间: {datetime.datetime.now().isoformat()}
处理的报告: {report_path}

执行的改进:
1. 已分析网站评审报告
2. 已建议并实施代码修复
3. 已优化 SEO 元素
4. 已改进整体质量

下一步:
- 检查 Codex 实施的更改
- 测试网站功能
- 在下一次审计中验证改进
"""

            # Write completion note
            completion_file = Path(str(report_path).replace('.json', '_codex_completion.txt'))
            with open(completion_file, 'w', encoding='utf-8') as f:
                f.write(completion_note)

            print(f"📝 Completion note saved: {completion_file}")

            # Run git operations to commit changes
            run_git_operations()

            return True
        else:
            return False

    except Exception as e:
        print(f"❌ Error processing with Codex: {str(e)}")
        return False

def run_git_operations():
    """Run git operations to commit any changes"""
    try:
        print("\n🔄 Running git operations...")

        # Check if there are changes to commit
        result = subprocess.run(
            ["git", "-C", PROJECT_DIR, "status", "--porcelain"],
            capture_output=True, text=True, check=True
        )

        if result.stdout.strip():  # If there are changes
            print("📦 Changes detected, committing...")

            # Add all changes to git
            subprocess.run(["git", "-C", PROJECT_DIR, "add", "."], check=True)

            # Commit changes
            commit_msg = f"Auto: Apply Codex recommendations from website audit {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            subprocess.run([
                "git", "-C", PROJECT_DIR,
                "commit", "-m", commit_msg
            ], check=True)

            print(f"✅ Changes committed: {commit_msg}")

            # Push changes
            subprocess.run([
                "git", "-C", PROJECT_DIR,
                "push", "origin", "master"
            ], check=True)

            print("🚀 Changes pushed to repository")
        else:
            print("ℹ️ No changes to commit")

    except subprocess.CalledProcessError as e:
        print(f"❌ Error executing git operations: {str(e)}")
    except Exception as e:
        print(f"❌ General error in git operations: {str(e)}")

def main():
    """Main function to process the latest audit report with Codex"""
    print("🎯 Website Audit Report Hook - Starting...")
    print(f"📂 Project directory: {PROJECT_DIR}")

    reports_dir = Path(PROJECT_DIR) / "reports/"

    # Find most recent audit report
    json_reports = list(reports_dir.glob("site_audit_*.json"))

    if not json_reports:
        print("⚠️ No audit reports found")
        print("🔍 Running audit now to generate a new report...")
        try:
            import site_audit_tool
            report = site_audit_tool.main()
            if report:
                # Find the most recently created report
                json_reports = list(reports_dir.glob("site_audit_*.json"))
                if json_reports:
                    latest_report = max(json_reports, key=lambda x: x.stat().st_mtime)
                    print(f"📊 Processing newly generated report with Codex: {latest_report}")
                    success = send_report_to_codex(latest_report)

                    if success:
                        print("✅ Report processed successfully with Codex")
                    else:
                        print("❌ Failed to process report with Codex")
                else:
                    print("❌ No report generated even after running audit")
            else:
                print("❌ The audit main() function returned None")
        except Exception as e:
            print(f"❌ Error running audit directly: {str(e)}")
        return

    # Get the most recent report
    latest_report = max(json_reports, key=lambda x: x.stat().st_mtime)

    print(f"📋 Processing most recent report with Codex: {latest_report}")

    # Send to Codex for analysis
    success = send_report_to_codex(latest_report)

    if success:
        print("✅ Report successfully processed by Codex and changes committed")
    else:
        print("❌ Failed to process report with Codex")

    print("🎉 Website Audit Report Hook - Completed")

if __name__ == "__main__":
    main()
