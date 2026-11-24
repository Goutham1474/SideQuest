/* FitLog front end - vanilla JS, no build step. */

const KIND_META = {
  pushups: { label: "Pushups", unit: "pushups", quick: [5, 10, 25], statLabel: "reps" },
  steps: { label: "Steps", unit: "steps", quick: [500, 1000, 2000], statLabel: "steps" },
};

const KINDS = Object.keys(KIND_META);
const RING_CIRCUMFERENCE = 2 * Math.PI * 44;

const ICONS = {
  flame: `<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M8.5 14.5A2.5 2.5 0 0 0 11 12c0-1.38-.5-2-1-3-1.07-2.14-.22-4.05 2-6 .5 2.5 2 4.9 4 6.5 2 1.6 3 3.5 3 5.5a7 7 0 1 1-14 0c0-1.15.43-2.29 1-3a2.5 2.5 0 0 0 2.5 2.5Z" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round"/></svg>`,
  trash: `<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 7h16M9.5 7V5.5A1.5 1.5 0 0 1 11 4h2a1.5 1.5 0 0 1 1.5 1.5V7M6.5 7l.8 12a2 2 0 0 0 2 1.9h5.4a2 2 0 0 0 2-1.9l.8-12M10 11v6M14 11v6" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"/></svg>`,
  empty: `<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 20h16M7 20v-6M12 20V8M17 20v-9" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/></svg>`,
  check: `<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 12.5l4.5 4.5L19 7.5" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"/></svg>`,
  star: `<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 3.4l2.7 5.5 6.05.88-4.38 4.27 1.04 6.03L12 17.24l-5.41 2.84 1.04-6.03L3.25 9.78l6.05-.88L12 3.4Z" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linejoin="round"/></svg>`,
  medal: `<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="14.5" r="5.5" fill="none" stroke="currentColor" stroke-width="1.7"/><path d="M8.5 9.5 6.5 3h11l-2 6.5M12 12.5v4M10.5 14.5h3" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"/></svg>`,
};

const BADGE_ICONS = {
  spark: '<path d="M12 3.5 14.2 9l5.3 2.2-5.3 2.2L12 19l-2.2-5.6L4.5 11.2 9.8 9 12 3.5Z"/>',
  target: '<circle cx="12" cy="12" r="7.5"/><circle cx="12" cy="12" r="4"/><circle cx="12" cy="12" r="1" fill="currentColor" stroke="none"/>',
  flame: '<path d="M8.5 14.5A2.5 2.5 0 0 0 11 12c0-1.4-.5-2-1-3-1.1-2.1-.2-4 2-6 .5 2.5 2 4.9 4 6.5 2 1.6 3 3.5 3 5.5a7 7 0 1 1-14 0c0-1.2.4-2.3 1-3a2.5 2.5 0 0 0 2.5 2.5Z"/>',
  calendar: '<rect x="3.5" y="5.5" width="17" height="15" rx="2"/><path d="M8 3v4M16 3v4M3.5 10.5h17M8.5 14.5l2 2 4-4"/>',
  mountain: '<path d="M3 19.5h18L14.5 6.5 11 12.5 9.2 9.7 3 19.5Z"/>',
  trophy: '<path d="M8 4h8v5.5a4 4 0 0 1-8 0V4Z"/><path d="M8 6H5v1.5A3.5 3.5 0 0 0 8.5 11M16 6h3v1.5A3.5 3.5 0 0 1 15.5 11M12 13.5V17M9 20h6M10 17h4"/>',
  bolt: '<path d="M13 2.5 5.5 14H11l-1 7.5L17.5 10H12l1-7.5Z"/>',
  footsteps: '<path d="M3 12h3.5l2-5 4.5 10 2-5H21"/>',
  check: '<circle cx="12" cy="12" r="8"/><path d="m8.5 12 2.5 2.5 4.5-5"/>',
  crown: '<path d="M4 18.5h16l-1.4-9-4.1 3.2L12 5l-2.5 7.7-4.1-3.2L4 18.5Z"/>',
  dumbbell: '<path d="M7 8v8M4.5 9.5v5M17 8v8M19.5 9.5v5M7 12h10"/>',
  globe: '<circle cx="12" cy="12" r="8.5"/><path d="M3.5 12h17M12 3.5c2.3 2.5 3.4 5.3 3.4 8.5s-1.1 6-3.4 8.5c-2.3-2.5-3.4-5.3-3.4-8.5S9.7 6 12 3.5Z"/>',
  compass: '<circle cx="12" cy="12" r="8.5"/><path d="m15.5 8.5-2 5-5 2 2-5 5-2Z"/>',
  sun: '<circle cx="12" cy="12" r="4"/><path d="M12 2.5v2M12 19.5v2M4.6 4.6 6 6M18 18l1.4 1.4M2.5 12h2M19.5 12h2M4.6 19.4 6 18M18 6l1.4-1.4"/>',
  moon: '<path d="M20.5 13.2A8.5 8.5 0 1 1 10.8 3.5a6.6 6.6 0 0 0 9.7 9.7Z"/>',
  star: '<path d="M12 3.4l2.7 5.5 6.05.88-4.38 4.27 1.04 6.03L12 17.24l-5.41 2.84 1.04-6.03L3.25 9.78l6.05-.88L12 3.4Z"/>',
  medal: '<circle cx="12" cy="14.5" r="5.5"/><path d="M8.5 9.5 6.5 3h11l-2 6.5M12 12.5v4M10.5 14.5h3"/>',
};

