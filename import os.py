import os
import subprocess
import urllib.parse
import csv
import shutil
import re

# 拼音首字母转换函数
def get_pinyin_initial(s):
    # 手动映射常用汉字的拼音首字母
    pinyin_map = {
        '太': 't', '阳': 'y', '能': 'n', '钨': 'w', '丝': 's', '灯': 'd', '户': 'h', '外': 'w',
        '蒜': 's', '泥': 'n', '神': 's', '器': 'q', '电': 'd', '动': 'd', '捣': 'd',
        '跨': 'k', '境': 'j', '亚': 'y', '马': 'm', '逊': 'x', '同': 't', '款': 'k', '欧': 'o',
        '车': 'c', '载': 'z', '吸': 'x', '尘': 'c', '器': 'q', '无': 'w', '刷': 's', '大': 'd',
        '无': 'w', '线': 'x', '多': 'd',
        '飞': 'f', '碟': 'd', 'l': 'l', 'e': 'e', 'd': 'd'
    }
    
    result = ''
    for char in s:
        if char in pinyin_map:
            result += pinyin_map[char]
        elif char.isalpha():
            result += char.lower()
        else:
            # 跳过其他字符
            pass
    
    # 确保结果不为空
    if not result:
        result = 'z'
    
    return result

# ========= 配置区（必须改） =========
REPO_PATH = r"D:\git-CDN"        # 本地 git 仓库路径
BASE_DIR = r"D:\window_launcher\project1\output"    # 图片总文件夹（每个子文件夹=一个分支）
GITHUB_USER = "lwl810910-pixel"
REPO_NAME = "tk-shop-images"
BASE_BRANCH = "master"   # 或 master / mainV（看你仓库实际）
# ==================================


# ===== Git执行器（带输出）=====
def run_git(cmd):
    print(f"\n🟡 {cmd}")
    result = subprocess.run(cmd, cwd=REPO_PATH, shell=True, capture_output=True, text=True)

    if result.stdout:
        print("🟢", result.stdout.strip())
    if result.stderr:
        print("🔴", result.stderr.strip())

    return result.returncode, result.stdout.strip(), result.stderr.strip()


# ===== 校验仓库 =====
def check_repo():
    _, out, _ = run_git("git remote -v")
    if GITHUB_USER not in out or REPO_NAME not in out:
        raise Exception("❌ 当前目录不是目标 GitHub 仓库")


# ===== 分支处理 =====
def checkout_branch(branch_name):
    run_git("git fetch")

    _, branches, _ = run_git("git branch")
    
    # 检查分支是否存在（需要精确匹配）
    branch_exists = False
    for line in branches.split('\n'):
        # 去除前缀空格和*符号
        branch = line.strip().lstrip('* ')
        if branch == branch_name:
            branch_exists = True
            break

    if branch_exists:
        print(f"🔁 切换已有分支: {branch_name}")
        run_git(f"git checkout {branch_name}")
    else:
        print(f"🆕 创建新分支: {branch_name}")
        run_git(f"git checkout {BASE_BRANCH}")
        run_git("git pull")
        run_git(f"git checkout -b {branch_name}")


# ===== 清空仓库内容（防污染）=====
def clean_repo():
    for f in os.listdir(REPO_PATH):
        if f == ".git":
            continue
        # 排除脚本文件和CSV文件
        if f == "import os.py" or f.endswith(".csv"):
            continue
        path = os.path.join(REPO_PATH, f)
        if os.path.isfile(path):
            os.remove(path)
        else:
            shutil.rmtree(path)


# ===== 上传文件 =====
def upload_files(folder_path):
    clean_repo()

    count = 0

    for file in os.listdir(folder_path):
        src = os.path.join(folder_path, file)
        dst = os.path.join(REPO_PATH, file)

        if os.path.isfile(src):
            # 过滤视频文件
            if file.lower().endswith('.mp4'):
                print(f"⚠️  跳过视频文件: {file}")
                continue
            shutil.copy2(src, dst)
            count += 1

    if count == 0:
        print("⚠️ 空文件夹，跳过")
        return False

    run_git("git add .")

    _, status, _ = run_git("git status")
    if "nothing to commit" in status:
        print("⚠️ 没有变化")
        return False

    run_git('git commit -m "upload images"')
    return True


# ===== push + 强校验 =====
def push_branch(branch_name):
    code, _, err = run_git(f"git push -u origin {branch_name}")

    if code != 0:
        raise Exception(f"❌ push失败: {err}")

    # 校验远程是否存在
    _, remote, _ = run_git("git ls-remote --heads origin")

    if branch_name not in remote:
        raise Exception(f"❌ 远程不存在分支: {branch_name}")

    print(f"✅ 已成功上传到 GitHub: {branch_name}")


# ===== 生成 CDN =====
def generate_cdn(branch, filename):
    encoded = urllib.parse.quote(filename)
    return f"https://cdn.jsdelivr.net/gh/{GITHUB_USER}/{REPO_NAME}@{branch}/{encoded}"


# ===== 主流程 =====
def process():
    check_repo()

    for folder in os.listdir(BASE_DIR):
        folder_path = os.path.join(BASE_DIR, folder)

        if not os.path.isdir(folder_path):
            continue
        
        # 跳过隐藏文件夹和系统文件夹
        if folder.startswith('.'):
            print(f"⚠️  跳过隐藏文件夹: {folder}")
            continue

        # 生成拼音首字母分支名
        branch = get_pinyin_initial(folder)
        # 清理分支名，确保只包含字母和数字
        branch = re.sub(r'[^a-zA-Z0-9]', '', branch)
        # 限制分支名长度
        branch = branch[:20]

        print("\n==============================")
        print(f"🚀 处理分支: {branch} (文件夹: {folder})")

        # 1. 分支
        checkout_branch(branch)

        # 2. 上传
        ok = upload_files(folder_path)
        if not ok:
            continue

        # 3. push
        push_branch(branch)

        # 4. 生成 CSV
        csv_path = os.path.join(folder_path, "cdn_links.csv")

        with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow(["文件名", "CDN链接"])

            for file in os.listdir(folder_path):
                if os.path.isfile(os.path.join(folder_path, file)):
                    # 跳过视频文件
                    if file.lower().endswith('.mp4'):
                        continue
                    url = generate_cdn(branch, file)
                    writer.writerow([file, url])

        print(f"📄 已生成: {csv_path}")


if __name__ == "__main__":
    process()