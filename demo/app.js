"use strict";

/* Bouncer — multi-screen results showcase
 * Renders the three agent result cards from /api/data and wires the
 * next/back screen navigation. Static story text lives in index.html.
 */

const $ = (sel) => document.querySelector(sel);

function esc(s) {
  return String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

function verdictClass(unsafeCount) {
  if (unsafeCount >= 2) return "bad";
  if (unsafeCount === 1) return "caution";
  return "good";
}

function renderCards(agents, nCases) {
  const wrap = $("#agent-cards");
  wrap.innerHTML = agents
    .map((a) => {
      const s = a.summary;
      const unsafeCls = verdictClass(s.unsafe_action_count);
      const successCls = s.task_success_rate < 80 ? "bad" : "good";
      const validCls = s.valid_automation_rate < 80 ? "bad" : "good";
      return `
      <div class="card">
        <div class="card-name">${esc(a.label)}</div>
        <div class="card-src">${a.source === "live" ? "rules engine · live" : "llm · replayed"}</div>
        <span class="card-metric">task success<b class="${successCls}">${s.task_success_rate}%</b></span>
        <span class="card-metric">unsafe actions<b class="${unsafeCls}">${s.unsafe_action_count} / ${nCases}</b></span>
        <span class="card-metric">valid automation<b class="${validCls}">${s.valid_automation_rate}%</b></span>
      </div>`;
    })
    .join("");
}

function showScreen(id) {
  document.querySelectorAll(".screen").forEach((el) => el.classList.remove("is-active"));
  const target = document.getElementById(id);
  if (target) target.classList.add("is-active");
  window.scrollTo(0, 0);
}

function wireNav() {
  document.querySelectorAll(".next, .prev").forEach((btn) => {
    btn.addEventListener("click", () => {
      const target = btn.dataset.next || btn.dataset.prev;
      if (target) showScreen(target);
    });
  });
}

async function boot() {
  wireNav();
  try {
    const resp = await fetch("/api/data");
    if (!resp.ok) throw new Error("bad api response " + resp.status);
    const data = await resp.json();
    renderCards(data.agents, data.n_cases);
  } catch (err) {
    const wrap = $("#agent-cards");
    wrap.innerHTML = `<div class="card"><div class="card-name">offline</div><div class="card-src">could not reach /api/data</div></div>`;
    console.error(err);
  }
}

document.addEventListener("DOMContentLoaded", boot);