function badgeSvg(key) {
  const paths = BADGE_ICONS[key] || BADGE_ICONS.spark;
  return `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6"
    stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${paths}</svg>`;
}

const view = { days: 14, data: null, cards: {} };

const $ = (selector, root = document) => root.querySelector(selector);
const root = document.documentElement;

const els = {
  cards: $("#cards"),
  charts: $("#charts"),
  log: $("#log"),
  logSub: $("#log-sub"),
  trendSub: $("#trend-sub"),
  pageSub: $("#page-sub"),
  summaryChip: $("#summary-chip"),
  summaryText: $("#summary-text"),
  lifetime: $("#lifetime"),
  rangeSeg: $("#range-seg"),
  settingsBtn: $("#settings-btn"),
  themeBtn: $("#theme-btn"),
  themeMeta: $("#theme-color"),
  dialog: $("#settings-dialog"),
  settingsForm: $("#settings-form"),
  toast: $("#toast"),
  levelNumber: $("#level-number"),
  levelTitle: $("#level-title"),
  levelXp: $("#level-xp"),
  xpFill: $("#xp-fill"),
  xpTrack: $("#xp-track"),
  levelSub: $("#level-sub"),
  statStreak: $("#stat-streak"),
  statBadges: $("#stat-badges"),
  statWeek: $("#stat-week"),
  quests: $("#quests"),
  questsSub: $("#quests-sub"),
  starRow: $("#star-row"),
  weekCount: $("#week-count"),
  weekFill: $("#week-fill"),
  weekHint: $("#week-hint"),
  badges: $("#badges"),
  badgesSub: $("#badges-sub"),
  celebrate: $("#celebrate"),
  celebrateIcon: $("#celebrate-icon"),
  celebrateTitle: $("#celebrate-title"),
  celebrateSub: $("#celebrate-sub"),
};

/* ------------------------------------------------------------------ */
/* Helpers                                                             */
/* ------------------------------------------------------------------ */

const fmt = (n) => Number(n).toLocaleString();

function compact(n) {
  if (n >= 1000000) {
    const value = n / 1000000;
    return `${Number.isInteger(value) ? value : value.toFixed(1)}M`;
  }
  if (n >= 10000) {
    const value = n / 1000;
    return `${Number.isInteger(value) ? value : value.toFixed(1)}K`;
  }
  return fmt(n);
}

function parseDay(value) {
  const [y, m, d] = value.split("-").map(Number);
  return new Date(y, m - 1, d);
}

