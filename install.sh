#!/usr/bin/env bash
# =============================================================================
# jee-forge 技能分发安装脚本
#
# 作用：把技能分发安装到本机已检测到的 Agent 技能目录，供不同编程 Agent
#       （Claude Code / opencode / Codex / CodeBuddy 等）使用。
#
# 【安装来源约定】本脚本**只从远端仓库安装**，不接受本地目录作为来源：
#       安装内容 = 远端指定 ref 的快照，本地工作区改了什么一律不影响安装结果。
#       因此「改完 → 提交并推送 → 再安装」是唯一路径，可避免装到未提交的半成品。
#
# 用法：
#   ./install.sh                       # 从 GitHub main 安装（默认）
#   ./install.sh --repo <git 地址>      # 直接指定任意 git 地址（也可只写 github 用顶部配置）
#   ./install.sh --repo https://...git # 直接指定任意 git 地址
#   ./install.sh --ref v1.2.0          # 指定分支 / 标签 / 提交号（默认 main）
#   ./install.sh --tool codebuddy      # 只装到指定工具的技能目录
#   ./install.sh --tool all            # 遍历全部已知目标（默认行为）
#   ./install.sh --list                # 只列出将要安装的目标与远端来源，不实际安装
#   ./install.sh --force               # 目标已存在时：备份后覆盖（默认跳过）
#   ./install.sh --no-prune            # 关闭备份自动清理（默认只保留最近 1 个批次，其余自动删除）
#   ./install.sh --link                # 链接模式：clone/更新安装副本 + 写安装回执 + 在技能目录建软链 + 分发全局规则
#
# 全局规则分发：无论 --link 还是拷贝模式，安装时都会把仓内真源 global-rules.md（「需要用户裁决
#       时必须给出 AI 推荐项」的全局行为规则）以受管块（`# BEGIN/END jee-forge::global-rules`）追加到
#       各 Agent 的全局指令文件（~/.claude/CLAUDE.md、~/.agents/AGENTS.md、~/.codex/AGENTS.md、
#       ~/.trae/AGENTS.md、~/.hermes/AGENTS.md、~/.qoder/AGENTS.md）；仅对配置目录已存在的 Agent 写入，
#       不新建目录。幂等：重跑整块替换、不叠加；不改动文件其它内容。--list 仅预览将写哪些文件。
#
# 说明：
#   - --link（链接模式）：只从远端 clone/更新一份安装副本到 ~/.agents/repos/jee-forge，
#     在该副本根写 .jee-forge-origin 安装回执（git 源 / ref / commit / 提交时间 / 安装时间），
#     再把 skill/<name> 以**软链**方式挂到各 Agent 技能目录。默认覆盖：
#       共享源 ~/.agents/skills（opencode / Codex / CodeBuddy 用）、以及本机已存在的
#       ~/.claude/skills、~/.trae/skills、~/.hermes/skills；
#     不含 ~/.codebuddy/skills（其实测原生读 ~/.agents/skills，无需软链；需要时用 --tool codebuddy 显式指定）。
#     更新 = 重跑 ./install.sh --link（内部 fetch + checkout，零拷贝、无备份残留）。
#     判断"源 vs 安装产物"：技能目录里是指向 ~/.agents/repos/jee-forge/skill/<name> 的软链、
#     且副本根有 .jee-forge-origin = 安装产物。
#   - 主流工具对技能目录的识别规则不同：
#       opencode/Codex 支持整仓 clone 后识别 skill/<name> 嵌套（无需本脚本）；
#       Claude Code 类工具通常只识别 ~/.claude/skills/<name>/SKILL.md 一级目录。
#     本脚本为后者（及不想整仓 clone 的用户）提供一键分发。
#   - 拷贝模式（默认）不依赖 symlink（部分工具不跟随软链，已验证会漏识别）；
#     --link 模式使用软链分发（本机实测 CodeBuddy / opencode / Trae / Claude / Hermes 均可跟随，
#     其中 opencode / CodeBuddy 原生读 ~/.agents/skills，不依赖链接）。
#   - 兼容 bash 3.2（macOS 自带）：不使用关联数组（declare -A）等 bash 4+ 特性。
#   - --force 覆盖前把旧目录备份为 <name>.pre-jee-forge-<14 位时间戳>；安装完成后自动清理旧备份，
#     每个技能目录只保留最近 KEEP_BACKUP_BATCHES（默认 1）个批次，其余批次自动删除
#     （同一次运行共用同一时间戳 = 同一批次；--no-prune 可关闭，--list 只预览不删除）。
# =============================================================================
set -euo pipefail

