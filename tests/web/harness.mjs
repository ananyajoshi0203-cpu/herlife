// Loads web/index.html's app script into Node with a minimal DOM, so render paths and pure
// logic can be tested without a browser. Every render or click error is collected, not printed.
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

const PAGE = fileURLToPath(new URL("../../web/index.html", import.meta.url));

function element() {
  const noop = () => {};
  return {
    dataset: {}, style: { setProperty: noop, getPropertyValue: () => "0" },
    classList: { toggle: noop, add: noop, remove: noop, contains: () => false },
    innerHTML: "", textContent: "", value: "", scrollTop: 0, clientWidth: 300, clientHeight: 300,
    querySelector: () => null, querySelectorAll: () => [], addEventListener: noop, removeEventListener: noop,
    appendChild: (x) => x, remove: noop, setAttribute: noop, getAttribute: () => null, hasAttribute: () => false,
    matches: () => true, closest: () => null, focus: noop, click: noop,
    getBoundingClientRect: () => ({ left: 0, top: 0, width: 300, height: 300 }),
    getContext: () => new Proxy({}, { get: (t, k) => (k in t ? t[k] : () => ({ addColorStop: noop })), set: (t, k, v) => ((t[k] = v), true) }),
  };
}

export function loadApp() {
  const page = readFileSync(PAGE, "utf8");
  const seed = page.match(/<script id="seed" type="application\/json">([\s\S]*?)<\/script>/)[1];
  const script = page.match(/<script>\n"use strict";([\s\S]*?)<\/script>/)[1];
  const nodes = { seed: { ...element(), textContent: seed } };
  const listeners = {};
  const store = {};
  Object.assign(globalThis, {
    document: {
      getElementById: (id) => nodes[id] || (nodes[id] = element()), querySelector: () => element(), querySelectorAll: () => [],
      createElement: element, body: element(), documentElement: element(),
      addEventListener: (type, fn) => (listeners[type] ||= []).push(fn), removeEventListener: () => {},
    },
    localStorage: { getItem: (k) => store[k] ?? null, setItem: (k, v) => (store[k] = String(v)), removeItem: (k) => delete store[k] },
    matchMedia: () => ({ matches: false, addEventListener() {}, addListener() {} }),
    location: { search: "", hash: "", href: "http://test/", pathname: "/", reload() {} },
    history: { replaceState() {} },
    getComputedStyle: () => ({ getPropertyValue: () => "#fff" }),
    requestAnimationFrame: () => 0, cancelAnimationFrame: () => {},
    fetch: async () => ({ ok: false, status: 503, json: async () => ({}) }),
    innerWidth: 400, innerHeight: 800,
  });
  globalThis.window = globalThis;
  const exportsList = "state, ui, render, PERSONAS, phaseOf, startsFromTemperature, cycleSignal, stressLoad, nextMove, goalProgress, habitTime, phaseChipText, rowsByDay, newLifeGoal, learnings, resolveSwipe, SEED, SEED_DEMO, CYCLE_LEN, TODAY, addDays, applyDataSource";
  (0, eval)(`${script}\n;globalThis.__app = { ${exportsList.split(", ").map((n) => `get ${n}() { return ${n}; }`).join(", ")}, set state(v) { state = v; } };`);
  const app = globalThis.__app;
  const errors = [];
  const render = (label) => { try { app.render(); } catch (e) { errors.push(`${label}: ${e.message}`); } };
  const click = (dataset) => {
    const target = { ...element(), dataset, matches: (s) => s === "button" };
    for (const fn of listeners.click || []) {
      try { fn({ target: { closest: () => target }, preventDefault() {}, stopPropagation() {} }); }
      catch (e) { errors.push(`click ${JSON.stringify(dataset)}: ${e.message}`); }
    }
  };
  return { app, render, click, errors };
}