function longDay(value) {
  return parseDay(value).toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

function shortDay(value, span) {
  const d = parseDay(value);
  return span <= 10
    ? d.toLocaleDateString(undefined, { weekday: "short" })
    : String(d.getDate());
}

function relativeDay(value) {
  const d = parseDay(value);
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const diff = Math.round((today - d) / 86400000);
  if (diff === 0) return "Today";
  if (diff === 1) return "Yesterday";
  return d.toLocaleDateString(undefined, { weekday: "short", month: "short", day: "numeric" });
}

function timeOf(iso) {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  return d.toLocaleTimeString(undefined, { hour: "numeric", minute: "2-digit" });
}

function escapeAttr(value) {
  return String(value).replace(/&/g, "&amp;").replace(/"/g, "&quot;").replace(/</g, "&lt;");
}

let toastTimer = null;
function toast(message, isError = false) {
  els.toast.textContent = message;
  els.toast.classList.toggle("is-error", isError);
  els.toast.classList.add("show");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => els.toast.classList.remove("show"), isError ? 3200 : 2000);
}

async function api(path, options = {}) {
  const init = { method: options.method || "GET", headers: {} };
  if (options.body !== undefined) {
    init.body = options.body;
    init.headers["Content-Type"] = "application/json";
  }
  const res = await fetch(path, init);
  if (res.status === 204) return null;
  let payload = null;
  try {
    payload = await res.json();
  } catch {
    /* non-JSON error page */
  }
  if (!res.ok) {
    throw new Error((payload && payload.error) || `Request failed (${res.status})`);
  }
  return payload;
}

/* ------------------------------------------------------------------ */
/* Theme                                                               */
/* ------------------------------------------------------------------ */

function applyTheme(theme, persist = true) {
  root.dataset.theme = theme;
  if (persist) {
    try {
      localStorage.setItem("fitlog-theme", theme);
    } catch {
      /* private mode */
    }
  }
  if (els.themeMeta) {
    els.themeMeta.setAttribute("content", theme === "light" ? "#f5f6f8" : "#0a0d12");
  }
  const label = theme === "dark" ? "Switch to light theme" : "Switch to dark theme";
  els.themeBtn.setAttribute("aria-label", label);
  els.themeBtn.title = label;
}

els.themeBtn.addEventListener("click", () => {
  applyTheme(root.dataset.theme === "dark" ? "light" : "dark");
});

/* ------------------------------------------------------------------ */
/* Cards                                                              */
/* ------------------------------------------------------------------ */

function buildCard(kind) {
  const meta = KIND_META[kind];
  const card = document.createElement("article");
  card.className = `card card--${kind}`;
  card.dataset.kind = kind;
  card.innerHTML = `
    <div class="card-head">
      <span class="dot dot--${kind}" aria-hidden="true"></span>
      <h2>${meta.label}</h2>
      <span class="streak-chip is-zero" title="No streak yet">
        ${ICONS.flame}
        <span class="streak-value">0d</span>
      </span>
    </div>
    <div class="card-body">
      <div class="ring" aria-hidden="true">
        <svg viewBox="0 0 100 100">
          <circle class="ring-track" cx="50" cy="50" r="44"></circle>
          <circle class="ring-fill" cx="50" cy="50" r="44"></circle>
        </svg>
        <div class="ring-center">
          <span class="ring-value">0%</span>
          <span class="ring-label">of goal</span>
        </div>
      </div>
      <div class="card-info">
        <div class="figure">
          <span class="value">0</span>
          <span class="goal">/ 0</span>
        </div>
        <p class="status"></p>
        <div class="quick">
          ${meta.quick
            .map(
              (n) =>
                `<button type="button" class="chip" data-add="${n}" aria-label="Add ${fmt(n)} ${meta.unit}">+${fmt(n)}</button>`
            )
            .join("")}
        </div>
        <form class="custom">
          <input type="number" inputmode="numeric" min="1" max="200000" step="1"
                 placeholder="Custom amount" aria-label="Custom ${meta.label.toLowerCase()} amount">
          <button type="submit" class="btn btn-secondary btn-sm">Add</button>
        </form>
      </div>
    </div>
    <div class="card-stats">
      <div class="stat"><span>7-day avg</span><b data-stat="avg">0</b></div>
      <div class="stat"><span>Best day</span><b data-stat="best">0</b></div>
      <div class="stat"><span>At goal</span><b data-stat="met">0 / 0</b></div>
    </div>`;
  return card;
}

function renderCards() {
  if (!view.data) return;
  for (const kind of KINDS) {
    if (!view.cards[kind]) {
      view.cards[kind] = buildCard(kind);
      els.cards.appendChild(view.cards[kind]);
    }
    updateCard(kind);
  }
}

function updateCard(kind) {
  const card = view.cards[kind];
  const meta = KIND_META[kind];
  const value = view.data.totals[kind].today;
  const goal = view.data.goals[kind];
  const streak = view.data.streaks[kind];
  const totals = view.data.totals[kind];
  const diff = value - goal;
  const done = diff >= 0;

  const progress = goal > 0 ? Math.min(1, value / goal) : 0;
  $(".ring-fill", card).style.strokeDashoffset = String(RING_CIRCUMFERENCE * (1 - progress));
  $(".ring-value", card).textContent = `${Math.min(100, Math.round(progress * 100))}%`;
  $(".ring-label", card).textContent = done ? "complete" : "of goal";

  $(".figure .value", card).textContent = fmt(value);
  $(".figure .goal", card).textContent = `/ ${fmt(goal)}`;

  const status = $(".status", card);
  status.textContent = done
    ? diff === 0
      ? "Daily goal met"
      : `Goal met · ${fmt(diff)} over`
    : `${fmt(-diff)} ${meta.unit} to go`;
  status.classList.toggle("is-done", done);

  const badge = $(".streak-chip", card);
  $(".streak-value", badge).textContent = `${streak}d`;
  badge.classList.toggle("is-zero", streak === 0);
  badge.title = streak === 0 ? "No streak yet" : `${streak} day${streak === 1 ? "" : "s"} at goal`;

  const recent = view.data.days.slice(-7);
  const avg = recent.length
    ? Math.round(recent.reduce((sum, day) => sum + day[kind], 0) / recent.length)
    : 0;

  $('[data-stat="avg"]', card).textContent = fmt(avg);
  $('[data-stat="best"]', card).textContent = fmt(totals.best);
  $('[data-stat="met"]', card).textContent = `${totals.daysMet} / ${view.data.days.length}`;

  card.classList.toggle("is-complete", done);
}

/* ------------------------------------------------------------------ */
/* Charts                                                            */
/* ------------------------------------------------------------------ */

function chartBlock(kind) {
  const meta = KIND_META[kind];
  const data = view.data;
  const goal = data.goals[kind];
  const series = data.days;
  const values = series.map((day) => day[kind]);
  const scale = Math.max(goal, ...values, 1) * 1.08;
  const empty = values.every((value) => value === 0);
  const labelEvery = Math.ceil(series.length / 6);
  const lastIndex = series.length - 1;

  const bars = series
    .map((day) => {
      const value = day[kind];
      const height = value > 0 ? Math.max(2, Math.min(100, (value / scale) * 100)) : 0;
      const tip = `${longDay(day.day)} · ${fmt(value)}`;
      return `<div class="bar-wrap" title="${escapeAttr(`${longDay(day.day)}: ${fmt(value)} ${meta.unit}`)}">
          <div class="bar${value >= goal ? " is-met" : ""}" style="height:${height.toFixed(2)}%" data-tip="${escapeAttr(tip)}"></div>
        </div>`;
    })
    .join("");

  const labels = series
    .map((day, index) => {
      const show = index === 0 || index === lastIndex || index % labelEvery === 0;
      const classes = ["", index === lastIndex ? "is-today" : ""].join(" ").trim();
      const text = show ? shortDay(day.day, series.length) : "";
      return `<span${classes ? ` class="${classes}"` : ""}>${text}</span>`;
    })
    .join("");

  const totals = data.totals[kind];
  const goalPct = Math.min(100, (goal / scale) * 100);

  return `<div class="chart-block chart-block--${kind}">
      <div class="chart-head">
        <span class="chart-name"><span class="dot" aria-hidden="true"></span>${meta.label}</span>
        <span class="chart-goal">Goal ${fmt(goal)}</span>
        <span class="chart-total">${fmt(totals.range)}<em>total</em></span>
      </div>
      <div class="chart${empty ? " is-empty" : ""}"
           role="img"
           aria-label="${meta.label}, ${fmt(totals.range)} total over the last ${series.length} days">
        <div class="bars">${bars}</div>
        <div class="goal-line" style="bottom:${goalPct.toFixed(2)}%"></div>
        ${empty ? '<p class="chart-empty">No activity in this range</p>' : ""}
      </div>
      <div class="x-labels">${labels}</div>
      <div class="chart-foot">
        <span>Avg/day <b>${fmt(Math.round(totals.avg))}</b></span>
        <span>Best <b>${fmt(totals.best)}</b></span>
        <span><b>${totals.daysMet}/${series.length}</b> at goal</span>
      </div>
    </div>`;
}

function renderCharts() {
  if (!view.data) return;
  els.charts.innerHTML = KINDS.map(chartBlock).join("");
  els.trendSub.textContent = `Daily totals · last ${view.days} days`;
}

/* ------------------------------------------------------------------ */
/* Activity log                                                       */
/* ------------------------------------------------------------------ */

function renderLog() {
  if (!view.data) return;
  const entries = view.data.entries;

  if (!entries.length) {
    els.log.innerHTML = `<div class="empty">
        ${ICONS.empty}
        <p>Nothing logged yet</p>
        <span>Log a set above and it will show up here.</span>
      </div>`;
    els.logSub.textContent = "Nothing logged yet";
    return;
  }

  const groups = [];
  for (const entry of entries) {
    const last = groups[groups.length - 1];
    if (last && last.day === entry.day) last.entries.push(entry);
    else groups.push({ day: entry.day, entries: [entry] });
  }

  els.log.innerHTML = groups
    .map((group) => {
      const count = group.entries.length;
      const rows = group.entries
        .map((entry) => {
          const meta = KIND_META[entry.kind] || { label: entry.kind };
          return `<li class="log-row">
              <span class="dot dot--${entry.kind}" aria-hidden="true"></span>
              <div class="log-main">
                <span class="log-kind">${meta.label}</span>
                <span class="log-time">${timeOf(entry.created_at)}</span>
              </div>
              <span class="log-amount">+${fmt(entry.amount)}</span>
              <button type="button" class="row-del" data-del="${entry.id}"
                      title="Delete entry" aria-label="Delete ${meta.label} entry">${ICONS.trash}</button>
            </li>`;
        })
        .join("");

      return `<section class="log-group">
          <header class="log-day">
            <h3>${relativeDay(group.day)}</h3>
            <span>${count} ${count === 1 ? "entry" : "entries"}</span>
          </header>
          <ul class="log-list">${rows}</ul>
        </section>`;
    })
    .join("");

  els.logSub.textContent = `${entries.length} ${entries.length === 1 ? "entry" : "entries"} · newest first`;
}

function goalsMet() {
  const data = view.data;
  return KINDS.every((kind) => data.totals[kind].today >= data.goals[kind]);
}

function renderSummary() {
  const met = KINDS.filter(
    (kind) => view.data.totals[kind].today >= view.data.goals[kind]
  ).length;
  els.summaryText.textContent = `${met} of ${KINDS.length} goals met`;
  els.summaryChip.classList.toggle("is-success", met === KINDS.length);
}

/* ------------------------------------------------------------------ */
/* Game: level, quests, achievements                                  */
/* ------------------------------------------------------------------ */

function renderLevel() {
  const game = view.data.game;
  els.levelNumber.textContent = String(game.level);
  els.levelTitle.textContent = game.title;
  els.levelXp.textContent = `${fmt(game.xp)} XP`;

  const pct = Math.round(game.progress * 100);
  els.xpFill.style.width = `${pct}%`;
  els.xpTrack.setAttribute("aria-valuenow", String(pct));
  els.levelSub.textContent =
    game.toNext > 0
      ? `${fmt(game.toNext)} XP to level ${game.level + 1}`
      : "Top level reached";

  els.statStreak.textContent = `${fmt(game.streak)} ${game.streak === 1 ? "day" : "days"}`;
  els.statBadges.textContent = `${game.badgesEarned} / ${game.badgesTotal}`;
  els.statWeek.textContent = `${game.week.activeDays} / ${game.week.target} days`;
}

function renderQuests() {
  const game = view.data.game;

  els.quests.innerHTML = game.quests
    .map((quest) => {
      const tone = quest.kind === "bonus" ? "bonus" : quest.kind;
      const pct = quest.progress
        ? Math.min(100, Math.round((quest.progress.current / quest.progress.target) * 100))
        : quest.done
          ? 100
          : 0;
      const track = quest.progress
        ? `<div class="quest-track" aria-hidden="true"><i style="width:${pct}%"></i></div>`
        : "";

      return `<div class="quest quest--${tone}${quest.done ? " is-done" : ""}"
            role="listitem"
            aria-label="${escapeAttr(
              `${quest.label} — ${quest.done ? "complete" : "not complete"}. ${quest.detail}`
            )}">
          <span class="quest-check" aria-hidden="true">${ICONS.check}</span>
          <div class="quest-body">
            <div class="quest-top">
              <span class="quest-label">${quest.label}</span>
              <span class="quest-detail">${quest.detail}</span>
            </div>
            ${track}
          </div>
        </div>`;
    })
    .join("");

  const done = game.questsDone;
  const total = game.quests.length;
  els.questsSub.textContent =
    done === total ? "All quests complete" : `${done} of ${total} complete`;

  els.starRow.innerHTML = game.quests
    .map(
      (quest) =>
        `<svg class="star${quest.done ? " is-on" : ""}" viewBox="0 0 24 24"
              aria-hidden="true">${BADGE_ICONS.star}</svg>`
    )
    .join("");
  els.starRow.setAttribute("aria-label", `${done} of ${total} quests complete`);

  const week = game.week;
  const remaining = Math.max(0, week.target - week.activeDays);
  els.weekCount.textContent = `${week.activeDays} / ${week.target} days`;
  els.weekFill.style.width = `${Math.min(100, (week.activeDays / week.target) * 100)}%`;
  els.weekHint.textContent =
    remaining === 0
      ? "Weekly challenge complete."
      : `${remaining} more active ${remaining === 1 ? "day" : "days"} to go${
          week.goalDays ? ` · ${week.goalDays} at goal` : ""
        }.`;
}

function renderBadges() {
  const game = view.data.game;

  els.badges.innerHTML = game.badges
    .map((badge) => {
      const pct = badge.earned
        ? 100
        : Math.min(100, Math.round((badge.progress.current / badge.progress.target) * 100));
      const meta = badge.earned
        ? badge.tier.charAt(0).toUpperCase() + badge.tier.slice(1)
        : `${compact(badge.progress.current)} / ${compact(badge.progress.target)}`;
      const check = badge.earned
        ? `<span class="badge-check" aria-hidden="true">${ICONS.check}</span>`
        : "";

      return `<article class="badge tier-${badge.tier}${badge.earned ? " is-earned" : ""}"
            role="listitem"
            title="${escapeAttr(`${badge.name} — ${badge.description}`)}"
            aria-label="${escapeAttr(
              `${badge.name} — ${badge.earned ? "unlocked" : "locked"}. ${badge.description}`
            )}">
          <span class="badge-icon" aria-hidden="true">${badgeSvg(badge.icon)}</span>
          ${check}
          <span class="badge-name">${badge.name}</span>
          <span class="badge-meta">${meta}</span>
          <span class="badge-track" aria-hidden="true"><i style="width:${pct}%"></i></span>
        </article>`;
    })
    .join("");

  els.badgesSub.textContent = `${game.badgesEarned} of ${game.badgesTotal} unlocked`;
}

function renderGame() {
  if (!view.data || !view.data.game) return;
  renderLevel();
  renderQuests();
  renderBadges();
}

function renderFooter() {
  const life = view.data.lifetime;
  if (!life.pushups && !life.steps) {
    els.lifetime.textContent = "Lifetime totals will appear here";
    return;
  }
  els.lifetime.textContent = `Lifetime · ${fmt(life.pushups)} pushups · ${fmt(life.steps)} steps`;
}

/* ------------------------------------------------------------------ */
/* Celebrations                                                        */
/* ------------------------------------------------------------------ */

function snapshot() {
  if (!view.data || !view.data.game) return null;
  const game = view.data.game;
  return {
    xp: game.xp,
    level: game.level,
    questsDone: game.questsDone,
    goalsMet: goalsMet(),
    badges: new Set(game.badges.filter((badge) => badge.earned).map((badge) => badge.id)),
  };
}

const celebrationQueue = [];
let celebrationTimer = null;

function checkCelebrations(before) {
  if (!before) return;
  const game = view.data.game;
  const events = [];

  if (game.level > before.level) {
    events.push({
      icon: "medal",
      title: `Level ${game.level} · ${game.title}`,
      sub: `${fmt(game.xp - before.xp)} XP earned in that session.`,
    });
  }

  const unlocked = game.badges.filter(
    (badge) => badge.earned && !before.badges.has(badge.id)
  );
  if (unlocked.length === 1) {
    events.push({
      icon: unlocked[0].icon,
      title: `${unlocked[0].name} unlocked`,
      sub: unlocked[0].description,
    });
  } else if (unlocked.length > 1) {
    events.push({
      icon: unlocked[0].icon,
      title: `${unlocked.length} achievements unlocked`,
      sub: unlocked.map((badge) => badge.name).join(" · "),
    });
  }

  if (goalsMet() && !before.goalsMet) {
    events.push({
      icon: "target",
      title: "Daily goals complete",
      sub: "Pushups and steps are both done for today.",
    });
  }

  if (game.questsDone > before.questsDone && !(goalsMet() && !before.goalsMet)) {
    events.push({
      icon: "check",
      title: "Daily quest complete",
      sub: `${game.questsDone} of ${game.quests.length} done today.`,
    });
  }

  if (!events.length) return;
  celebrationQueue.push(...events.slice(0, 2));
  showNextCelebration();
}

function showNextCelebration() {
  if (celebrationTimer || !celebrationQueue.length) return;
  const event = celebrationQueue.shift();

  els.celebrateIcon.innerHTML = badgeSvg(event.icon);
  els.celebrateTitle.textContent = event.title;
  els.celebrateSub.textContent = event.sub;
  els.celebrate.hidden = false;
  burstConfetti();

  celebrationTimer = setTimeout(() => {
    els.celebrate.hidden = true;
    celebrationTimer = null;
    showNextCelebration();
  }, 3200);
}

function burstConfetti() {
  if (!window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
    const colors = ["--pushups", "--steps", "--gold", "--focus"];
    const fragment = document.createDocumentFragment();

    for (let i = 0; i < 30; i += 1) {
      const piece = document.createElement("span");
      const size = 4 + Math.random() * 5;
      piece.className = "confetti";
      piece.style.left = `${4 + Math.random() * 92}vw`;
      piece.style.width = `${size}px`;
      piece.style.height = `${size * (Math.random() > 0.5 ? 1 : 0.55)}px`;
      piece.style.background = `var(${colors[i % colors.length]})`;
      piece.style.opacity = String(0.55 + Math.random() * 0.45);
      piece.style.setProperty("--dx", `${(Math.random() - 0.5) * 140}px`);
      piece.style.setProperty("--rot", `${360 + Math.random() * 540}deg`);
      piece.style.animationDuration = `${1.7 + Math.random() * 0.9}s`;
      piece.style.animationDelay = `${Math.random() * 0.25}s`;
      piece.addEventListener("animationend", () => piece.remove());
      fragment.appendChild(piece);
    }

    document.body.appendChild(fragment);
  }
}

/* ------------------------------------------------------------------ */
/* Data flow                                                          */
/* ------------------------------------------------------------------ */

async function load() {
  try {
    view.data = await api(`/api/state?days=${view.days}`);
    renderCards();
    renderCharts();
    renderLog();
    renderSummary();
    renderGame();
    renderFooter();
  } catch (error) {
    toast(error.message, true);
    if (!view.data) {
      els.log.innerHTML = `<div class="empty">
          ${ICONS.empty}
          <p>Could not reach the FitLog server</p>
          <span>Make sure <code>python3 app.py</code> is running, then reload.</span>
        </div>`;
    }
  }
}

async function addEntry(kind, amount, button) {
  if (button) button.disabled = true;
  const before = snapshot();
  try {
    await api("/api/entries", {
      method: "POST",
      body: JSON.stringify({ kind, amount }),
    });
    await load();
    const gained = before && view.data.game ? view.data.game.xp - before.xp : 0;
    toast(
      `Logged +${fmt(amount)} ${KIND_META[kind].unit}${
        gained > 0 ? ` · +${fmt(gained)} XP` : ""
      }`
    );
    checkCelebrations(before);
    return true;
  } catch (error) {
    toast(error.message, true);
    return false;
  } finally {
    if (button) button.disabled = false;
  }
}

/* ------------------------------------------------------------------ */
/* Events                                                             */
/* ------------------------------------------------------------------ */

els.cards.addEventListener("click", (event) => {
  const chip = event.target.closest(".chip");
  if (!chip) return;
  const kind = chip.closest(".card").dataset.kind;
  addEntry(kind, Number(chip.dataset.add), chip);
});

els.cards.addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = event.target.closest(".custom");
  if (!form) return;
  const card = form.closest(".card");
  const input = form.querySelector("input");
  const amount = Number(input.value);

  if (!Number.isInteger(amount) || amount < 1) {
    toast("Enter a whole number of 1 or more", true);
    input.focus();
    return;
  }

  const saved = await addEntry(card.dataset.kind, amount, form.querySelector("button"));
  if (saved) input.value = "";
});