# ---- 远端源（唯一允许的安装来源）-------------------------------------------
# 改这里即可切换默认来源；也可用 --repo / --repo <git 地址> 在命令行覆盖。
REMOTE_GITHUB="https://github.com/soft6096/jee-forge.git"   # 默认来源（GitHub 开源仓库）
DEFAULT_REPO="github"                  # 默认来源标识：github
DEFAULT_REF="main"                     # 默认拉取的分支/标签/提交
KEEP_BACKUP_BATCHES=1                  # 自动清理：每个技能目录只保留最近 N 个备份批次（0 = 保留全部）
LINK_REPO_DIR="${JEE_FORGE_LINK_DIR:-$HOME/.agents/repos/jee-forge}"   # --link 模式安装副本位置（环境变量可覆盖）

# 各工具 -> 技能目录（按需增补；目录不存在则自动跳过）
# 用函数 + case 做映射，避免 bash 4+ 的关联数组（详见文件头"兼容 bash 3.2"说明）
ALL_TOOLS=(claude codebuddy opencode codex)

tool_dir() {
  case "$1" in
    claude)    printf '%s' "$HOME/.claude/skills" ;;
    codebuddy) printf '%s' "$HOME/.codebuddy/skills" ;;
    opencode)  printf '%s' "$HOME/.agents/skills" ;;
    codex)     printf '%s' "$HOME/.agents/skills" ;;   # opencode / Codex 共用 ~/.agents/skills
    trae)      printf '%s' "$HOME/.trae/skills" ;;     # 仅可显式 --tool trae 指定（不在 ALL_TOOLS 默认列表）
    hermes)    printf '%s' "$HOME/.hermes/skills" ;;   # 仅可显式 --tool hermes 指定（同上）
    *)         return 1 ;;
  esac
}

# 各工具 -> 全局指令文件（always-on 规则入口，用于分发「全局裁决推荐规则」）
# 与技能目录不同：这里写的是「Agent 每次都读的全局说明文件」，不是技能。
# 只有当该文件的父目录（= 该 Agent 的配置目录）已存在才写入；父目录不存在 = 该 Agent 未安装，跳过、不新建。
global_file_for() {
  case "$1" in
    claude)    printf '%s' "$HOME/.claude/CLAUDE.md" ;;
    codex)     printf '%s' "$HOME/.codex/AGENTS.md" ;;
    opencode)  printf '%s' "$HOME/.agents/AGENTS.md" ;;   # opencode / CodeBuddy / Codex 共享 hub 目录 ~/.agents
    codebuddy) printf '%s' "$HOME/.agents/AGENTS.md" ;;
    trae)      printf '%s' "$HOME/.trae/AGENTS.md" ;;
    hermes)    printf '%s' "$HOME/.hermes/AGENTS.md" ;;
    qoder)     printf '%s' "$HOME/.qoder/AGENTS.md" ;;
    *)         return 1 ;;
  esac
}

# 需要分发全局规则的 Agent 清单（与 global_file_for 对应；Qoder 另有记忆机制，这里也尽力写一份）
GLOBAL_RULE_TOOLS=(claude codex opencode trae hermes qoder)
GLOBAL_RULE_BEGIN_MARK="# BEGIN jee-forge::global-rules"
GLOBAL_RULE_END_MARK="# END jee-forge::global-rules"

