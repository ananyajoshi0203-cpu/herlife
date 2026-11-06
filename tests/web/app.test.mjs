import { test } from "node:test";
import assert from "node:assert/strict";
import { loadApp } from "./harness.mjs";

const { app, render, click, errors } = loadApp();
const tick = (ms = 30) => new Promise((r) => setTimeout(r, ms));
const withRing = () => { app.state.connected = { oura: true, calendar: false }; app.state.checkins = {}; app.applyDataSource(); };

test("every persona renders every tab without errors", async () => {
  render("welcome");
  click({ go: "login" });
  render("login");
  for (const persona of Object.keys(app.PERSONAS)) {
    click({ persona });
    for (const step of ["about", "cycle", "privacy", "connect", "goals"]) { app.state.step = step; render(`${persona}:${step}`); }
    app.state.habits = (app.state.habitCandidates?.length ? app.state.habitCandidates : [{ id: "h1", title: "Screens down by 10:15 pm", cue: "When your 10 pm alarm goes off", why: "x" }]).slice(0, 3);
    app.state.step = "app";
    for (const tab of ["today", "habits", "log", "cycle", "record"]) { app.state.tab = tab; render(`${persona}:${tab}`); }
    app.ui.moodOpen = true; render(`${persona}:mood`); app.ui.moodOpen = false;
    app.ui.infoOpen = "energy"; render(`${persona}:info`); app.ui.infoOpen = null;
    await tick();
  }
  assert.deepEqual(errors, []);
});

test("phase boundaries match the backend's _phase_for", () => {
  assert.equal(app.phaseOf(1, 29), "menstrual");
  assert.equal(app.phaseOf(5, 29), "menstrual");
  assert.equal(app.phaseOf(6, 29), "follicular");
  assert.equal(app.phaseOf(15, 29), "ovulatory");
  assert.equal(app.phaseOf(17, 29), "luteal");
});

test("temperature alone recovers the demo persona's logged period starts", () => {
  assert.deepEqual(app.startsFromTemperature(app.SEED_DEMO), ["2026-08-29", "2026-09-27", "2026-10-26"]);
});

test("cycle signal never raises menopause under 40, and flags 90 days without a period", () => {
  const withPeriods = (age, gaps, sinceLast) => {
    let day = app.addDays(app.TODAY, -(gaps.reduce((a, b) => a + b, 0) + sinceLast));
    const periods = [day];
    for (const g of gaps) { day = app.addDays(day, g); periods.push(day); }
    app.state.profile.age = String(age);
    app.state.periods = periods;
    return app.cycleSignal();
  };
  const young = withPeriods(24, [29, 30, 41, 52], 6);
  assert.equal(young.level, "watch");
  assert.doesNotMatch(`${young.title} ${young.body} ${young.ask}`, /menopaus/i);
  assert.match(withPeriods(48, [27, 36, 23, 64], 6).title, /menopause transition/);
  assert.equal(withPeriods(35, [28, 28], 95).level, "flag");
});

test("stress load is 50 at her own average and estimated without a ring", () => {
  withRing();
  const base = app.SEED.slice(-30).reduce((a, r) => a + r.stress, 0) / 30;
  assert.equal(app.stressLoad({ stress: base, day: app.TODAY }), 50);
  assert.ok(app.stressLoad({ stress: base * 1.5, day: app.TODAY }) > 70);
  app.state.connected.calendar = false;
  app.state.checkins = { [app.TODAY]: { sleepH: 5.5, energy: 2, stress: 5 } };
  assert.ok(app.stressLoad({ self: true, day: app.TODAY }) >= 90);
});

test("habit cue times are parsed or placed by part of day", () => {
  assert.equal(app.habitTime({ title: "x", cue: "at 9:30 pm" }), 21 * 60 + 30);
  assert.equal(app.habitTime({ title: "Protein at breakfast", cue: "With your first coffee" }), 7 * 60 + 30);
  assert.equal(app.habitTime({ title: "Box breathing", cue: "Between meetings" }), null);
});

test("next move shrinks a habit she keeps missing and levels up when on track", () => {
  const goal = app.newLifeGoal("Sleep better", app.addDays(app.TODAY, -14));
  const habit = { id: "hx", title: "Screens down by 10:15 pm", cue: "Before bed", why: "" };
  app.state.habits = [habit];
  const prog = (rate, flag) => ({ total: 14, consistent: Math.round(14 * rate), flag, habits: [habit] });
  app.state.checks = {};
  assert.equal(app.nextMove(goal, prog(0.2, "steady")).kind, "easier");
  assert.equal(app.nextMove(goal, prog(0.8, "on")).kind, "levelup");
  assert.equal(app.nextMove(goal, prog(0.7, "off")).kind, "swap");
  assert.equal(app.nextMove(goal, { total: 3, consistent: 3, flag: "on", habits: [habit] }).kind, "wait");
});