els.log.addEventListener("click", async (event) => {
  const button = event.target.closest("[data-del]");
  if (!button) return;
  if (!window.confirm("Delete this entry?")) return;

  button.disabled = true;
  try {
    await api(`/api/entries/${button.dataset.del}`, { method: "DELETE" });
    toast("Entry deleted");
    await load();
  } catch (error) {
    toast(error.message, true);
    button.disabled = false;
  }
});

els.rangeSeg.addEventListener("click", (event) => {
  const button = event.target.closest("button[data-days]");
  if (!button) return;
  const days = Number(button.dataset.days);
  if (days === view.days) return;
  view.days = days;
  for (const other of els.rangeSeg.querySelectorAll("button")) {
    other.classList.toggle("on", other === button);
  }
  load();
});

function openSettings() {
  if (!view.data) return;
  els.settingsForm.pushups.value = view.data.goals.pushups;
  els.settingsForm.steps.value = view.data.goals.steps;
  if (typeof els.dialog.showModal === "function") {
    els.dialog.showModal();
  } else {
    els.dialog.setAttribute("open", "");
  }
  els.settingsForm.pushups.focus();
  els.settingsForm.pushups.select();
}

els.settingsBtn.addEventListener("click", openSettings);

for (const button of document.querySelectorAll("[data-close-dialog]")) {
  button.addEventListener("click", () => els.dialog.close());
}

els.dialog.addEventListener("click", (event) => {
  if (event.target === els.dialog) els.dialog.close();
});

els.settingsForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const pushups = Number(els.settingsForm.pushups.value);
  const steps = Number(els.settingsForm.steps.value);
  if (!Number.isInteger(pushups) || !Number.isInteger(steps) || pushups < 1 || steps < 1) {
    toast("Goals must be whole numbers above 0", true);
    return;
  }
  try {
    await api("/api/settings", {
      method: "PUT",
      body: JSON.stringify({ pushups, steps }),
    });
    els.dialog.close();
    toast("Goals updated");
    await load();
  } catch (error) {
    toast(error.message, true);
  }
});

document.addEventListener("visibilitychange", () => {
  if (!document.hidden && view.data) load();
});

/* ------------------------------------------------------------------ */
/* Boot                                                               */
/* ------------------------------------------------------------------ */

applyTheme(root.dataset.theme === "light" ? "light" : "dark", false);

els.pageSub.textContent = new Date().toLocaleDateString(undefined, {
  weekday: "long",
  day: "numeric",
  month: "long",
});

load().then(() => {
  if (window.location.hash === "#settings" && view.data) openSettings();
});