# 分发「全局裁决推荐规则」：把真源 global-rules.md 以受管块写入/更新各 Agent 全局指令文件。
# 幂等：先删同名旧块（BEGIN..END 之间），再追加新块；重复运行不会叠加。--dry 只预览。
# 用法：install_global_rules <global-rules.md 路径> <dry 0|1>
install_global_rules() {
  local src="$1" dry="${2:-0}"
  if [[ ! -f "$src" ]]; then
    warn "未找到全局规则源 ${src}，跳过全局规则分发"
    return 0
  fi
  local t gf parent changed=0
  for t in "${GLOBAL_RULE_TOOLS[@]}"; do
    gf="$(global_file_for "$t" 2>/dev/null)" || continue
    [[ -n "$gf" ]] || continue
    parent="$(dirname "$gf")"
    [[ -d "$parent" ]] || continue          # 该 Agent 配置目录不存在 → 未安装，跳过、不新建
    if [[ "$dry" = "1" ]]; then
      log "全局规则（预览）：将更新 ${gf} [${t}]"
      changed=1
      continue
    fi
    # 1) 去掉旧受管块（BEGIN..END 含两端一并删除），保留其余内容
    if [[ -f "$gf" ]]; then
      if awk -v b="$GLOBAL_RULE_BEGIN_MARK" -v e="$GLOBAL_RULE_END_MARK" \
           'index($0,b){skip=1} !skip{print} index($0,e){skip=0}' "$gf" > "$gf.tmp.$$"; then
        cat "$gf.tmp.$$" > "$gf"; rm -f "$gf.tmp.$$"
      else
        rm -f "$gf.tmp.$$"; warn "全局规则：处理 ${gf} 失败，跳过"
        continue
      fi
    fi
    # 2) 追加新受管块
    {
      printf '\n%s\n' "$GLOBAL_RULE_BEGIN_MARK"
      cat "$src"
      printf '%s\n' "$GLOBAL_RULE_END_MARK"
    } >> "$gf"
    log "已分发全局规则 -> ${gf} [${t}]"
    changed=1
  done
  [[ "$changed" = "1" ]] || log "全局规则：本机未检测到已知 Agent 的全局配置目录，未分发"
}

TOOLS=()
LIST_ONLY=0
FORCE=0
PRUNE=1
LINK=0
REPO_SEL="$DEFAULT_REPO"
REF="$DEFAULT_REF"

log()  { printf '[install] %s\n' "$*"; }
warn() { printf '[install][warn] %s\n' "$*" >&2; }
die()  { printf '[install][error] %s\n' "$*" >&2; exit 1; }

