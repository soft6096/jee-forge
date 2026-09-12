#!/usr/bin/env bash
# =============================================================================
# jee-forge 技能分发安装脚本
#
# 作用：把本仓库 skill/ 下的 9 个 Agent Skill 分发安装到本机已检测到的
#       Agent 技能目录，供不同编程 Agent（Claude Code / opencode / Codex /
#       CodeBuddy 等）使用。
#
# 用法：
#   ./install.sh                # 自动检测所有已存在的技能目录并安装
#   ./install.sh --tool claude  # 只装到指定工具的技能目录
#   ./install.sh --tool all     # 同上默认，遍历全部已知目标
#   ./install.sh --list         # 只列出将要安装到的目标，不实际安装
#   ./install.sh --force        # 目标目录已存在时：备份后覆盖（默认跳过）
#
# 说明：
#   - 主流工具对技能目录的识别规则不同：
#       opencode/Codex 支持整仓 clone 后识别 skill/<name> 嵌套（无需本脚本）；
#       Claude Code 类工具通常只识别 ~/.claude/skills/<name>/SKILL.md 一级目录。
#     本脚本为后者（及不想整仓 clone 的用户）提供一键分发。
#   - 不依赖 symlink（部分工具不跟随软链，已验证会漏识别）。
#   - 兼容 bash 3.2（macOS 自带）：不使用关联数组（declare -A）等 bash 4+ 特性。
# =============================================================================
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_ROOT="$REPO_DIR/skill"

# 各工具 -> 技能目录（按需增补；目录不存在则自动跳过）
# 用函数 + case 做映射，避免 bash 4+ 的关联数组（详见文件头"兼容 bash 3.2"说明）
ALL_TOOLS=(claude codebuddy opencode codex)

tool_dir() {
  case "$1" in
    claude)    printf '%s' "$HOME/.claude/skills" ;;
    codebuddy) printf '%s' "$HOME/.codebuddy/skills" ;;
    opencode)  printf '%s' "$HOME/.agents/skills" ;;
    codex)     printf '%s' "$HOME/.agents/skills" ;;   # opencode / Codex 共用 ~/.agents/skills
    *)         return 1 ;;
  esac
}

TOOLS=()
LIST_ONLY=0
FORCE=0

log()  { printf '[install] %s\n' "$*"; }
warn() { printf '[install][warn] %s\n' "$*" >&2; }

# ---- 解析参数 --------------------------------------------------------------
while [[ $# -gt 0 ]]; do
  case "$1" in
    --tool)
      shift
      if [[ -z "${1:-}" ]]; then warn "--tool 需要一个值（all|claude|opencode|codex|codebuddy）"; exit 2; fi
      if [[ "$1" == "all" ]]; then TOOLS=("${ALL_TOOLS[@]}")
      elif tool_dir "$1" >/dev/null 2>&1; then TOOLS+=("$1")
      else warn "未知工具: $1（可选：claude codebuddy opencode codex）"; exit 2; fi
      ;;
    --list) LIST_ONLY=1 ;;
    --force) FORCE=1 ;;
    -h|--help) grep '^#' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) warn "未知参数: $1（--help 查看用法）"; exit 2 ;;
  esac
  shift
done

# ---- 解析最终安装目标目录（去重、过滤不存在的目录）-------------------------
if [[ ${#TOOLS[@]} -eq 0 ]]; then
  for t in "${ALL_TOOLS[@]}"; do
    d="$(tool_dir "$t")"
    [[ -d "$d" ]] && TOOLS+=("$t")
  done
fi

SEEN=""
TARGETS=()
for t in "${TOOLS[@]}"; do
  dir="$(tool_dir "$t")"
  case "|$SEEN|" in
    *"|$dir|"*) ;;                                    # 该目录已登记 → 去重跳过
    *) SEEN="$SEEN|$dir"; TARGETS+=("$dir|$t") ;;
  esac
done

if [[ ${#TARGETS[@]} -eq 0 ]]; then
  warn "未检测到任何已知 Agent 技能目录。可手动指定：./install.sh --tool claude"
  exit 1
fi

log "将处理以下技能目录："
for entry in "${TARGETS[@]}"; do
  dir="${entry%%|*}"; tool="${entry##*|}"
  log "  - [${tool}] ${dir}"
done
[[ $LIST_ONLY -eq 1 ]] && { log "--list：仅列出，未安装。"; exit 0; }

# ---- 分发安装 ---------------------------------------------------------------
installed=0
skipped=0
for entry in "${TARGETS[@]}"; do
  dir="${entry%%|*}"
  [[ -d "$dir" ]] || mkdir -p "$dir"
  for skill in "$SKILL_ROOT"/*/; do
    [[ -d "$skill" ]] || continue
    name="$(basename "$skill")"
    dest="$dir/$name"

    if [[ -e "$dest" ]]; then
      if [[ $FORCE -eq 1 ]]; then
        backup="$dest.pre-jee-forge-$(date +%Y%m%d%H%M%S)"
        mv "$dest" "$backup"
        warn "已存在 ${dest}，--force 备份为 ${backup} 后覆盖"
      else
        warn "跳过：${dest} 已存在（若为旧独立安装，请备份后删除，或加 --force）"
        skipped=$((skipped+1))
        continue
      fi
    fi

    cp -R "$skill" "$dest"
    log "已安装 ${name} -> ${dest}"
    installed=$((installed+1))
  done
done

log "完成：新装 ${installed} 个技能，跳过 ${skipped} 个。"
if [[ $skipped -gt 0 ]]; then
  log "提示：若目的是升级旧副本，请先确认旧副本已备份再执行 ./install.sh --force"
fi
exit 0
