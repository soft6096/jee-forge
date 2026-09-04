#!/usr/bin/env bash
# =============================================================================
# jee-forge 技能分发安装脚本
#
# 作用：把本仓库 skill/ 下的 8 个 Agent Skill 分发安装到本机已检测到的
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
# =============================================================================
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_ROOT="$REPO_DIR/skill"

# 各工具 -> 技能目录（按需增补；目录不存在则自动跳过）
declare -A TOOL_DIRS=(
  [claude]="$HOME/.claude/skills"
  [codebuddy]="$HOME/.codebuddy/skills"
  [opencode]="$HOME/.agents/skills"
  [codex]="$HOME/.agents/skills"   # opencode / Codex 共用 ~/.agents/skills
)

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
      if [[ "$1" == "all" ]]; then TOOLS=("${!TOOL_DIRS[@]}")
      elif [[ -n "${TOOL_DIRS[$1]+x}" ]]; then TOOLS+=("$1")
      else warn "未知工具: $1（可选：${!TOOL_DIRS[*]}）"; exit 2; fi
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
  for t in "${!TOOL_DIRS[@]}"; do
    [[ -d "${TOOL_DIRS[$t]}" ]] && TOOLS+=("$t")
  done
fi

declare -A SEEN
TARGETS=()
for t in "${TOOLS[@]}"; do
  dir="${TOOL_DIRS[$t]}"
  if [[ -z "${SEEN[$dir]+x}" ]]; then
    SEEN[$dir]=1
    TARGETS+=("$dir|$t")
  fi
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