# ---- 备份批次清理 -----------------------------------------------------------
# 批次定义：同一时间戳后缀 `*.pre-jee-forge-<14 位数字>` 记为一个批次。
# 保留最近 KEEP_BACKUP_BATCHES 个批次，其余批次目录**逐个删除**。
# 用法：prune_backups <目标技能目录> <dry_run 0|1>；dry_run=1 只打印预览、绝不删除。
prune_backups() {
  local dir="$1" dry="${2:-0}"
  local ts name path parent i
  local -a all_ts keep_ts
  all_ts=(); keep_ts=()

  # 1) 收集该目录下的备份批次时间戳：严格 14 位纯数字 + 父目录即本目标目录 + 确为目录
  all_ts=($(find "$dir" -maxdepth 1 -mindepth 1 -type d -name '*.pre-jee-forge-*' 2>/dev/null \
    | while IFS= read -r path; do
        name="$(basename "$path")"
        parent="$(dirname "$path")"
        [ "$parent" = "$dir" ] || continue
        [ -d "$path" ] || continue
        printf '%s' "${name##*.pre-jee-forge-}" | grep -Eq '^[0-9]{14}$' || continue
        printf '%s\n' "${name##*.pre-jee-forge-}"
      done | sort -u -r || true))

  if [ "${#all_ts[@]}" -eq 0 ]; then
    log "备份清理：${dir} —— 无备份批次，未清理"
    return 0
  fi

  # 2) KEEP_BACKUP_BATCHES=0 视为「不清理（保留全部）」，不是「全删」
  if [ "$KEEP_BACKUP_BATCHES" -eq 0 ]; then
    log "备份清理：${dir} —— KEEP_BACKUP_BATCHES=0，保留全部 ${#all_ts[@]} 批（未清理）"
    return 0
  fi

  # 3) 倒序列表前 KEEP_BACKUP_BATCHES 个为保留批次，其余为待删批次
  i=0
  local -a drop_ts
  drop_ts=()
  for ts in "${all_ts[@]}"; do
    i=$((i + 1))
    if [ "$i" -le "$KEEP_BACKUP_BATCHES" ]; then keep_ts+=("$ts"); else drop_ts+=("$ts"); fi
  done

  # 4) 逐个目录执行（dry_run=1 时只预览）；删除前三道安全守卫全部满足才动手
  # 注意：bash 3.2 + set -u 下空数组 `"${drop_ts[@]}"` 会报 unbound variable，故先判空再遍历
  local del_cnt=0
  if [ "${#drop_ts[@]}" -eq 0 ]; then
    if [ "$dry" = "1" ]; then
      log "备份清理（--list 预览，未删除）：${dir} —— 将保留 ${#keep_ts[@]} 批 / 将删除 0 个"
    else
      log "备份清理：${dir} —— 保留 ${#keep_ts[@]} 批 / 删除 0 个"
    fi
    return 0
  fi
  for ts in "${drop_ts[@]}"; do
    while IFS= read -r path; do
      [ -n "$path" ] || continue
      name="$(basename "$path")"
      parent="$(dirname "$path")"
      [ "$parent" = "$dir" ] || continue                                    # 守卫：父目录必须是目标技能目录
      [ -d "$path" ] || continue                                           # 守卫：必须是目录
      printf '%s' "${name##*.pre-jee-forge-}" | grep -Eq '^[0-9]{14}$' || continue   # 守卫：后缀必须 14 位纯数字
      if [ "$dry" = "1" ]; then
        log "备份清理（预览）：将删除 ${path}"
      else
        rm -rf "$path"
        log "备份清理：已删除 ${path}"
      fi
      del_cnt=$((del_cnt + 1))
    done < <(find "$dir" -maxdepth 1 -mindepth 1 -type d -name "*.pre-jee-forge-${ts}" 2>/dev/null || true)
  done

  if [ "$dry" = "1" ]; then
    log "备份清理（--list 预览，未删除）：${dir} —— 将保留 ${#keep_ts[@]} 批 / 将删除 ${del_cnt} 个"
  else
    log "备份清理：${dir} —— 保留 ${#keep_ts[@]} 批 / 删除 ${del_cnt} 个"
  fi
}

# ---- 解析参数 --------------------------------------------------------------
while [[ $# -gt 0 ]]; do
  case "$1" in
    --tool)
      shift
      if [[ -z "${1:-}" ]]; then warn "--tool 需要一个值（all|claude|opencode|codex|codebuddy|trae|hermes）"; exit 2; fi
      if [[ "$1" == "all" ]]; then TOOLS=("${ALL_TOOLS[@]}")
      elif tool_dir "$1" >/dev/null 2>&1; then TOOLS+=("$1")
      else warn "未知工具: $1（可选：claude codebuddy opencode codex trae hermes）"; exit 2; fi
      ;;
    --repo)
      shift
      if [[ -z "${1:-}" ]]; then warn "--repo 需要一个值（github|<git 地址>）"; exit 2; fi
      REPO_SEL="$1"
      ;;
    --ref)
      shift
      if [[ -z "${1:-}" ]]; then warn "--ref 需要一个值（分支/标签/提交号，默认 ${DEFAULT_REF}）"; exit 2; fi
      REF="$1"
      ;;
    --list) LIST_ONLY=1 ;;
    --link) LINK=1 ;;
    --force) FORCE=1 ;;
    --no-prune) PRUNE=0 ;;
    -h|--help) grep '^#' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) warn "未知参数: $1（--help 查看用法）"; exit 2 ;;
  esac
  shift
done

# 配置健壮性：KEEP_BACKUP_BATCHES 只接受非负整数，非法值回退默认（避免 set -e 下算术报错）
case "$KEEP_BACKUP_BATCHES" in
  ''|*[!0-9]*) warn "KEEP_BACKUP_BATCHES 配置非法（${KEEP_BACKUP_BATCHES}），回退为 1"; KEEP_BACKUP_BATCHES=1 ;;
esac

# ---- 解析安装来源地址 -------------------------------------------------------
case "$REPO_SEL" in
  github)  REMOTE_URL="$REMOTE_GITHUB" ;;
  http*|https*|git@*|ssh*) REMOTE_URL="$REPO_SEL" ;;
  *) die "无法识别的 --repo 取值：${REPO_SEL}（可选 github / 完整 git 地址）" ;;
esac

if [[ -z "$REMOTE_URL" ]]; then
  die "未配置安装来源：请先编辑本脚本顶部的 REMOTE_GITHUB，或改用
        ./install.sh --repo <完整 git 地址>"
fi

# ---- 解析最终安装目标目录（去重、过滤不存在的目录）-------------------------
if [[ ${#TOOLS[@]} -eq 0 ]]; then
  if [[ $LINK -eq 1 ]]; then
    # 链接模式默认覆盖：共享源（始终包含，opencode/Codex/CodeBuddy 读它）
    # + 本机已存在的 claude / trae / hermes 目录。
    # 不含 codebuddy：其实测原生读 ~/.agents/skills，无需软链（需要时 --tool codebuddy 显式指定）。
    TOOLS=(opencode)
    for t in claude trae hermes; do
      d="$(tool_dir "$t")"
      [[ -d "$d" ]] && TOOLS+=("$t")
    done
  else
    for t in "${ALL_TOOLS[@]}"; do
      d="$(tool_dir "$t")"
      [[ -d "$d" ]] && TOOLS+=("$t")
    done
  fi
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

log "安装来源：${REMOTE_URL}  (ref=${REF})"
log "将处理以下技能目录："
for entry in "${TARGETS[@]}"; do
  dir="${entry%%|*}"; tool="${entry##*|}"
  log "  - [${tool}] ${dir}"
done
if [[ $LIST_ONLY -eq 1 ]]; then
  # --list 也对备份清理做只读预览（只打印将保留/将删除的批次数，不删任何东西）
  for entry in "${TARGETS[@]}"; do
    dir="${entry%%|*}"
    if [[ $PRUNE -eq 1 ]]; then
      prune_backups "$dir" 1
    else
      log "备份清理：${dir} —— 已按 --no-prune 跳过（保留全部备份）"
    fi
  done
  # 全局规则分发预览（不写盘）：用本脚本所在仓的 global-rules.md 列出将更新的各 Agent 全局文件
  LOCAL_ROOT="$(cd "$(dirname "$0")" 2>/dev/null && pwd || true)"
  [[ -n "$LOCAL_ROOT" ]] && install_global_rules "$LOCAL_ROOT/global-rules.md" 1
  log "--list：仅列出，未安装。"
  exit 0
fi

# ---- 链接模式（--link）：安装副本 + 安装回执 + 软链 ---------------------------
# 与拷贝模式的区别：不做实体拷贝，而是保留一份 git 安装副本，技能目录只放软链，
# 更新时重跑本模式（内部 fetch + checkout），零拷贝、无备份残留。
if [[ $LINK -eq 1 ]]; then
  command -v git >/dev/null 2>&1 || die "未找到 git，无法从远端安装"

  RUN_TS="$(date +%Y%m%d%H%M%S)"

  # 1) 安装副本：不存在则 clone，已是 git 仓库则更新到指定 ref
  if [[ -d "$LINK_REPO_DIR/.git" ]]; then
    log "更新安装副本：${LINK_REPO_DIR}（ref=${REF}）"
    git -C "$LINK_REPO_DIR" fetch -q --depth 1 origin "$REF" \
      || die "从 ${REMOTE_URL} 拉取 ref=${REF} 失败：请检查网络/地址/ref 与访问权限"
    git -C "$LINK_REPO_DIR" checkout -q --force FETCH_HEAD || die "切换到 FETCH_HEAD 失败"
  elif [[ -e "$LINK_REPO_DIR" ]]; then
    die "安装副本路径已存在且不是 git 仓库：${LINK_REPO_DIR}（请先手动处理后再安装）"
  else
    log "克隆安装副本：${REMOTE_URL} -> ${LINK_REPO_DIR}"
    mkdir -p "$(dirname "$LINK_REPO_DIR")"
    git clone -q --depth 1 "$REMOTE_URL" "$LINK_REPO_DIR" \
      || die "clone 失败：请检查网络/地址/访问权限"
    git -C "$LINK_REPO_DIR" fetch -q --depth 1 origin "$REF" \
      || die "从 ${REMOTE_URL} 拉取 ref=${REF} 失败"
    git -C "$LINK_REPO_DIR" checkout -q --force FETCH_HEAD || die "切换到 FETCH_HEAD 失败"
  fi

  LINK_SKILL_ROOT="$LINK_REPO_DIR/skill"
  [[ -d "$LINK_SKILL_ROOT" ]] || die "安装副本中未找到 skill/ 目录（地址或 ref 可能不对）"

  # 2) 安装回执：该文件存在 = 本目录是 git 远端安装的副本（安装产物），不是开发源
  LINK_COMMIT="$(git -C "$LINK_REPO_DIR" log -1 --format='%H')"
  cat > "$LINK_REPO_DIR/.jee-forge-origin" <<EOF
# jee-forge 安装回执 —— 由 install.sh --link 自动生成，请勿手改
# 本文件存在 = 本目录是从 git 远端安装的副本（安装产物），不是开发源
# 要改技能：改开发源仓库 skill/<name> → commit + push → 重跑 ./install.sh --link
remote=${REMOTE_URL}
ref=${REF}
commit=${LINK_COMMIT}
commit_date=$(git -C "$LINK_REPO_DIR" log -1 --format='%ad' --date=iso)
commit_subject=$(git -C "$LINK_REPO_DIR" log -1 --format='%s')
installed_at=$(date '+%Y-%m-%dT%H:%M:%S%z')
installed_by=$(whoami)@$(hostname)
mode=link
EOF
  log "安装回执：${LINK_REPO_DIR}/.jee-forge-origin（远端快照：$(git -C "$LINK_REPO_DIR" log -1 --format='%h %ad %s' --date=short)）"

  # 3) 软链分发：skill/<name> -> 各目标技能目录/<name>
  linked=0
  skipped=0
  for entry in "${TARGETS[@]}"; do
    dir="${entry%%|*}"
    [[ -d "$dir" ]] || mkdir -p "$dir"
    for skill in "$LINK_SKILL_ROOT"/*/; do
      [[ -d "$skill" ]] || continue
      name="$(basename "$skill")"
      target="${skill%/}"
      dest="$dir/$name"

      if [[ -L "$dest" ]]; then
        # 已是软链时的处理：只认一种合法形态——指向本次安装副本；
        # 指向别处一律提示并跳过（--force 才覆盖），避免静默覆盖同名技能。
        existing="$(readlink "$dest")"
        case "$existing" in
          "$LINK_SKILL_ROOT"/*) rm -f "$dest" ;;
          *)
            if [[ $FORCE -eq 1 ]]; then
              rm -f "$dest"
              warn "覆盖：${dest} 原指向 ${existing}（--force 已改为本次副本）"
            else
              warn "跳过：${dest} 已指向别处 ${existing}"
              warn "      · 同名技能冲突（指向另一个仓库的技能）→ 建议给冲突技能改名；"
              warn "      · 软链形态不统一（如指向 ~/.agents/skills 的中转链）→ 加 --force 重指为直连副本即可。"
              skipped=$((skipped+1))
              continue
            fi
            ;;
        esac
      elif [[ -e "$dest" ]]; then
        if [[ $FORCE -eq 1 ]]; then
          backup="$dest.pre-jee-forge-$RUN_TS"
          mv "$dest" "$backup"
          warn "已存在实体 ${dest}，--force 备份为 ${backup} 后改建软链"
        else
          warn "跳过：${dest} 已存在实体目录（加 --force 可备份后改建软链）"
          skipped=$((skipped+1))
          continue
        fi
      fi

      ln -s "$target" "$dest"
      log "已链接 ${dest} -> ${target}"
      linked=$((linked+1))
    done
  done

  # 全局规则分发：把安装副本里的 global-rules.md 以受管块写入各 Agent 全局指令文件（幂等）
  install_global_rules "$LINK_REPO_DIR/global-rules.md" 0

  log "完成（链接模式）：新建/更新软链 ${linked} 个，跳过 ${skipped} 个（来源 ${REMOTE_URL}@${REF}）。"
  if [[ $skipped -gt 0 ]]; then
    log "提示：若目的是把实体副本换成软链，请加 --force 重跑一次。"
  fi

  for entry in "${TARGETS[@]}"; do
    dir="${entry%%|*}"
    if [[ $PRUNE -eq 1 ]]; then
      prune_backups "$dir" 0
    else
      log "备份清理：${dir} —— 已按 --no-prune 跳过（保留全部备份）"
    fi
  done
  exit 0
fi

# ---- 从远端拉取快照（只认远端，本地工作区不作为来源）-----------------------
command -v git >/dev/null 2>&1 || die "未找到 git，无法从远端安装"

TMP="$(mktemp -d 2>/dev/null || mktemp -d -t jee-forge)"
cleanup() { rm -rf "$TMP"; }
trap cleanup EXIT INT TERM

log "正在从远端拉取 ref=${REF} ..."
git init -q "$TMP/repo"
git -C "$TMP/repo" remote add origin "$REMOTE_URL"
if ! git -C "$TMP/repo" fetch -q --depth 1 origin "$REF"; then
  die "从 ${REMOTE_URL} 拉取 ref=${REF} 失败：请检查网络/地址/ref 是否正确，以及是否有访问权限"
fi
git -C "$TMP/repo" checkout -q FETCH_HEAD

SKILL_ROOT="$TMP/repo/skill"
[[ -d "$SKILL_ROOT" ]] || die "远端快照中未找到 skill/ 目录（地址或 ref 可能不对）"

log "远端快照：$(git -C "$TMP/repo" log -1 --format='%h %ad %s' --date=short)"

# ---- 分发安装 ---------------------------------------------------------------
# 运行级时间戳：同一次安装的全部备份共用一个批次号（循环内不再各取一次 date，
# 否则安装跨秒会让同一次运行的备份得到不同时间戳，按批次清理时会被拆成多批而误删）。
RUN_TS="$(date +%Y%m%d%H%M%S)"
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
        backup="$dest.pre-jee-forge-$RUN_TS"
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

# 全局规则分发（拷贝模式同样）：用刚拉取的远端快照里的 global-rules.md
install_global_rules "$TMP/repo/global-rules.md" 0

log "完成：新装 ${installed} 个技能，跳过 ${skipped} 个（来源 ${REMOTE_URL}@${REF}）。"
if [[ $skipped -gt 0 ]]; then
  log "提示：若目的是升级旧副本，请先确认旧副本已备份再执行 ./install.sh --force"
fi

# ---- 备份批次清理（只保留最近 KEEP_BACKUP_BATCHES 个批次，其余自动删除）----
for entry in "${TARGETS[@]}"; do
  dir="${entry%%|*}"
  if [[ $PRUNE -eq 1 ]]; then
    prune_backups "$dir" 0
  else
    log "备份清理：${dir} —— 已按 --no-prune 跳过（保留全部备份）"
  fi
done

# ---- 多 Agent 环境引导（只提示，不改变默认行为）-----------------------------
# 检测原则：本机存在 >=2 个已知 Agent 技能目录 = 多 Agent 混用环境，
# 此时同一技能会出现多份实体副本，提示可改用 --link 形态（一份副本 + 软链共享）。
# 这里只打印提示，绝不自动切换模式（软链是否被跟随因工具而异，需使用者自行确认）。
hint_cnt=0
for t in "${ALL_TOOLS[@]}" trae hermes; do
  d="$(tool_dir "$t" 2>/dev/null || true)"
  [[ -n "$d" && -d "$d" ]] && hint_cnt=$((hint_cnt + 1))
done
if [[ $LINK -eq 0 && $hint_cnt -ge 2 ]]; then
  log "提示：本机检测到 ${hint_cnt} 个 Agent 技能目录（多 Agent 混用）。"
  log "      可改用 ./install.sh --link：只保留一份安装副本（含 .jee-forge-origin 回执），"
  log "      各 Agent 目录用软链共享它，更新 = 重跑 --link（零拷贝、无备份残留）。"
  log "      改用前提：你的 Agent 能跟随软链；若某个工具装了却看不到技能，退回本模式即可。"
fi

exit 0
